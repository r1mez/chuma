"""Persisted teacher lesson-plan generation jobs."""

from sqlalchemy import BigInteger, Boolean, Column, DateTime, ForeignKey, Index, Integer, JSON, String, Text, func

from app.core.database import Base


class LessonPlan(Base):
    """One generated lesson-plan deck and its generation state."""

    __tablename__ = "lesson_plans"

    lesson_plan_id = Column(BigInteger, primary_key=True, autoincrement=True)
    tea_id = Column(BigInteger, ForeignKey("teachers.tea_id", ondelete="CASCADE"), nullable=False, index=True)
    class_id = Column(BigInteger, ForeignKey("classes.class_id", ondelete="CASCADE"), nullable=False, index=True)
    course_id = Column(BigInteger, ForeignKey("courses.course_id", ondelete="CASCADE"), nullable=False, index=True)
    kg_graph_id = Column(BigInteger, ForeignKey("kg_graphs.id", ondelete="SET NULL"), nullable=True)

    section_id = Column(String(256), nullable=False)
    section_name = Column(String(256), nullable=False)
    section_path = Column(String(1024), nullable=False, server_default="")
    previous_section_name = Column(String(256), nullable=True)
    include_review = Column(Boolean, nullable=False, server_default="true")
    slide_count = Column(Integer, nullable=False, server_default="8")
    theme_pack = Column(String(20), nullable=False, server_default="theme03")

    title = Column(String(256), nullable=False)
    task_id = Column(String(64), nullable=False, unique=True)
    status = Column(String(20), nullable=False, server_default="queued")
    content = Column(JSON, nullable=True)
    file_name = Column(String(512), nullable=True)
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)

    __table_args__ = (
        Index("ix_lesson_plans_teacher_created", "tea_id", "created_at"),
        Index("ix_lesson_plans_class_course", "class_id", "course_id"),
    )
