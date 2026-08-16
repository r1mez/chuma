"""AI-service endpoints for queued lesson-plan generation."""

from __future__ import annotations

import json
from pathlib import Path

import redis.asyncio as aioredis
from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

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
        return {"status": "failed", "error": "教案任务状态损坏"}


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
        raise HTTPException(status_code=409, detail="教案尚未生成完成")
    candidate = Path(str(state.get("file_path") or "")).resolve()
    output_dir = get_lesson_plan_output_dir().resolve()
    if output_dir not in candidate.parents or not candidate.is_file():
        raise HTTPException(status_code=404, detail="教案文件不存在或已过期")
    return FileResponse(
        path=candidate,
        media_type="application/vnd.openxmlformats-officedocument.presentationml.presentation",
        filename=str(state.get("file_name") or candidate.name),
    )
