"""知识图谱查询工具"""
import logging

from app.agent.tool_registry import ToolRegistry
from app.kg_pipeline.queries import search_nodes, GraphQueryError

logger = logging.getLogger(__name__)


@ToolRegistry.register(
    name="search_kg",
    description="查询知识图谱中的概念节点和关系。用于查找408考研/计算机学科相关的知识点、算法、数据结构等信息。",
    parameters={
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "搜索关键词，如'红黑树'、'TCP三次握手'等",
            },
            "top_k": {
                "type": "integer",
                "description": "返回的最大节点数，默认10",
            },
        },
        "required": ["query"],
    },
)
async def search_kg(user_id: int, query: str, top_k: int = 10) -> str:
    """查询知识图谱中的概念节点和关系"""
    try:
        nodes = search_nodes(query)
        if not nodes:
            return f"未在知识图谱中找到与 '{query}' 相关的概念。建议尝试其他关键词。"

        limited = nodes[:top_k]
        output_lines = [f"知识图谱查询结果（关键词: {query}，共 {len(nodes)} 个结果，展示前 {len(limited)} 个）:\n"]

        for node in limited:
            output_lines.append(
                f"- {node['name']} [{node.get('type', 'Concept')}]: {node.get('description', '无描述')}"
            )

        return "\n".join(output_lines)
    except GraphQueryError as e:
        logger.error(f"KG query failed: {e}")
        return f"知识图谱查询失败: {str(e)}"
