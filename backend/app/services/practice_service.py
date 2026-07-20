"""Practice 业务逻辑层 — 题库与做题记录"""
from typing import Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.question import Question
from app.models.exercise_record import ExerciseRecord
from app.schemas.practice import QuestionCreate, QuestionResponse, ExerciseRecordCreate, ExerciseRecordResponse


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

    async def list_questions(self, db: AsyncSession, course_id: Optional[int] = None, kg_node_name: Optional[str] = None, difficulty: Optional[int] = None) -> list[QuestionResponse]:
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

    async def submit_exercise(self, stu_id: int, data: ExerciseRecordCreate, db: AsyncSession) -> ExerciseRecordResponse:
        record = ExerciseRecord(
            question_id=data.question_id,
            stu_id=stu_id,
            kg_node_name=data.kg_node_name,
            do_stu_answer=data.do_stu_answer,
        )
        db.add(record)
        await db.commit()
        await db.refresh(record)
        return ExerciseRecordResponse.model_validate(record)

    async def get_student_exercise_records(self, stu_id: int, db: AsyncSession) -> list[ExerciseRecordResponse]:
        result = await db.execute(
            select(ExerciseRecord).where(ExerciseRecord.stu_id == stu_id).order_by(ExerciseRecord.created_at.desc())
        )
        records = result.scalars().all()
        return [ExerciseRecordResponse.model_validate(r) for r in records]
