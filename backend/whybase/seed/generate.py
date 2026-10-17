"""Deterministic synthetic company graph and benchmark generator."""
from __future__ import annotations

import json
import random
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[3]


def build_tenant(tenant: str, people_count: int, services_count: int) -> dict[str, Any]:
    rng = random.Random(42 if tenant == "northwind" else 84)
    people = [{"id": f"{tenant}-p-{i:03}", "name": f"{tenant.title()} Person {i:03}", "role": "Engineer",
               "joined": f"202{3 + i % 3}-01-15", "left": None if i % 9 else "2026-02-01"} for i in range(people_count)]
    teams = [{"id": f"{tenant}-team-{i:02}", "name": f"{tenant.title()} Platform Team {i:02}"} for i in range(8 if tenant == "northwind" else 4)]
    services = [{"id": f"{tenant}-svc-{i:02}", "name": f"{tenant.title()} Service {i:02}", "tier": "critical" if i < 5 else "standard"} for i in range(services_count)]
    decisions = [{"id": f"{tenant}-adr-{i:03}", "title": f"Reliability decision {i:03}", "status": "accepted", "decided_at": f"202{3 + i % 3}-06-{(i % 27) + 1:02}"} for i in range(60 if tenant == "northwind" else 16)]
    incidents = [{"id": f"{tenant}-inc-{i:03}", "severity": "SEV1" if i < 3 else "SEV2", "summary": f"Dependency incident {i:03}"} for i in range(14 if tenant == "northwind" else 3)]
    documents = [{"id": f"{tenant}-doc-{i:03}", "kind": "runbook" if i % 4 == 0 else "postmortem", "title": f"{tenant.title()} operating note {i:03}",
                  "text": f"The operating note explains a service dependency, the owner team, and the decision history for {tenant} item {i:03}."} for i in range(350 if tenant == "northwind" else 60)]
    edges = []
    for i, service in enumerate(services):
        if i:
            edges.append({"type": "DEPENDS_ON", "from": service["id"], "to": services[(i - 1) // 2]["id"]})
    for i, person in enumerate(people):
        edges.append({"type": "MEMBER_OF", "from": person["id"], "to": teams[i % len(teams)]["id"], "valid_from": "2023-01-01", "valid_to": person["left"]})
    for i, service in enumerate(services):
        edges.append({"type": "OWNS", "from": teams[i % len(teams)]["id"], "to": service["id"], "valid_from": "2023-01-01", "valid_to": None})
    for i, decision in enumerate(decisions):
        edges.append({"type": "DECIDED", "from": people[i % len(people)]["id"], "to": decision["id"]})
        edges.append({"type": "AFFECTS", "from": decision["id"], "to": services[i % len(services)]["id"]})
        edges.append({"type": "DOCUMENTED_IN", "from": decision["id"], "to": documents[i % len(documents)]["id"]})
        if i >= 1 and i % 7 == 0:
            edges.append({"type": "SUPERSEDES", "from": decision["id"], "to": decisions[i - 1]["id"]})
    for i, incident in enumerate(incidents):
        edges.append({"type": "CAUSED_BY", "from": incident["id"], "to": decisions[(i * 7) % len(decisions)]["id"]})
    base_needles = [
                    ("multihop", f"Which team owns the service upstream of {services[4]['name']}?", teams[2]["name"], [services[4]["id"], services[1]["id"], teams[2]["id"]]),
                    ("temporal", f"Who owned {services[2]['name']} on 2024-06-01?", teams[2]["name"], [services[2]["id"], teams[2]["id"]]),
                    ("absence", f"Is {people[-1]['name']} connected to {services[0]['name']}?", "No connecting path exists.", [people[-1]["id"], services[0]["id"]]),
                    ("aggregate", "Which services have the largest blast radius?", services[0]["name"], [services[0]["id"]]),
                    ("decision-lineage", f"Which decision superseded {decisions[0]['title']}?", decisions[7]["title"] if len(decisions) > 7 else decisions[1]["title"], [decisions[0]["id"], decisions[7]["id"] if len(decisions) > 7 else decisions[1]["id"]]),
                    ("counterfactual", f"What changes if {people[0]['name']} leaves?", "The service coverage alert increases.", [people[0]["id"], services[0]["id"]]),
                ]
    # Variants are generated from structured graph facts, not from an LLM.
    for i in range(1, 8):
        base_needles.extend([
            ("multihop", f"Which team is responsible for the dependency behind {services[(i + 3) % len(services)]['name']}?", teams[i % len(teams)]["name"], [services[(i + 3) % len(services)]["id"], teams[i % len(teams)]["id"]]),
            ("temporal", f"Who owned {services[i % len(services)]['name']} on 2025-03-01?", teams[i % len(teams)]["name"], [services[i % len(services)]["id"], teams[i % len(teams)]["id"]]),
            ("absence", f"Does {people[(i + 5) % len(people)]['name']} have a path to {services[(i + 8) % len(services)]['name']}?", "No connecting path exists.", [people[(i + 5) % len(people)]["id"], services[(i + 8) % len(services)]["id"]]),
            ("decision-lineage", f"What is the history of {decisions[i]['title']}?", decisions[i]["title"], [decisions[i]["id"]]),
            ("counterfactual", f"What changes if {people[i % len(people)]['name']} leaves?", "The service coverage alert increases.", [people[i % len(people)]["id"]]),
        ])
    needles = [{"id": f"{tenant}-needle-{i:02}", "type": t, "question": q,
                "ground_truth_answer": a, "ground_truth_node_ids": ids}
               for i, (t, q, a, ids) in enumerate(base_needles)]
    return {"tenant": tenant, "people": people, "teams": teams, "services": services, "decisions": decisions,
            "incidents": incidents, "documents": documents, "edges": edges, "needles": needles}


def generate() -> None:
    northwind = build_tenant("northwind", 45, 28)
    halcyon = build_tenant("halcyon", 12, 8)
    benchmark = [needle for data in (northwind, halcyon) for needle in data["needles"]]
    out = ROOT / "benchmark" / "questions.json"
    out.parent.mkdir(exist_ok=True)
    out.write_text(json.dumps(benchmark, indent=2), encoding="utf-8")
    seed_dir = ROOT / "backend" / "whybase" / "seed" / "data"
    seed_dir.mkdir(parents=True, exist_ok=True)
    for data in (northwind, halcyon):
        (seed_dir / f"{data['tenant']}.json").write_text(json.dumps(data, indent=2), encoding="utf-8")


if __name__ == "__main__":
    generate()
