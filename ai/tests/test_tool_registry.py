import pytest
from app.agent.tool_registry import ToolRegistry


class TestToolRegistry:
    def setup_method(self):
        """Reset registry before each test"""
        ToolRegistry._tools = {}

    @pytest.mark.asyncio
    async def test_register_and_execute_local_tool(self):
        @ToolRegistry.register(
            name="echo",
            description="Echo back the input",
            parameters={"type": "object", "properties": {"text": {"type": "string"}}, "required": ["text"]},
        )
        async def echo(user_id: int, text: str) -> str:
            return f"user={user_id} says {text}"

        result = await ToolRegistry.execute("echo", {"text": "hello"}, user_id=42)
        assert result == "user=42 says hello"

    @pytest.mark.asyncio
    async def test_unknown_tool_returns_error(self):
        result = await ToolRegistry.execute("nonexistent", {}, user_id=1)
        assert "未知工具" in result

    def test_get_definitions_returns_openai_format(self):
        ToolRegistry._tools = {}

        @ToolRegistry.register(
            name="test_tool",
            description="A test tool",
            parameters={"type": "object", "properties": {}},
        )
        async def test_tool(user_id: int) -> str:
            return "ok"

        defs = ToolRegistry.get_definitions()
        assert len(defs) == 1
        assert defs[0]["type"] == "function"
        assert defs[0]["function"]["name"] == "test_tool"

    def test_truncate_result_under_limit(self):
        text = "line1\nline2\nline3"
        result = ToolRegistry._truncate_result(text, max_lines=5)
        assert result == text

    def test_truncate_result_over_limit(self):
        lines = [f"line{i}" for i in range(200)]
        text = "\n".join(lines)
        result = ToolRegistry._truncate_result(text, max_lines=100)
        result_lines = result.split("\n")
        assert len(result_lines) == 101  # 100 lines + truncation marker
        assert "已截断" in result_lines[-1]
        assert "省略 100 行" in result_lines[-1]

    @pytest.mark.asyncio
    async def test_register_mcp_tool(self):
        ToolRegistry.register_mcp_tool(
            name="remote_search",
            description="Search remotely",
            parameters={"type": "object", "properties": {}},
        )
        assert "remote_search" in ToolRegistry._tools
        assert ToolRegistry._tools["remote_search"].is_mcp
