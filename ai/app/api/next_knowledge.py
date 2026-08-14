"""Dashboard-facing next knowledge point and daily question APIs."""

from datetime import date

from fastapi import APIRouter, Query

from app.engines.gnn.recommendation_service import NextKnowledgePointService

router = APIRouter()


@router.get("/next_knowledge_points")
async def next_knowledge_points(
    stu_id: int = Query(..., ge=1),
):
    return await NextKnowledgePointService().recommend_for_student(stu_id)


@router.get("/daily_question")
async def daily_question(
    stu_id: int = Query(..., ge=1),
):
    """Select today's question without persisting it.

    The backend owns persistence. This endpoint is used for the after-04:30
    lazy-generation path when the scheduled batch has not produced a row yet.
    """
    candidate = await NextKnowledgePointService().select_daily_question(stu_id)
    if candidate is None:
        return None
    return {
        "stu_id": stu_id,
        "course_id": candidate["course_id"],
        "question_id": candidate["question_id"],
        "target_date": date.today().isoformat(),
        "kg_node_name": candidate.get("knowledge_point"),
        "recommendation_status": candidate.get("recommendation_status", "model"),
        "recommendation_reason": candidate.get("reason"),
        "rrf_score": candidate.get("rrf_score"),
    }


@router.get("/daily_questions")
async def daily_questions(
    stu_id: int = Query(..., ge=1),
):
    """Select one daily question for each course without persisting it."""
    candidates = await NextKnowledgePointService().select_daily_questions(stu_id)
    return [
        {
            "stu_id": stu_id,
            "course_id": candidate["course_id"],
            "question_id": candidate["question_id"],
            "target_date": date.today().isoformat(),
            "kg_node_name": candidate.get("knowledge_point"),
            "recommendation_status": candidate.get("recommendation_status", "model"),
            "recommendation_reason": candidate.get("recommendation_reason") or candidate.get("reason"),
            "rrf_score": candidate.get("rrf_score"),
        }
        for candidate in candidates
    ]
