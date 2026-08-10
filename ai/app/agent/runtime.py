"""Unified Agent runtime."""

from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Any

from app.agent.context import AgentContext
from app.agent.registry import AgentRegistry
from app.engines.llm.client import LLMClient


class AgentRuntime:
    """Resolve and run an Agent without coupling routes to concrete classes."""

    def __init__(self, llm_client: LLMClient):
        self.llm = llm_client

    def resolve(self, agent_id: str, context: AgentContext):
        definition = AgentRegistry.get(agent_id)
        if definition.allowed_roles and context.user_role not in definition.allowed_roles:
            raise PermissionError(f"Role {context.user_role!r} cannot use {agent_id}")
        agent = definition.factory(context, self.llm)
        # Existing chat Agents expose this attribute; workflow adapters can
        # opt into the same policy later without changing the registry API.
        if definition.allowed_tools is not None and hasattr(agent, "allowed_tools"):
            agent.allowed_tools = definition.allowed_tools
        return definition, agent

    async def stream(
        self,
        agent_id: str,
        context: AgentContext,
        message: str,
    ) -> AsyncIterator[dict]:
        definition, agent = self.resolve(agent_id, context)
        if definition.mode != "chat":
            raise TypeError(f"Agent {agent_id} is not a chat Agent")

        async for event in agent.run(
            message,
            history=list(context.history),
            kg_graph_ids=list(context.kg_graph_ids),
            graph_names=list(context.graph_names),
            message_id=context.message_id,
            context=context,
        ):
            yield event

    async def execute(
        self,
        agent_id: str,
        context: AgentContext,
        payload: dict[str, Any] | None = None,
    ) -> Any:
        """Run a structured workflow Agent through the same registry."""

        definition = AgentRegistry.get(agent_id)
        if definition.allowed_roles and context.user_role not in definition.allowed_roles:
            raise PermissionError(f"Role {context.user_role!r} cannot use {agent_id}")
        if definition.mode != "workflow" or definition.executor is None:
            raise TypeError(f"Agent {agent_id} is not a workflow Agent")
        return await definition.executor(context, self.llm, payload or {})
