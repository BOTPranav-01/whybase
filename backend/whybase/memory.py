"""Persistent episodic, semantic, procedural, and coordination memory in FalkorDB."""
from __future__ import annotations

import hashlib
import time
from typing import Any

from .db import QueryResult, store, validate_tenant


def _id(prefix: str, text: str) -> str:
    return f"{prefix}-{hashlib.sha1(text.encode('utf-8')).hexdigest()[:12]}"


def remember_answer(tenant: str, question: str, answer: dict[str, Any]) -> QueryResult:
    validate_tenant(tenant)
    episode_id = _id("episode", f"{tenant}:{question}:{time.time_ns()}")
    procedure_id = _id("procedure", question.lower())
    return store.query(
        tenant,
        """
        MERGE (s:Session {id: $session})
        CREATE (e:Episode {id: $episode, ts: $ts, role: 'analyst', text: $text})
        MERGE (s)-[:HAS_EPISODE]->(e)
        MERGE (p:Procedure {id: $procedure})
        SET p.intent = $intent, p.cypher_template = $cypher,
            p.tool_chain = $tools, p.last_used = $ts
        SET p.success_count = coalesce(p.success_count, 0) + 1
        RETURN e.id AS episode_id, p.id AS procedure_id
        """,
        {
            "session": _id("session", tenant),
            "episode": episode_id,
            "procedure": procedure_id,
            "ts": time.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "text": answer.get("answer", ""),
            "intent": question,
            "cypher": answer.get("receipt", {}).get("cypher", ""),
            "tools": answer.get("tool_calls", []),
        },
        memory=True,
    )


def memory_summary(tenant: str) -> QueryResult:
    return store.ro_query(
        tenant,
        "MATCH (n) RETURN labels(n) AS labels, count(n) AS count ORDER BY count DESC",
        {},
        memory=True,
    )
