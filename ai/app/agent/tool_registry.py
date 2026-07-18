"""工具注册与调度 — 统一管理本地工具和 MCP 远程工具"""
import logging

from app.agent.schemas import ToolDef

logger = logging.getLogger(__name__)


class ToolRegistry:
    """工具注册中心

    支持两种工具来源：
    1. 本地工具 — 通过 @ToolRegistry.register() 装饰器注册的 Python 函数
    2. MCP 工具 — 通过 ToolRegistry.register_mcp_tool() 注册的远程工具

    Usage:
        @ToolRegistry.register("search_kg", "查询知识图谱", {...})
        async def search_kg(user_id: int, query: str) -> str: ...

        ToolRegistry.register_mcp_tool("search_web", "联网搜索", {...})
    """
    _tools: dict[str, ToolDef] = {}

    @classmethod
    def register(
        cls,
        name: str,
        description: str,
        parameters: dict,
        is_mcp: bool = False,
    ):
        """装饰器 — 注册本地工具处理函数"""
        def decorator(func):
            cls._tools[name] = ToolDef(
                name=name,
                description=description,
                parameters=parameters,
                handler=func,
                is_mcp=is_mcp,
            )
            logger.info(f"Registered local tool: {name}")
            return func
        return decorator

    @classmethod
    def register_mcp_tool(cls, name: str, description: str, parameters: dict):
        """注册 MCP 远程工具（无本地 handler，执行时分发到 MCP 客户端）"""
        cls._tools[name] = ToolDef(
            name=name,
            description=description,
            parameters=parameters,
            handler=None,
            is_mcp=True,
        )
        logger.info(f"Registered MCP tool: {name}")

    @classmethod
    def get_definitions(cls) -> list[dict]:
        """返回所有工具的 OpenAI function-calling 格式定义"""
        return [tool.to_openai_format() for tool in cls._tools.values()]

    @classmethod
    async def execute(cls, name: str, arguments: dict, user_id: int) -> str:
        """执行工具并返回文本结果，自动截断超长内容

        Args:
            name: 工具名称
            arguments: 工具参数（LLM 返回的 JSON 对象）
            user_id: 当前用户 ID

        Returns:
            工具执行结果文本（截断后）
        """
        tool = cls._tools.get(name)
        if tool is None:
            return f"未知工具: {name}"

        try:
            if tool.is_mcp:
                from app.agent.mcp_client import mcp_client
                result = await mcp_client.call_tool(name, arguments)
            elif tool.handler is not None:
                result = await tool.handler(user_id=user_id, **arguments)
            else:
                return f"工具 {name} 没有配置处理器"

            return cls._truncate_result(str(result))
        except Exception as e:
            logger.error(f"Tool '{name}' execution failed: {e}")
            return f"执行出错: {str(e)}"

    @staticmethod
    def _truncate_result(text: str, max_lines: int = 100) -> str:
        """截断超长内容"""
        lines = text.split("\n")
        if len(lines) <= max_lines:
            return text
        omitted = len(lines) - max_lines
        return "\n".join(lines[:max_lines]) + f"\n...（已截断，省略 {omitted} 行）"
