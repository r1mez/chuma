"""MCP SSE 客户端 — 连接远程 MCP Server，获取工具并执行调用"""
import asyncio
import logging
from typing import Any

logger = logging.getLogger(__name__)


class MCPClient:
    """封装 MCP SSE 连接和工具调用

    Usage:
        # 启动时初始化
        mcp_client = MCPClient()
        await mcp_client.connect("http://mcp-server:8080/sse")
        # 工具会自动注册到 ToolRegistry

        # 运行时调用工具
        result = await mcp_client.call_tool("search_web", {"query": "408考研"})
    """

    def __init__(self):
        self._session = None
        self._read = None
        self._write = None
        self._url: str = ""
        self._token: str | None = None

    @property
    def is_connected(self) -> bool:
        return self._session is not None

    async def connect(self, url: str, token: str | None = None) -> bool:
        """连接远程 MCP Server 并注册其工具

        Returns True if connection succeeded, False otherwise.
        """
        if not url:
            logger.info("MCP_SEARCH_URL not configured, skipping MCP connection")
            return False

        self._url = url
        self._token = token

        try:
            from mcp.client.session import ClientSession
            from mcp.client.sse import sse_client

            # Build headers
            headers = {}
            if token:
                headers["Authorization"] = f"Bearer {token}"

            self._read, self._write = await sse_client(url, headers=headers)
            self._session = ClientSession(self._read, self._write)
            await self._session.initialize()

            # Discover tools and register to ToolRegistry
            tools_result = await self._session.list_tools()
            from app.agent.tool_registry import ToolRegistry

            for tool in tools_result.tools:
                ToolRegistry.register_mcp_tool(
                    name=tool.name,
                    description=tool.description or "",
                    parameters=tool.inputSchema if hasattr(tool, 'inputSchema') else {},
                )
                logger.info(f"Discovered MCP tool: {tool.name}")

            logger.info(f"MCP connected to {url}, {len(tools_result.tools)} tools discovered")
            return True

        except ImportError:
            logger.warning("mcp package not installed, MCP tools unavailable")
            return False
        except Exception as e:
            logger.error(f"MCP connection failed: {e}")
            self._session = None
            self._read = None
            self._write = None
            return False

    async def call_tool(self, name: str, arguments: dict[str, Any]) -> str:
        """调用 MCP Server 的工具"""
        if not self._session:
            return "搜索服务暂不可用（MCP 未连接）"

        try:
            result = await asyncio.wait_for(
                self._session.call_tool(name, arguments),
                timeout=10.0,
            )

            # Extract text from content blocks
            parts = []
            for block in result.content:
                if hasattr(block, "text"):
                    parts.append(block.text)
                elif hasattr(block, "data"):
                    parts.append(str(block.data))
                else:
                    parts.append(str(block))
            return "\n".join(parts) if parts else "(empty result)"

        except asyncio.TimeoutError:
            return "工具调用超时"
        except Exception as e:
            logger.error(f"MCP tool '{name}' failed: {e}")
            return f"搜索服务异常: {str(e)}"

    async def close(self):
        """关闭 MCP 连接"""
        if self._session:
            try:
                await self._session.__aexit__(None, None, None)
            except Exception:
                pass
            self._session = None
            self._read = None
            self._write = None


# Global singleton
mcp_client = MCPClient()
