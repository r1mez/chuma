"""GraphRAG 请求/响应模型"""

from pydantic import BaseModel


class RAGQueryRequest(BaseModel):
    question: str
    mode: str = "deep"  # "quick" | "deep"


class RAGQueryResponse(BaseModel):
    answer: str
    sources: list[dict]  # 引用来源
    confidence: float
