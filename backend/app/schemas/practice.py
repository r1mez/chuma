"""Practice Pydantic 请求/响应模型"""
from datetime import datetime
from typing import Optional, Any
from pydantic import BaseModel, Field


class QuestionCreate(BaseModel):
    question_description: str
    question_answer: str
    question_options: Optional[Any] = None
    question_type: str
    question_difficulty: int
    question_explanation: Optional[str] = None
    course_id: int
    kg_node_name: Optional[str] = None


class QuestionResponse(BaseModel):
    question_id: int
    question_description: str
    question_answer: str
    question_options: Optional[Any] = None
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
    course_id: int
    assignment_id: Optional[int] = None
    kg_node_name: Optional[str] = None
    question_type: str
    question_difficulty: int
    do_stu_answer: str


class ExerciseRecordResponse(BaseModel):
    do_id: int
    question_id: int
    stu_id: int
    kg_id: Optional[int] = None
    course_id: Optional[int] = None
    kg_node_name: Optional[str] = None
    question_type: Optional[str] = None
    question_difficulty: Optional[int] = None
    do_stu_answer: str
    do_score: Optional[float] = None
    do_isTrue: Optional[bool] = None
    iserror_firstly: Optional[bool] = None
    created_at: datetime
    class Config:
        from_attributes = True


class ExerciseRecordListResponse(BaseModel):
    """做题记录列表响应（含题目题干和学科名称）"""
    do_id: int
    question_id: int
    question_description: str
    course_name: Optional[str] = None
    question_type: Optional[str] = None
    question_difficulty: Optional[int] = None
    do_stu_answer: str
    do_score: Optional[float] = None
    do_isTrue: Optional[bool] = None
    kg_node_name: Optional[str] = None
    created_at: datetime
    class Config:
        from_attributes = True


class SocraticHintRequest(BaseModel):
    """练习过程中的分级苏格拉底式求助请求。"""

    question_id: int = Field(..., ge=1)
    student_attempt: str = Field(default="", max_length=10000)
    elapsed_seconds: int = Field(..., ge=0)
    hint_level: int = Field(default=1, ge=1, le=3)


class SocraticHintResponse(BaseModel):
    """AI 返回的安全提示，不包含题目的标准答案。"""

    content: str
    hint_level: int
    next_question: str
    rule: str
    source: str = "ai"
