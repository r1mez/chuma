"""Request and response models for teacher assignments."""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class AssignmentQuestionSelection(BaseModel):
    question_id: int = Field(..., ge=1)
    sort_order: int | None = Field(default=None, ge=0)
    priority_score: float | None = None
    recommendation_source: str | None = None
    recommendation_reason: str | None = None


class AssignmentCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=128)
    description: str | None = Field(default=None, max_length=4000)
    class_id: int = Field(..., ge=1)
    course_id: int = Field(..., ge=1)
    due_at: datetime | None = None
    questions: list[AssignmentQuestionSelection] = Field(..., min_length=1, max_length=200)


class AssignmentSubmissionPayload(BaseModel):
    assignment_id: int = Field(..., ge=1)


class AssignmentQuestionView(BaseModel):
    question_id: int
    question_description: str
    question_options: Any | None = None
    question_type: str
    question_difficulty: int
    course_id: int
    kg_node_name: str | None = None
    sort_order: int
    priority_score: float | None = None
    recommendation_source: str | None = None
    recommendation_reason: str | None = None


class AssignmentListItem(BaseModel):
    assignment_id: int
    title: str
    description: str | None = None
    class_id: int
    class_name: str | None = None
    course_id: int
    course_name: str | None = None
    due_at: datetime | None = None
    status: str
    question_count: int
    submitted_count: int = 0
    created_at: datetime


class AssignmentDetail(AssignmentListItem):
    questions: list[AssignmentQuestionView]
    submitted_question_ids: list[int] = Field(default_factory=list)
    can_submit: bool = True


class AssignmentResultStudent(BaseModel):
    stu_id: int
    stu_name: str
    submitted_count: int
    total_questions: int
    completion_rate: float
    average_score: float | None = None
    accuracy: float | None = None
    latest_submitted_at: datetime | None = None


class AssignmentResults(BaseModel):
    assignment: AssignmentListItem
    summary: dict[str, int | float | None]
    students: list[AssignmentResultStudent]
