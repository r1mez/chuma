"""Redis worker task for producing a lesson-plan draft and PPTX file."""

from __future__ import annotations

import json
import logging

import redis.asyncio as aioredis

from app.agent.context import AgentContext
from app.agent.runtime import AgentRuntime
from app.config import settings
from app.pptx.dashi_runner import DashiPptRunner
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
        agent_result = await AgentRuntime.default().execute(
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
        if not isinstance(agent_result, dict):
            raise RuntimeError("lesson-plan Agent returned an invalid result")
        draft = agent_result.get("draft")
        dashi = agent_result.get("dashi") if isinstance(agent_result.get("dashi"), dict) else {}
        if not isinstance(draft, dict) or not isinstance(dashi.get("briefs"), list):
            raise RuntimeError("lesson-plan Agent did not return a Dashi content plan")
        render_result = await DashiPptRunner().render(
            task_id=task_id,
            title=str(dashi.get("title") or f"{payload['section'].get('name', '课堂')} 教案"),
            goal=str(dashi.get("goal") or "生成课堂教案"),
            theme_pack=str(dashi.get("theme_pack") or payload.get("theme_pack") or "theme03"),
            slide_count=int(dashi.get("page_count") or payload.get("slide_count") or 10),
            briefs=dashi["briefs"],
            source_notes=_source_notes(agent_result),
            preflight_quality_report=(
                agent_result.get("quality_report")
                if isinstance(agent_result.get("quality_report"), dict)
                else None
            ),
        )
        result = {
            "status": "completed",
            "draft": draft,
            "file_name": render_result.pptx_filename,
            "file_path": str(render_result.pptx_path),
            "html_file_name": render_result.html_path.name,
            "html_file_path": str(render_result.html_path),
            "html_dir": str(render_result.ppt_dir),
            "goal_file_path": str(render_result.goal_path),
            "quality_report_file_path": str(render_result.quality_report_path),
            "quality_report": render_result.quality_report,
            "preview_port": render_result.preview_port,
            "preview_http_url": render_result.preview_http_url,
            "source_manifest": agent_result.get("source_manifest", {}),
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


def _source_notes(agent_result: dict) -> str:
    manifest = agent_result.get("source_manifest")
    if not isinstance(manifest, dict):
        return "Source provenance unavailable."
    refs = manifest.get("source_refs") if isinstance(manifest.get("source_refs"), list) else []
    lines = [
        "Dashi lesson-plan source notes",
        f"section_path: {manifest.get('section_path', '')}",
        f"quality: {manifest.get('quality', 'unknown')}",
        f"previous_quality: {manifest.get('previous_quality', 'unknown')}",
        f"rag_used: {manifest.get('rag_used', False)}",
        "references:",
    ]
    for ref in refs:
        if isinstance(ref, dict):
            lines.append(f"- {ref.get('source_name', '')} / {ref.get('heading_path', '')} ({ref.get('quality', '')})")
    return "\n".join(lines) + "\n"
