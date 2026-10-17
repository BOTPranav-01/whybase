"""Small deterministic Arena runner contrasting connected retrieval and vectors."""
from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

from .agents.analyst import ask


def run(tenant: str = "northwind") -> dict[str, Any]:
    questions = json.loads((Path(__file__).resolve().parents[2] / "benchmark" / "questions.json").read_text(encoding="utf-8"))
    questions = [q for q in questions if q["id"].startswith(tenant)]
    rows = []
    for q in questions:
        started = time.perf_counter()
        graph = ask(tenant, q["question"], True)
        graph_ok = any(node in str(graph) for node in q["ground_truth_node_ids"])
        graph_ms = round((time.perf_counter() - started) * 1000, 2)
        started = time.perf_counter()
        baseline = ask(tenant, q["question"], False)
        vector_ms = round((time.perf_counter() - started) * 1000, 2)
        vector_ok = any(node in str(baseline["receipt"].get("evidence", {})) for node in q["ground_truth_node_ids"])
        rows.append({"id": q["id"], "type": q["type"], "graph_correct": graph_ok, "vector_correct": vector_ok,
                     "graph_ms": graph_ms, "vector_ms": vector_ms})
    result = {"tenant": tenant, "rows": rows, "graph_accuracy": round(sum(r["graph_correct"] for r in rows) / max(len(rows), 1), 2),
              "vector_accuracy": round(sum(r["vector_correct"] for r in rows) / max(len(rows), 1), 2),
              "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ")}
    path = Path(__file__).resolve().parents[2] / "results" / "arena_latest.json"
    path.parent.mkdir(exist_ok=True)
    path.write_text(json.dumps(result, indent=2), encoding="utf-8")
    return result
