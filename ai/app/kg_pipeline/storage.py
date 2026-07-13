"""Apache AGE 持久化适配器

通过 PostgreSQL 协议操作 AGE 扩展的 Cypher 接口。
AGE 图数据模型：
  - Vertex label: Entity
    - Properties: id (str), name (str), type (str), description (str)
  - Edge label: RELATION
    - Properties: relationship_name (str), description (str)
"""

import logging
from typing import Optional

import networkx as nx
import psycopg2

from app.config import settings


logger = logging.getLogger(__name__)


class AgeConnectionError(Exception):
    """AGE 数据库连接失败"""
    pass


def _build_dsn() -> str:
    """从 settings 构建 PostgreSQL DSN"""
    return (
        f"host={settings.AGE_HOST} "
        f"port={settings.AGE_PORT} "
        f"dbname={settings.AGE_DB} "
        f"user={settings.AGE_USER} "
        f"password={settings.AGE_PASSWORD}"
    )


def _escape(value: str) -> str:
    """转义 Cypher 字符串中的单引号和反斜杠"""
    return value.replace("\\", "\\\\").replace("'", "\\'")


class AgeStorage:
    """Apache AGE 持久化适配器"""

    def __init__(self, dsn: Optional[str] = None, graph_name: Optional[str] = None):
        self._dsn = dsn or _build_dsn()
        self._graph_name = graph_name or settings.AGE_GRAPH_NAME

    def _get_conn(self):
        """创建 AGE 数据库连接"""
        try:
            conn = psycopg2.connect(self._dsn)
            conn.set_session(autocommit=True)
            return conn
        except psycopg2.OperationalError as e:
            raise AgeConnectionError(f"Cannot connect to AGE: {e}") from e

    def initialize_graph(self) -> None:
        """初始化 AGE 图（幂等）"""
        conn = self._get_conn()
        try:
            with conn.cursor() as cur:
                cur.execute("SELECT * FROM ag_catalog.create_graph(%s)", (self._graph_name,))
        except psycopg2.errors.DuplicateObject:
            logger.info(f"Graph '{self._graph_name}' already exists, skipping")
        finally:
            conn.close()

    def write_graph(self, graph: nx.DiGraph) -> int:
        """将 NetworkX 图写入 AGE

        Args:
            graph: NetworkX DiGraph

        Returns:
            写入的边数
        """
        conn = self._get_conn()
        edge_count = 0

        try:
            with conn.cursor() as cur:
                cur.execute("SET search_path TO ag_catalog, public;")

                for node_id, attrs in graph.nodes(data=True):
                    name = attrs.get("name", node_id)
                    ntype = attrs.get("type", "Concept")
                    desc = attrs.get("description", "")

                    cypher = (
                        f"SELECT * FROM cypher('{self._graph_name}', $$ "
                        f"MERGE (n:Entity {{id: '{_escape(node_id)}'}}) "
                        f"SET n.name = '{_escape(name)}', "
                        f"n.type = '{_escape(ntype)}', "
                        f"n.description = '{_escape(desc)}' "
                        f"$$) AS (n ag_catalog.vertex);"
                    )
                    cur.execute(cypher)

                for src, dst, attrs in graph.edges(data=True):
                    rel_name = attrs.get("relationship_name", "related_to")
                    desc = attrs.get("description", "")

                    cypher = (
                        f"SELECT * FROM cypher('{self._graph_name}', $$ "
                        f"MATCH (a:Entity {{id: '{_escape(src)}'}}) "
                        f"MATCH (b:Entity {{id: '{_escape(dst)}'}}) "
                        f"CREATE (a)-[r:RELATION {{"
                        f"relationship_name: '{_escape(rel_name)}', "
                        f"description: '{_escape(desc)}'"
                        f"}}]->(b) "
                        f"$$) AS (r ag_catalog.edge);"
                    )
                    cur.execute(cypher)
                    edge_count += 1

        except psycopg2.Error as e:
            logger.error(f"AGE write failed: {e}")
            raise AgeConnectionError(f"AGE write failed: {e}") from e
        finally:
            conn.close()

        return edge_count

    def clear_graph(self) -> None:
        """清除当前图的所有数据"""
        conn = self._get_conn()
        try:
            with conn.cursor() as cur:
                cur.execute("SET search_path TO ag_catalog, public;")
                cypher = (
                    f"SELECT * FROM cypher('{self._graph_name}', $$ "
                    f"MATCH (n) DETACH DELETE n "
                    f"$$) AS (n ag_catalog.vertex);"
                )
                cur.execute(cypher)
        except psycopg2.Error as e:
            logger.error(f"AGE clear failed: {e}")
            raise AgeConnectionError(f"AGE clear failed: {e}") from e
        finally:
            conn.close()
