"""Shared runtime context for Agent executions."""

from __future__ import annotations

from contextvars import ContextVar, Token
from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class AgentContext:
    """Identity, authorization scope, and conversation state for one run."""

    user_id: int
    user_role: str | None = None
    agent_id: str = "student.tutor"
    student_id: int | None = None
    teacher_id: int | None = None
    class_id: int | None = None
    course_id: int | None = None
    kg_graph_ids: tuple[int, ...] = ()
    graph_names: tuple[str, ...] = ()
    history: tuple[dict[str, Any], ...] = ()
    message_id: str | None = None
    conversation_id: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


current_agent_context: ContextVar[AgentContext | None] = ContextVar(
    "agent_context", default=None
)
current_kg_graph_ids: ContextVar[list[int]] = ContextVar("kg_graph_ids", default=[])
current_graph_names: ContextVar[list[str]] = ContextVar("graph_names", default=[])


@dataclass(frozen=True)
class AgentContextTokens:
    context: Token[AgentContext | None]
    kg_graph_ids: Token[list[int]]
    graph_names: Token[list[str]]


def bind_agent_context(context: AgentContext) -> AgentContextTokens:
    """Bind context to the current async task so tools can read it safely."""

    return AgentContextTokens(
        context=current_agent_context.set(context),
        kg_graph_ids=current_kg_graph_ids.set(list(context.kg_graph_ids)),
        graph_names=current_graph_names.set(list(context.graph_names)),
    )


def reset_agent_context(tokens: AgentContextTokens) -> None:
    """Restore the previous context and prevent request-to-request leakage."""

    current_graph_names.reset(tokens.graph_names)
    current_kg_graph_ids.reset(tokens.kg_graph_ids)
    current_agent_context.reset(tokens.context)
