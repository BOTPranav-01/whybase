"""Load deterministic seed data into one FalkorDB graph per tenant."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from ..db import store
from .generate import ROOT, generate


def _load_graph(tenant: str, data: dict[str, Any]) -> None:
    source_keys = {
        "Person": "people",
        "Team": "teams",
        "Service": "services",
        "Decision": "decisions",
        "Incident": "incidents",
        "Document": "documents",
    }
    for label, source_key in source_keys.items():
        store.query(tenant, f"UNWIND $items AS item MERGE (n:{label} {{id: item.id}}) SET n += item", {"items": data[source_key]})
    chunks = []
    for document in data["documents"]:
        text = document["text"]
        chunks.append({
            "id": f"{document['id']}-chunk-0",
            "text": text,
            "embedding": [0.0] * 8,
        })
    store.query(
        tenant,
        "UNWIND $items AS item MERGE (c:Chunk {id: item.id}) SET c.text = item.text, c.embedding = vecf32(item.embedding)",
        {"items": chunks},
    )
    for edge in data["edges"]:
        rel = edge["type"]
        store.query(tenant, f"MATCH (a {{id: $from}}), (b {{id: $to}}) MERGE (a)-[r:{rel}]->(b) SET r += $props",
                    {"from": edge["from"], "to": edge["to"], "props": {k: v for k, v in edge.items() if k not in {"type", "from", "to"}}})
    for document in data["documents"]:
        store.query(
            tenant,
            "MATCH (c:Chunk {id: $chunk}), (d:Document {id: $document}) MERGE (c)-[:PART_OF]->(d)",
            {"chunk": f"{document['id']}-chunk-0", "document": document["id"]},
        )
    for index_query in (
        "CREATE INDEX FOR (n:Service) ON (n.id)",
        "CREATE FULLTEXT INDEX FOR (n:Document) ON (n.title, n.text)",
        "CREATE FULLTEXT INDEX FOR (n:Chunk) ON (n.text)",
        "CREATE VECTOR INDEX FOR (n:Chunk) ON (n.embedding) OPTIONS {dimension: 8, similarityFunction: 'cosine'}",
    ):
        try:
            store.query(tenant, index_query, {})
        except Exception as exc:
            if "already exists" not in str(exc).lower():
                raise


def seed() -> None:
    generate()
    if not store.available:
        raise RuntimeError("FalkorDB is required to seed WHYBASE")
    for tenant in ("northwind", "halcyon"):
        path = ROOT / "backend" / "whybase" / "seed" / "data" / f"{tenant}.json"
        _load_graph(tenant, json.loads(path.read_text(encoding="utf-8")))


if __name__ == "__main__":
    seed()
