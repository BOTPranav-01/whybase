"""Scribe ingests a public event into the tenant knowledge graph."""
from __future__ import annotations

import time
from typing import Any

from .db import store, validate_tenant


def ingest_event(tenant: str, title: str, text: str, kind: str = "chat") -> dict[str, Any]:
    validate_tenant(tenant)
    document_id = f"{tenant}-event-{int(time.time() * 1000)}"
    result = store.query(
        tenant,
        """
        CREATE (d:Document {id: $id, kind: $kind, title: $title,
                            text: $text, created_at: $created_at})
        CREATE (c:Chunk {id: $chunk_id, text: $text, embedding: $embedding})
        CREATE (c)-[:PART_OF]->(d)
        RETURN d.id AS document_id, c.id AS chunk_id
        """,
        {
            "id": document_id,
            "chunk_id": f"{document_id}-chunk-0",
            "kind": kind,
            "title": title,
            "text": text,
            "created_at": time.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "embedding": [0.0] * 8,
        },
    )
    handoff = store.query(
        tenant,
        """
        CREATE (h:Handoff {id: $id, from_agent: 'scribe', to_agent: 'sentinel',
                           payload_ref: $payload, ts: $ts})
        RETURN h.id AS handoff_id
        """,
        {
            "id": f"{tenant}-handoff-{int(time.time() * 1000)}",
            "payload": document_id,
            "ts": time.strftime("%Y-%m-%dT%H:%M:%SZ"),
        },
        memory=True,
    )
    return {"document": result.rows, "handoff": handoff.rows}
