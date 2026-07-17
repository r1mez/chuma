import json
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from app.engines.llm.client import LLMClient, ChatResponse, ToolCall


def make_mock_response(content=None, tool_calls=None):
    """Helper: build a mock httpx response"""
    msg = {}
    if content is not None:
        msg["content"] = content
    if tool_calls is not None:
        msg["tool_calls"] = tool_calls
    return {"choices": [{"message": msg}]}


def _make_mock_httpx(json_data: dict):
    """Build a mock httpx.AsyncClient that returns json_data from post().json()"""
    mock_response = MagicMock()
    mock_response.json.return_value = json_data

    mock_client = AsyncMock()
    mock_client.post = AsyncMock(return_value=mock_response)
    # async with client: -> client.__aenter__ -> returns client
    mock_client.__aenter__.return_value = mock_client
    return mock_client


class TestChatResponse:
    def test_content_only(self):
        resp = ChatResponse(content="hello")
        assert resp.content == "hello"
        assert resp.tool_calls is None

    def test_tool_calls_only(self):
        tc = ToolCall(id="call_1", name="search_kg", arguments={"query": "test"})
        resp = ChatResponse(tool_calls=[tc])
        assert resp.content is None
        assert len(resp.tool_calls) == 1
        assert resp.tool_calls[0].name == "search_kg"

    def test_defaults(self):
        resp = ChatResponse()
        assert resp.content is None
        assert resp.tool_calls is None


class TestLLMClientToolCalling:
    @pytest.mark.asyncio
    async def test_chat_with_tools_passes_them_to_api(self):
        """Verify tools are included in the API request payload"""
        client = LLMClient()

        json_data = make_mock_response(content="I'll search for that")
        mock_client = _make_mock_httpx(json_data)

        with patch("httpx.AsyncClient", return_value=mock_client):
            tools = [{
                "type": "function",
                "function": {"name": "search", "description": "search", "parameters": {}}
            }]
            await client.chat(
                [{"role": "user", "content": "hi"}],
                tools=tools,
            )

        call_args = mock_client.post.call_args
        payload = call_args[1]["json"]
        assert "tools" in payload
        assert payload["tools"] == tools
        assert payload["tool_choice"] == "auto"

    @pytest.mark.asyncio
    async def test_chat_parses_tool_calls(self):
        """Verify tool_calls from API response are parsed correctly"""
        client = LLMClient()

        json_data = make_mock_response(tool_calls=[{
            "id": "call_abc",
            "type": "function",
            "function": {
                "name": "search_kg",
                "arguments": '{"query": "红黑树"}',
            }
        }])
        mock_client = _make_mock_httpx(json_data)

        with patch("httpx.AsyncClient", return_value=mock_client):
            response = await client.chat([{"role": "user", "content": "hi"}])

        assert response.tool_calls is not None
        assert len(response.tool_calls) == 1
        assert response.tool_calls[0].id == "call_abc"
        assert response.tool_calls[0].name == "search_kg"
        assert response.tool_calls[0].arguments == {"query": "红黑树"}

    @pytest.mark.asyncio
    async def test_chat_without_tools_returns_content(self):
        """Backward compatibility: no tools -> normal content"""
        client = LLMClient()

        json_data = make_mock_response(content="Hello!")
        mock_client = _make_mock_httpx(json_data)

        with patch("httpx.AsyncClient", return_value=mock_client):
            response = await client.chat([{"role": "user", "content": "hi"}])

        assert response.content == "Hello!"
        assert response.tool_calls is None
