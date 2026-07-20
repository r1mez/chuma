"""学习管理路由"""
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.core.deps import get_current_user_optional
from app.schemas.learning import (
    StudentCourseMasteryCreate, StudentCourseMasteryResponse,
    StudentKnowledgeMasteryCreate, StudentKnowledgeMasteryResponse,
)
from app.services.learning_service import LearningService

router = APIRouter()


@router.get("/dashboard")
async def get_learning_dashboard():
    return {"message": "dashboard endpoint - not in scope"}


@router.get("/plan")
async def get_learning_plan():
    return {"message": "plan endpoint - not in scope"}


@router.post("/plan/generate")
async def generate_learning_plan():
    return {"message": "plan generate endpoint - not in scope"}


@router.get("/progress")
async def get_learning_progress(
    current_user: dict = Depends(get_current_user_optional),
    db: AsyncSession = Depends(get_db),
):
    stu_id = current_user.get("id")
    service = LearningService()
    course_mastery = await service.get_student_course_mastery(stu_id, db)
    knowledge_mastery = await service.get_student_knowledge_mastery(stu_id, db)
    return {"course_mastery": course_mastery, "knowledge_mastery": knowledge_mastery}


@router.get("/history")
async def get_learning_history():
    return {"message": "history endpoint - not in scope"}


@router.post("/mastery/course", response_model=StudentCourseMasteryResponse)
async def set_course_mastery(
    data: StudentCourseMasteryCreate,
    current_user: dict = Depends(get_current_user_optional),
    db: AsyncSession = Depends(get_db),
):
    stu_id = current_user.get("id")
    service = LearningService()
    return await service.set_course_mastery(stu_id, data, db)


@router.post("/mastery/knowledge", response_model=StudentKnowledgeMasteryResponse)
async def set_knowledge_mastery(
    data: StudentKnowledgeMasteryCreate,
    current_user: dict = Depends(get_current_user_optional),
    db: AsyncSession = Depends(get_db),
):
    stu_id = current_user.get("id")
    service = LearningService()
    return await service.set_knowledge_mastery(stu_id, data, db)
