"""Concurrent memory-graph smoke load test used by the demo and Makefile."""
from __future__ import annotations

import statistics
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any

from .db import store


def run(workers: int = 20, seconds: int = 5) -> dict[str, Any]:
    if not store.available:
        raise RuntimeError("FalkorDB is required for the load test")
    latencies: list[float] = []
    errors = 0
    stop = time.perf_counter() + seconds

    def one() -> float:
        started = time.perf_counter()
        store.ro_query("northwind", "MATCH (n) RETURN count(n) AS count", {}, memory=True)
        return (time.perf_counter() - started) * 1000

    with ThreadPoolExecutor(max_workers=workers) as pool:
        while time.perf_counter() < stop:
            futures = [pool.submit(one) for _ in range(workers)]
            for future in as_completed(futures):
                try:
                    latencies.append(future.result())
                except Exception:
                    errors += 1
    ordered = sorted(latencies)
    percentile = lambda p: round(ordered[min(int(len(ordered) * p), max(len(ordered) - 1, 0))], 2) if ordered else None
    return {"workers": workers, "seconds": seconds, "ops": len(latencies), "ops_per_sec": round(len(latencies) / seconds, 2),
            "p50_ms": percentile(.50), "p95_ms": percentile(.95), "p99_ms": percentile(.99), "errors": errors}
