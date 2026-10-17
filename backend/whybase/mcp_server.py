"""MCP server exposing the same receipt-producing tools used by Analyst."""
from mcp.server.fastmcp import FastMCP

from .tools.tools import (
    absence_check, blast_radius, communities, counterfactual_leave,
    critical_services, decision_lineage, knowledge_bottlenecks,
    read_cypher, semantic_search, trace_incident, who_owned,
)

mcp = FastMCP("whybase")
mcp.tool()(blast_radius)
mcp.tool()(trace_incident)
mcp.tool()(who_owned)
mcp.tool()(decision_lineage)
mcp.tool()(absence_check)
mcp.tool()(critical_services)
mcp.tool()(semantic_search)
mcp.tool()(counterfactual_leave)
mcp.tool()(knowledge_bottlenecks)
mcp.tool()(communities)
mcp.tool()(read_cypher)

if __name__ == "__main__":
    mcp.run()
