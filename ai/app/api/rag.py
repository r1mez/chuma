"""GraphRAG 查询路由"""

from fastapi import APIRouter

router = APIRouter()


@router.post("/query")
async def rag_query():
    """GraphRAG 增强问答 — 检索知识图谱 + 远程大模型生成"""
    pass


@router.post("/query/stream")
async def rag_query_stream():
    """GraphRAG 流式问答（SSE）"""
    pass
