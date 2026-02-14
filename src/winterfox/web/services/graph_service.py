"""
Graph service - Business logic for knowledge graph operations.
"""

import logging
from datetime import datetime
from pathlib import Path

from ...graph.models import KnowledgeNode
from ...graph.store import KnowledgeGraph
from ..models.api_models import (
    EvidenceItem,
    GraphSummaryResponse,
    GraphTreeResponse,
    NodeResponse,
    NodesListResponse,
    NodeTreeItem,
    SearchResponse,
    SearchResultItem,
)

logger = logging.getLogger(__name__)


class GraphService:
    """
    Service layer for knowledge graph operations.

    Wraps KnowledgeGraph with:
    - Type conversions (KnowledgeNode → NodeResponse)
    - Query helpers (pagination, filtering)
    - Business logic (tree building, search)
    """

    def __init__(self, db_path: str, workspace_id: str = "default"):
        """
        Initialize graph service.

        Args:
            db_path: Path to SQLite database
            workspace_id: Workspace identifier for multi-tenancy
        """
        self.db_path = db_path
        self.workspace_id = workspace_id
        self._graph: KnowledgeGraph | None = None

    async def _get_graph(self) -> KnowledgeGraph:
        """Get or create graph instance."""
        if self._graph is None:
            self._graph = KnowledgeGraph(self.db_path, workspace_id=self.workspace_id)
            await self._graph.initialize()
        return self._graph

    async def close(self) -> None:
        """Close graph connection."""
        if self._graph:
            await self._graph.close()
            self._graph = None

    def _node_to_response(self, node: KnowledgeNode) -> NodeResponse:
        """Convert KnowledgeNode to NodeResponse."""
        return NodeResponse(
            id=node.id,
            claim=node.claim,
            confidence=node.confidence,
            importance=node.importance,
            depth=node.depth,
            parent_id=node.parent_id,
            children_ids=node.children,
            evidence=[
                EvidenceItem(
                    text=e.text,
                    source=e.source,
                    date=e.timestamp,
                    verified_by=e.verified_by if hasattr(e, "verified_by") else [],
                )
                for e in node.evidence
            ],
            status=node.status,
            created_at=node.created_at,
            updated_at=node.updated_at,
        )

    async def get_summary(self) -> GraphSummaryResponse:
        """
        Get graph summary statistics.

        Returns:
            GraphSummaryResponse with totals and averages
        """
        # Check if database exists
        if not Path(self.db_path).exists():
            logger.info(f"Database not found: {self.db_path}")
            return GraphSummaryResponse(
                total_nodes=0,
                avg_confidence=0.0,
                avg_importance=0.0,
                root_nodes=0,
                low_confidence_count=0,
                last_cycle_at=None,
                workspace_id=self.workspace_id,
            )

        graph = await self._get_graph()

        # Get all nodes
        nodes = await graph.get_all_active_nodes()

        if not nodes:
            return GraphSummaryResponse(
                total_nodes=0,
                avg_confidence=0.0,
                avg_importance=0.0,
                root_nodes=0,
                low_confidence_count=0,
                last_cycle_at=None,
                workspace_id=self.workspace_id,
            )

        # Calculate statistics
        total_nodes = len(nodes)
        avg_confidence = sum(n.confidence for n in nodes) / total_nodes
        avg_importance = sum(n.importance for n in nodes) / total_nodes
        root_nodes = len([n for n in nodes if n.parent_id is None])
        low_confidence_count = len([n for n in nodes if n.confidence < 0.5])

        # Get last cycle time (from most recent node update)
        last_cycle_at = max(n.updated_at for n in nodes)

        return GraphSummaryResponse(
            total_nodes=total_nodes,
            avg_confidence=avg_confidence,
            avg_importance=avg_importance,
            root_nodes=root_nodes,
            low_confidence_count=low_confidence_count,
            last_cycle_at=last_cycle_at,
            workspace_id=self.workspace_id,
        )

    async def get_nodes(
        self,
        limit: int = 100,
        offset: int = 0,
        status: str = "active",
        min_confidence: float | None = None,
        max_depth: int | None = None,
        sort: str = "confidence",
    ) -> NodesListResponse:
        """
        Get paginated list of nodes with filtering and sorting.

        Args:
            limit: Max nodes to return
            offset: Offset for pagination
            status: Node status filter
            min_confidence: Minimum confidence threshold
            max_depth: Maximum depth filter
            sort: Sort field (confidence, importance, created_at, updated_at)

        Returns:
            NodesListResponse with filtered nodes
        """
        # Check if database exists
        if not Path(self.db_path).exists():
            return NodesListResponse(nodes=[], total=0, limit=limit, offset=offset)

        graph = await self._get_graph()

        # Get all nodes (could be optimized with DB query)
        all_nodes = await graph.get_all_active_nodes()

        # Apply filters
        filtered_nodes = all_nodes

        if min_confidence is not None:
            filtered_nodes = [n for n in filtered_nodes if n.confidence >= min_confidence]

        if max_depth is not None:
            filtered_nodes = [n for n in filtered_nodes if n.depth <= max_depth]

        # Sort
        sort_key_map = {
            "confidence": lambda n: n.confidence,
            "importance": lambda n: n.importance,
            "created_at": lambda n: n.created_at,
            "updated_at": lambda n: n.updated_at,
        }
        if sort in sort_key_map:
            filtered_nodes.sort(key=sort_key_map[sort], reverse=True)

        # Paginate
        total = len(filtered_nodes)
        paginated_nodes = filtered_nodes[offset : offset + limit]

        return NodesListResponse(
            nodes=[self._node_to_response(n) for n in paginated_nodes],
            total=total,
            limit=limit,
            offset=offset,
        )

    async def get_node(self, node_id: str) -> NodeResponse | None:
        """
        Get single node by ID.

        Args:
            node_id: Node identifier

        Returns:
            NodeResponse or None if not found
        """
        graph = await self._get_graph()
        node = await graph.get_node(node_id)

        if node is None:
            return None

        return self._node_to_response(node)

    async def get_tree(self, max_depth: int = 3) -> GraphTreeResponse:
        """
        Get hierarchical tree structure.

        Args:
            max_depth: Maximum tree depth

        Returns:
            GraphTreeResponse with nested nodes
        """
        graph = await self._get_graph()

        # Get root nodes
        root_nodes = await graph.get_root_nodes()

        # Build tree recursively
        async def build_tree(node: KnowledgeNode, current_depth: int) -> NodeTreeItem:
            children = []

            if current_depth < max_depth:
                child_nodes = await graph.get_children(node.id)
                for child in child_nodes:
                    children.append(await build_tree(child, current_depth + 1))

            return NodeTreeItem(
                id=node.id,
                claim=node.claim,
                confidence=node.confidence,
                importance=node.importance,
                children=children,
            )

        roots = []
        for root in root_nodes:
            roots.append(await build_tree(root, 0))

        return GraphTreeResponse(roots=roots)

    async def search(self, query: str, limit: int = 10) -> SearchResponse:
        """
        Search nodes by claim text.

        Args:
            query: Search query
            limit: Max results to return

        Returns:
            SearchResponse with matching nodes
        """
        graph = await self._get_graph()

        # Use FTS if available, otherwise fallback to simple search
        try:
            results = await graph.search(query, limit=limit)
        except Exception as e:
            logger.warning(f"Search failed: {e}")
            results = []

        # Convert to search results
        search_results = []
        for node in results:
            # Extract snippet (first 150 chars of claim)
            snippet = node.claim[:150]
            if len(node.claim) > 150:
                snippet += "..."

            search_results.append(
                SearchResultItem(
                    node_id=node.id,
                    claim=node.claim,
                    snippet=snippet,
                    relevance_score=0.8,  # TODO: Implement proper relevance scoring
                )
            )

        return SearchResponse(results=search_results)
