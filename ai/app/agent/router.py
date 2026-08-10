"""HTTP routes for conversational Agents."""

import json
import logging

from fastapi import APIRouter
from fastapi.responses import StreamingResponse

from app.agent.builtin import register_builtin_agents
from app.agent.context import AgentContext
from app.agent.registry import AgentRegistry
from app.agent.runtime import AgentRuntime
from app.agent.schemas import AgentChatRequest
from app.engines.llm.client import LLMClient
from app.engines.llm.profiles import deepseek_profile

logger = logging.getLogger(__name__)

router = APIRouter()
register_builtin_agents()


@router.get("/catalog")
async def agent_catalog() -> list[dict[str, str]]:
    """Return the registered Agent catalog for diagnostics and future UI use."""

    return [
        {
            "agent_id": item.agent_id,
            "display_name": item.display_name,
            "description": item.description,
            "mode": item.mode,
        }
        for item in AgentRegistry.list()
    ]


@router.post("/chat/stream")
async def agent_chat_stream(req: AgentChatRequest):
    """Stream a registered conversational Agent."""

    llm = LLMClient(default_profile=deepseek_profile())
    context = AgentContext(
        user_id=req.user_id,
        user_role=req.user_role or "student",
        agent_id=req.agent_id,
        student_id=req.student_id,
        teacher_id=req.teacher_id,
        class_id=req.class_id,
        course_id=req.course_id,
        kg_graph_ids=tuple(req.kg_graph_ids),
        graph_names=tuple(req.graph_names),
        history=tuple(req.history),
        message_id=req.message_id,
    )
    runtime = AgentRuntime(llm_client=llm)

    async def event_stream():
        try:
            async for event in runtime.stream(
                agent_id=req.agent_id,
                context=context,
                message=req.message,
            ):
                event_id = event.get("event_id", "")
                event_name = event.get("event", "message")
                yield (
                    f"id: {event_id}\n"
                    f"event: {event_name}\n"
                    f"data: {json.dumps(event, ensure_ascii=False)}\n\n"
                )
        except Exception as e:
            logger.error("Agent stream error: %s", e, exc_info=True)
            yield f"data: {json.dumps({'type': 'error', 'content': 'Agent service unavailable'}, ensure_ascii=False)}\n\n"
        finally:
            yield "data: [DONE]\n\n"

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
