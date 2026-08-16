"""Cross-service contract for asynchronous lesson-plan generation."""

from typing import Any, Literal

from pydantic import BaseModel, Field


SlideLayout = Literal[
    "title",
    "objectives",
    "review",
    "knowledge_map",
    "concept",
    "example",
    "difficulty_focus",
    "activity",
    "summary",
]


class SectionContext(BaseModel):
    id: str
    name: str
    type: str = "Chapter"
    path: str = ""
    parent_id: str | None = None
    description: str = ""


class LessonPlanSubmitRequest(BaseModel):
    task_id: str = Field(..., min_length=8, max_length=64)
    lesson_plan_id: int = Field(..., ge=1)
    teacher_id: int = Field(..., ge=1)
    class_id: int = Field(..., ge=1)
    class_name: str = Field(..., min_length=1, max_length=64)
    course_id: int = Field(..., ge=1)
    course_name: str = Field(..., min_length=1, max_length=128)
    kg_graph_id: int | None = Field(default=None, ge=1)
    section: SectionContext
    previous_section: SectionContext | None = None
    include_review: bool = True
    slide_count: int = Field(default=9, ge=7, le=16)
    class_summary: dict[str, Any] = Field(default_factory=dict)
    difficult_knowledge: list[dict[str, Any]] = Field(default_factory=list)
    difficult_chapters: list[dict[str, Any]] = Field(default_factory=list)


class LessonPlanSlide(BaseModel):
    layout: SlideLayout = "concept"
    title: str = Field(..., min_length=1, max_length=80)
    bullets: list[str] = Field(default_factory=list, max_length=6)
    presenter_notes: str = ""
    source_refs: list[str] = Field(default_factory=list, max_length=6)


class LessonPlanDraft(BaseModel):
    title: str = Field(..., min_length=1, max_length=256)
    summary: str = ""
    review_inserted: bool = False
    slides: list[LessonPlanSlide] = Field(default_factory=list, min_length=6, max_length=16)
