"""Shared next-knowledge-point and daily-question recommendation service."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from app.agent.tools.learning_plan_db import execute_learning_plan_tool
from app.engines.gnn.inference import TGNNInference
from app.engines.gnn.repository import TGNNRepository


class NextKnowledgePointService:
    """Reuse the same TGNN + weighted-RRF path used by the learning plan."""

    def __init__(
        self,
        repository: TGNNRepository | None = None,
        inference: TGNNInference | None = None,
    ):
        self.repository = repository or TGNNRepository()
        self.inference = inference or TGNNInference(repository=self.repository)

    async def recommend_for_student(self, stu_id: int, top_k: int = 3) -> dict[str, Any]:
        courses = await self._list_courses()
        ai_analysis, teacher_opinion = await self._load_learning_plan_context(stu_id)
        subjects: list[dict[str, Any]] = []
        for course in courses:
            course_id = int(course["course_id"])
            course_name = str(course["course_name"])
            try:
                recommendation = await self.inference.recommend_for_course(
                    stu_id=stu_id,
                    course_id=course_id,
                    top_k=top_k,
                    ai_analysis=ai_analysis,
                    teacher_opinion=teacher_opinion,
                )
            except Exception as exc:
                recommendation = {
                    "status": "unavailable",
                    "model_version": None,
                    "history_event_count": 0,
                    "candidate_count": 0,
                    "recommendations": [],
                    "message": f"推荐暂不可用：{exc}",
                }

            first = (recommendation.get("recommendations") or [None])[0]
            subjects.append(
                {
                    "course_id": course_id,
                    "course_name": course_name,
                    "recommendation": recommendation,
                    "next_knowledge_point": first.get("knowledge_point") if first else None,
                    "next_question_id": first.get("question_id") if first else None,
                    "next_reason": first.get("reason") if first else recommendation.get("message"),
                }
            )

        return {
            "stu_id": stu_id,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "subjects": subjects,
        }

    async def select_daily_question(self, stu_id: int) -> dict[str, Any] | None:
        result = await self.recommend_for_student(stu_id, top_k=3)
        candidates: list[dict[str, Any]] = []
        for subject in result["subjects"]:
            for item in subject["recommendation"].get("recommendations", []):
                candidates.append(
                    {
                        **item,
                        "course_id": subject["course_id"],
                        "course_name": subject["course_name"],
                        "recommendation_status": subject["recommendation"].get("status", "model"),
                    }
                )
        if not candidates:
            return None

        # RRF scores are comparable across the course-isolated recommendation
        # runs. Ties are resolved by rank, mastery, and question id.
        return max(
            candidates,
            key=lambda item: (
                float(item.get("rrf_score") or 0.0),
                -int(item.get("rank") or 999),
                -float(item.get("current_mastery") or 0.0),
                -int(item.get("question_id") or 0),
            ),
        )

    async def select_daily_questions(self, stu_id: int) -> list[dict[str, Any]]:
        """Select the top RRF recommendation independently for every course."""
        result = await self.recommend_for_student(stu_id, top_k=3)
        candidates: list[dict[str, Any]] = []
        for subject in result["subjects"]:
            recommendation = subject["recommendation"]
            first = (recommendation.get("recommendations") or [None])[0]
            if first is None:
                continue
            candidates.append(
                {
                    **first,
                    "course_id": subject["course_id"],
                    "course_name": subject["course_name"],
                    "recommendation_status": recommendation.get("status", "model"),
                    "recommendation_reason": first.get("reason"),
                }
            )
        return candidates

    async def _list_courses(self) -> list[dict[str, Any]]:
        import asyncio

        return await asyncio.to_thread(self.repository.list_courses)

    @staticmethod
    async def _load_learning_plan_context(stu_id: int) -> tuple[str | None, str | None]:
        """Load the two text dimensions that the full learning plan passes to RRF."""
        import asyncio

        ai_result, teacher_result = await asyncio.gather(
            asyncio.to_thread(
                execute_learning_plan_tool,
                "query_ai_analysis",
                {"stu_id": stu_id},
            ),
            asyncio.to_thread(
                execute_learning_plan_tool,
                "query_teacher_opinion",
                {"stu_id": stu_id},
            ),
        )
        ai_analysis = ai_result.get("data", {}).get("ai_analysis") if ai_result.get("success") else None
        teacher_opinion = teacher_result.get("data", {}).get("teacher_opinion") if teacher_result.get("success") else None
        return ai_analysis, teacher_opinion
