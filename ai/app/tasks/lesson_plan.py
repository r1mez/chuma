"""Redis worker task for producing a lesson-plan draft and PPTX file."""

from __future__ import annotations

import json
import logging

import redis.asyncio as aioredis

from app.agent.context import AgentContext
from app.agent.runtime import AgentRuntime
from app.config import get_lesson_plan_output_dir, settings
from app.pptx.lesson_plan_renderer import render_lesson_plan
from app.tasks.registry import task_handler

logger = logging.getLogger(__name__)


def _state_key(task_id: str) -> str:
    return f"lesson-plan:state:{task_id}"


@task_handler("lesson_plan_generate")
async def run_lesson_plan_generation(task_data: dict):
    task_id = str(task_data.get("task_id") or "")
    if not task_id:
        logger.error("Lesson-plan task has no task_id")
        return
    redis = aioredis.from_url(settings.REDIS_URL)
    ttl = settings.LESSON_PLAN_TASK_RETENTION_SECONDS
    try:
        await redis.set(_state_key(task_id), json.dumps({"status": "generating"}, ensure_ascii=False), ex=ttl)
        payload = dict(task_data)
        payload.pop("type", None)
        draft = await AgentRuntime.default().execute(
            "teacher.lesson_plan",
            AgentContext(
                user_id=int(payload["teacher_id"]),
                user_role="service",
                teacher_id=int(payload["teacher_id"]),
                class_id=int(payload["class_id"]),
                course_id=int(payload["course_id"]),
                kg_graph_ids=(int(payload["kg_graph_id"]),) if payload.get("kg_graph_id") else (),
                agent_id="teacher.lesson_plan",
            ),
            payload,
        )
        output_path, filename = render_lesson_plan(
            draft=draft,
            output_dir=get_lesson_plan_output_dir(),
            task_id=task_id,
            course_name=str(payload["course_name"]),
            class_name=str(payload["class_name"]),
        )
        result = {
            "status": "completed",
            "draft": draft,
            "file_name": filename,
            "file_path": str(output_path),
        }
        await redis.set(_state_key(task_id), json.dumps(result, ensure_ascii=False), ex=ttl)
        logger.info("Lesson-plan task %s completed", task_id)
    except Exception as exc:
        logger.exception("Lesson-plan task %s failed", task_id)
        await redis.set(
            _state_key(task_id),
            json.dumps({"status": "failed", "error": str(exc)}, ensure_ascii=False),
            ex=ttl,
        )
    finally:
        await redis.aclose()
