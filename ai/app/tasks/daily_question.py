"""Generate and persist one personalized question per course and student each day."""

from __future__ import annotations

import asyncio
import logging
from datetime import date

import httpx

from app.config import settings
from app.engines.gnn.recommendation_service import NextKnowledgePointService
from app.engines.gnn.repository import TGNNRepository
from app.tasks.registry import scheduled_task

logger = logging.getLogger(__name__)


@scheduled_task("daily_question", trigger="cron", hour=4, minute=30)
async def generate_daily_questions():
    """每天凌晨 4:30 生成并推送个性化每日一题。"""
    if not settings.BACKEND_URL:
        logger.warning("BACKEND_URL is empty; daily questions were not persisted")
        return

    repository = TGNNRepository()
    student_ids = await asyncio.to_thread(repository.list_student_ids)
    service = NextKnowledgePointService(repository=repository)
    target_date = date.today().isoformat()

    async with httpx.AsyncClient(timeout=60.0) as client:
        for stu_id in student_ids:
            try:
                candidates = await service.select_daily_questions(stu_id)
                if not candidates:
                    logger.info("no daily question candidates stu_id=%s", stu_id)
                    continue

                for candidate in candidates:
                    try:
                        response = await client.post(
                            f"{settings.BACKEND_URL.rstrip('/')}/api/learning/daily-question/internal",
                            headers={"X-Service-Token": settings.SERVICE_TOKEN},
                            json={
                                "stu_id": stu_id,
                                "course_id": candidate["course_id"],
                                "question_id": candidate["question_id"],
                                "target_date": target_date,
                                "kg_node_name": candidate.get("knowledge_point"),
                                "recommendation_status": candidate.get("recommendation_status", "model"),
                                "recommendation_reason": candidate.get("recommendation_reason") or candidate.get("reason"),
                                "rrf_score": candidate.get("rrf_score"),
                            },
                        )
                        response.raise_for_status()
                        logger.info(
                            "daily question persisted stu_id=%s course_id=%s question_id=%s",
                            stu_id,
                            candidate["course_id"],
                            candidate["question_id"],
                        )
                    except Exception:
                        # A failed course must not prevent the other courses
                        # from being persisted for the same student.
                        logger.exception(
                            "daily question persistence failed stu_id=%s course_id=%s",
                            stu_id,
                            candidate.get("course_id"),
                        )
            except Exception:
                # One student's data/model failure must not prevent the rest of
                # the daily batch from being generated.
                logger.exception("daily question generation failed stu_id=%s", stu_id)
