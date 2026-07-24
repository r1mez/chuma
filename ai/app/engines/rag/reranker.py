"""BGE-Reranker-v2-M3 重排序客户端 — vLLM :8011

vLLM 对 reranker 模型的 endpoint 可能与标准 chat 不同。
先尝试 /v1/chat/completions，若运行时不可用则改为 /score（需人工确认）。
"""

import logging

import httpx

from app.config import settings

logger = logging.getLogger(__name__)

RERANKER_MODEL = "bge-reranker-v2-m3"


class RerankerClient:
    """BGE-Reranker 重排序客户端

    用法:
        client = RerankerClient()
        pairs = [("什么是栈", "栈的定义..."), ("什么是栈", "队列的定义...")]
        scores = await client.rerank(pairs)
        # scores = [0.95, 0.12]
    """

    def __init__(
        self,
        base_url: str = "",
        endpoint: str = "",
    ):
        self._base_url = (base_url or settings.BGE_RERANKER_URL).rstrip("/")
        self._endpoint = endpoint or "/v1/chat/completions"

    async def rerank_with_retry(
        self, pairs: list[tuple[str, str]], top_k: int | None = None, retries: int = 2,
    ) -> list[float]:
        """带重试的重排序"""
        for attempt in range(retries + 1):
            try:
                return await self.rerank(pairs, top_k=top_k)
            except (httpx.HTTPStatusError, httpx.ConnectError, httpx.TimeoutException) as e:
                if attempt == retries:
                    raise
                logger.warning("Reranker attempt %d/%d failed: %s", attempt + 1, retries + 1, e)
        raise RuntimeError("unreachable")

    async def rerank(
        self,
        pairs: list[tuple[str, str]],
        top_k: int | None = None,
    ) -> list[float]:
        """对 (query, candidate) 对进行重排序打分

        Args:
            pairs: (query, candidate_text) 列表
            top_k: 可选，只保留前 top_k 个分数，其余置 -inf

        Returns:
            分数列表（与输入顺序一致）
        """
        if not pairs:
            return []

        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"{self._base_url}{self._endpoint}",
                json={
                    "model": RERANKER_MODEL,
                    "pairs": [[p[0], p[1]] for p in pairs],
                },
                timeout=60.0,
            )
            resp.raise_for_status()
            data = resp.json()

            if "scores" in data:
                scores = data["scores"]
            elif "data" in data:
                scores = [item["score"] for item in data["data"]]
            else:
                raise ValueError(
                    f"Unexpected reranker response format: {list(data.keys())}"
                )

            if top_k is not None and top_k < len(scores):
                indexed = list(enumerate(scores))
                indexed.sort(key=lambda x: x[1], reverse=True)
                keep = {i for i, _ in indexed[:top_k]}
                return [
                    s if i in keep else -float("inf")
                    for i, s in enumerate(scores)
                ]

            return scores
