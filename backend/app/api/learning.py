"""学习管理路由"""
from datetime import date, datetime, time
import logging

import httpx

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.core.config import settings
from app.core.deps import get_current_user_optional
from app.schemas.learning import (
    StudentCourseMasteryCreate, StudentCourseMasteryResponse,
    StudentKnowledgeMasteryCreate, StudentKnowledgeMasteryResponse,
)
from app.services.learning_service import LearningService
from app.services.mastery_service import MasteryService
from app.core.service_auth import verify_ai_service_token
from app.schemas.daily_question import DailyQuestionResponse, DailyQuestionUpsert
from app.services.daily_question_service import DailyQuestionService

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("/daily-question", response_model=list[DailyQuestionResponse])
async def get_daily_question(
    current_user: dict = Depends(get_current_user_optional),
    db: AsyncSession = Depends(get_db),
):
    """Return one persisted daily question for every available course."""
    stu_id = current_user.get("id")
    service = DailyQuestionService()
    target_date = date.today()
    existing = await service.list_for_student(stu_id, target_date, db)
    if datetime.now().time() < time(4, 30):
        return existing

    # Once the daily generation window has opened, only fill missing courses.
    # This keeps completed questions stable and makes a page refresh idempotent.
    existing_course_ids = {question.course_id for question in existing}
    course_ids = await service.list_course_ids(db)
    if course_ids and course_ids.issubset(existing_course_ids):
        return existing

    # The scheduler remains the primary path. This lazy path guarantees that
    # a student who opens the app after 04:30 is not stuck without a question
    # when the batch job was skipped or the AI service restarted.
    try:
        async with httpx.AsyncClient(timeout=120.0) as client:
            headers = {"X-Service-Token": settings.AI_SERVICE_TOKEN}
            response = await client.get(
                f"{settings.AI_SERVICE_URL}/analysis/daily_questions",
                headers=headers,
                params={"stu_id": stu_id},
            )
            if response.status_code >= 400:
                # Keep the fallback compatible with an AI service that has the
                # shared next-knowledge endpoint but not the newer daily list
                # endpoint yet. Both paths use the same TGNN/RRF result.
                response = await client.get(
                    f"{settings.AI_SERVICE_URL}/analysis/next_knowledge_points",
                    headers=headers,
                    params={"stu_id": stu_id},
                )
        response.raise_for_status()
        candidates = _daily_candidates_from_ai_response(
            response.json(),
            stu_id=stu_id,
            target_date=target_date,
        )
        generated = list(existing)
        for candidate in candidates:
            try:
                data = DailyQuestionUpsert.model_validate(candidate).model_copy(
                    update={"stu_id": stu_id, "target_date": target_date}
                )
                if data.course_id in existing_course_ids:
                    continue
                generated.append(await service.upsert(data, db))
                existing_course_ids.add(data.course_id)
            except Exception:
                logger.exception(
                    "lazy daily question candidate failed stu_id=%s candidate=%s",
                    stu_id,
                    candidate,
                )
        return sorted(generated, key=lambda question: question.course_id)
    except Exception:
        # Keep the dashboard usable if the fallback generation is temporarily
        # unavailable. The next page load can retry it.
        logger.exception(
            "lazy daily question generation failed stu_id=%s", stu_id
        )
        return existing


def _daily_candidates_from_ai_response(
    payload: object,
    *,
    stu_id: int,
    target_date: date,
) -> list[dict]:
    """Normalize both the plural daily endpoint and the shared recommendation response."""
    if isinstance(payload, list):
        return payload
    if not isinstance(payload, dict):
        return []

    candidates: list[dict] = []
    for subject in payload.get("subjects", []):
        if not isinstance(subject, dict):
            continue
        recommendation = subject.get("recommendation") or {}
        recommendations = recommendation.get("recommendations") or []
        if not recommendations:
            continue
        first = recommendations[0]
        if not isinstance(first, dict):
            continue
        candidates.append(
            {
                "stu_id": stu_id,
                "course_id": subject.get("course_id"),
                "question_id": first.get("question_id"),
                "target_date": target_date,
                "kg_node_name": first.get("knowledge_point"),
                "recommendation_status": recommendation.get("status", "model"),
                "recommendation_reason": first.get("reason"),
                "rrf_score": first.get("rrf_score"),
            }
        )
    return candidates


@router.post("/daily-question/internal", response_model=DailyQuestionResponse)
async def upsert_daily_question(
    data: DailyQuestionUpsert,
    _service_token: None = Depends(verify_ai_service_token),
    db: AsyncSession = Depends(get_db),
):
    """Persist a question selected by the AI scheduler."""
    try:
        return await DailyQuestionService().upsert(data, db)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/dashboard")
async def get_learning_dashboard():
    return {"message": "dashboard endpoint - not in scope"}


@router.get("/plan")
async def get_learning_plan():
    return {"message": "plan endpoint - not in scope"}


@router.post("/plan/generate")
async def generate_learning_plan():
    return {"message": "plan generate endpoint - not in scope"}


@router.get("/progress")
async def get_learning_progress(
    current_user: dict = Depends(get_current_user_optional),
    db: AsyncSession = Depends(get_db),
):
    stu_id = current_user.get("id")
    service = LearningService()
    course_mastery = await service.get_student_course_mastery(stu_id, db)
    knowledge_mastery = await service.get_student_knowledge_mastery(stu_id, db)
    return {"course_mastery": course_mastery, "knowledge_mastery": knowledge_mastery}


@router.get("/history")
async def get_learning_history():
    return {"message": "history endpoint - not in scope"}

@router.get("/dashboard-progress")
async def get_dashboard_progress(
    current_user: dict = Depends(get_current_user_optional),
    db: AsyncSession = Depends(get_db),
):
    """
    Return course_process for each course of the current student.
    Format: { course_id: course_process, ... }
    course_process is null-safe, returns 0.
    """
    stu_id = current_user.get("id")
    service = LearningService()
    course_masteries = await service.get_student_course_mastery(stu_id, db)
    return {str(m.course_id): m.course_process if m.course_process is not None else 0.0 for m in course_masteries}


@router.post("/mastery/course", response_model=StudentCourseMasteryResponse)
async def set_course_mastery(
    data: StudentCourseMasteryCreate,
    current_user: dict = Depends(get_current_user_optional),
    db: AsyncSession = Depends(get_db),
):
    stu_id = current_user.get("id")
    service = LearningService()
    return await service.set_course_mastery(stu_id, data, db)


@router.post("/mastery/knowledge", response_model=StudentKnowledgeMasteryResponse)
async def set_knowledge_mastery(
    data: StudentKnowledgeMasteryCreate,
    current_user: dict = Depends(get_current_user_optional),
    db: AsyncSession = Depends(get_db),
):
    stu_id = current_user.get("id")
    service = LearningService()
    return await service.set_knowledge_mastery(stu_id, data, db)


@router.get("/mastery/hierarchy")
async def get_mastery_hierarchy(
    course_id: int = Query(..., description="学科 ID"),
    current_user: dict = Depends(get_current_user_optional),
    db: AsyncSession = Depends(get_db),
):
    """获取某学科下学生的掌握度层级树（学科→章节→小节→知识点）。

    掌握度由做题记录自动聚合：
    - 知识点掌握度：做题时更新（客观题 5/0 分，主观题按得分映射，加权平均）
    - 小节掌握度 = 该小节下所有知识点掌握度的平均值
    - 章节掌握度 = 该章节下所有小节掌握度的平均值
    - 学科掌握度 = 该学科下所有知识点掌握度的平均值
    """
    stu_id = current_user.get("id")
    service = MasteryService()
    return await service.get_mastery_hierarchy(stu_id, course_id, db)
