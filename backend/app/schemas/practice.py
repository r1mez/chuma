"""Practice Pydantic 请求/响应模型"""
from datetime import datetime
from typing import Optional
from pydantic import BaseModel


class QuestionCreate(BaseModel):
    question_description: str
    question_answer: str
    question_options: Optional[dict] = None
    question_type: str
    question_difficulty: int
    question_explanation: Optional[str] = None
    course_id: int
    kg_node_name: Optional[str] = None


class QuestionResponse(BaseModel):
    question_id: int
    question_description: str
    question_answer: str
    question_options: Optional[dict] = None
    question_type: str
    question_difficulty: int
    question_explanation: Optional[str] = None
    course_id: int
    kg_node_name: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    class Config:
        from_attributes = True


class ExerciseRecordCreate(BaseModel):
    question_id: int
    kg_node_name: Optional[str] = None
    do_stu_answer: str


class ExerciseRecordResponse(BaseModel):
    do_id: int
    question_id: int
    stu_id: int
    kg_node_name: Optional[str] = None
    do_stu_answer: str
    do_score: Optional[float] = None
    created_at: datetime
    class Config:
        from_attributes = True
