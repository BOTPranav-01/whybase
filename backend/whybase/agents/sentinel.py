"""Sentinel invariant checks and human-approval action records."""
from __future__ import annotations

import time
from typing import Any

from ..db import store


def scan(tenant: str) -> list[dict[str, Any]]:
    query = "MATCH (s:Service) OPTIONAL MATCH (t:Team)-[:OWNS]->(s) RETURN s.id AS service_id, s.name AS service, count(t) AS owners ORDER BY owners LIMIT 10"
    result = store.ro_query(tenant, query, {})
    alerts = []
    for row in result.rows:
        if int(row.get("owners", 0)) <= 1:
            alert_id = f"alert-{row['service_id']}"
            store.query(
                tenant,
                """
                MERGE (a:Alert {id: $id})
                SET a.type = 'BUS_FACTOR', a.severity = 'high',
                    a.service = $service, a.state = 'open'
                MERGE (x:Action {id: $action})
                SET x.kind = 'draft_reviewer_assignment',
                    x.target = $service, x.state = 'awaiting_approval'
                MERGE (a)-[:PROPOSES]->(x)
                RETURN a.id AS alert_id, x.id AS action_id
                """,
                {"id": alert_id, "action": f"{alert_id}-action", "service": row["service"]},
                memory=True,
            )
            alerts.append({"id": alert_id, "type": "BUS_FACTOR", "severity": "high",
                           "service": row["service"], "state": "open",
                           "action": {"kind": "draft_reviewer_assignment", "state": "awaiting_approval"}})
    return alerts


def approve_action(tenant: str, action_id: str) -> dict[str, Any]:
    result = store.query(
        tenant,
        """
        MATCH (a:Action {id: $action})
        SET a.state = 'approved', a.approved_at = $ts
        RETURN a.id AS action_id, a.state AS state
        """,
        {"action": action_id, "ts": time.strftime("%Y-%m-%dT%H:%M:%SZ")},
        memory=True,
    )
    return {"rows": result.rows, "cypher": result.cypher, "params": result.params, "ms": result.ms}
