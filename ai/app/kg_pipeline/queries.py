"""AGE 图数据只读查询封装"""

import logging
from typing import Any

from app.kg_pipeline.storage import AgeStorage, AgeConnectionError

logger = logging.getLogger(__name__)


class GraphQueryError(Exception):
    pass


def get_full_graph(dataset_id: str = "main") -> dict[str, Any]:
    """获取完整图数据（节点 + 边 + 统计）"""
    storage = AgeStorage()
    try:
        conn = storage._get_conn()
    except AgeConnectionError as e:
        raise GraphQueryError(f"Cannot connect to AGE: {e}") from e
    try:
        with conn.cursor() as cur:
            cur.execute("SET search_path TO ag_catalog, public;")
            cur.execute(
                f"SELECT * FROM cypher('{storage._graph_name}', $$ "
                f"MATCH (n:Entity) RETURN n.id, n.name, n.type, n.description "
                f"$$) AS (id text, name text, type text, description text)"
            )
            rows = cur.fetchall()
            nodes = []
            type_counter: dict[str, int] = {}
            for row in rows:
                nid, name, ntype, desc = row
                nodes.append({
                    "id": nid, "name": name or nid, "type": ntype or "Concept",
                    "description": desc or "", "degree": 0,
                })
                t = ntype or "Concept"
                type_counter[t] = type_counter.get(t, 0) + 1

            cur.execute(
                f"SELECT * FROM cypher('{storage._graph_name}', $$ "
                f"MATCH (a:Entity)-[r:RELATION]->(b:Entity) "
                f"RETURN a.id, b.id, r.relationship_name, r.description "
                f"$$) AS (source text, target text, rel text, desc text)"
            )
            edge_rows = cur.fetchall()
            edges = []
            degree_counter: dict[str, int] = {}
            for row in edge_rows:
                src, tgt, rel, desc = row
                edges.append({
                    "source": src, "target": tgt,
                    "relationship_name": rel or "related_to",
                    "description": desc or "",
                })
                degree_counter[src] = degree_counter.get(src, 0) + 1
                degree_counter[tgt] = degree_counter.get(tgt, 0) + 1
            for node in nodes:
                node["degree"] = degree_counter.get(node["id"], 0)
    except Exception as e:
        logger.error(f"Graph query failed: {e}")
        raise GraphQueryError(str(e)) from e
    finally:
        conn.close()
    return {"nodes": nodes, "edges": edges,
            "stats": {"total_nodes": len(nodes), "total_edges": len(edges),
                      "node_types": type_counter}}


def search_nodes(query: str, dataset_id: str = "main") -> list[dict]:
    """按名称搜索实体"""
    storage = AgeStorage()
    try:
        conn = storage._get_conn()
    except AgeConnectionError as e:
        raise GraphQueryError(f"Cannot connect to AGE: {e}") from e
    try:
        with conn.cursor() as cur:
            cur.execute("SET search_path TO ag_catalog, public;")
            cur.execute(
                f"SELECT * FROM cypher('{storage._graph_name}', $$ "
                f"MATCH (n:Entity) "
                f"WHERE toLower(n.name) CONTAINS toLower('{_escape(query)}') "
                f"RETURN n.id, n.name, n.type, n.description LIMIT 20 "
                f"$$) AS (id text, name text, type text, description text)"
            )
            rows = cur.fetchall()
    except Exception as e:
        logger.error(f"Graph search failed: {e}")
        raise GraphQueryError(str(e)) from e
    finally:
        conn.close()
    return [{"id": r[0], "name": r[1], "type": r[2], "description": r[3]} for r in rows]


def _escape(value: str) -> str:
    return value.replace("\\", "\\\\").replace("'", "\\'")
