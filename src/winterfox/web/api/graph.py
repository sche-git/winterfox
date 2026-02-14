"""
Graph REST API endpoints.

Provides:
- GET /api/graph/summary - Graph statistics
- GET /api/graph/nodes - Paginated node list
- GET /api/graph/nodes/{node_id} - Single node details
- GET /api/graph/tree - Hierarchical tree structure
- GET /api/graph/search - Search nodes
"""

import logging
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query

from ..models.api_models import (
    GraphSummaryResponse,
    GraphTreeResponse,
    NodeResponse,
    NodesListResponse,
    SearchResponse,
)
from ..services.graph_service import GraphService

logger = logging.getLogger(__name__)

router = APIRouter(tags=["graph"])


# Dependency injection
_graph_service: GraphService | None = None


def get_graph_service() -> GraphService:
    """
    Get or create GraphService instance.

    This is a dependency that will be injected by FastAPI.
    The service is initialized in server.py with db_path and workspace_id.
    """
    if _graph_service is None:
        raise HTTPException(status_code=500, detail="Graph service not initialized")
    return _graph_service


def init_graph_service(db_path: str, workspace_id: str) -> None:
    """
    Initialize graph service (called by server.py on startup).

    Args:
        db_path: Path to SQLite database
        workspace_id: Workspace identifier
    """
    global _graph_service
    _graph_service = GraphService(db_path, workspace_id)
    logger.info(f"Graph service initialized: {db_path} (workspace: {workspace_id})")


async def shutdown_graph_service() -> None:
    """Shutdown graph service (called by server.py on shutdown)."""
    global _graph_service
    if _graph_service:
        await _graph_service.close()
        _graph_service = None
        logger.info("Graph service closed")


@router.get("/summary", response_model=GraphSummaryResponse)
async def get_graph_summary(
    service: Annotated[GraphService, Depends(get_graph_service)],
) -> GraphSummaryResponse:
    """
    Get graph summary statistics.

    Returns:
        - Total nodes count
        - Average confidence and importance
        - Number of root nodes
        - Low confidence nodes count
        - Last cycle timestamp
    """
    try:
        return await service.get_summary()
    except Exception as e:
        logger.error(f"Failed to get graph summary: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/nodes", response_model=NodesListResponse)
async def get_nodes(
    service: Annotated[GraphService, Depends(get_graph_service)],
    limit: Annotated[int, Query(ge=1, le=500)] = 100,
    offset: Annotated[int, Query(ge=0)] = 0,
    status: Annotated[str, Query()] = "active",
    min_confidence: Annotated[float | None, Query(ge=0.0, le=1.0)] = None,
    max_depth: Annotated[int | None, Query(ge=0)] = None,
    sort: Annotated[str, Query()] = "confidence",
) -> NodesListResponse:
    """
    Get paginated list of nodes with filtering and sorting.

    Query Parameters:
        - limit: Max nodes to return (1-500, default: 100)
        - offset: Offset for pagination (default: 0)
        - status: Node status filter (default: "active")
        - min_confidence: Minimum confidence threshold (0.0-1.0)
        - max_depth: Maximum depth filter
        - sort: Sort field (confidence, importance, created_at, updated_at)

    Returns:
        Paginated list with total count
    """
    try:
        return await service.get_nodes(
            limit=limit,
            offset=offset,
            status=status,
            min_confidence=min_confidence,
            max_depth=max_depth,
            sort=sort,
        )
    except Exception as e:
        logger.error(f"Failed to get nodes: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/nodes/{node_id}", response_model=NodeResponse)
async def get_node(
    node_id: str,
    service: Annotated[GraphService, Depends(get_graph_service)],
) -> NodeResponse:
    """
    Get detailed information for a single node.

    Path Parameters:
        - node_id: Node identifier

    Returns:
        Complete node details including evidence and relationships

    Raises:
        404: Node not found
    """
    try:
        node = await service.get_node(node_id)

        if node is None:
            raise HTTPException(status_code=404, detail=f"Node not found: {node_id}")

        return node
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get node {node_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/tree", response_model=GraphTreeResponse)
async def get_tree(
    service: Annotated[GraphService, Depends(get_graph_service)],
    max_depth: Annotated[int, Query(ge=1, le=10)] = 3,
) -> GraphTreeResponse:
    """
    Get hierarchical tree structure of the knowledge graph.

    Query Parameters:
        - max_depth: Maximum tree depth (1-10, default: 3)

    Returns:
        Nested tree structure starting from root nodes
    """
    try:
        return await service.get_tree(max_depth=max_depth)
    except Exception as e:
        logger.error(f"Failed to get tree: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/search", response_model=SearchResponse)
async def search_nodes(
    service: Annotated[GraphService, Depends(get_graph_service)],
    q: Annotated[str, Query(min_length=1)],
    limit: Annotated[int, Query(ge=1, le=100)] = 10,
) -> SearchResponse:
    """
    Search nodes by claim text.

    Query Parameters:
        - q: Search query (required)
        - limit: Max results to return (1-100, default: 10)

    Returns:
        List of matching nodes with relevance scores
    """
    try:
        return await service.search(query=q, limit=limit)
    except Exception as e:
        logger.error(f"Failed to search nodes: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
