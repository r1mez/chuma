"""Assignment workflow built on the existing question bank and recommenders."""

from __future__ import annotations

import asyncio
import logging
from collections import defaultdict
from datetime import datetime, timezone
from typing import Any

import httpx
from sqlalchemy import and_, case, distinct, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.assignment import Assignment, AssignmentQuestion, AssignmentSubmission
from app.models.classes import Class as ClassModel
from app.models.course import Course
from app.models.exercise_record import ExerciseRecord
from app.models.question import Question
from app.models.teacher_relation import TeacherClass, TeacherCourse
from app.models.user import Student
from app.schemas.assignment import (
    AssignmentCreate,
    AssignmentQuestionView,
    AssignmentResultStudent,
)
from app.schemas.practice import QuestionResponse

logger = logging.getLogger(__name__)
PASS_SCORE = 6.0


class AssignmentService:
    async def teacher_has_access(
        self, tea_id: int, class_id: int, course_id: int, db: AsyncSession
    ) -> bool:
        class_result = await db.execute(
            select(TeacherClass.class_id).where(
                TeacherClass.tea_id == tea_id,
                TeacherClass.class_id == class_id,
            )
        )
        if class_result.first() is None:
            return False
        course_result = await db.execute(
            select(TeacherCourse.course_id).where(
                TeacherCourse.tea_id == tea_id,
                TeacherCourse.course_id == course_id,
            )
        )
        return course_result.first() is not None

    async def create(
        self, tea_id: int, data: AssignmentCreate, db: AsyncSession
    ) -> dict[str, Any]:
        if not await self.teacher_has_access(tea_id, data.class_id, data.course_id, db):
            raise ValueError("教师没有该班级或学科的管理权限")

        question_ids = [item.question_id for item in data.questions]
        if len(set(question_ids)) != len(question_ids):
            raise ValueError("作业题目不能重复")

        question_result = await db.execute(
            select(Question).where(
                Question.course_id == data.course_id,
                Question.question_id.in_(question_ids),
            )
        )
        questions = {int(question.question_id): question for question in question_result.scalars().all()}
        missing = [question_id for question_id in question_ids if question_id not in questions]
        if missing:
            raise ValueError(f"以下题目不存在或不属于该学科：{missing}")

        assignment = Assignment(
            title=data.title.strip(),
            description=data.description.strip() if data.description else None,
            tea_id=tea_id,
            class_id=data.class_id,
            course_id=data.course_id,
            due_at=_as_naive_datetime(data.due_at),
            status="published",
        )
        db.add(assignment)
        await db.flush()

        for index, item in enumerate(data.questions):
            db.add(
                AssignmentQuestion(
                    assignment_id=assignment.assignment_id,
                    question_id=item.question_id,
                    sort_order=item.sort_order if item.sort_order is not None else index,
                    priority_score=item.priority_score,
                    recommendation_source=item.recommendation_source,
                    recommendation_reason=item.recommendation_reason,
                )
            )

        await db.commit()
        await db.refresh(assignment)
        return await self.get_teacher_detail(tea_id, int(assignment.assignment_id), db)

    async def list_for_teacher(
        self,
        tea_id: int,
        db: AsyncSession,
        class_id: int | None = None,
        course_id: int | None = None,
    ) -> list[dict[str, Any]]:
        query = (
            select(
                Assignment,
                ClassModel.class_name,
                Course.course_name,
                func.count(AssignmentQuestion.question_id),
            )
            .join(ClassModel, ClassModel.class_id == Assignment.class_id)
            .join(Course, Course.course_id == Assignment.course_id)
            .outerjoin(
                AssignmentQuestion,
                AssignmentQuestion.assignment_id == Assignment.assignment_id,
            )
            .where(Assignment.tea_id == tea_id)
            .group_by(Assignment.assignment_id, ClassModel.class_name, Course.course_name)
            .order_by(Assignment.created_at.desc(), Assignment.assignment_id.desc())
        )
        if class_id is not None:
            query = query.where(Assignment.class_id == class_id)
        if course_id is not None:
            query = query.where(Assignment.course_id == course_id)

        result = await db.execute(query)
        return [
            self._assignment_item(assignment, class_name, course_name, int(question_count), 0)
            for assignment, class_name, course_name, question_count in result.all()
        ]

    async def list_for_student(self, stu_id: int, db: AsyncSession) -> list[dict[str, Any]]:
        student_result = await db.execute(select(Student.class_id).where(Student.stu_id == stu_id))
        class_id = student_result.scalar_one_or_none()
        if class_id is None:
            return []

        query = (
            select(
                Assignment,
                ClassModel.class_name,
                Course.course_name,
                func.count(distinct(AssignmentQuestion.question_id)),
            )
            .join(ClassModel, ClassModel.class_id == Assignment.class_id)
            .join(Course, Course.course_id == Assignment.course_id)
            .outerjoin(
                AssignmentQuestion,
                AssignmentQuestion.assignment_id == Assignment.assignment_id,
            )
            .where(Assignment.class_id == class_id, Assignment.status == "published")
            .group_by(Assignment.assignment_id, ClassModel.class_name, Course.course_name)
            .order_by(Assignment.created_at.desc(), Assignment.assignment_id.desc())
        )
        result = await db.execute(query)
        rows = result.all()
        if not rows:
            return []

        assignment_ids = [int(row[0].assignment_id) for row in rows]
        submitted_result = await db.execute(
            select(AssignmentSubmission.assignment_id, func.count(AssignmentSubmission.submission_id))
            .where(
                AssignmentSubmission.stu_id == stu_id,
                AssignmentSubmission.assignment_id.in_(assignment_ids),
            )
            .group_by(AssignmentSubmission.assignment_id)
        )
        submitted_counts = {int(assignment_id): int(count) for assignment_id, count in submitted_result.all()}
        return [
            self._assignment_item(
                assignment,
                class_name,
                course_name,
                int(question_count),
                submitted_counts.get(int(assignment.assignment_id), 0),
            )
            for assignment, class_name, course_name, question_count in rows
        ]

    async def get_teacher_detail(
        self, tea_id: int, assignment_id: int, db: AsyncSession
    ) -> dict[str, Any]:
        assignment, class_name, course_name, question_count = await self._get_assignment_context(
            assignment_id, db
        )
        if assignment is None or assignment.tea_id != tea_id:
            raise ValueError("作业不存在或无权访问")

        questions = await self._get_assignment_questions(assignment_id, db, include_answer=True)
        item = self._assignment_item(assignment, class_name, course_name, question_count, 0)
        return {**item, "questions": questions, "submitted_question_ids": [], "can_submit": False}

    async def get_student_detail(
        self, stu_id: int, assignment_id: int, db: AsyncSession
    ) -> dict[str, Any]:
        student_result = await db.execute(select(Student.class_id).where(Student.stu_id == stu_id))
        student_class_id = student_result.scalar_one_or_none()
        assignment, class_name, course_name, question_count = await self._get_assignment_context(
            assignment_id, db
        )
        if (
            assignment is None
            or assignment.status != "published"
            or student_class_id != assignment.class_id
        ):
            raise ValueError("作业不存在、未发布或不属于当前学生班级")

        questions = await self._get_assignment_questions(assignment_id, db, include_answer=False)
        submitted_result = await db.execute(
            select(AssignmentSubmission.question_id).where(
                AssignmentSubmission.assignment_id == assignment_id,
                AssignmentSubmission.stu_id == stu_id,
            )
        )
        submitted_ids = [int(question_id) for question_id in submitted_result.scalars().all()]
        due_at = _as_naive_datetime(assignment.due_at)
        can_submit = due_at is None or due_at >= datetime.now(timezone.utc).replace(tzinfo=None)
        item = self._assignment_item(
            assignment,
            class_name,
            course_name,
            question_count,
            len(submitted_ids),
        )
        return {
            **item,
            "questions": questions,
            "submitted_question_ids": submitted_ids,
            "can_submit": can_submit,
        }

    async def validate_student_question(
        self, stu_id: int, assignment_id: int, question_id: int, db: AsyncSession
    ) -> Assignment:
        query = (
            select(Assignment)
            .join(
                AssignmentQuestion,
                AssignmentQuestion.assignment_id == Assignment.assignment_id,
            )
            .join(Student, Student.class_id == Assignment.class_id)
            .where(
                Assignment.assignment_id == assignment_id,
                AssignmentQuestion.question_id == question_id,
                Student.stu_id == stu_id,
                Assignment.status == "published",
            )
        )
        assignment = (await db.execute(query)).scalar_one_or_none()
        if assignment is None:
            raise ValueError("该题目不属于当前学生可提交的作业")
        due_at = _as_naive_datetime(assignment.due_at)
        if due_at is not None and due_at < datetime.now(timezone.utc).replace(tzinfo=None):
            raise ValueError("作业已截止，不能继续提交")
        return assignment

    async def upsert_submission(
        self,
        assignment_id: int,
        stu_id: int,
        question_id: int,
        exercise_record_id: int,
        do_score: float | None,
        do_is_true: bool | None,
        db: AsyncSession,
    ) -> None:
        result = await db.execute(
            select(AssignmentSubmission).where(
                AssignmentSubmission.assignment_id == assignment_id,
                AssignmentSubmission.question_id == question_id,
                AssignmentSubmission.stu_id == stu_id,
            )
        )
        submission = result.scalar_one_or_none()
        if submission is None:
            submission = AssignmentSubmission(
                assignment_id=assignment_id,
                question_id=question_id,
                stu_id=stu_id,
            )
            db.add(submission)
        submission.exercise_record_id = exercise_record_id
        submission.do_score = do_score
        submission.do_is_true = do_is_true
        submission.submitted_at = datetime.now(timezone.utc).replace(tzinfo=None)
        await db.commit()

    async def get_results(
        self, tea_id: int, assignment_id: int, db: AsyncSession
    ) -> dict[str, Any]:
        assignment, class_name, course_name, question_count = await self._get_assignment_context(
            assignment_id, db
        )
        if assignment is None or assignment.tea_id != tea_id:
            raise ValueError("作业不存在或无权访问")

        students_result = await db.execute(
            select(Student.stu_id, Student.stu_name)
            .where(Student.class_id == assignment.class_id)
            .order_by(Student.stu_id)
        )
        students = students_result.all()
        submissions_result = await db.execute(
            select(AssignmentSubmission).where(AssignmentSubmission.assignment_id == assignment_id)
        )
        grouped: dict[int, list[AssignmentSubmission]] = defaultdict(list)
        for submission in submissions_result.scalars().all():
            grouped[int(submission.stu_id)].append(submission)

        result_students: list[AssignmentResultStudent] = []
        for stu_id, stu_name in students:
            submissions = grouped.get(int(stu_id), [])
            values = [_normalised_score(item.do_score, item.do_is_true) for item in submissions]
            known_values = [value for value in values if value is not None]
            correct_values = [
                1.0 if item.do_is_true is True else 0.0 if item.do_is_true is False else (item.do_score or 0) / 10.0
                for item in submissions
            ]
            result_students.append(
                AssignmentResultStudent(
                    stu_id=int(stu_id),
                    stu_name=stu_name,
                    submitted_count=len(submissions),
                    total_questions=question_count,
                    completion_rate=round(len(submissions) / question_count * 100, 1) if question_count else 0,
                    average_score=round(sum(known_values) / len(known_values), 1) if known_values else None,
                    accuracy=round(sum(correct_values) / len(correct_values) * 100, 1) if correct_values else None,
                    latest_submitted_at=max((item.submitted_at for item in submissions), default=None),
                )
            )

        completed = sum(1 for item in result_students if item.submitted_count >= question_count)
        scored = [item.average_score for item in result_students if item.average_score is not None]
        summary = {
            "student_count": len(result_students),
            "submitted_student_count": sum(1 for item in result_students if item.submitted_count > 0),
            "completed_student_count": completed,
            "question_count": question_count,
            "completion_rate": round(completed / len(result_students) * 100, 1) if result_students else 0,
            "average_score": round(sum(scored) / len(scored), 1) if scored else None,
        }
        item = self._assignment_item(assignment, class_name, course_name, question_count, 0)
        return {"assignment": item, "summary": summary, "students": result_students}

    async def get_recommendations(
        self,
        tea_id: int,
        class_id: int,
        course_id: int,
        db: AsyncSession,
        limit: int = 20,
    ) -> list[dict[str, Any]]:
        if not await self.teacher_has_access(tea_id, class_id, course_id, db):
            raise ValueError("教师没有该班级或学科的管理权限")

        student_ids = list(
            (await db.execute(select(Student.stu_id).where(Student.class_id == class_id))).scalars().all()
        )
        questions_result = await db.execute(
            select(Question).where(Question.course_id == course_id).order_by(Question.question_id)
        )
        questions = list(questions_result.scalars().all())
        if not questions:
            return []

        stats: dict[int, dict[str, int]] = {
            int(question.question_id): {"attempted_students": 0, "wrong_count": 0}
            for question in questions
        }
        if student_ids:
            wrong_condition = or_(
                ExerciseRecord.do_isTrue.is_(False),
                ExerciseRecord.do_score < PASS_SCORE,
            )
            stats_query = (
                select(
                    ExerciseRecord.question_id,
                    func.count(distinct(ExerciseRecord.stu_id)),
                    func.sum(case((wrong_condition, 1), else_=0)),
                )
                .where(
                    ExerciseRecord.course_id == course_id,
                    ExerciseRecord.stu_id.in_(student_ids),
                )
                .group_by(ExerciseRecord.question_id)
            )
            for question_id, attempted, wrong_count in (await db.execute(stats_query)).all():
                stats[int(question_id)] = {
                    "attempted_students": int(attempted or 0),
                    "wrong_count": int(wrong_count or 0),
                }

        weak_by_node: dict[str, int] = defaultdict(int)
        for question in questions:
            node = (question.kg_node_name or "").strip()
            if node:
                weak_by_node[node] += stats[int(question.question_id)]["wrong_count"]
        max_weak = max(weak_by_node.values(), default=1)

        # Keep the teacher-facing request bounded. The class-level SQL fallback
        # remains available even when the AI service is unavailable.
        ai_student_ids = student_ids[:10]
        ai_recommendations = await self._collect_ai_recommendations(ai_student_ids, course_id)
        ranked: list[dict[str, Any]] = []
        class_size = max(1, len(student_ids))
        for question in questions:
            question_id = int(question.question_id)
            item_stats = stats[question_id]
            node_weakness = weak_by_node.get((question.kg_node_name or "").strip(), 0)
            weakness_score = node_weakness / max_weak
            unseen_score = 1 - item_stats["attempted_students"] / class_size
            difficulty_score = 1 - abs(int(question.question_difficulty) - 3) / 4
            ai_items = ai_recommendations.get(question_id, [])
            ai_votes = len(ai_items)
            ai_rrf_score = sum(float(item.get("rrf_score") or 0) for item in ai_items)
            # The AI service has already applied weighted RRF. Normalise the
            # returned score so it can be fused with class-level signals.
            ai_score = min(1.0, ai_rrf_score * 60 / max(1, len(ai_student_ids)))
            priority = weakness_score * 0.45 + unseen_score * 0.25 + difficulty_score * 0.10 + ai_score * 0.20
            if ai_votes:
                source = "tgnn_rrf"
                reason = f"DyGKT/RRF 为 {ai_votes} 名学生推荐；班级薄弱知识点为“{question.kg_node_name or '未标注'}”。"
            else:
                source = "class_mastery"
                reason = f"班级薄弱点/未做比例推荐；知识点“{question.kg_node_name or '未标注'}”错题数 {node_weakness}。"
            data = QuestionResponse.model_validate(question).model_dump()
            ranked.append(
                {
                    **data,
                    "attempted_students": item_stats["attempted_students"],
                    "wrong_count": item_stats["wrong_count"],
                    "recommendation_rrf_score": round(ai_rrf_score, 8) if ai_rrf_score else None,
                    "priority_score": round(priority, 6),
                    "recommendation_source": source,
                    "recommendation_reason": reason,
                }
            )

        ranked.sort(key=lambda item: (-item["priority_score"], item["question_id"]))
        return ranked[: max(1, min(limit, 100))]

    async def _collect_ai_recommendations(
        self, student_ids: list[int], course_id: int
    ) -> dict[int, list[dict[str, Any]]]:
        if not student_ids:
            return {}
        result: dict[int, list[dict[str, Any]]] = defaultdict(list)
        semaphore = asyncio.Semaphore(5)

        async with httpx.AsyncClient(timeout=8.0) as client:
            async def fetch(student_id: int) -> None:
                async with semaphore:
                    try:
                        response = await client.post(
                            f"{settings.AI_SERVICE_URL}/gnn/recommend",
                            headers={"X-Service-Token": settings.AI_SERVICE_TOKEN},
                            json={"student_id": student_id, "course_id": course_id, "top_k": 5},
                        )
                        if response.status_code >= 400:
                            return
                        payload = response.json()
                        for item in payload.get("recommendations", []):
                            question_id = item.get("question_id")
                            if question_id is not None:
                                result[int(question_id)].append(item)
                    except Exception:
                        logger.info("AI assignment recommendation unavailable for student %s", student_id)

            await asyncio.gather(*(fetch(student_id) for student_id in student_ids))
        return result

    async def _get_assignment_context(self, assignment_id: int, db: AsyncSession):
        query = (
            select(Assignment, ClassModel.class_name, Course.course_name, func.count(AssignmentQuestion.question_id))
            .join(ClassModel, ClassModel.class_id == Assignment.class_id)
            .join(Course, Course.course_id == Assignment.course_id)
            .outerjoin(AssignmentQuestion, AssignmentQuestion.assignment_id == Assignment.assignment_id)
            .where(Assignment.assignment_id == assignment_id)
            .group_by(Assignment.assignment_id, ClassModel.class_name, Course.course_name)
        )
        row = (await db.execute(query)).one_or_none()
        return row if row else (None, None, None, 0)

    async def _get_assignment_questions(
        self, assignment_id: int, db: AsyncSession, include_answer: bool
    ) -> list[dict[str, Any]]:
        query = (
            select(AssignmentQuestion, Question)
            .join(Question, Question.question_id == AssignmentQuestion.question_id)
            .where(AssignmentQuestion.assignment_id == assignment_id)
            .order_by(AssignmentQuestion.sort_order, AssignmentQuestion.question_id)
        )
        rows = (await db.execute(query)).all()
        result: list[dict[str, Any]] = []
        for selection, question in rows:
            data = QuestionResponse.model_validate(question).model_dump()
            if not include_answer:
                data.pop("question_answer", None)
                data.pop("question_explanation", None)
            result.append(
                {
                    **data,
                    "sort_order": selection.sort_order,
                    "priority_score": selection.priority_score,
                    "recommendation_source": selection.recommendation_source,
                    "recommendation_reason": selection.recommendation_reason,
                }
            )
        return result

    @staticmethod
    def _assignment_item(
        assignment: Assignment,
        class_name: str | None,
        course_name: str | None,
        question_count: int,
        submitted_count: int,
    ) -> dict[str, Any]:
        return {
            "assignment_id": int(assignment.assignment_id),
            "title": assignment.title,
            "description": assignment.description,
            "class_id": int(assignment.class_id),
            "class_name": class_name,
            "course_id": int(assignment.course_id),
            "course_name": course_name,
            "due_at": assignment.due_at,
            "status": assignment.status,
            "question_count": question_count,
            "submitted_count": submitted_count,
            "created_at": assignment.created_at,
        }


def _as_naive_datetime(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    return value.replace(tzinfo=None) if value.tzinfo else value


def _normalised_score(score: float | None, is_true: bool | None) -> float | None:
    if is_true is not None:
        return 100.0 if is_true else 0.0
    return float(score) * 10 if score is not None else None
