"""Practice 业务逻辑层 — 题库与做题记录"""
from typing import Optional
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.question import Question
from app.models.exercise_record import ExerciseRecord
from app.models.course import Course
from app.schemas.practice import (
    QuestionCreate,
    QuestionResponse,
    ExerciseRecordCreate,
    ExerciseRecordResponse,
    ExerciseRecordListResponse,
)


class PracticeService:
    async def create_question(self, data: QuestionCreate, db: AsyncSession) -> QuestionResponse:
        question = Question(
            question_description=data.question_description,
            question_answer=data.question_answer,
            question_options=data.question_options,
            question_type=data.question_type,
            question_difficulty=data.question_difficulty,
            question_explanation=data.question_explanation,
            course_id=data.course_id,
            kg_node_name=data.kg_node_name,
        )
        db.add(question)
        await db.commit()
        await db.refresh(question)
        return QuestionResponse.model_validate(question)

    async def list_questions(
        self,
        db: AsyncSession,
        course_id: Optional[int] = None,
        kg_node_name: Optional[str] = None,
        difficulty: Optional[int] = None,
    ) -> list[QuestionResponse]:
        query = select(Question)
        if course_id is not None:
            query = query.where(Question.course_id == course_id)
        if kg_node_name is not None:
            query = query.where(Question.kg_node_name == kg_node_name)
        if difficulty is not None:
            query = query.where(Question.question_difficulty == difficulty)
        result = await db.execute(query.order_by(Question.question_id))
        questions = result.scalars().all()
        return [QuestionResponse.model_validate(q) for q in questions]

    async def get_question_by_id(self, question_id: int, db: AsyncSession) -> Optional[QuestionResponse]:
        result = await db.execute(select(Question).where(Question.question_id == question_id))
        question = result.scalar_one_or_none()
        if question is None:
            return None
        return QuestionResponse.model_validate(question)

    async def submit_exercise(
        self, stu_id: int, data: ExerciseRecordCreate, db: AsyncSession
    ) -> ExerciseRecordResponse:
        """提交答案并存入 exercise_records，根据题目类型处理 do_score / do_isTrue。

        规则：
        - single_choice / multiple_choice / T_or_F：从数据库查询题目的 question_answer，
          比较 question_answer == do_stu_answer，结果存入 do_isTrue，do_score 设为 None。
        - Fill_blanks / Q_A：do_score 设为 10.0（满分），do_isTrue 设为 None。
        """
        # 从数据库查询题目信息，获取正确答案
        question_result = await db.execute(
            select(Question).where(Question.question_id == data.question_id)
        )
        question = question_result.scalar_one_or_none()
        if question is None:
            raise ValueError(f"题目不存在: question_id={data.question_id}")

        objective_types = {"single_choice", "multiple_choice", "T_or_F", "choice", "true_false"}
        subjective_types = {"Fill_blanks", "Q_A", "fill_blanks", "q_a"}

        do_isTrue = None
        do_score = None

        if data.question_type in objective_types:
            # 客观题：比较学生答案与正确答案
            do_isTrue = data.do_stu_answer.strip() == question.question_answer.strip()
            do_score = None
        elif data.question_type in subjective_types:
            # 主观题：给满分，不判定对错
            do_isTrue = None
            do_score = 10.0

        # 检查是否已存在相同 question_id + stu_id 的记录
        existing_result = await db.execute(
            select(ExerciseRecord).where(
                ExerciseRecord.question_id == data.question_id,
                ExerciseRecord.stu_id == stu_id,
            )
        )
        existing_record = existing_result.scalar_one_or_none()

        if existing_record:
            # 已存在则更新作答内容和判定结果
            existing_record.do_stu_answer = data.do_stu_answer
            existing_record.do_isTrue = do_isTrue
            existing_record.do_score = do_score
            await db.commit()
            await db.refresh(existing_record)
            return ExerciseRecordResponse.model_validate(existing_record)
        else:
            # 不存在则创建新记录
            record = ExerciseRecord(
                question_id=data.question_id,
                stu_id=stu_id,
                course_id=data.course_id,
                kg_node_name=data.kg_node_name,
                question_type=data.question_type,
                question_difficulty=data.question_difficulty,
                do_stu_answer=data.do_stu_answer,
                do_score=do_score,
                do_isTrue=do_isTrue,
            )
            db.add(record)
            await db.commit()
            await db.refresh(record)
            return ExerciseRecordResponse.model_validate(record)

    async def get_student_exercise_records(
        self, stu_id: int, db: AsyncSession
    ) -> list[ExerciseRecordListResponse]:
        """获取当前学生的所有做题记录（含题目题干和学科名称），按时间倒序"""
        result = await db.execute(
            select(ExerciseRecord, Question.question_description, Course.course_name)
            .join(Question, ExerciseRecord.question_id == Question.question_id)
            .join(Course, ExerciseRecord.course_id == Course.course_id, isouter=True)
            .where(ExerciseRecord.stu_id == stu_id)
            .order_by(ExerciseRecord.created_at.desc())
        )
        rows = result.all()
        records = []
        for record, question_description, course_name in rows:
            records.append(
                ExerciseRecordListResponse(
                    do_id=record.do_id,
                    question_id=record.question_id,
                    question_description=question_description,
                    course_name=course_name,
                    question_type=record.question_type,
                    question_difficulty=record.question_difficulty,
                    do_stu_answer=record.do_stu_answer,
                    do_score=record.do_score,
                    do_isTrue=record.do_isTrue,
                    kg_node_name=record.kg_node_name,
                    created_at=record.created_at,
                )
            )
        return records

    async def get_student_exercise_records_by_course(
        self, stu_id: int, course_id: int, db: AsyncSession
    ) -> list[ExerciseRecordListResponse]:
        """获取当前学生在指定学科下的做题记录"""
        result = await db.execute(
            select(ExerciseRecord, Question.question_description, Course.course_name)
            .join(Question, ExerciseRecord.question_id == Question.question_id)
            .join(Course, ExerciseRecord.course_id == Course.course_id, isouter=True)
            .where(
                and_(
                    ExerciseRecord.stu_id == stu_id,
                    ExerciseRecord.course_id == course_id,
                )
            )
            .order_by(ExerciseRecord.created_at.desc())
        )
        rows = result.all()
        records = []
        for record, question_description, course_name in rows:
            records.append(
                ExerciseRecordListResponse(
                    do_id=record.do_id,
                    question_id=record.question_id,
                    question_description=question_description,
                    course_name=course_name,
                    question_type=record.question_type,
                    question_difficulty=record.question_difficulty,
                    do_stu_answer=record.do_stu_answer,
                    do_score=record.do_score,
                    do_isTrue=record.do_isTrue,
                    kg_node_name=record.kg_node_name,
                    created_at=record.created_at,
                )
            )
        return records

    async def get_student_wrong_records_by_course(
        self, stu_id: int, course_id: int, db: AsyncSession
    ) -> list[ExerciseRecordListResponse]:
        """获取当前学生在指定学科下的错题记录（仅 do_isTrue=False）"""
        result = await db.execute(
            select(ExerciseRecord, Question.question_description, Course.course_name)
            .join(Question, ExerciseRecord.question_id == Question.question_id)
            .join(Course, ExerciseRecord.course_id == Course.course_id, isouter=True)
            .where(
                and_(
                    ExerciseRecord.stu_id == stu_id,
                    ExerciseRecord.course_id == course_id,
                    ExerciseRecord.do_isTrue == False,  # noqa: E712
                )
            )
            .order_by(ExerciseRecord.created_at.desc())
        )
        rows = result.all()
        records = []
        for record, question_description, course_name in rows:
            records.append(
                ExerciseRecordListResponse(
                    do_id=record.do_id,
                    question_id=record.question_id,
                    question_description=question_description,
                    course_name=course_name,
                    question_type=record.question_type,
                    question_difficulty=record.question_difficulty,
                    do_stu_answer=record.do_stu_answer,
                    do_score=record.do_score,
                    do_isTrue=record.do_isTrue,
                    kg_node_name=record.kg_node_name,
                    created_at=record.created_at,
                )
            )
        return records

    async def get_student_wrong_records_grouped(
        self, stu_id: int, db: AsyncSession
    ) -> dict:
        """获取当前学生所有错题，按 course_id 分组。

        返回格式：{ course_id: { course_name, records: [...] } }
        """
        result = await db.execute(
            select(ExerciseRecord, Question.question_description, Course.course_name)
            .join(Question, ExerciseRecord.question_id == Question.question_id)
            .join(Course, ExerciseRecord.course_id == Course.course_id, isouter=True)
            .where(
                and_(
                    ExerciseRecord.stu_id == stu_id,
                    ExerciseRecord.do_isTrue == False,  # noqa: E712
                )
            )
            .order_by(ExerciseRecord.created_at.desc())
        )
        rows = result.all()
        grouped: dict = {}
        for record, question_description, course_name in rows:
            cid = record.course_id
            if cid not in grouped:
                grouped[cid] = {
                    "course_name": course_name or f"学科{cid}",
                    "records": [],
                }
            grouped[cid]["records"].append(
                ExerciseRecordListResponse(
                    do_id=record.do_id,
                    question_id=record.question_id,
                    question_description=question_description,
                    course_name=course_name,
                    question_type=record.question_type,
                    question_difficulty=record.question_difficulty,
                    do_stu_answer=record.do_stu_answer,
                    do_score=record.do_score,
                    do_isTrue=record.do_isTrue,
                    kg_node_name=record.kg_node_name,
                    created_at=record.created_at,
                )
            )
        return grouped
