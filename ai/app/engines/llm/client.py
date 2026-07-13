"""统一 LLM 客户端 — 一个 deep module，所有 LLM 调用的唯一入口

Interface:
    chat(messages, temperature, profile?) -> str
    stream(messages, temperature, profile?) -> AsyncIterator[str]

Caller 只需要知道：传入消息，选择 profile（默认 remote）。
内部实现隐藏了：HTTP 客户端管理、auth header 注入、重试、超时、错误处理。
"""

import json
from collections.abc import AsyncIterator

import httpx

from app.engines.llm.profiles import ModelProfile, remote_profile


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
    ) -> str:
        """发送对话请求，返回完整回答文本"""
        p = self._get_profile(profile)
        for attempt in range(p.max_retries + 1):
            try:
                async with httpx.AsyncClient() as client:
                    response = await client.post(
                        f"{p.base_url}/chat/completions",
                        headers=p.auth_headers,
                        json={
                            "model": p.model_name,
                            "messages": messages,
                            "temperature": temperature,
                        },
                        timeout=p.timeout,
                    )
                    response.raise_for_status()
                    return response.json()["choices"][0]["message"]["content"]
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
    ) -> AsyncIterator[dict]:
        """流式输出 — 逐 chunk 返回文本和 reasoning

        Yields dict with keys:
            - content: str  — 正式回答内容
            - reasoning: str — 思考过程（可能为空）
        """
        p = self._get_profile(profile)
        async with httpx.AsyncClient() as client:
            async with client.stream(
                "POST",
                f"{p.base_url}/chat/completions",
                headers=p.auth_headers,
                json={
                    "model": p.model_name,
                    "messages": messages,
                    "temperature": temperature,
                    "stream": True,
                },
                timeout=p.timeout,
            ) as response:
                response.raise_for_status()
                async for line in response.aiter_lines():
                    if not line.startswith("data: "):
                        continue
                    data = line[6:]
                    if data.strip() == "[DONE]":
                        break
                    try:
                        chunk = json.loads(data)
                        delta = chunk["choices"][0].get("delta", {})
                        content = delta.get("content", "")
                        reasoning = delta.get("reasoning_content", "")
                        if content or reasoning:
                            yield {"content": content, "reasoning": reasoning}
                    except (json.JSONDecodeError, KeyError, IndexError):
                        continue
