"""Markdown 感知的文本切片器

按标题分割 Markdown 文档，在每个 section 内部按句子粒度切分，
聚合为不超过 max_chunk_size 的块。不会跨越标题边界。

改造：支持 heading_path / heading_levels 元数据，动态标题层级映射。
"""

import re
import uuid
from typing import Optional

from app.kg_pipeline.models import DocumentChunk


def _scan_heading_levels(markdown_text: str) -> list[int]:
    """扫描 Markdown 中出现的所有标题级别，排序去重返回

    Returns:
        排序后的标题级别列表，如 [1, 2, 3]
    """
    heading_pattern = re.compile(r'^(#{1,6})\s+(.+)$', re.MULTILINE)
    levels = set()
    for match in heading_pattern.finditer(markdown_text):
        level = len(match.group(1))
        levels.add(level)
    return sorted(levels)


def _map_heading_levels(heading_levels: list[int]) -> dict[int, int]:
    """将实际标题级别映射为 2 层结构

    映射规则：
    - 按从小到大，第1种级别 → 第1层（章），第2种级别 → 第2层（知识点）
    - 超过2种级别时，第3种及以上归入第2层
    - 只有1种级别时，全部映射为第1层

    Args:
        heading_levels: 排序去重后的标题级别列表

    Returns:
        映射字典，如 {2: 1, 3: 2} 表示 ## → 第1层，### → 第2层
    """
    if not heading_levels:
        return {}

    mapping = {}
    if len(heading_levels) == 1:
        # 只有一种级别，全部映射为第1层
        mapping[heading_levels[0]] = 1
    else:
        # 第1种 → 第1层，第2种及以上 → 第2层
        for i, level in enumerate(heading_levels):
            if i == 0:
                mapping[level] = 1
            else:
                mapping[level] = 2

    return mapping


def _split_by_heading(markdown_text: str, level_mapping: dict[int, int]) -> list[tuple[str, list[str], list[int]]]:
    """按 Markdown 标题分割文档，返回带有标题路径的 section 列表

    支持 # ~ ###### 级别的标题。维护标题栈，每个 section 继承其上方所有父标题。

    Args:
        markdown_text: Markdown 文档
        level_mapping: 标题级别映射，如 {2: 1, 3: 2}

    Returns:
        列表，每个元素为 (section文本, heading_path, heading_levels)
    """
    heading_pattern = re.compile(r'^(#{1,6})\s+(.+)$', re.MULTILINE)

    # 收集所有标题位置
    headings = []
    for match in heading_pattern.finditer(markdown_text):
        level = len(match.group(1))
        title = match.group(2).strip()
        pos = match.start()
        headings.append((pos, level, title))

    # 无标题时，整篇作为一个 section
    if not headings:
        return [(markdown_text.strip(), [], [])]

    # 维护标题栈，生成每个 section 的 heading_path
    sections = []
    title_stack: list[tuple[int, str]] = []  # [(level, title), ...]

    for i, (pos, level, title) in enumerate(headings):
        # 更新标题栈：弹出比当前级别 >= 的标题
        while title_stack and title_stack[-1][0] >= level:
            title_stack.pop()
        title_stack.append((level, title))

        # 当前 section 文本范围：从本标题到下一个标题
        next_pos = headings[i + 1][0] if i + 1 < len(headings) else len(markdown_text)
        section_text = markdown_text[pos:next_pos].strip()

        # 构建 heading_path：只包含映射后的层级的标题
        heading_path = [t for (l, t) in title_stack if l in level_mapping]
        heading_levels = [l for (l, t) in title_stack if l in level_mapping]

        if section_text:
            sections.append((section_text, heading_path, heading_levels))

    return sections


def _estimate_token_count(text: str) -> int:
    """估算文本的 token 数量（中英文混合，约 1.5 chars/token）"""
    return max(1, len(text) // 2)


def _chunk_section(
    section: str,
    max_chunk_size: int = 0,  # kept for backward compat, ignored
    base_index: int = 0,
    heading_path: Optional[list[str]] = None,
    heading_levels: Optional[list[int]] = None,
) -> list[DocumentChunk]:
    """一个 section 直接作为一个大切片（不再按 token 聚合）

    每个 heading section 是完整的语义块，LLM 抽取需要有完整的上下文。
    向量检索使用时，由 DocIngestion.split_sub_chunks() 二次分割为段落级子切片。
    """
    if heading_path is None:
        heading_path = []
    if heading_levels is None:
        heading_levels = []

    if not section:
        return []

    return [DocumentChunk(
        id=str(uuid.uuid4()),
        text=section.strip(),
        chunk_index=base_index,
        chunk_size=_estimate_token_count(section),
        heading_path=heading_path,
        heading_levels=heading_levels,
    )]


class MarkdownChunker:
    """Markdown 感知的文本切片器"""

    def __init__(self, max_chunk_size: int = 1024):
        self.max_chunk_size = max_chunk_size

    def chunk(self, markdown_text: str) -> list[DocumentChunk]:
        """对 Markdown 文本进行切片

        Args:
            markdown_text: 完整的 Markdown 文档内容

        Returns:
            按阅读顺序排列的 DocumentChunk 列表，每个 chunk 携带 heading_path 和 heading_levels
        """
        if not markdown_text:
            return []

        # 第一遍：扫描所有标题级别
        all_levels = _scan_heading_levels(markdown_text)

        # 动态映射为 2 层结构
        level_mapping = _map_heading_levels(all_levels)

        # 第二遍：按标题分割，生成带标题路径的 section
        sections = _split_by_heading(markdown_text, level_mapping)

        # 第三遍：对每个 section 进行切分
        all_chunks: list[DocumentChunk] = []
        chunk_index = 0

        for section_text, heading_path, heading_levels in sections:
            section_chunks = _chunk_section(
                section_text,
                self.max_chunk_size,
                chunk_index,
                heading_path=heading_path,
                heading_levels=heading_levels,
            )
            all_chunks.extend(section_chunks)
            chunk_index += len(section_chunks)

        return all_chunks
