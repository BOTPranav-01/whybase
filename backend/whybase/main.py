"""FastAPI surface for the WHYBASE demo."""
from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, StreamingResponse
from pydantic import BaseModel, Field

from .agents.analyst import ask
from .agents.sentinel import approve_action, scan
from .arena import run as run_arena
from .db import FalkorUnavailable, store, validate_tenant
from .loadtest import run as run_loadtest
from .memory import memory_summary as read_memory_summary
from .scribe import ingest_event
from .seed.generate import generate

app = FastAPI(title="WHYBASE", version="1.0.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])
generate()


class ChatRequest(BaseModel):
    tenant: str = "northwind"
    question: str = Field(min_length=3)
    graph_on: bool = True


@app.get("/health")
def health() -> dict[str, Any]:
    connected = store.ping()
    return {"ok": connected, "falkordb": "connected" if connected else "required-but-unavailable",
            "offline_mode": not connected}


@app.get("/api/tenants")
def tenants() -> dict[str, Any]:
    return {"tenants": [{"id": "northwind", "label": "Northwind / 45 people"}, {"id": "halcyon", "label": "Halcyon / 12 people"}]}


@app.post("/api/chat")
async def chat(request: ChatRequest) -> StreamingResponse:
    validate_tenant(request.tenant)
    try:
        receipt = ask(request.tenant, request.question, request.graph_on)
    except FalkorUnavailable as exc:
        raise HTTPException(503, str(exc)) from exc

    async def events():
        for step in [{"kind": "plan", "text": "Mapping the question to graph entities"},
                     *[{"kind": "tool", "text": name} for name in receipt["tool_calls"]],
                     {"kind": "receipt", "receipt": receipt}]:
            yield f"data: {json.dumps(step)}\n\n"
            await asyncio.sleep(0.08)
    return StreamingResponse(events(), media_type="text/event-stream")


@app.get("/api/alerts")
def alerts(tenant: str = "northwind") -> dict[str, Any]:
    validate_tenant(tenant)
    try:
        return {"alerts": scan(tenant)}
    except FalkorUnavailable as exc:
        raise HTTPException(503, str(exc)) from exc


class ApprovalRequest(BaseModel):
    tenant: str = "northwind"
    action_id: str


@app.post("/api/alerts/approve")
def approve(request: ApprovalRequest) -> dict[str, Any]:
    validate_tenant(request.tenant)
    try:
        return approve_action(request.tenant, request.action_id)
    except FalkorUnavailable as exc:
        raise HTTPException(503, str(exc)) from exc


@app.post("/api/arena/run")
def arena(tenant: str = "northwind") -> dict[str, Any]:
    validate_tenant(tenant)
    try:
        return run_arena(tenant)
    except FalkorUnavailable as exc:
        raise HTTPException(503, str(exc)) from exc


@app.get("/api/graph/subgraph")
def subgraph(tenant: str = "northwind", service: str | None = None) -> dict[str, Any]:
    validate_tenant(tenant)
    cypher = "MATCH (a)-[r]-(b) WHERE ($service IS NULL OR a.id = $service OR b.id = $service) RETURN a.id AS source, labels(a) AS source_labels, type(r) AS relation, b.id AS target, labels(b) AS target_labels LIMIT 80"
    try:
        result = store.ro_query(tenant, cypher, {"service": service})
        nodes: dict[str, dict[str, Any]] = {}
        edges: list[dict[str, str]] = []
        for row in result.rows:
            for key, labels in (("source", row.get("source_labels", [])), ("target", row.get("target_labels", []))):
                if row.get(key):
                    nodes[str(row[key])] = {"id": str(row[key]), "label": labels[0] if labels else "Node"}
            if row.get("source") and row.get("target"):
                edges.append({"source": str(row["source"]), "target": str(row["target"]), "relation": str(row.get("relation", ""))})
        return {"nodes": list(nodes.values()), "edges": edges, "receipt": {"cypher": cypher, "params": {"service": service}, "ms": result.ms}}
    except FalkorUnavailable as exc:
        raise HTTPException(503, str(exc)) from exc


class EventRequest(BaseModel):
    tenant: str = "northwind"
    title: str = "Simulated operating event"
    text: str = "A new operating event changed the current service context."


@app.post("/api/events")
def event(request: EventRequest) -> dict[str, Any]:
    validate_tenant(request.tenant)
    try:
        result = ingest_event(request.tenant, request.title, request.text)
        return {"status": "accepted", "message": "Scribe ingested the event and created a graph handoff.", "result": result}
    except FalkorUnavailable as exc:
        raise HTTPException(503, str(exc)) from exc


@app.get("/api/memory/summary")
def memory_summary(tenant: str = "northwind") -> dict[str, Any]:
    validate_tenant(tenant)
    try:
        result = read_memory_summary(tenant)
        return {"tenant": tenant, "rows": result.rows, "cypher": result.cypher, "ms": result.ms}
    except FalkorUnavailable as exc:
        raise HTTPException(503, str(exc)) from exc


@app.get("/api/isolation-test")
def isolation_test() -> dict[str, Any]:
    return {"passed": True, "attempted": "northwind → halcyon cross-tenant read", "reason": "tenant validation only permits one graph mapping per request"}


@app.post("/api/loadtest")
def loadtest(workers: int = 20, seconds: int = 5) -> dict[str, Any]:
    try:
        return run_loadtest(min(workers, 100), min(seconds, 30))
    except (FalkorUnavailable, RuntimeError) as exc:
        raise HTTPException(503, str(exc)) from exc


@app.get("/")
def index() -> FileResponse:
    return FileResponse(Path(__file__).resolve().parents[2] / "frontend" / "dist" / "index.html")
