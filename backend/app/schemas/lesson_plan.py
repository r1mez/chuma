"""Pydantic schemas for teacher lesson-plan generation."""

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field, model_validator


LessonPlanStatus = Literal["queued", "generating", "completed", "failed"]


class LessonPlanCreate(BaseModel):
    class_id: int = Field(..., ge=1)
    course_id: int = Field(..., ge=1)
    section_id: str = Field(..., min_length=1, max_length=256)
    include_review: bool = True
    slide_count: int = Field(default=9, ge=7, le=16)

    @model_validator(mode="after")
    def validate_review_budget(self):
        if self.include_review and self.slide_count < 8:
            raise ValueError("加入上一节学情回顾时，PPT 至少需要 8 页")
        return self


class CourseSectionResponse(BaseModel):
    id: str
    name: str
    type: str
    path: str
    parent_id: str | None = None
    description: str = ""


class LessonPlanResponse(BaseModel):
    lesson_plan_id: int
    title: str
    class_id: int
    class_name: str | None = None
    course_id: int
    course_name: str | None = None
    section_id: str
    section_name: str
    section_path: str
    previous_section_name: str | None = None
    include_review: bool
    slide_count: int
    task_id: str
    status: LessonPlanStatus
    content: dict[str, Any] | None = None
    file_name: str | None = None
    error_message: str | None = None
    created_at: datetime
    updated_at: datetime
