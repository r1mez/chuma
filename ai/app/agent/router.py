"""HTTP routes for conversational Agents."""

import json
import logging

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from app.agent.builtin import register_builtin_agents
from app.agent.context import AgentContext, bind_agent_context, reset_agent_context
from app.agent.event_serializer import EventSerializer
from app.agent.registry import AgentRegistry
from app.agent.runtime import AgentRuntime
from app.agent.schemas import AgentChatRequest, SocraticHintRequest
from app.agent.session_store import agent_session_store
from app.agent.tool_registry import ToolRegistry
from app.engines.llm.client import LLMClient
from app.engines.llm.profiles import socratic_hint_profile

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


@router.post("/socratic-hint")
async def socratic_hint(req: SocraticHintRequest) -> dict:
    """Generate one safe, structured hint for the practice page.

    The local tool enforces the 60-second rule and selects the hint level;
    the model turns that structured guidance into natural language. Until a
    dedicated fine-tuned model is configured, this uses the existing AI Q&A
    model profile.
    The question answer is intentionally never sent to this endpoint.
    """
    context = AgentContext(
        user_id=req.user_id,
        user_role="student",
        agent_id="student.tutor",
        student_id=req.user_id,
    )
    context_tokens = bind_agent_context(context)

    try:
        tool_result = await ToolRegistry.execute(
            "socratic_hint",
            {
                "question": req.question,
                "student_attempt": req.student_attempt,
                "elapsed_seconds": req.elapsed_seconds,
                "hint_level": req.hint_level,
            },
            req.user_id,
        )
        try:
            tool_payload = json.loads(tool_result.raw)
        except (TypeError, json.JSONDecodeError) as exc:
            raise HTTPException(status_code=502, detail="苏格拉底式提示工具返回了无效结果") from exc

        if not tool_result.success or not tool_payload.get("success"):
            raise HTTPException(
                status_code=400,
                detail=tool_payload.get("summary", "暂时无法生成提示"),
            )

        tool_data = tool_payload.get("data") or {}
        next_question = str(tool_data.get("next_question") or "你认为下一步最需要确认的条件是什么？")
        level = int(tool_data.get("hint_level", req.hint_level))
        system_prompt = (
            "你是计算机科学题目练习中的苏格拉底式助教。"
            "你的任务是帮助学生自己思考，绝对不能直接给出最终答案、正确选项、完整代码或完整推导。"
            "每次只给当前提示层级的一条简短引导，优先使用问题引导学生检查概念、条件、输入输出或反例。"
            "如果学生没有提供思路，就先邀请他写出已知条件和第一步想法。使用中文，控制在2到4句话。"
        )
        user_prompt = (
            f"题目：\n{req.question}\n\n"
            f"学生当前作答/思路：\n{req.student_attempt or '（学生还没有填写具体思路）'}\n\n"
            f"已独立思考时间：{req.elapsed_seconds}秒\n"
            f"当前提示层级：{level}\n"
            f"本层级引导方向：{next_question}\n\n"
            "请根据以上信息生成一条不泄露答案的苏格拉底式提示。"
        )

        source = "ai"
        try:
            response = await LLMClient(default_profile=socratic_hint_profile()).chat(
                [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=0.2,
            )
            content = (response.content or "").strip()
        except Exception as exc:
            logger.warning("Socratic hint model failed, using safe fallback: %s", exc)
            content = next_question
            source = "rule_fallback"

        if not content:
            content = next_question
            source = "rule_fallback"

        return {
            "content": content,
            "hint_level": level,
            "next_question": next_question,
            "rule": str(tool_data.get("rule") or "提示只引导思考，不直接给出最终答案。"),
            "source": source,
        }
    finally:
        reset_agent_context(context_tokens)
