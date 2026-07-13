"""AI 网关 — 代理转发到 ai/ 服务"""

import httpx
from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse

from app.core.config import settings

router = APIRouter()


def _ai_headers() -> dict[str, str]:
    """构造转发到 AI 引擎的请求头（含服务间认证 token）"""
    return {"X-Service-Token": settings.AI_SERVICE_TOKEN}


@router.post("/chat/quick")
async def chat_quick(request: Request):
    """快速回答 — SSE 透传到 AI 引擎"""
    body = await request.json()

    async def proxy_stream():
        try:
            async with httpx.AsyncClient(timeout=120.0) as client:
                async with client.stream(
                    "POST",
                    f"{settings.AI_SERVICE_URL}/rag/query/stream",
                    headers=_ai_headers(),
                    json=body,
                ) as resp:
                    async for chunk in resp.aiter_bytes():
                        yield chunk
        except httpx.RemoteProtocolError:
            pass

    return StreamingResponse(
        proxy_stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.post("/chat/deep")
async def deep_chat(request: Request):
    """深度解答 — SSE 透传到 AI 引擎（调用 DeepSeek）"""
    body = await request.json()

    async def proxy_stream():
        try:
            async with httpx.AsyncClient(timeout=120.0) as client:
                async with client.stream(
                    "POST",
                    f"{settings.AI_SERVICE_URL}/rag/chat/deep/stream",
                    headers=_ai_headers(),
                    json=body,
                ) as resp:
                    async for chunk in resp.aiter_bytes():
                        yield chunk
        except httpx.RemoteProtocolError:
            pass

    return StreamingResponse(
        proxy_stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.post("/recommend")
async def recommend_questions():
    """GNN 题目推荐 — 转发到 ai/ 服务"""
    pass
