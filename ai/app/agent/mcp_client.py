"""MCP 客户端 — 连接远程 MCP Server，获取工具并执行调用

使用 Streamable HTTP 传输协议（/mcp 端点）。
相比 SSE 传输，Streamable HTTP 每次请求都是独立的 HTTP POST，
无需维持长连接，更适合通过代理访问外网 MCP Server。
"""
import asyncio
import logging
import os
from typing import Any

import httpx

from app.config import settings

logger = logging.getLogger(__name__)


def _resolve_proxy() -> str | None:
    """解析代理地址：优先 MCP_PROXY 配置，其次环境变量"""
    return (
        settings.MCP_PROXY
        or os.environ.get("https_proxy")
        or os.environ.get("HTTPS_PROXY")
        or os.environ.get("http_proxy")
        or os.environ.get("HTTP_PROXY")
        or None
    )


class MCPClient:
    """封装 MCP 连接和工具调用

    使用 Streamable HTTP 传输协议连接 MCP Server。
    在应用 lifespan 中通过 async with 管理连接生命周期。

    Usage:
        # 启动时（在 lifespan 中）
        async with mcp_client:
            ...  # 应用运行期间保持连接

        # 运行时调用工具
        result = await mcp_client.call_tool("search", {"query": "408考研"})
    """

    def __init__(self):
        self._session: Any = None
        self._cm_stack: Any = None  # contextlib.AsyncExitStack

    @property
    def is_connected(self) -> bool:
        return self._session is not None

    async def __aenter__(self):
        await self.connect(settings.MCP_SEARCH_URL, settings.MCP_SEARCH_TOKEN)
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()

    async def connect(self, url: str, token: str | None = None) -> bool:
        """连接远程 MCP Server 并注册其工具

        Returns True if connection succeeded, False otherwise.
        """
        if not url:
            logger.info("MCP_SEARCH_URL not configured, skipping MCP connection")
            return False

        try:
            from contextlib import AsyncExitStack

            from mcp.client.session import ClientSession
            from mcp.client.streamable_http import streamablehttp_client

            # Build httpx client factory with proxy support
            # mcp 库会传入 headers, auth, timeout 等关键字参数
            proxy_url = _resolve_proxy()

            def httpx_factory(**kwargs: Any) -> httpx.AsyncClient:
                if proxy_url:
                    kwargs["proxy"] = proxy_url
                    logger.info(f"MCP client using proxy: {proxy_url}")
                return httpx.AsyncClient(**kwargs)

            # Build headers
            headers: dict[str, Any] = {}
            if token:
                headers["Authorization"] = f"Bearer {token}"

            # 使用 AsyncExitStack 管理 streamablehttp_client 和 ClientSession 的生命周期
            # 必须在同一个 async task 中进入和退出上下文管理器
            self._cm_stack = AsyncExitStack()

            # 进入 streamablehttp_client 上下文
            read, write, _ = await self._cm_stack.enter_async_context(
                streamablehttp_client(url, headers=headers, httpx_client_factory=httpx_factory)
            )

            # 进入 ClientSession 上下文
            self._session = await self._cm_stack.enter_async_context(
                ClientSession(read, write)
            )

            # 初始化会话
            await self._session.initialize()

            # 发现工具并注册到 ToolRegistry
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
            if self._cm_stack:
                try:
                    await self._cm_stack.aclose()
                except Exception:
                    pass
                self._cm_stack = None
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
        if self._cm_stack:
            try:
                await self._cm_stack.aclose()
            except Exception:
                pass
            self._cm_stack = None
        self._session = None


# Global singleton
mcp_client = MCPClient()
