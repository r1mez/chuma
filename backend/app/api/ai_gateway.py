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


@router.post("/agent/chat")
async def agent_chat(request: Request):
    """智能体模式对话 — SSE 透传到 AI 引擎 Agent 路由"""
    body = await request.json()
    # Inject current user ID from auth context
    user = getattr(request.state, "user", None)
    if user and "user_id" not in body:
        body["user_id"] = user.get("id", 1)

    # Resolve kg_graph_ids → graph_names
    kg_graph_ids: list[int] = body.get("kg_graph_ids", [])
    graph_names: list[str] = []
    if kg_graph_ids:
        from app.core.database import async_session
        from app.services.kg_graph_service import KgGraphService
        kg_service = KgGraphService()
        async with async_session() as db:
            for gid in kg_graph_ids:
                graph = await kg_service.get_graph_by_id(gid, db)
                if graph and graph.graph_name:
                    graph_names.append(graph.graph_name)
    else:
        # 未选教材 → 查询全部图谱
        from app.core.database import async_session
        from app.services.kg_graph_service import KgGraphService
        kg_service = KgGraphService()
        async with async_session() as db:
            all_graphs = await kg_service.list_graphs(db)
            graph_names = [g.graph_name for g in all_graphs]
            kg_graph_ids = [g.id for g in all_graphs]

    body["kg_graph_ids"] = kg_graph_ids
    body["graph_names"] = graph_names

    async def proxy_stream():
        try:
            async with httpx.AsyncClient(timeout=180.0) as client:
                async with client.stream(
                    "POST",
                    f"{settings.AI_SERVICE_URL}/agent/chat/stream",
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
