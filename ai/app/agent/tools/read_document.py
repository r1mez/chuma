"""文档读取工具 — 从 ChromaDB 向量数据库检索上传的课件/笔记/教材内容"""
import logging

import chromadb

from app.agent.tool_registry import ToolRegistry
from app.config import settings

logger = logging.getLogger(__name__)

DOCUMENT_COLLECTION = "documents"


def _get_collection():
    """获取 ChromaDB 文档集合"""
    client = chromadb.HttpClient(
        host=settings.CHROMADB_HOST,
        port=settings.CHROMADB_PORT,
    )
    try:
        return client.get_collection(DOCUMENT_COLLECTION)
    except Exception:
        return None


@ToolRegistry.register(
    name="read_document",
    description="读取学生上传的课件、笔记、教材内容。当用户询问特定课程/章节内容时使用。",
    parameters={
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "文档检索关键词，如'虚存管理'、'数据库范式'等",
            },
            "top_k": {
                "type": "integer",
                "description": "返回的最大文档片段数，默认5",
            },
        },
        "required": ["query"],
    },
)
async def read_document(user_id: int, query: str, top_k: int = 5) -> str:
    """从 ChromaDB 检索相关文档片段"""
    try:
        collection = _get_collection()
        if collection is None:
            return "文档库暂无内容。请先上传课件或教材文档。"

        results = collection.query(
            query_texts=[query],
            n_results=min(top_k, 10),
        )

        documents = results.get("documents", [[]])[0]
        metadatas = results.get("metadatas", [[]])[0]

        if not documents:
            return f"未在已上传文档中找到与 '{query}' 相关的内容。"

        output_lines = [f"文档检索结果（关键词: {query}，共 {len(documents)} 个片段）:\n"]

        for i, doc in enumerate(documents):
            source = ""
            if metadatas and i < len(metadatas) and metadatas[i]:
                source = metadatas[i].get("source", "")
            header = f"--- 片段 {i + 1}"
            if source:
                header += f"（来源: {source}）"
            header += " ---"
            output_lines.append(header)
            output_lines.append(doc.strip())
            output_lines.append("")

        return "\n".join(output_lines)
    except Exception as e:
        logger.error(f"Document query failed: {e}")
        return f"文档检索失败: {str(e)}"
