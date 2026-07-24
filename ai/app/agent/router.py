"""Agent API 路由 — 智能体模式对话 SSE 端点"""
import json
import logging

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse

from app.agent.orchestrator import AgentOrchestrator
from app.agent.schemas import AgentChatRequest
from app.dependencies import verify_service_token
from app.engines.llm.client import LLMClient
from app.engines.llm.profiles import deepseek_profile

logger = logging.getLogger(__name__)

router = APIRouter()
auth_dep = [Depends(verify_service_token)]


@router.post("/chat/stream")
async def agent_chat_stream(req: AgentChatRequest):
    """智能体模式 Agent 对话（SSE 流式）

    支持多步推理和工具调用。Agent 会在必要时自动查询知识图谱、
    检索文档或联网搜索，然后整合信息给出回答。
    """
    llm = LLMClient(default_profile=deepseek_profile())
    agent = AgentOrchestrator(user_id=req.user_id, llm_client=llm)

    async def event_stream():
        try:
            async for event in agent.run(req.message, req.history):
                yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"
        except Exception as e:
            logger.error(f"Agent stream error: {e}")
            yield f"data: {json.dumps({'type': 'error', 'content': str(e)}, ensure_ascii=False)}\n\n"
        finally:
            yield "data: [DONE]\n\n"

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
