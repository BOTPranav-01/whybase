# WHYBASE — Graph Hacks submission

FalkorDB is the primary source of truth. Every answer must include a receipt: answer text, parameterized Cypher, evidence node/edge ids, and source snippets. The dataset is synthetic and deterministic. Keep tenant graphs isolated (`kb_northwind`, `kb_halcyon`) and never add a non-graph database as a source of truth.

Use Python 3.11, FastAPI, pydantic v2, the official `falkordb` client, and parameterized Cypher. Keep the offline mode clearly labeled and only for deterministic demo fallback when FalkorDB is unavailable; the product health state must show that FalkorDB is required.
