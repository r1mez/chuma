"""AI-service endpoints for queued lesson-plan generation."""

from __future__ import annotations

import json
import mimetypes
from pathlib import Path
from urllib.parse import unquote

import redis.asyncio as aioredis
from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse, HTMLResponse

from app.config import get_lesson_plan_output_dir, settings
from app.schemas.lesson_plan import LessonPlanSubmitRequest

router = APIRouter()


def _state_key(task_id: str) -> str:
    return f"lesson-plan:state:{task_id}"


async def _read_state(task_id: str) -> dict:
    redis = aioredis.from_url(settings.REDIS_URL)
    try:
        raw = await redis.get(_state_key(task_id))
    finally:
        await redis.aclose()
    if not raw:
        return {"status": "queued"}
    try:
        return json.loads(raw.decode() if isinstance(raw, bytes) else raw)
    except json.JSONDecodeError:
        return {"status": "failed", "error": "Lesson-plan task state is invalid"}


@router.post("/submit")
async def submit_lesson_plan(request: LessonPlanSubmitRequest):
    payload = request.model_dump()
    redis = aioredis.from_url(settings.REDIS_URL)
    try:
        await redis.set(
            _state_key(request.task_id),
            json.dumps({"status": "queued"}, ensure_ascii=False),
            ex=settings.LESSON_PLAN_TASK_RETENTION_SECONDS,
        )
        await redis.lpush("chuma:tasks", json.dumps({"type": "lesson_plan_generate", **payload}, ensure_ascii=False))
    finally:
        await redis.aclose()
    return {"task_id": request.task_id, "status": "queued"}


@router.get("/tasks/{task_id}")
async def get_lesson_plan_task(task_id: str):
    return await _read_state(task_id)


@router.get("/tasks/{task_id}/download")
async def download_lesson_plan_task(task_id: str):
    state = await _read_state(task_id)
    if state.get("status") != "completed":
        raise HTTPException(status_code=409, detail="Lesson plan is not completed")
    candidate = Path(str(state.get("file_path") or "")).resolve()
    output_dir = get_lesson_plan_output_dir().resolve()
    if output_dir not in candidate.parents or not candidate.is_file():
        raise HTTPException(status_code=404, detail="PPTX file is unavailable")
    return FileResponse(
        path=candidate,
        media_type="application/vnd.openxmlformats-officedocument.presentationml.presentation",
        filename=str(state.get("file_name") or candidate.name),
    )


@router.get("/tasks/{task_id}/html")
async def preview_lesson_plan_html(task_id: str):
    state = await _read_state(task_id)
    if state.get("status") != "completed":
        raise HTTPException(status_code=409, detail="Lesson plan is not completed")
    candidate = Path(str(state.get("html_file_path") or "")).resolve()
    output_dir = get_lesson_plan_output_dir().resolve()
    if output_dir not in candidate.parents or not candidate.is_file():
        raise HTTPException(status_code=404, detail="HTML file is unavailable")
    return HTMLResponse(content=candidate.read_text(encoding="utf-8"))


@router.get("/tasks/{task_id}/preview/{asset_path:path}")
async def preview_lesson_plan_asset(task_id: str, asset_path: str = ""):
    """Serve generated HTML and its relative assets from the task directory."""
    state = await _read_state(task_id)
    if state.get("status") != "completed":
        raise HTTPException(status_code=409, detail="Lesson plan is not completed")

    html_dir = Path(str(state.get("html_dir") or "")).resolve()
    output_dir = get_lesson_plan_output_dir().resolve()
    if not html_dir.is_dir() or (html_dir != output_dir and output_dir not in html_dir.parents):
        raise HTTPException(status_code=404, detail="HTML lesson-plan directory is unavailable")

    normalized = unquote(asset_path or "").replace("\\", "/").lstrip("/") or "index.html"
    parts = normalized.split("/")
    if any(part in {"", ".", ".."} for part in parts):
        raise HTTPException(status_code=400, detail="Invalid preview asset path")
    target = (html_dir / normalized).resolve()
    if target != html_dir and html_dir not in target.parents:
        raise HTTPException(status_code=400, detail="Invalid preview asset path")
    if not target.is_file():
        raise HTTPException(status_code=404, detail="Preview asset is unavailable")

    media_type = mimetypes.guess_type(target.name)[0] or "application/octet-stream"
    return FileResponse(path=target, media_type=media_type)
