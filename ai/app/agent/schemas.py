"""Agent 模块数据结构"""
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any

from pydantic import BaseModel, Field


class AgentChatRequest(BaseModel):
    """Agent 对话请求"""
    user_id: int = 1  # TODO 暂时默认 1，登录实现后改为必填
    message: str
    history: list[dict] = Field(default_factory=list)


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
