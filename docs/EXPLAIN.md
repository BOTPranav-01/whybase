# WHYBASE explained

## The core loop

Scribe writes typed entities and relationships into FalkorDB. Analyst selects a typed query through MCP, executes it against the tenant graph, and builds a receipt. Sentinel reads the same graph to find weak ownership and creates an alert/action chain. Agents coordinate through graph state, not process-local variables.

## Twelve judge questions

1. **Why a graph?** A vector can retrieve similar prose; it cannot prove a typed path from incident to decision to author to current owner.
2. **Why FalkorDB?** It is the primary queryable context layer and executes the relationship traversal where the data lives.
3. **What happens without it?** Graph ON returns a clear unavailable error; there is no hidden source-of-truth fallback.
4. **How are tenants isolated?** Every request validates a tenant allow-list and maps it to a separate graph name.
5. **How do receipts work?** The tool result carries Cypher, parameters, timing, evidence ids, and snippets.
6. **How does time travel work?** `valid_from` and `valid_to` are filtered against an as-of date.
7. **What is an absence answer?** A bounded optional path query returns zero paths plus scan counts.
8. **How are superseded facts retained?** Old edges are closed with `valid_to`; they are never deleted.
9. **How does Sentinel act safely?** It drafts actions; a human must approve them in the UI.
10. **How does Arena stay fair?** Both modes use the same questions and corpus; only the retrieval substrate changes.
11. **Why is the data synthetic?** The challenge requires public/synthetic data and this avoids privacy and licensing risk.
12. **What is next?** Add production embedding indexes and enable the exact FalkorDB algorithms supported by the deployment version.
