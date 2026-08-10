"""HTTP routes for conversational Agents."""

import logging

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from app.agent.builtin import register_builtin_agents
from app.agent.context import AgentContext
from app.agent.event_serializer import EventSerializer
from app.agent.registry import AgentRegistry
from app.agent.runtime import AgentRuntime
from app.agent.schemas import AgentChatRequest
from app.agent.session_store import agent_session_store

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


@router.get("/conversations")
async def list_agent_conversations(
    user_id: int,
    user_role: str = "student",
    limit: int = 30,
) -> list[dict]:
    """List the current user's persisted Agent conversations."""

    return await agent_session_store.list_conversations(user_id, user_role, limit)


@router.get("/conversations/{conversation_id}")
async def get_agent_conversation(
    conversation_id: str,
    user_id: int,
    user_role: str = "student",
) -> dict:
    conversation = await agent_session_store.get_conversation(
        user_id,
        user_role,
        conversation_id,
    )
    if conversation is None:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return conversation


@router.delete("/conversations/{conversation_id}")
async def delete_agent_conversation(
    conversation_id: str,
    user_id: int,
    user_role: str = "student",
) -> dict[str, object]:
    deleted = await agent_session_store.delete_conversation(
        user_id,
        user_role,
        conversation_id,
    )
    if not deleted:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return {"deleted": True, "conversation_id": conversation_id}


@router.post("/chat/stream")
async def agent_chat_stream(req: AgentChatRequest):
    """Stream a registered conversational Agent."""

    user_role = req.user_role or "student"
    history = list(req.history)
    if not history:
        history = await agent_session_store.load_history(
            req.user_id,
            user_role,
            req.conversation_id,
        )
    context = AgentContext(
        user_id=req.user_id,
        user_role=user_role,
        agent_id=req.agent_id,
        student_id=req.student_id,
        teacher_id=req.teacher_id,
        class_id=req.class_id,
        course_id=req.course_id,
        kg_graph_ids=tuple(req.kg_graph_ids),
        graph_names=tuple(req.graph_names),
        history=tuple(history),
        message_id=req.message_id,
        conversation_id=req.conversation_id,
    )
    runtime = AgentRuntime.default()

    async def event_stream():
        events: list[dict] = []
        answer_parts: list[str] = []
        run_id: str | None = None
        status = "failed"
        try:
            async for event in runtime.stream(
                agent_id=req.agent_id,
                context=context,
                message=req.message,
            ):
                events.append(event)
                run_id = event.get("run_id") or run_id
                if event.get("event") == "answer.delta":
                    delta = event.get("data", {}).get("delta", "")
                    if delta:
                        answer_parts.append(delta)
                if event.get("event") == "run.completed":
                    status = "success"
                elif event.get("event") == "run.failed":
                    status = "failed"
                yield EventSerializer.to_sse(event)
        except Exception as e:
            logger.error("Agent stream error: %s", e, exc_info=True)
            yield EventSerializer.error("Agent service unavailable")
        finally:
            await agent_session_store.persist_exchange(
                req.user_id,
                user_role,
                req.conversation_id,
                req.message,
                "".join(answer_parts),
                agent_id=req.agent_id,
            )
            await agent_session_store.persist_run(
                req.user_id,
                user_role,
                req.conversation_id,
                run_id,
                req.agent_id,
                status,
                events,
            )
            yield EventSerializer.done()

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
