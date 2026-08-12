"""DyGKT recommendation endpoints used by learning planning and practice."""

from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.engines.gnn.inference import TGNNInference

router = APIRouter()


class RecommendRequest(BaseModel):
    student_id: int = Field(..., ge=1, description="学生 ID")
    course_id: int = Field(..., ge=1, description="学科 ID")
    top_k: int = Field(default=3, ge=1, le=10)
    ai_analysis: str | None = None
    teacher_opinion: str | None = None


class RecommendResponse(BaseModel):
    status: str
    model_version: str | None = None
    history_event_count: int
    candidate_count: int
    target_correct_probability: float | None = None
    fusion: dict[str, Any]
    recommendations: list[dict[str, Any]]
    message: str | None = None


@router.post("/recommend", response_model=RecommendResponse)
async def recommend(request: RecommendRequest):
    """Return explainable DyGKT + weighted-RRF next practice targets."""

    try:
        return await TGNNInference().recommend_for_course(
            stu_id=request.student_id,
            course_id=request.course_id,
            top_k=request.top_k,
            ai_analysis=request.ai_analysis,
            teacher_opinion=request.teacher_opinion,
        )
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"动态题目推荐暂不可用: {exc}") from exc


@router.post("/lesson-plan")
async def recommend_lesson_plan():
    """Reserved teacher-side endpoint; lesson planning remains Agent-owned."""

    raise HTTPException(status_code=501, detail="DyGKT 教案推荐尚未实现")
