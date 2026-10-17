"""Graph-native investigation tools. Each result includes a receipt payload."""
from __future__ import annotations

from typing import Any

from ..db import QueryResult, store, validate_tenant
from ..queries.core import ABSENCE_CHECK, BLAST_RADIUS, DECISION_LINEAGE, TRACE_INCIDENT, WHO_OWNED


def _receipt(result: QueryResult, node_ids: list[str] | None = None,
             edge_ids: list[str] | None = None, snippets: list[str] | None = None) -> dict[str, Any]:
    return {
        "rows": result.rows,
        "cypher": result.cypher,
        "params": result.params,
        "ms": result.ms,
        "evidence": {"node_ids": node_ids or [], "edge_ids": edge_ids or []},
        "source_snippets": snippets or [],
    }


def blast_radius(tenant: str, service: str, depth: int = 3) -> dict[str, Any]:
    validate_tenant(tenant)
    result = store.ro_query(tenant, BLAST_RADIUS, {"service": service, "depth": min(depth, 5), "cap": 100})
    ids = [str(row.get("id")) for row in result.rows if row.get("id")]
    return _receipt(result, [service, *ids])


def trace_incident(tenant: str, incident: str) -> dict[str, Any]:
    result = store.ro_query(tenant, TRACE_INCIDENT, {"incident": incident})
    ids: list[str] = []
    for row in result.rows:
        for key in ("i", "d", "p", "s", "t"):
            value = row.get(key)
            if isinstance(value, dict) and value.get("id"):
                ids.append(str(value["id"]))
    return _receipt(result, list(dict.fromkeys(ids)))


def who_owned(tenant: str, service: str, as_of: str) -> dict[str, Any]:
    result = store.ro_query(tenant, WHO_OWNED, {"service": service, "as_of": as_of})
    return _receipt(result, [service, *[str(row["team_id"]) for row in result.rows if row.get("team_id")]])


def decision_lineage(tenant: str, decision: str) -> dict[str, Any]:
    result = store.ro_query(tenant, DECISION_LINEAGE, {"decision": decision, "cap": 50})
    return _receipt(result, [decision])


def absence_check(tenant: str, subject: str, scope: str, depth: int = 4) -> dict[str, Any]:
    result = store.ro_query(tenant, ABSENCE_CHECK, {"subject": subject, "scope": scope, "depth": min(depth, 5)})
    count = result.rows[0].get("connecting_paths", 0) if result.rows else 0
    return _receipt(result, [subject, scope], snippets=[
        f"Scanned subject {subject} against scope {scope}; connecting paths = {count}.",
        "An empty path result is an explicit graph proof, not a language-model guess.",
    ])


def critical_services(tenant: str, k: int = 5) -> dict[str, Any]:
    cypher = "MATCH (s:Service) OPTIONAL MATCH (s)<-[:DEPENDS_ON]-(down:Service) RETURN s.id AS id, s.name AS name, count(down) AS dependents ORDER BY dependents DESC LIMIT $k"
    result = store.ro_query(tenant, cypher, {"k": min(k, 20)})
    return _receipt(result, [str(r["id"]) for r in result.rows if r.get("id")])


def semantic_search(tenant: str, query: str, k: int = 8) -> dict[str, Any]:
    cypher = """
    CALL db.idx.fulltext.queryNodes('Chunk', $query) YIELD node, score
    MATCH (node)-[:PART_OF]->(d:Document)
    RETURN node.id AS id, node.text AS text, d.id AS document_id,
           d.title AS title, score
    ORDER BY score DESC LIMIT $k
    """
    result = store.ro_query(tenant, cypher, {"query": query, "k": min(k, 20)})
    return _receipt(result, [str(r["id"]) for r in result.rows if r.get("id")])


def counterfactual_leave(tenant: str, person: str) -> dict[str, Any]:
    cypher = """
    MATCH (p:Person {id: $person})
    OPTIONAL MATCH (p)-[:MEMBER_OF]->(t:Team)-[:OWNS]->(s:Service)
    RETURN p.id AS person, collect(DISTINCT s.id) AS affected_services,
           size(collect(DISTINCT s.id)) AS coverage_loss
    """
    result = store.ro_query(tenant, cypher, {"person": person})
    return _receipt(result, [person])


def knowledge_bottlenecks(tenant: str, k: int = 5) -> dict[str, Any]:
    cypher = """
    MATCH (p:Person)-[:COLLABORATES_WITH]-(q:Person)
    RETURN p.id AS person, count(q) AS connections
    ORDER BY connections DESC LIMIT $k
    """
    result = store.ro_query(tenant, cypher, {"k": min(k, 20)})
    return _receipt(result, [str(row["person"]) for row in result.rows if row.get("person")])


def communities(tenant: str) -> dict[str, Any]:
    cypher = """
    MATCH (p:Person)
    OPTIONAL MATCH (p)-[:MEMBER_OF]->(t:Team)
    RETURN p.id AS person, t.id AS team
    ORDER BY team, person LIMIT 500
    """
    result = store.ro_query(tenant, cypher, {})
    return _receipt(result, [str(row["person"]) for row in result.rows if row.get("person")])


def read_cypher(tenant: str, cypher: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
    result = store.ro_query(tenant, cypher, params or {})
    capped = result.rows[:100]
    return _receipt(QueryResult(capped, result.cypher, result.params, result.ms),
                    [str(row["id"]) for row in capped if row.get("id")])
