"""题目练习路由"""
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.core.deps import get_current_user_optional
from app.schemas.practice import QuestionCreate, QuestionResponse, ExerciseRecordCreate, ExerciseRecordResponse
from app.services.practice_service import PracticeService

router = APIRouter()


@router.get("/questions", response_model=list[QuestionResponse])
async def list_questions(
    course_id: Optional[int] = Query(None),
    kg_node_name: Optional[str] = Query(None),
    difficulty: Optional[int] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    service = PracticeService()
    return await service.list_questions(db, course_id, kg_node_name, difficulty)


@router.get("/questions/{question_id}", response_model=QuestionResponse)
async def get_question(question_id: int, db: AsyncSession = Depends(get_db)):
    service = PracticeService()
    result = await service.get_question_by_id(question_id, db)
    if result is None:
        raise HTTPException(status_code=404, detail="题目不存在")
    return result


@router.post("/submit", response_model=ExerciseRecordResponse)
async def submit_answer(
    data: ExerciseRecordCreate,
    current_user: dict = Depends(get_current_user_optional),
    db: AsyncSession = Depends(get_db),
):
    stu_id = current_user.get("id")
    service = PracticeService()
    return await service.submit_exercise(stu_id, data, db)


@router.get("/exercise-records", response_model=list[ExerciseRecordResponse])
async def get_exercise_records(
    current_user: dict = Depends(get_current_user_optional),
    db: AsyncSession = Depends(get_db),
):
    stu_id = current_user.get("id")
    service = PracticeService()
    return await service.get_student_exercise_records(stu_id, db)


@router.get("/exercise-records/analytics")
async def get_exercise_records_analytics():
    return {"message": "analytics endpoint - not in scope"}


@router.post("/hint")
async def get_hint():
    return {"message": "hint endpoint - not in scope"}
