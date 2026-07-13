"""Markdown 感知的文本切片器

按标题分割 Markdown 文档，在每个 section 内部按句子粒度切分，
聚合为不超过 max_chunk_size 的块。不会跨越标题边界。
"""

import re
import uuid

from app.kg_pipeline.models import DocumentChunk


def _split_by_heading(markdown_text: str) -> list[str]:
    """按 Markdown 标题分割文档

    支持 # ## ### 级别的标题，保留标题文本在 section 内容开头。
    """
    heading_pattern = re.compile(r'^(#{1,3})\s+(.+)$', re.MULTILINE)
    sections = []
    last_start = 0

    for match in heading_pattern.finditer(markdown_text):
        sections.append(markdown_text[last_start:match.start()].strip())
        last_start = match.start()

    if last_start < len(markdown_text):
        sections.append(markdown_text[last_start:].strip())

    if not sections:
        sections = [markdown_text.strip()]

    return [s for s in sections if s]


def _estimate_token_count(text: str) -> int:
    """估算文本的 token 数量（中英文混合，约 1.5 chars/token）"""
    return max(1, len(text) // 2)


def _chunk_section(section: str, max_chunk_size: int, base_index: int = 0) -> list[DocumentChunk]:
    """将一个 section 按段落/句子切分为 chunks"""
    if not section:
        return []

    chunks = []
    current_text = ""
    current_size = 0
    chunk_index = base_index

    paragraphs = re.split(r'\n\s*\n', section)

    for para in paragraphs:
        para = para.strip()
        if not para:
            continue

        para_size = _estimate_token_count(para)

        if current_size > 0 and current_size + para_size > max_chunk_size:
            chunks.append(DocumentChunk(
                id=str(uuid.uuid4()),
                text=current_text.strip(),
                chunk_index=chunk_index,
                chunk_size=current_size,
            ))
            chunk_index += 1
            current_text = ""
            current_size = 0

        if para_size > max_chunk_size:
            sentences = re.split(r'(?<=[。！？；;.!?])\s*', para)
            for sent in sentences:
                sent = sent.strip()
                if not sent:
                    continue
                sent_size = _estimate_token_count(sent)
                if current_size + sent_size > max_chunk_size and current_size > 0:
                    chunks.append(DocumentChunk(
                        id=str(uuid.uuid4()),
                        text=current_text.strip(),
                        chunk_index=chunk_index,
                        chunk_size=current_size,
                    ))
                    chunk_index += 1
                    current_text = ""
                    current_size = 0
                current_text += sent + " "
                current_size += sent_size
        else:
            current_text += para + "\n\n"
            current_size += para_size

    if current_text.strip():
        chunks.append(DocumentChunk(
            id=str(uuid.uuid4()),
            text=current_text.strip(),
            chunk_index=chunk_index,
            chunk_size=current_size,
        ))

    return chunks


class MarkdownChunker:
    """Markdown 感知的文本切片器"""

    def __init__(self, max_chunk_size: int = 1024):
        self.max_chunk_size = max_chunk_size

    def chunk(self, markdown_text: str) -> list[DocumentChunk]:
        if not markdown_text:
            return []

        sections = _split_by_heading(markdown_text)
        all_chunks: list[DocumentChunk] = []
        chunk_index = 0

        for section in sections:
            section_chunks = _chunk_section(section, self.max_chunk_size, chunk_index)
            all_chunks.extend(section_chunks)
            chunk_index += len(section_chunks)

        return all_chunks
