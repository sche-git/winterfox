"""
Graph interaction tools for agents.

These tools allow agents to:
- Read existing knowledge graph nodes
- Search the knowledge graph
- Record new findings
"""

import json
import logging
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from ...graph.store import KnowledgeGraph

logger = logging.getLogger(__name__)

# Global graph instance (will be set by orchestrator)
_graph: "KnowledgeGraph | None" = None


def set_graph_context(graph: "KnowledgeGraph"):
    """
    Set the knowledge graph context for tools.

    Args:
        graph: KnowledgeGraph instance
    """
    global _graph
    _graph = graph


def get_graph() -> "KnowledgeGraph":
    """Get the current graph context."""
    if _graph is None:
        raise RuntimeError("Graph context not set. Call set_graph_context() first.")
    return _graph


async def read_graph_node(node_id: str) -> dict[str, Any]:
    """
    Read a knowledge graph node by ID.

    Args:
        node_id: Node ID to read

    Returns:
        Node data as dict
    """
    graph = get_graph()
    node = await graph.get_node(node_id)

    if not node:
        return {"error": f"Node {node_id} not found"}

    return {
        "id": node.id,
        "claim": node.claim,
        "confidence": node.confidence,
        "importance": node.importance,
        "depth": node.depth,
        "children_count": len(node.children_ids),
        "evidence_count": len(node.evidence),
        "tags": node.tags,
        "created_by_cycle": node.created_by_cycle,
    }


async def search_graph(query: str, limit: int = 5) -> list[dict[str, Any]]:
    """
    Full-text search the knowledge graph.

    Args:
        query: Search query
        limit: Maximum results

    Returns:
        List of matching nodes
    """
    graph = get_graph()
    nodes = await graph.search(query, limit=limit)

    return [
        {
            "id": node.id,
            "claim": node.claim,
            "confidence": node.confidence,
            "importance": node.importance,
        }
        for node in nodes
    ]


def get_graph_summary() -> str:
    """
    Get a summary of the current knowledge graph state.

    Returns:
        Summary string
    """
    # This is a synchronous wrapper for async operations
    import asyncio

    graph = get_graph()

    # Get count
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

    count = loop.run_until_complete(graph.count_nodes())

    return f"Knowledge graph contains {count} active nodes"
