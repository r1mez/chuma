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


def _build_chapter_context(chunk: DocumentChunk) -> str:
    """构建章节上下文注入文本

    当 chunk 携带 heading_path 时，在 user message 开头注入章节上下文，
    提醒 LLM 不要提取章节标题，只提取具体知识点。

    Args:
        chunk: 文档切片

    Returns:
        章节上下文字符串，无 heading_path 时返回空字符串
    """
    if not chunk.heading_path:
        return ""

    path_str = " > ".join(chunk.heading_path)
    return (
        f"## 章节上下文\n\n"
        f"你正在处理教材的以下章节：\n"
        f"{path_str}\n\n"
        f"规则：\n"
        f"- 不要提取章节标题作为实体（章节节点已自动生成）\n"
        f"- 只提取章节内的具体知识点（算法、数据结构、概念等）\n"
        f"- 提取的知识点将自动归属于上述章节\n\n"
    )


def _parse_llm_json_response(raw: str) -> dict:
    """从 LLM 响应中提取 JSON

    处理多种 LLM 输出格式，包括：
    - Markdown 包裹的 JSON 代码块（```json ... ``` 或 ``` ... ```）
    - 裸 JSON
    - JSON 对象后跟额外解释文本
    - 尾随逗号（LLM 常见错误）
    - 单引号字符串
    - 不完整的截断 JSON（尽力闭合括号）

    Raises:
        ValueError: 所有恢复策略均失败
    """
    if not raw or not raw.strip():
        raise ValueError("Empty LLM response")

    # ---- Step 1: 提取 Markdown 代码块 ----
    # 改进的正则：兼容 ``` 前后有无换行、有无 json 标记
    code_block = re.search(r'```(?:json)?\s*\n?(.*?)\n?\s*```', raw, re.DOTALL)
    if code_block:
        raw = code_block.group(1).strip()

    # ---- Step 2: 定位 JSON 对象边界（花括号配对计数）----
    brace_start = raw.find('{')
    if brace_start < 0:
        raise ValueError(f"No JSON object found in response: {raw[:200]}")

    depth = 0
    brace_end = -1
    for i in range(brace_start, len(raw)):
        ch = raw[i]
        if ch == '{':
            depth += 1
        elif ch == '}':
            depth -= 1
            if depth == 0:
                brace_end = i
                break

    if brace_end >= 0:
        raw = raw[brace_start:brace_end + 1]
    else:
        # 括号未闭合（截断），取到末尾
        raw = raw[brace_start:]

    # ---- Step 3: 直接解析 ----
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        pass

    # ---- Step 4: 尝试修复后解析 ----
    repaired = _repair_json(raw)
    if repaired is not None:
        try:
            return json.loads(repaired)
        except json.JSONDecodeError:
            pass

    # ---- Step 5: 尽力提取部分数据 ----
    partial = _extract_partial_json(raw)
    if partial is not None:
        return partial

    raise ValueError(f"Unable to parse JSON after all recovery attempts: {raw[:300]}")


def _repair_json(raw: str) -> str | None:
    """尝试修复常见的 LLM JSON 格式错误

    返回修复后的字符串，如果无需/无法修复则返回 None。
    """
    repaired = raw
    changed = False

    # Fix 1: 移除 } 或 ] 前的尾随逗号 → 最常见的 LLM JSON 错误
    new_repaired = re.sub(r',\s*([}\]])', r'\1', repaired)
    if new_repaired != repaired:
        changed = True
        repaired = new_repaired

    # Fix 2: 单引号 → 双引号（仅在完全没有双引号且存在单引号时尝试）
    if '"' not in repaired and "'" in repaired:
        # 替换键名的单引号: 'key':
        repaired = re.sub(r"'([^']*)'(?=\s*:)", r'"\1"', repaired)
        # 替换值的单引号: : 'value'
        repaired = re.sub(r":\s*'([^']*)'", r': "\1"', repaired)
        changed = True

    # Fix 3: 移除 JSON 对象前的 BOM 或不可见字符
    stripped = repaired.lstrip('﻿​ ')
    if stripped != repaired:
        changed = True
        repaired = stripped

    return repaired if changed else None


def _extract_partial_json(raw: str) -> dict | None:
    """从损坏的 JSON 中尽力提取 nodes/edges 数组

    当完整对象无法解析时，尝试单独提取 nodes 和 edges 数组。
    返回 {"nodes": [...], "edges": [...]} 或 None。
    """
    result: dict = {"nodes": [], "edges": []}

    # 尝试提取 nodes 数组
    nodes_match = re.search(r'"nodes"\s*:\s*(\[.*?\])', raw, re.DOTALL)
    if nodes_match:
        try:
            result["nodes"] = json.loads(nodes_match.group(1))
        except json.JSONDecodeError:
            # 尝试修复尾随逗号后重试
            fixed = re.sub(r',\s*\]', ']', nodes_match.group(1))
            try:
                result["nodes"] = json.loads(fixed)
            except json.JSONDecodeError:
                pass

    # 尝试提取 edges 数组
    edges_match = re.search(r'"edges"\s*:\s*(\[.*?\])', raw, re.DOTALL)
    if edges_match:
        try:
            result["edges"] = json.loads(edges_match.group(1))
        except json.JSONDecodeError:
            fixed = re.sub(r',\s*\]', ']', edges_match.group(1))
            try:
                result["edges"] = json.loads(fixed)
            except json.JSONDecodeError:
                pass

    # 只有至少提取到一些数据才返回
    if result["nodes"] or result["edges"]:
        return result
    return None


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

    async def _retry_with_feedback(
        self,
        original_messages: list[dict],
        raw_response: str,
        parse_error: str,
    ) -> dict | None:
        """将解析错误反馈给 LLM，请求修复 JSON 格式

        Args:
            original_messages: 原始对话消息（system + user）
            raw_response: LLM 原始返回内容
            parse_error: 解析错误描述

        Returns:
            修复后的 dict，失败返回 None
        """
        retry_messages = original_messages + [
            {"role": "assistant", "content": raw_response},
            {
                "role": "user",
                "content": (
                    f"Your previous response could not be parsed as valid JSON.\n"
                    f"Error: {parse_error}\n\n"
                    f"Please output ONLY a valid JSON object with \"nodes\" and \"edges\" arrays.\n"
                    f"Do NOT include any explanation, markdown formatting, or trailing commas."
                ),
            },
        ]

        try:
            resp = await self.llm.chat(
                retry_messages,
                temperature=0.0,
                profile=self.profile,
                response_format={"type": "json_object"},
            )
            retry_raw = resp.content or ""
            return _parse_llm_json_response(retry_raw)
        except Exception as e:
            logger.warning(f"Retry with feedback also failed: {e}")
            return None

    async def extract_from_chunk(self, chunk: DocumentChunk) -> KnowledgeGraph:
        """从单个切片提取知识图谱

        Args:
            chunk: 文档切片

        Returns:
            KnowledgeGraph 包含抽取的节点和边

        Raises:
            LlmExtractionError: LLM 返回格式无法解析（含重试后仍失败）
        """
        # 构建章节上下文 + 原始文本
        chapter_context = _build_chapter_context(chunk)
        user_content = chapter_context + chunk.text

        messages = [
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": user_content},
        ]

        try:
            resp = await self.llm.chat(
                messages,
                temperature=0.1,
                profile=self.profile,
                response_format={"type": "json_object"},
            )
        except Exception as e:
            raise LlmExtractionError(f"LLM call failed: {e}") from e

        raw = resp.content or ""

        # ---- 解析 JSON（失败时重试一次） ----
        try:
            data = _parse_llm_json_response(raw)
        except (json.JSONDecodeError, ValueError) as e:
            logger.warning(
                f"JSON parse failed for chunk {chunk.chunk_index}, "
                f"attempting retry with error feedback: {e}"
            )
            data = await self._retry_with_feedback(messages, raw, str(e))
            if data is None:
                logger.error(
                    f"Retry also failed for chunk {chunk.chunk_index}: {raw[:200]}"
                )
                raise LlmExtractionError(
                    f"JSON parse failed after retry: {e}"
                ) from e

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
