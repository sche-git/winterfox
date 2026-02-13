"""Tools for agent use during research."""

from typing import TYPE_CHECKING

from .search import SearchManager, web_search
from .web_fetch import web_fetch
from .graph_tools import read_graph_node, search_graph, note_finding, set_graph_context

if TYPE_CHECKING:
    from ...graph.store import KnowledgeGraph
    from ..protocol import ToolDefinition

__all__ = [
    "SearchManager",
    "web_search",
    "web_fetch",
    "read_graph_node",
    "search_graph",
    "note_finding",
    "get_research_tools",
]


def get_research_tools(graph: "KnowledgeGraph") -> list["ToolDefinition"]:
    """
    Get standard research tools for agents.

    Args:
        graph: Knowledge graph context

    Returns:
        List of tool definitions for web search, web fetch, and graph interaction
    """
    from ..protocol import ToolDefinition

    set_graph_context(graph)

    tools = [
        ToolDefinition(
            name="web_search",
            description="Search the web for information",
            parameters={
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Search query"},
                    "max_results": {"type": "integer", "description": "Maximum results to return", "default": 10},
                },
                "required": ["query"],
            },
            execute=lambda query, max_results=10: web_search(query, max_results),
        ),
        ToolDefinition(
            name="web_fetch",
            description="Fetch and extract content from a URL",
            parameters={
                "type": "object",
                "properties": {
                    "url": {"type": "string", "description": "URL to fetch"},
                },
                "required": ["url"],
            },
            execute=lambda url: web_fetch(url),
        ),
        ToolDefinition(
            name="read_graph_node",
            description="Read a knowledge graph node by ID",
            parameters={
                "type": "object",
                "properties": {
                    "node_id": {"type": "string", "description": "Node ID to read"},
                },
                "required": ["node_id"],
            },
            execute=lambda node_id: read_graph_node(node_id),
        ),
        ToolDefinition(
            name="search_graph",
            description="Full-text search the knowledge graph",
            parameters={
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Search query"},
                    "limit": {"type": "integer", "description": "Maximum results", "default": 5},
                },
                "required": ["query"],
            },
            execute=lambda query, limit=5: search_graph(query, limit),
        ),
        ToolDefinition(
            name="note_finding",
            description="Record a research finding (queued for orchestrator)",
            parameters={
                "type": "object",
                "properties": {
                    "claim": {"type": "string", "description": "Factual claim (2-3 sentences)"},
                    "confidence": {"type": "number", "description": "Confidence 0.0-1.0", "minimum": 0, "maximum": 1},
                    "evidence": {
                        "type": "array",
                        "description": "List of evidence",
                        "items": {
                            "type": "object",
                            "properties": {
                                "text": {"type": "string"},
                                "source": {"type": "string"},
                            },
                            "required": ["text", "source"],
                        },
                    },
                },
                "required": ["claim", "confidence", "evidence"],
            },
            execute=lambda claim, confidence, evidence: note_finding(claim, confidence, evidence),
        ),
    ]

    return tools
