"""AGE 图数据只读查询封装"""

import logging
from typing import Any, Optional

from app.kg_pipeline.storage import AgeStorage, AgeConnectionError

logger = logging.getLogger(__name__)


class GraphQueryError(Exception):
    pass


def get_full_graph(graph_name: Optional[str] = None) -> dict[str, Any]:
    """获取完整图数据（节点 + 边 + 统计），自动去重"""
    storage = AgeStorage(graph_name=graph_name)
    try:
        conn = storage._get_conn()
    except AgeConnectionError as e:
        raise GraphQueryError(f"Cannot connect to AGE: {e}") from e
    try:
        with conn.cursor() as cur:
            cur.execute("LOAD 'age';")
            cur.execute("SET search_path TO ag_catalog, public;")
            cur.execute(
                f"SELECT * FROM cypher('{storage._graph_name}', $$ "
                f"MATCH (n:Entity) RETURN n.id, n.name, n.type, n.description "
                f"$$) AS (id agtype, name agtype, type agtype, description agtype)"
            )
            rows = cur.fetchall()

            # 按 id 去重，保留第一个
            seen_ids: set[str] = set()
            nodes = []
            type_counter: dict[str, int] = {}
            for row in rows:
                nid, name, ntype, desc = row
                nid = _strip_agtype(nid)
                if nid in seen_ids:
                    continue
                seen_ids.add(nid)
                name = _strip_agtype(name)
                ntype = _strip_agtype(ntype)
                desc = _strip_agtype(desc)
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
                f"$$) AS (source agtype, target agtype, rel agtype, rel_desc agtype)"
            )
            edge_rows = cur.fetchall()

            # 按 (source, target) 去重
            seen_edges: set[tuple[str, str]] = set()
            edges = []
            degree_counter: dict[str, int] = {}
            for row in edge_rows:
                src, tgt, rel, rel_desc = row
                src = _strip_agtype(src)
                tgt = _strip_agtype(tgt)
                edge_key = (src, tgt)
                if edge_key in seen_edges:
                    continue
                seen_edges.add(edge_key)
                rel = _strip_agtype(rel)
                rel_desc = _strip_agtype(rel_desc)
                edges.append({
                    "source": src, "target": tgt,
                    "relationship_name": rel or "related_to",
                    "description": rel_desc or "",
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


def search_nodes(query: str, graph_name: Optional[str] = None) -> list[dict]:
    """按名称搜索实体，自动去重"""
    storage = AgeStorage(graph_name=graph_name)
    try:
        conn = storage._get_conn()
    except AgeConnectionError as e:
        raise GraphQueryError(f"Cannot connect to AGE: {e}") from e
    try:
        with conn.cursor() as cur:
            cur.execute("LOAD 'age';")
            cur.execute("SET search_path TO ag_catalog, public;")
            cur.execute(
                f"SELECT * FROM cypher('{storage._graph_name}', $$ "
                f"MATCH (n:Entity) "
                f"WHERE toLower(n.name) CONTAINS toLower('{_escape(query)}') "
                f"RETURN n.id, n.name, n.type, n.description LIMIT 20 "
                f"$$) AS (id agtype, name agtype, type agtype, description agtype)"
            )
            rows = cur.fetchall()
    except Exception as e:
        logger.error(f"Graph search failed: {e}")
        raise GraphQueryError(str(e)) from e
    finally:
        conn.close()
    # 按 id 去重
    seen: set[str] = set()
    results = []
    for r in rows:
        nid = _strip_agtype(r[0])
        if nid in seen:
            continue
        seen.add(nid)
        results.append({"id": nid, "name": _strip_agtype(r[1]),
                        "type": _strip_agtype(r[2]), "description": _strip_agtype(r[3])})
    return results


def _escape(value: str) -> str:
    return value.replace("\\", "\\\\").replace("'", "\\'")


def _strip_agtype(value) -> str:
    """去掉 AGE agtype 返回值的外层引号"""
    if value is None:
        return ""
    s = str(value)
    if s.startswith('"') and s.endswith('"'):
        s = s[1:-1]
    return s
