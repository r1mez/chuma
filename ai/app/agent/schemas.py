"""Shared Agent request and tool schemas."""

from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field


class AgentChatRequest(BaseModel):
    """Request for a conversational Agent."""

    # Kept optional for backward compatibility with direct AI-engine callers.
    # The backend gateway should always inject the authenticated user ID.
    user_id: int = 1
    agent_id: str = "student.tutor"
    user_role: str | None = None
    message: str
    history: list[dict] = Field(default_factory=list)
    kg_graph_ids: list[int] = Field(default_factory=list)
    graph_names: list[str] = Field(default_factory=list)
    student_id: int | None = None
    teacher_id: int | None = None
    class_id: int | None = None
    course_id: int | None = None
    message_id: str = Field(default_factory=lambda: f"msg_{uuid4().hex}")


@dataclass
class ToolDef:
    """Unified description of a local or MCP tool."""

    name: str
    description: str
    parameters: dict
    handler: Callable[..., Awaitable[str]] | None = None
    is_mcp: bool = False
    display_name: str | None = None
    purpose: str | None = None

    def to_openai_format(self) -> dict:
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.parameters,
            },
        }


@dataclass
class ToolExecutionResult:
    """Internal tool result plus a safe summary for the UI."""

    raw: str
    success: bool
    summary: str
    duration_ms: int
    metrics: dict[str, int | float | str]
    error_code: str | None = None
    error_message: str | None = None
    retryable: bool = False
