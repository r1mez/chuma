"""KgGraph Pydantic 校验模型"""

from datetime import datetime

from pydantic import BaseModel


class KgGraphCreate(BaseModel):
    """创建图谱时的入参（内部使用）"""
    user_id: int
    original_filename: str
    file_path: str
    graph_name: str


class KgGraphResponse(BaseModel):
    """返回给前端的图谱信息"""
    id: int
    graph_name: str
    original_filename: str
    node_count: int
    edge_count: int
    chunk_count: int
    status: str
    created_at: datetime

    class Config:
        from_attributes = True
