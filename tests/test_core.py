import json
from pathlib import Path

from backend.whybase.db import READ_DENY, validate_tenant
from backend.whybase.seed.generate import generate


def test_benchmark_contains_all_required_types():
    generate()
    rows = json.loads(Path("benchmark/questions.json").read_text(encoding="utf-8"))
    assert len(rows) >= 12
    assert {"multihop", "temporal", "absence", "aggregate", "decision-lineage", "counterfactual"} <= {r["type"] for r in rows}
    assert all(r["ground_truth_answer"] for r in rows)


def test_tenant_validation():
    validate_tenant("northwind")
    validate_tenant("halcyon")
    try:
        validate_tenant("cross-tenant")
    except ValueError:
        pass
    else:
        raise AssertionError("unknown tenant was accepted")


def test_read_guard_rejects_writes():
    assert READ_DENY.search("MATCH (n) DELETE n")
    assert READ_DENY.search("MATCH (n) SET n.name = 'x'")
    assert READ_DENY.search("CREATE (n:Person)")
    assert READ_DENY.search("MATCH (n) RETURN n") is None
