"""AI 网关 — 代理转发到 ai/ 服务"""

import httpx
from fastapi import APIRouter

from app.core.config import settings

router = APIRouter()


def _ai_headers() -> dict[str, str]:
    """构造转发到 AI 引擎的请求头（含服务间认证 token）"""
    return {"X-Service-Token": settings.AI_SERVICE_TOKEN}


@router.post("/chat/quick")
async def quick_chat():
    """快速问答 — 转发到 ai/ 服务，使用微调小模型"""
    # TODO: async with httpx.AsyncClient() as client:
    #     resp = await client.post(f"{settings.AI_SERVICE_URL}/rag/query", json={...}, headers=_ai_headers())
    pass


@router.post("/chat/deep")
async def deep_chat():
    """深度解答 — 转发到 ai/ 服务，使用 GraphRAG + 远程大模型"""
    pass


@router.post("/recommend")
async def recommend_questions():
    """GNN 题目推荐 — 转发到 ai/ 服务"""
    pass
