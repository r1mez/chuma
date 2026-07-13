"""NetworkX 内存图构建与去重"""

import logging

import networkx as nx

from app.kg_pipeline.models import KnowledgeGraph


logger = logging.getLogger(__name__)


class GraphBuilder:
    """合并多个切片的知识图谱为一张统一的内存图

    使用 NetworkX DiGraph 作为中间表示，
    在写入 AGE 前完成实体去重和边验证。
    """

    def build(
        self,
        chunk_graphs: list[KnowledgeGraph],
    ) -> nx.DiGraph:
        """合并多个 KnowledgeGraph 片段为统一图

        Args:
            chunk_graphs: 每个切片抽取的图片段

        Returns:
            NetworkX DiGraph，节点属性含 name/type/description，
            边属性含 relationship_name/description
        """
        G = nx.DiGraph()

        for kg in chunk_graphs:
            for node in kg.nodes:
                if node.id in G:
                    existing = G.nodes[node.id]
                    if len(node.name) > len(existing.get("name", "")):
                        G.nodes[node.id]["name"] = node.name
                    if len(node.description) > len(existing.get("description", "")):
                        G.nodes[node.id]["description"] = node.description
                else:
                    G.add_node(
                        node.id,
                        name=node.name,
                        type=node.type.value if hasattr(node.type, 'value') else node.type,
                        description=node.description,
                        source_chunk_index=node.source_chunk_index,
                    )

            for edge in kg.edges:
                if edge.source_node_id not in G:
                    logger.warning(f"Edge source {edge.source_node_id} not in graph, skipping")
                    continue
                if edge.target_node_id not in G:
                    logger.warning(f"Edge target {edge.target_node_id} not in graph, skipping")
                    continue

                key = (edge.source_node_id, edge.target_node_id)
                if G.has_edge(*key):
                    existing_edge = G.edges[key]
                    if existing_edge.get("relationship_name") == edge.relationship_name:
                        continue

                G.add_edge(
                    edge.source_node_id,
                    edge.target_node_id,
                    relationship_name=edge.relationship_name,
                    description=edge.description,
                )

        return G
