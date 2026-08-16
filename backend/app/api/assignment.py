"""Student-facing assignment routes."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import get_current_user
from app.services.assignment_service import AssignmentService

router = APIRouter()


def _require_student(current_user: dict) -> None:
    if current_user["user_type"] != "student":
        raise HTTPException(status_code=403, detail="仅学生可以访问作业")


@router.get("")
async def list_student_assignments(
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    _require_student(current_user)
    return await AssignmentService().list_for_student(current_user["id"], db)


@router.get("/{assignment_id}")
async def get_student_assignment(
    assignment_id: int,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    _require_student(current_user)
    try:
        return await AssignmentService().get_student_detail(current_user["id"], assignment_id, db)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
