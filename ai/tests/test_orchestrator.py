import pytest
from unittest.mock import AsyncMock, patch

from app.agent.orchestrator import AgentOrchestrator
from app.agent.tool_registry import ToolRegistry
from app.engines.llm.client import ChatResponse


class FakeLLMClient:
    """Mock LLM client for testing orchestrator"""
    def __init__(self, responses: list[ChatResponse]):
        self.responses = responses
        self.call_count = 0
        self.chat_calls = []

    async def chat(self, messages, temperature=0.7, profile=None, tools=None):
        self.chat_calls.append({"messages": messages, "tools": tools})
        if self.call_count < len(self.responses):
            resp = self.responses[self.call_count]
            self.call_count += 1
            return resp
        return ChatResponse(content="Default answer")

    async def stream(self, messages, temperature=0.7, profile=None, tools=None):
        for char in "streamed answer":
            yield {"content": char, "reasoning": ""}


class TestAgentOrchestrator:
    @pytest.mark.asyncio
    async def test_simple_answer_no_tools(self):
        """When LLM returns content directly, stream it to user"""
        client = FakeLLMClient([ChatResponse(content="你好！有什么可以帮助你的？")])
        agent = AgentOrchestrator(user_id=1, llm_client=client)

        chunks = []
        async for chunk in agent.run("你好", []):
            chunks.append(chunk)

        assert any(c["type"] == "content" for c in chunks)
        assert any(c["type"] == "done" for c in chunks)

    @pytest.mark.asyncio
    async def test_single_tool_call_loop(self):
        """When LLM calls a tool, execute it and continue"""
        from app.engines.llm.client import ToolCall

        # First response: tool call, second: content
        client = FakeLLMClient([
            ChatResponse(tool_calls=[
                ToolCall(id="call_1", name="search_kg", arguments={"query": "红黑树"})
            ]),
            ChatResponse(content="根据知识图谱查询，红黑树是一种自平衡二叉查找树..."),
        ])
        agent = AgentOrchestrator(user_id=1, llm_client=client)

        chunks = []
        async for chunk in agent.run("什么是红黑树", []):
            chunks.append(chunk)

        # Should have tool_used and tool_result events
        types = [c["type"] for c in chunks]
        assert "tool_used" in types
        assert "tool_result" in types
        assert "content" in types
        assert "done" in types

    @pytest.mark.asyncio
    async def test_max_turns_enforced(self):
        """After 10 tool-calling turns, force final answer"""
        from app.engines.llm.client import ToolCall

        # All responses are tool calls (never converges)
        responses = [
            ChatResponse(tool_calls=[
                ToolCall(id=f"call_{i}", name="search_kg", arguments={"query": f"q{i}"})
            ])
            for i in range(12)
        ]
        client = FakeLLMClient(responses)
        agent = AgentOrchestrator(user_id=1, llm_client=client)

        chunks = []
        async for chunk in agent.run("问题", []):
            chunks.append(chunk)

        # Must eventually produce done
        assert any(c["type"] == "done" for c in chunks)
        # Must not exceed 10 + 1 (force) turns worth of tool calls
        tool_used_count = sum(1 for c in chunks if c["type"] == "tool_used")
        assert tool_used_count <= 11  # 10 normal + 1 forced


class TestReadDocumentTool:
    """read_document 工具 — 验证薄封装行为"""

    @pytest.mark.asyncio
    async def test_tool_delegates_to_pipeline(self):
        """read_document 应委托给 RagPipeline.run()"""
        with patch("app.agent.tools.read_document.RagPipeline") as MockPipeline:
            mock_instance = AsyncMock()
            mock_instance.run.return_value = "模拟结果"
            MockPipeline.return_value = mock_instance

            result = await ToolRegistry.execute(
                "read_document",
                {"query": "共享栈", "top_k": 3, "detail_level": "subgraph"},
                user_id=1,
            )

            assert "模拟结果" in result
            mock_instance.run.assert_called_once_with(
                query="共享栈", top_k=3,
                detail_level="subgraph", course_id=None,
            )

    @pytest.mark.asyncio
    async def test_tool_with_course_id(self):
        """course_id 参数应透传到 pipeline"""
        with patch("app.agent.tools.read_document.RagPipeline") as MockPipeline:
            mock_instance = AsyncMock()
            mock_instance.run.return_value = "结果"
            MockPipeline.return_value = mock_instance

            await ToolRegistry.execute(
                "read_document",
                {"query": "栈", "course_id": 1},
                user_id=1,
            )

            mock_instance.run.assert_called_once_with(
                query="栈", top_k=5,
                detail_level="text", course_id=1,
            )

    @pytest.mark.asyncio
    async def test_tool_handles_pipeline_error(self):
        """pipeline 异常时应返回友好错误信息"""
        with patch("app.agent.tools.read_document.RagPipeline") as MockPipeline:
            mock_instance = AsyncMock()
            mock_instance.run.side_effect = Exception("数据库连接失败")
            MockPipeline.return_value = mock_instance

            result = await ToolRegistry.execute(
                "read_document",
                {"query": "共享栈"},
                user_id=1,
            )

            assert "检索失败" in result or "数据库" in result

