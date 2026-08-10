"""Agent-level tool permissions."""

from __future__ import annotations

from collections.abc import Iterable

from app.agent.tool_registry import ToolRegistry


class ToolPolicy:
    """Allowlist policy shared by Agent construction and tool execution."""

    def __init__(self, allowed_tools: Iterable[str] | None = None):
        self.allowed_tools = (
            frozenset(allowed_tools) if allowed_tools is not None else None
        )

    def allows(self, tool_name: str) -> bool:
        return self.allowed_tools is None or tool_name in self.allowed_tools

    def definitions(self) -> list[dict]:
        if self.allowed_tools is None:
            return ToolRegistry.get_definitions()
        return ToolRegistry.get_definitions(self.allowed_tools)
