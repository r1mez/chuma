"""Daily personalized question persisted for the student dashboard."""

from sqlalchemy import (
    BigInteger,
    Column,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Index,
    String,
    Text,
    UniqueConstraint,
    func,
)

from app.core.database import Base


class DailyQuestion(Base):
    __tablename__ = "daily_questions"

    daily_question_id = Column(BigInteger, primary_key=True, autoincrement=True)
    stu_id = Column(BigInteger, ForeignKey("students.stu_id", ondelete="CASCADE"), nullable=False)
    course_id = Column(BigInteger, ForeignKey("courses.course_id", ondelete="CASCADE"), nullable=False)
    question_id = Column(BigInteger, ForeignKey("questions.question_id", ondelete="CASCADE"), nullable=False)
    target_date = Column(Date, nullable=False)
    kg_node_name = Column(String(128), nullable=True)
    recommendation_status = Column(String(32), nullable=False, default="model")
    recommendation_reason = Column(Text, nullable=True)
    rrf_score = Column(Float, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)

    __table_args__ = (
        UniqueConstraint(
            "stu_id",
            "course_id",
            "target_date",
            name="uq_daily_questions_student_course_date",
        ),
        Index("ix_daily_questions_stu_date", "stu_id", "target_date"),
    )
