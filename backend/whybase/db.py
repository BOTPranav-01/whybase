"""FalkorDB connection and guarded, parameterized query helpers."""
from __future__ import annotations

import os
import re
import time
from dataclasses import dataclass
from typing import Any

from dotenv import load_dotenv

load_dotenv()

TENANTS = {"northwind", "halcyon"}
READ_DENY = re.compile(
    r"\b(CREATE|MERGE|DELETE|DETACH|SET|REMOVE|DROP|GRAPH\.DELETE|CALL\s+db\.)\b",
    re.IGNORECASE,
)


@dataclass
class QueryResult:
    rows: list[dict[str, Any]]
    cypher: str
    params: dict[str, Any]
    ms: float


class TenantError(ValueError):
    """Raised when a request attempts to leave the tenant boundary."""


class FalkorUnavailable(RuntimeError):
    """Raised when FalkorDB is required but cannot be reached."""


class GraphStore:
    def __init__(self) -> None:
        self.client: Any | None = None
        self._connect_error: str | None = None
        try:
            from falkordb import FalkorDB

            url = os.getenv("FALKORDB_URL")
            if url:
                self.client = FalkorDB.from_url(url)
            else:
                kwargs: dict[str, Any] = {
                    "host": os.getenv("FALKORDB_HOST", "localhost"),
                    "port": int(os.getenv("FALKORDB_PORT", "6379")),
                }
                username = os.getenv("FALKORDB_USERNAME")
                password = os.getenv("FALKORDB_PASSWORD")
                if username:
                    kwargs["username"] = username
                if password:
                    kwargs["password"] = password
                self.client = FalkorDB(**kwargs)
        except Exception as exc:
            self._connect_error = str(exc)

    @property
    def available(self) -> bool:
        return self.client is not None

    def ping(self) -> bool:
        if not self.client:
            return False
        try:
            self.graph("northwind").query("MATCH (n) RETURN count(n) AS count")
            return True
        except Exception:
            return False

    @staticmethod
    def graph_name(tenant: str, memory: bool = False) -> str:
        validate_tenant(tenant)
        return f"{'mem' if memory else 'kb'}_{tenant}"

    def graph(self, tenant: str, memory: bool = False) -> Any:
        if not self.client:
            raise FalkorUnavailable(self._connect_error or "FalkorDB is unavailable")
        return self.client.select_graph(self.graph_name(tenant, memory))

    def query(
        self,
        tenant: str,
        cypher: str,
        params: dict[str, Any] | None = None,
        memory: bool = False,
    ) -> QueryResult:
        validate_tenant(tenant)
        started = time.perf_counter()
        result = self.graph(tenant, memory).query(cypher, params or {})
        return QueryResult(_rows(result), cypher, params or {}, _elapsed_ms(started))

    def ro_query(
        self,
        tenant: str,
        cypher: str,
        params: dict[str, Any] | None = None,
        memory: bool = False,
    ) -> QueryResult:
        if READ_DENY.search(cypher):
            raise ValueError("read_cypher rejected a write clause")
        validate_tenant(tenant)
        started = time.perf_counter()
        graph = self.graph(tenant, memory)
        result = graph.ro_query(cypher, params or {}) if hasattr(graph, "ro_query") else graph.query(cypher, params or {})
        return QueryResult(_rows(result), cypher, params or {}, _elapsed_ms(started))


def _elapsed_ms(started: float) -> float:
    return round((time.perf_counter() - started) * 1000, 2)


def validate_tenant(tenant: str) -> None:
    if tenant not in TENANTS:
        raise TenantError(f"unknown tenant: {tenant}")


def _rows(result: Any) -> list[dict[str, Any]]:
    header = getattr(result, "header", None) or getattr(result, "columns", None) or []
    raw = getattr(result, "result_set", None) or getattr(result, "rows", None) or []
    names = [str(item) for item in header]
    return [item if isinstance(item, dict) else dict(zip(names, item)) for item in raw]


store = GraphStore()
