"""Agent registry and definitions."""

from __future__ import annotations

from dataclasses import dataclass, field
from collections.abc import Awaitable
from typing import Any, Callable

from app.agent.context import AgentContext
from app.engines.llm.client import LLMClient


AgentFactory = Callable[[AgentContext, LLMClient], Any]
AgentExecutor = Callable[[AgentContext, LLMClient, dict[str, Any]], Awaitable[Any]]


@dataclass(frozen=True)
class AgentDefinition:
    agent_id: str
    display_name: str
    description: str
    mode: str
    factory: AgentFactory
    executor: AgentExecutor | None = None
    allowed_roles: frozenset[str] = field(default_factory=frozenset)
    allowed_tools: frozenset[str] | None = None


class AgentRegistry:
    """In-process registry used to resolve business Agents by stable IDs."""

    _definitions: dict[str, AgentDefinition] = {}

    @classmethod
    def register(cls, definition: AgentDefinition) -> AgentDefinition:
        if definition.agent_id in cls._definitions:
            raise ValueError(f"Agent already registered: {definition.agent_id}")
        cls._definitions[definition.agent_id] = definition
        return definition

    @classmethod
    def get(cls, agent_id: str) -> AgentDefinition:
        try:
            return cls._definitions[agent_id]
        except KeyError as exc:
            available = ", ".join(sorted(cls._definitions)) or "none"
            raise LookupError(
                f"Unknown Agent: {agent_id}; available Agents: {available}"
            ) from exc

    @classmethod
    def list(cls) -> list[AgentDefinition]:
        return list(cls._definitions.values())

    @classmethod
    def clear(cls) -> None:
        """Testing-only reset hook."""
        cls._definitions.clear()
