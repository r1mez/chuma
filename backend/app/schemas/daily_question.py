"""Schemas for daily personalized questions."""

from datetime import date, datetime
from typing import Any

from pydantic import BaseModel


class DailyQuestionUpsert(BaseModel):
    stu_id: int
    course_id: int
    question_id: int
    target_date: date
    kg_node_name: str | None = None
    recommendation_status: str = "model"
    recommendation_reason: str | None = None
    rrf_score: float | None = None


class DailyQuestionResponse(BaseModel):
    daily_question_id: int
    target_date: date
    completed: bool
    completed_at: datetime | None = None
    course_id: int
    course_name: str
    question_id: int
    question_description: str
    question_options: Any | None = None
    question_type: str
    question_difficulty: int
    kg_node_name: str | None = None
    recommendation_status: str
    recommendation_reason: str | None = None
    rrf_score: float | None = None
