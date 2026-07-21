"""知识图谱构建 Pipeline 的数据模型"""

from __future__ import annotations

import uuid
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class EntityType(str, Enum):
    """预定义的计算机学科实体类型"""
    CHAPTER = "Chapter"           # 章（标题层级第1层）
    CONCEPT = "Concept"
    ALGORITHM = "Algorithm"
    DATA_STRUCTURE = "DataStructure"
    PROTOCOL = "Protocol"
    PRINCIPLE = "Principle"
    TERM = "Term"
    TECHNOLOGY = "Technology"
    MODEL = "Model"


class KGNode(BaseModel):
    """知识图谱节点 — 对应 AGE 中的一个 Vertex"""
    id: str
    name: str = ""
    type: EntityType
    description: str = ""
    source_chunk_index: Optional[int] = None

    def __init__(self, **data):
        if not data.get("name"):
            data["name"] = data.get("id", "")
        super().__init__(**data)


class KGEdge(BaseModel):
    """知识图谱边 — 对应 AGE 中的一条 Edge"""
    source_node_id: str
    target_node_id: str
    relationship_name: str
    description: Optional[str] = None


class KnowledgeGraph(BaseModel):
    """单个切片的知识图谱"""
    nodes: list[KGNode] = Field(default_factory=list)
    edges: list[KGEdge] = Field(default_factory=list)


class DocumentChunk(BaseModel):
    """文档切片"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    text: str
    chunk_index: int = 0
    chunk_size: int = 0
    heading_path: list[str] = []      # 如 ["第3章 栈和队列", "3.1 栈"]
    heading_levels: list[int] = []    # 如 [2, 3]


class PipelineResult(BaseModel):
    """Pipeline 执行结果统计"""
    chunks: int = 0
    nodes: int = 0
    edges: int = 0
    status: str = "pending"
    error: Optional[str] = None
