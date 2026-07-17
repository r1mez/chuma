"""Agent 模块数据结构"""
from dataclasses import dataclass, field
from collections.abc import Awaitable, Callable
from typing import Any


@dataclass
class AgentChatRequest:
    """Agent 对话请求"""
    user_id: int
    message: str
    history: list[dict] = field(default_factory=list)


@dataclass
class ToolDef:
    """工具定义 — 本地或 MCP 工具的统一描述"""
    name: str
    description: str
    parameters: dict          # JSON Schema for the tool's parameters
    handler: Callable[..., Awaitable[str]] | None = None  # None for MCP tools
    is_mcp: bool = False

    def to_openai_format(self) -> dict:
        """转为 OpenAI function-calling 格式"""
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.parameters,
            },
        }
