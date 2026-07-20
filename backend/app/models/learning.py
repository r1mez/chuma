"""Learning SQLAlchemy ORM 模型 — 学生掌握度"""
from sqlalchemy import BigInteger, Column, DateTime, Float, ForeignKey, String, func, CheckConstraint, Index
from app.core.database import Base


class StudentCourseMastery(Base):
    __tablename__ = "student_course_mastery"

    stu_id = Column(BigInteger, ForeignKey("students.stu_id"), primary_key=True)
    course_id = Column(BigInteger, ForeignKey("courses.course_id"), primary_key=True)
    course_degree = Column(Float, nullable=False)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        CheckConstraint(
            "course_degree >= 0.0 AND course_degree <= 5.0",
            name="ck_course_degree_range",
        ),
    )


class StudentKnowledgeMastery(Base):
    __tablename__ = "student_knowledge_mastery"

    stu_id = Column(BigInteger, ForeignKey("students.stu_id"), primary_key=True)
    kg_node_name = Column(String(128), primary_key=True)
    kg_degree = Column(Float, nullable=False)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        CheckConstraint(
            "kg_degree >= 0.0 AND kg_degree <= 5.0",
            name="ck_kg_degree_range",
        ),
        Index("ix_student_knowledge_mastery_node_name", "kg_node_name"),
    )
