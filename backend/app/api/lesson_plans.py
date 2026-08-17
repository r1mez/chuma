"""Teacher lesson-plan generation and download routes."""

from urllib.parse import quote

from fastapi import APIRouter, Depends, HTTPException, Query, Request
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
    safe_filename = (
        filename
        .replace('"', "")
        .replace("\r", "")
        .replace("\n", "")
    )
    content_disposition = (
        'attachment; filename="lesson-plan.pptx"; '
        f"filename*=UTF-8''{quote(safe_filename, safe='')}"
    )
    return Response(
        content=content,
        media_type="application/vnd.openxmlformats-officedocument.presentationml.presentation",
        headers={"Content-Disposition": content_disposition},
    )


@router.get("/{lesson_plan_id}/html")
async def preview_lesson_plan_html(
    lesson_plan_id: int,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    _require_teacher(current_user)
    try:
        content = await LessonPlanService().preview_html_for_teacher(current_user["id"], lesson_plan_id, db)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return Response(
        content=content,
        media_type="text/html",
        headers={"Content-Disposition": "inline; filename=lesson-plan.html"},
    )


@router.get("/{lesson_plan_id}/preview-ticket")
async def create_lesson_plan_preview_ticket(
    lesson_plan_id: int,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    _require_teacher(current_user)
    try:
        token = await LessonPlanService().create_preview_ticket(current_user["id"], lesson_plan_id, db)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return {"url": f"/api/teacher/lesson-plans/{lesson_plan_id}/preview/?ticket={token}"}


@router.get("/{lesson_plan_id}/preview/{asset_path:path}")
async def preview_lesson_plan_asset(
    lesson_plan_id: int,
    request: Request,
    asset_path: str = "",
    ticket: str | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
):
    token = ticket or request.cookies.get("chuma_lesson_plan_preview")
    service = LessonPlanService()
    teacher_id = await service.resolve_preview_ticket(token or "", lesson_plan_id)
    if teacher_id is None:
        raise HTTPException(status_code=401, detail="课堂预览链接已失效，请重新打开")
    try:
        content, media_type = await service.preview_asset_for_teacher(
            teacher_id, lesson_plan_id, asset_path or "index.html", db
        )
    except ValueError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    response = Response(content=content, media_type=media_type.split(";", 1)[0])
    if ticket:
        response.set_cookie(
            "chuma_lesson_plan_preview",
            token,
            max_age=900,
            httponly=True,
            samesite="lax",
            path=f"/api/teacher/lesson-plans/{lesson_plan_id}/preview",
        )
    return response
