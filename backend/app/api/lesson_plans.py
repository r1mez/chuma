"""Teacher lesson-plan generation and download routes."""

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import get_current_user
from app.schemas.lesson_plan import LessonPlanCreate
from app.services.lesson_plan_service import LessonPlanService

router = APIRouter()


def _require_teacher(current_user: dict) -> None:
    if current_user.get("user_type") != "teacher":
        raise HTTPException(status_code=403, detail="仅教师可以使用教案生成")


@router.post("")
async def create_lesson_plan(
    data: LessonPlanCreate,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    _require_teacher(current_user)
    try:
        return await LessonPlanService().create(current_user["id"], data, db)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("")
async def list_lesson_plans(
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    _require_teacher(current_user)
    return await LessonPlanService().list_for_teacher(current_user["id"], db)


@router.get("/{lesson_plan_id}")
async def get_lesson_plan(
    lesson_plan_id: int,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    _require_teacher(current_user)
    try:
        return await LessonPlanService().get_for_teacher(current_user["id"], lesson_plan_id, db)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/{lesson_plan_id}/download")
async def download_lesson_plan(
    lesson_plan_id: int,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    _require_teacher(current_user)
    try:
        content, filename = await LessonPlanService().download_for_teacher(
            current_user["id"], lesson_plan_id, db
        )
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    escaped = filename.replace('"', "")
    return Response(
        content=content,
        media_type="application/vnd.openxmlformats-officedocument.presentationml.presentation",
        headers={"Content-Disposition": f'attachment; filename="{escaped}"'},
    )
