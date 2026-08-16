"""Assignment models used by teacher publishing and student submissions."""

from sqlalchemy import (
    BigInteger,
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)

from app.core.database import Base


class Assignment(Base):
    __tablename__ = "assignments"

    assignment_id = Column(BigInteger, primary_key=True, autoincrement=True)
    title = Column(String(128), nullable=False)
    description = Column(Text, nullable=True)
    tea_id = Column(BigInteger, ForeignKey("teachers.tea_id", ondelete="CASCADE"), nullable=False, index=True)
    class_id = Column(BigInteger, ForeignKey("classes.class_id", ondelete="CASCADE"), nullable=False, index=True)
    course_id = Column(BigInteger, ForeignKey("courses.course_id", ondelete="CASCADE"), nullable=False, index=True)
    due_at = Column(DateTime, nullable=True)
    status = Column(String(20), nullable=False, server_default="published")
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)

    __table_args__ = (
        Index("ix_assignments_teacher_created", "tea_id", "created_at"),
        Index("ix_assignments_class_course", "class_id", "course_id"),
    )


class AssignmentQuestion(Base):
    __tablename__ = "assignment_questions"

    assignment_id = Column(
        BigInteger,
        ForeignKey("assignments.assignment_id", ondelete="CASCADE"),
        primary_key=True,
    )
    question_id = Column(
        BigInteger,
        ForeignKey("questions.question_id", ondelete="CASCADE"),
        primary_key=True,
    )
    sort_order = Column(Integer, nullable=False, default=0)
    priority_score = Column(Float, nullable=True)
    recommendation_source = Column(String(32), nullable=True)
    recommendation_reason = Column(Text, nullable=True)

    __table_args__ = (
        Index("ix_assignment_questions_question", "question_id"),
    )


class AssignmentSubmission(Base):
    """Latest answer snapshot for one student/question in one assignment."""

    __tablename__ = "assignment_submissions"

    submission_id = Column(BigInteger, primary_key=True, autoincrement=True)
    assignment_id = Column(
        BigInteger,
        ForeignKey("assignments.assignment_id", ondelete="CASCADE"),
        nullable=False,
    )
    question_id = Column(
        BigInteger,
        ForeignKey("questions.question_id", ondelete="CASCADE"),
        nullable=False,
    )
    stu_id = Column(
        BigInteger,
        ForeignKey("students.stu_id", ondelete="CASCADE"),
        nullable=False,
    )
    exercise_record_id = Column(
        BigInteger,
        ForeignKey("exercise_records.do_id", ondelete="SET NULL"),
        nullable=True,
    )
    do_score = Column(Float, nullable=True)
    do_is_true = Column(Boolean, nullable=True)
    submitted_at = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)

    __table_args__ = (
        UniqueConstraint(
            "assignment_id",
            "question_id",
            "stu_id",
            name="uq_assignment_submission_student_question",
        ),
        Index("ix_assignment_submissions_assignment_student", "assignment_id", "stu_id"),
    )
