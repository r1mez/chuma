"""KgGraphService -- 知识图谱元数据管理"""

import os
import re
from typing import Optional
from uuid import uuid4

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.kg_graph import KgGraph
from app.schemas.kg_graph import KgGraphResponse


def sanitize_filename(filename: str) -> str:
    """清理文件名：保留中英文、数字，其余替换为 _，合并连续 _"""
    # 去除扩展名
    stem = os.path.splitext(filename)[0]
    # 保留中文、英文字母、数字
    cleaned = re.sub(r"[^一-龥a-zA-Z0-9]", "_", stem)
    # 合并连续下划线
    cleaned = re.sub(r"_+", "_", cleaned)
    # 去除首尾下划线
    cleaned = cleaned.strip("_")
    # 截断到 100 字符（为 UUID 和 kg_ 前缀留空间）
    return cleaned[:100]


class KgGraphService:
    """知识图谱元数据服务"""

    def _generate_graph_name(self, original_filename: str) -> str:
        """生成 graph_name: kg_{sanitized}_{uuid4[:8]}"""
        sanitized = sanitize_filename(original_filename)
        uid = uuid4().hex[:8]
        return f"kg_{sanitized}_{uid}"

    async def create_graph(
        self,
        original_filename: str,
        file_path: str,
        db: AsyncSession,
    ) -> KgGraphResponse:
        """创建图谱元数据记录"""
        graph_name = self._generate_graph_name(original_filename)
        kg_graph = KgGraph(
            original_filename=original_filename,
            file_path=file_path,
            graph_name=graph_name,
            status="pending",
        )
        db.add(kg_graph)
        await db.commit()
        await db.refresh(kg_graph)
        return KgGraphResponse.model_validate(kg_graph)

    async def list_graphs(
        self,
        db: AsyncSession,
    ) -> list[KgGraphResponse]:
        """查询所有图谱列表，按创建时间降序"""
        result = await db.execute(
            select(KgGraph)
            .order_by(KgGraph.created_at.desc())
        )
        graphs = result.scalars().all()
        return [KgGraphResponse.model_validate(g) for g in graphs]

    async def get_graph_by_id(
        self,
        graph_id: int,
        db: AsyncSession,
    ) -> Optional[KgGraph]:
        """按 ID 查询图谱"""
        result = await db.execute(
            select(KgGraph).where(KgGraph.id == graph_id)
        )
        return result.scalar_one_or_none()

    async def update_graph_stats(
        self,
        graph_id: int,
        node_count: int,
        edge_count: int,
        chunk_count: int,
        status: str,
        db: AsyncSession,
    ) -> None:
        """更新图谱统计信息（构建完成后调用）"""
        result = await db.execute(
            select(KgGraph).where(KgGraph.id == graph_id)
        )
        kg_graph = result.scalar_one_or_none()
        if kg_graph:
            kg_graph.node_count = node_count
            kg_graph.edge_count = edge_count
            kg_graph.chunk_count = chunk_count
            kg_graph.status = status
            await db.commit()

    async def delete_graph(
        self,
        graph_id: int,
        db: AsyncSession,
    ) -> Optional[str]:
        """删除图谱元数据记录，返回 graph_name（用于通知 AI 引擎清图）"""
        kg_graph = await self.get_graph_by_id(graph_id, db)
        if kg_graph is None:
            return None
        graph_name = kg_graph.graph_name
        file_path = kg_graph.file_path
        await db.execute(delete(KgGraph).where(KgGraph.id == graph_id))
        await db.commit()
        # 清理本地文件
        if file_path and os.path.exists(file_path):
            try:
                os.remove(file_path)
            except OSError:
                pass
        return graph_name
