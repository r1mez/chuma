"""统一 LLM 客户端 — 一个 deep module，所有 LLM 调用的唯一入口

Interface:
    chat(messages, temperature, profile?, tools?) -> ChatResponse
    stream(messages, temperature, profile?, tools?) -> AsyncIterator[dict]

Caller 只需要知道：传入消息，选择 profile（默认 remote）。
内部实现隐藏了：HTTP 客户端管理、auth header 注入、重试、超时、错误处理。
"""

import json
import logging
from collections.abc import AsyncIterator
from dataclasses import dataclass

import httpx

from app.engines.llm.profiles import ModelProfile, remote_profile

logger = logging.getLogger(__name__)


@dataclass
class ToolCall:
    """LLM 返回的工具调用请求"""
    id: str
    name: str
    arguments: dict


@dataclass
class ChatResponse:
    """LLM 对话响应 — 可能是纯文本或工具调用请求"""
    content: str | None = None
    tool_calls: list[ToolCall] | None = None


class LLMClient:
    """统一 LLM 调用客户端

    Usage:
        llm = LLMClient()
        answer = await llm.chat([{"role": "user", "content": "什么是银行家算法？"}])

        # 使用本地模型
        from app.engines.llm.profiles import local_profile
        answer = await llm.chat(messages, profile=local_profile())

        # 流式输出
        async for chunk in llm.stream(messages):
            print(chunk, end="")
    """

    def __init__(self, default_profile: ModelProfile | None = None):
        self._default_profile = default_profile

    def _get_profile(self, profile: ModelProfile | None) -> ModelProfile:
        if profile is not None:
            return profile
        if self._default_profile is not None:
            return self._default_profile
        return remote_profile()

    async def chat(
        self,
        messages: list[dict],
        temperature: float = 0.7,
        profile: ModelProfile | None = None,
        tools: list[dict] | None = None,
    ) -> ChatResponse:
        """发送对话请求，返回 ChatResponse（含 tool_calls 或 content）"""
        p = self._get_profile(profile)
        for attempt in range(p.max_retries + 1):
            try:
                async with httpx.AsyncClient() as client:
                    payload: dict = {
                        "model": p.model_name,
                        "messages": messages,
                        "temperature": temperature,
                    }
                    if tools:
                        payload["tools"] = tools
                        payload["tool_choice"] = "auto"

                    response = await client.post(
                        f"{p.base_url}/chat/completions",
                        headers=p.auth_headers,
                        json=payload,
                        timeout=p.timeout,
                    )
                    response.raise_for_status()
                    choice = response.json()["choices"][0]
                    msg = choice.get("message", {})

                    tool_calls = None
                    if msg.get("tool_calls"):
                        try:
                            tool_calls = [
                                ToolCall(
                                    id=tc["id"],
                                    name=tc["function"]["name"],
                                    arguments=json.loads(tc["function"]["arguments"]),
                                )
                                for tc in msg["tool_calls"]
                            ]
                        except (json.JSONDecodeError, KeyError) as e:
                            logger.warning(f"Malformed tool_call from LLM: {e}")
                            return ChatResponse(
                                content="工具调用参数格式错误，请重试",
                                tool_calls=None,
                            )

                    return ChatResponse(
                        content=msg.get("content"),
                        tool_calls=tool_calls,
                    )
            except (httpx.HTTPStatusError, httpx.ConnectError, httpx.TimeoutException):
                if attempt == p.max_retries:
                    raise
                continue
        raise RuntimeError("unreachable")

    async def stream(
        self,
        messages: list[dict],
        temperature: float = 0.7,
        profile: ModelProfile | None = None,
        tools: list[dict] | None = None,
    ) -> AsyncIterator[dict]:
        """流式输出 — 逐 chunk 返回 text/reasoning，或累积 tool_calls

        Yields dict with keys:
            - content: str       — 正式回答内容
            - reasoning: str     — 思考过程（可能为空）
            - tool_calls: list   — 完整的 tool_calls 列表（流结束时，如有）
        """
        p = self._get_profile(profile)
        async with httpx.AsyncClient() as client:
            payload: dict = {
                "model": p.model_name,
                "messages": messages,
                "temperature": temperature,
                "stream": True,
            }
            if tools:
                payload["tools"] = tools
                payload["tool_choice"] = "auto"

            print(f"--- Sending LLM request to: {p.base_url}/chat/completions ---")

            try:
                async with client.stream(
                    "POST",
                    f"{p.base_url}/chat/completions",
                    headers=p.auth_headers,
                    json=payload,
                    timeout=p.timeout,
                ) as response:
                    response.raise_for_status()

                    # Accumulate tool_calls across chunks
                    tool_call_accum: dict[int, dict] = {}
                    has_any_tool_calls = False

                    async for line in response.aiter_lines():
                        if not line.startswith("data: "):
                            continue
                        data = line[6:]
                        if data.strip() == "[DONE]":
                            break
                        try:
                            chunk = json.loads(data)
                            delta = chunk["choices"][0].get("delta", {})

                            # Handle tool_calls streaming
                            if delta.get("tool_calls"):
                                has_any_tool_calls = True
                                for tc in delta["tool_calls"]:
                                    idx = tc.get("index", 0)
                                    if idx not in tool_call_accum:
                                        tool_call_accum[idx] = {
                                            "id": "", "name": "", "arguments": ""
                                        }
                                    if "id" in tc and tc["id"]:
                                        tool_call_accum[idx]["id"] = tc["id"]
                                    if tc.get("function", {}).get("name"):
                                        tool_call_accum[idx]["name"] = tc["function"]["name"]
                                    if tc.get("function", {}).get("arguments"):
                                        tool_call_accum[idx]["arguments"] += tc["function"]["arguments"]

                            content = delta.get("content", "")
                            reasoning = delta.get("reasoning_content", "")
                            if content or reasoning:
                                yield {"content": content, "reasoning": reasoning}
                        except (json.JSONDecodeError, KeyError, IndexError):
                            continue

                    # Yield accumulated tool_calls at end of stream
                    if has_any_tool_calls and tool_call_accum:
                        parsed = []
                        for idx in sorted(tool_call_accum.keys()):
                            tc = tool_call_accum[idx]
                            try:
                                parsed.append({
                                    "id": tc["id"],
                                    "name": tc["name"],
                                    "arguments": json.loads(tc["arguments"]) if tc["arguments"] else {},
                                })
                            except json.JSONDecodeError:
                                parsed.append({
                                    "id": tc["id"],
                                    "name": tc["name"],
                                    "arguments": {},
                                })
                        yield {"tool_calls": parsed}
            except httpx.HTTPStatusError as e:
                # 友好的流式错误提示，不让服务直接崩掉
                err_msg = f"大模型接口调用失败 (HTTP {e.response.status_code})。请检查您的 API Key 是否正确加载！"
                if e.response.status_code == 401:
                    err_msg = "大模型 API Key 无效或未提供 (HTTP 401)。请确保终端没有缓存错误的全局环境变量，并已重载 .env 文件！"
                yield {"content": f"⚠️ {err_msg}", "reasoning": ""}
            except Exception as e:
                yield {"content": f"⚠️ 内部发生未知网络错误: {str(e)}", "reasoning": ""}
