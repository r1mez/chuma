"""Cross-service contract for asynchronous lesson-plan generation."""

from typing import Any, Literal

from pydantic import BaseModel, Field, model_validator


SlideLayout = Literal[
    "title",
    "objectives",
    "review",
    "knowledge_map",
    "concept",
    "comparison",
    "example",
    "difficulty_focus",
    "activity",
    "summary",
]

ThemePack = Literal[
    "theme01",
    "theme02",
    "theme03",
    "theme04",
    "theme05",
    "theme06",
    "theme07",
    "theme08",
    "theme09",
    "theme10",
    "theme11",
    "theme12",
]

BlockType = Literal[
    "highlight",
    "text",
    "comparison",
    "process",
    "question",
    "code",
    "table",
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
    theme_pack: ThemePack = "theme03"
    class_summary: dict[str, Any] = Field(default_factory=dict)
    difficult_knowledge: list[dict[str, Any]] = Field(default_factory=list)
    difficult_chapters: list[dict[str, Any]] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_review_budget(self):
        if self.include_review and self.slide_count < 8:
            raise ValueError("加入上一节学情回顾时，PPT 至少需要 8 页")
        return self


class LessonPlanBlock(BaseModel):
    """Editable teaching-content block rendered inside a slide."""

    type: BlockType = "text"
    title: str = Field(default="", max_length=80)
    text: str = Field(default="", max_length=500)
    items: list[str] = Field(default_factory=list, max_length=6)
    steps: list[str] = Field(default_factory=list, max_length=5)
    question: str = Field(default="", max_length=240)
    options: list[str] = Field(default_factory=list, max_length=4)
    teacher_answer: str = Field(default="", max_length=300)
    left_title: str = Field(default="", max_length=60)
    left_items: list[str] = Field(default_factory=list, max_length=5)
    right_title: str = Field(default="", max_length=60)
    right_items: list[str] = Field(default_factory=list, max_length=5)
    language: str = Field(default="", max_length=30)
    code: str = Field(default="", max_length=1600)
    columns: list[str] = Field(default_factory=list, max_length=6)
    rows: list[list[str]] = Field(default_factory=list, max_length=8)
    caption: str = Field(default="", max_length=160)


class LessonPlanSlide(BaseModel):
    layout: SlideLayout = "concept"
    title: str = Field(..., min_length=1, max_length=80)
    takeaway: str = Field(default="", max_length=160)
    bullets: list[str] = Field(default_factory=list, max_length=6)
    blocks: list[LessonPlanBlock] = Field(default_factory=list, max_length=6)
    presenter_notes: str = ""
    source_refs: list[str] = Field(default_factory=list, max_length=6)
    diagram_center: str = Field(default="", max_length=100)
    diagram_nodes: list[str] = Field(default_factory=list, max_length=3)
    duration_minutes: int = Field(default=0, ge=0, le=45)
    narrative_job: str = Field(default="", max_length=160)
    learning_objective: str = Field(default="", max_length=200)
    student_prompt: str = Field(default="", max_length=300)
    expected_answer: str = Field(default="", max_length=500)
    visual_type: str = Field(default="text", max_length=40)
    visual_description: str = Field(default="", max_length=300)
    source_evidence: list[str] = Field(default_factory=list, max_length=6)


class LessonPlanDraft(BaseModel):
    title: str = Field(..., min_length=1, max_length=256)
    summary: str = ""
    review_inserted: bool = False
    slides: list[LessonPlanSlide] = Field(default_factory=list, min_length=6, max_length=16)
