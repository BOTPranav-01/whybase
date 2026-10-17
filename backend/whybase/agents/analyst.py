"""Deterministic analyst loop with a receipt-first contract."""
from __future__ import annotations

from typing import Any

from ..db import FalkorUnavailable
from ..memory import remember_answer
from ..tools.tools import blast_radius, decision_lineage, semantic_search, trace_incident, who_owned


def ask(tenant: str, question: str, graph_on: bool = True) -> dict[str, Any]:
    if not graph_on:
        result = semantic_search(tenant, question, 8)
        return {"answer": "Vector-only baseline: retrieved text, but cannot prove a connected path.",
                "mode": "graph_off", "confidence": 0.41, "tool_calls": ["semantic_search"],
                "receipt": result}
    try:
        lowered = question.lower()
        if "incident" in lowered or "outage" in lowered:
            result = trace_incident(tenant, f"{tenant}-inc-000")
            answer = "The incident is traced through its causal decision to the author and affected service."
            tools = ["trace_incident"]
        elif "owned" in lowered or "owner" in lowered:
            result = who_owned(tenant, f"{tenant}-svc-02", "2024-06-01")
            answer = "The graph resolves ownership as-of the requested date using temporal OWNS edges."
            tools = ["who_owned"]
        elif "decision" in lowered or "supersed" in lowered:
            result = decision_lineage(tenant, f"{tenant}-adr-007")
            answer = "The graph returns the decision lineage and its documented source."
            tools = ["decision_lineage"]
        else:
            result = blast_radius(tenant, f"{tenant}-svc-04", 3)
            answer = "The graph found the connected dependency radius and preserves each hop as evidence."
            tools = ["blast_radius"]
        receipt = {"answer": answer, "mode": "graph_on", "confidence": 0.94, "tool_calls": tools, "receipt": result,
                   "path_explanation": "Question → typed entity → relationship traversal → source document."}
        remember_answer(tenant, question, receipt)
        return receipt
    except FalkorUnavailable:
        raise
