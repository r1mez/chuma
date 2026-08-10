"""AI 简答题（Q_A）评分路由"""

import logging

from fastapi import APIRouter
from pydantic import BaseModel, Field

from app.agent.context import AgentContext
from app.agent.runtime import AgentRuntime

logger = logging.getLogger(__name__)

router = APIRouter()


class QaScoreRequest(BaseModel):
    question_description: str = Field(..., description="题目题干")
    question_answer: str = Field(..., description="标准答案")
    stu_answer: str = Field(..., description="学生回答")


@router.post("/qa_score")
async def qa_score(req: QaScoreRequest):
    """对简答题作答进行大模型评分（满分 10 分，float）

    根据题目题干、标准答案与学生回答，由大模型酌情给分。
    """
    result = await AgentRuntime.default().execute(
        "student.qa_score",
        AgentContext(
            user_id=0,
            user_role="service",
            agent_id="student.qa_score",
        ),
        {
            "question_description": req.question_description,
            "question_answer": req.question_answer,
            "stu_answer": req.stu_answer,
        },
    )
    return result
