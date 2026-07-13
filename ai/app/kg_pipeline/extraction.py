"""LLM 实体与关系抽取器"""

import json
import logging
import os
import re
from typing import Optional

from app.kg_pipeline.models import DocumentChunk, KnowledgeGraph, KGNode, KGEdge
from app.engines.llm.client import LLMClient
from app.engines.llm.profiles import ModelProfile, remote_profile
from app.config import settings


def _kg_extraction_profile() -> ModelProfile:
    """KG 抽取专用 profile：使用 deepseek-v4-flash"""
    return ModelProfile(
        base_url=settings.KG_MODEL_BASE_URL,
        model_name=settings.KG_MODEL_NAME,
        api_key=settings.KG_MODEL_API_KEY,
        timeout=120.0,
    )


logger = logging.getLogger(__name__)

PROMPT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "prompts")


def _load_prompt(filename: str = "kg_extraction.txt") -> str:
    """从 prompts 目录加载提示词文件"""
    path = os.path.join(PROMPT_DIR, filename)
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def _parse_llm_json_response(raw: str) -> dict:
    """从 LLM 响应中提取 JSON

    处理 LLM 返回 markdown 包裹的 JSON 代码块：
    ```json\n{"nodes": ...}\n```
    或裸 JSON。
    """
    code_block = re.search(r'```(?:json)?\s*\n?(.*?)\n?```', raw, re.DOTALL)
    if code_block:
        raw = code_block.group(1).strip()

    brace_start = raw.find('{')
    if brace_start >= 0:
        raw = raw[brace_start:]

    return json.loads(raw)


class LlmExtractionError(Exception):
    """LLM 解析格式错误"""
    pass


class KGExtractor:
    """从文档切片中提取知识图谱"""

    def __init__(
        self,
        llm_client: Optional[LLMClient] = None,
        profile: Optional[ModelProfile] = None,
        custom_prompt: Optional[str] = None,
    ):
        self.llm = llm_client or LLMClient()
        self.profile = profile or _kg_extraction_profile()
        self.system_prompt = custom_prompt or _load_prompt()

    async def extract_from_chunk(self, chunk: DocumentChunk) -> KnowledgeGraph:
        """从单个切片提取知识图谱

        Args:
            chunk: 文档切片

        Returns:
            KnowledgeGraph 包含抽取的节点和边

        Raises:
            LlmExtractionError: LLM 返回格式无法解析
        """
        messages = [
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": chunk.text},
        ]

        try:
            raw = await self.llm.chat(
                messages,
                temperature=0.1,
                profile=self.profile,
            )
        except Exception as e:
            raise LlmExtractionError(f"LLM call failed: {e}") from e

        try:
            data = _parse_llm_json_response(raw)
        except (json.JSONDecodeError, ValueError) as e:
            logger.error(f"Failed to parse LLM response: {raw[:200]}")
            raise LlmExtractionError(f"JSON parse failed: {e}") from e

        try:
            nodes = [
                KGNode(
                    id=n.get("id", n.get("name", "")),
                    name=n.get("name", n.get("id", "")),
                    type=n["type"],
                    description=n.get("description", ""),
                    source_chunk_index=chunk.chunk_index,
                )
                for n in data.get("nodes", [])
                if n.get("id") or n.get("name")
            ]
            edges = [
                KGEdge(
                    source_node_id=e["source_node_id"],
                    target_node_id=e["target_node_id"],
                    relationship_name=e["relationship_name"],
                    description=e.get("description"),
                )
                for e in data.get("edges", [])
                if e.get("source_node_id") and e.get("target_node_id")
            ]
        except (KeyError, TypeError) as e:
            raise LlmExtractionError(f"Field validation failed: {e}") from e

        return KnowledgeGraph(nodes=nodes, edges=edges)
