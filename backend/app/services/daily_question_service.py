"""Persistence and read model for the daily personalized question."""

from datetime import date

from sqlalchemy.exc import IntegrityError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.course import Course
from app.models.daily_question import DailyQuestion
from app.models.question import Question
from app.schemas.daily_question import DailyQuestionResponse, DailyQuestionUpsert


class DailyQuestionService:
    async def list_course_ids(self, db: AsyncSession) -> set[int]:
        result = await db.execute(select(Course.course_id).order_by(Course.course_id))
        return {int(course_id) for course_id in result.scalars().all()}

    async def get_for_student(
        self,
        stu_id: int,
        target_date: date,
        db: AsyncSession,
        course_id: int | None = None,
    ) -> DailyQuestionResponse | None:
        filters = [
            DailyQuestion.stu_id == stu_id,
            DailyQuestion.target_date == target_date,
        ]
        if course_id is not None:
            filters.append(DailyQuestion.course_id == course_id)

        result = await db.execute(
            select(DailyQuestion, Course, Question)
            .join(Course, Course.course_id == DailyQuestion.course_id)
            .join(Question, Question.question_id == DailyQuestion.question_id)
            .where(*filters)
            .order_by(DailyQuestion.course_id)
        )
        row = result.first()
        if row is None:
            return None
        daily, course, question = row
        return self._to_response(daily, course, question)

    async def list_for_student(
        self,
        stu_id: int,
        target_date: date,
        db: AsyncSession,
    ) -> list[DailyQuestionResponse]:
        result = await db.execute(
            select(DailyQuestion, Course, Question)
            .join(Course, Course.course_id == DailyQuestion.course_id)
            .join(Question, Question.question_id == DailyQuestion.question_id)
            .where(
                DailyQuestion.stu_id == stu_id,
                DailyQuestion.target_date == target_date,
            )
            .order_by(DailyQuestion.course_id)
        )
        return [
            self._to_response(daily, course, question)
            for daily, course, question in result.all()
        ]

    async def upsert(
        self,
        data: DailyQuestionUpsert,
        db: AsyncSession,
    ) -> DailyQuestionResponse:
        question_result = await db.execute(
            select(Question).where(
                Question.question_id == data.question_id,
                Question.course_id == data.course_id,
            )
        )
        question = question_result.scalar_one_or_none()
        if question is None:
            raise ValueError("daily question does not belong to the requested course")

        result = await db.execute(
            select(DailyQuestion).where(
                DailyQuestion.stu_id == data.stu_id,
                DailyQuestion.course_id == data.course_id,
                DailyQuestion.target_date == data.target_date,
            )
        )
        daily = result.scalar_one_or_none()
        if daily is None:
            daily = DailyQuestion(
                stu_id=data.stu_id,
                course_id=data.course_id,
                target_date=data.target_date,
            )
            db.add(daily)
        elif daily.question_id != data.question_id:
            daily.completed_at = None

        daily.question_id = data.question_id
        daily.kg_node_name = data.kg_node_name or question.kg_node_name
        daily.recommendation_status = data.recommendation_status
        daily.recommendation_reason = data.recommendation_reason
        daily.rrf_score = data.rrf_score

        try:
            await db.commit()
        except IntegrityError:
            # The scheduler and a student's first page load can race at 04:30.
            # Keep the first persisted question instead of surfacing a 500.
            await db.rollback()
        response = await self.get_for_student(
            data.stu_id,
            data.target_date,
            db,
            course_id=data.course_id,
        )
        if response is None:
            raise RuntimeError("daily question could not be loaded after upsert")
        return response

    @staticmethod
    def _to_response(daily: DailyQuestion, course: Course, question: Question) -> DailyQuestionResponse:
        return DailyQuestionResponse(
            daily_question_id=int(daily.daily_question_id),
            target_date=daily.target_date,
            completed=daily.completed_at is not None,
            completed_at=daily.completed_at,
            course_id=int(course.course_id),
            course_name=course.course_name,
            question_id=int(question.question_id),
            question_description=question.question_description,
            question_options=question.question_options,
            question_type=question.question_type,
            question_difficulty=int(question.question_difficulty),
            kg_node_name=daily.kg_node_name or question.kg_node_name,
            recommendation_status=daily.recommendation_status,
            recommendation_reason=daily.recommendation_reason,
            rrf_score=daily.rrf_score,
        )
