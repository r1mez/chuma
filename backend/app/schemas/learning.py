"""Learning Pydantic 请求/响应模型 — 掌握度"""
from datetime import datetime
from pydantic import BaseModel


class StudentCourseMasteryCreate(BaseModel):
    course_id: int
    course_degree: float


class StudentCourseMasteryResponse(BaseModel):
    stu_id: int
    course_id: int
    course_degree: float
    updated_at: datetime
    class Config:
        from_attributes = True


class StudentKnowledgeMasteryCreate(BaseModel):
    kg_node_name: str
    kg_degree: float


class StudentKnowledgeMasteryResponse(BaseModel):
    stu_id: int
    kg_node_name: str
    kg_degree: float
    updated_at: datetime
    class Config:
        from_attributes = True
