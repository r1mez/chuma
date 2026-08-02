"""教师管理路由"""
from typing import List

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import get_current_user
from app.services.teacher_service import TeacherService

router = APIRouter()


@router.get("/courses")
async def list_teacher_courses(
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> List[dict]:
    """获取当前登录教师所授学科列表"""
    if current_user["user_type"] != "teacher":
        return []
    service = TeacherService()
    return await service.get_teacher_courses(current_user["id"], db)


@router.get("/classes")
async def list_teacher_classes(
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> List[dict]:
    """获取当前登录教师所管班级列表（含学生数量）"""
    if current_user["user_type"] != "teacher":
        return []
    service = TeacherService()
    return await service.get_teacher_classes(current_user["id"], db)


@router.get("/classes/{class_id}/students")
async def list_class_students(class_id: int):
    """获取班级学生列表"""
    pass


@router.get("/analytics/{class_id}")
async def get_class_analytics(class_id: int):
    """获取班级学情分析报告"""
    pass


@router.get("/alerts")
async def get_learning_alerts():
    """获取学习风险预警列表"""
    pass


@router.get("/students/{student_id}/profile")
async def get_student_profile(student_id: int):
    """获取学生能力画像"""
    pass


@router.post("/assignments")
async def create_assignment():
    """发布作业/考试"""
    pass


@router.get("/assignments/{assignment_id}/results")
async def get_assignment_results(assignment_id: int):
    """获取作业批改结果"""
    pass
