"""
Graph service - Business logic for knowledge graph operations.
"""

import json
import logging
from datetime import datetime, timedelta
from pathlib import Path

from ...graph.models import KnowledgeNode
from ...graph.store import KnowledgeGraph
from ..models.api_models import (
    AgentFinding,
    AgentOutputSummary,
    AgentSearchRecord,
    ContradictionItem,
    CycleDetailResponse,
    DirectionNodeRef,
    CycleResponse,
    CyclesListResponse,
    EvidenceItem,
    FindingEvidence,
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

    async def get_context_documents(self) -> list[dict[str, str]]:
        """Get persisted project context documents for this workspace."""
        graph = await self._get_graph()
        return await graph.get_context_documents()

    def _node_to_response(self, node: KnowledgeNode) -> NodeResponse:
        """Convert KnowledgeNode to NodeResponse."""
        api_status = self._map_status(node.status)

        return NodeResponse(
            id=node.id,
            claim=node.claim,
            description=node.description,
            confidence=node.confidence,
            importance=node.importance,
            depth=node.depth,
            parent_id=node.parent_id,
            children_ids=node.children_ids,
            evidence=[
                EvidenceItem(
                    text=e.text,
                    source=e.source,
                    date=e.date,
                    verified_by=e.verified_by,
                )
                for e in node.evidence
            ],
            status=api_status,
            node_type=node.node_type,
            created_by_cycle=node.created_by_cycle,
            updated_by_cycle=node.updated_by_cycle,
            created_at=node.created_at,
            updated_at=node.updated_at,
        )

    @staticmethod
    def _map_status(status: str) -> str:
        """Map internal statuses to API-compatible status values."""
        status_map = {
            "killed": "archived",
            "closed": "archived",
            "completed": "archived",
            "speculative": "active",
        }
        return status_map.get(status, status)

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

        # Include completed/closed branches so the UI can show the full storyline tree.
        root_nodes = await graph.get_root_nodes(include_inactive=True)

        # Build tree recursively
        async def build_tree(node: KnowledgeNode, current_depth: int) -> NodeTreeItem:
            children = []

            if current_depth < max_depth:
                child_nodes = await graph.get_children(node.id, include_inactive=True)
                for child in child_nodes:
                    children.append(await build_tree(child, current_depth + 1))

            return NodeTreeItem(
                id=node.id,
                claim=node.claim,
                description=node.description,
                status=self._map_status(node.status),
                confidence=node.confidence,
                importance=node.importance,
                node_type=node.node_type,
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

    # --- Cycle Operations ---

    async def get_cycles(
        self,
        limit: int = 20,
        offset: int = 0,
    ) -> CyclesListResponse:
        """
        Get paginated list of research cycles.

        Args:
            limit: Max cycles to return
            offset: Offset for pagination

        Returns:
            CyclesListResponse with cycles and total count
        """
        if not Path(self.db_path).exists():
            return CyclesListResponse(cycles=[], total=0)

        graph = await self._get_graph()

        # Get cycle outputs from database
        rows = await graph.list_cycle_outputs(
            workspace_id=self.workspace_id,
            limit=limit,
            offset=offset,
        )

        # Get total count
        total = await self._count_cycle_outputs(graph)

        # Map database rows to CycleResponse models
        cycles = []
        for row in rows:
            started_at = datetime.fromisoformat(row["created_at"]) if isinstance(row["created_at"], str) else row["created_at"]
            completed_at = None
            if row["duration_seconds"] and row["duration_seconds"] > 0:
                completed_at = started_at + timedelta(seconds=row["duration_seconds"])

            status: str = "completed" if row["success"] else "failed"
            findings_count = row.get("findings_created", 0) + row.get("findings_updated", 0)
            lead_llm_cost = row.get("lead_llm_cost_usd", 0.0)
            research_agents_cost = row.get("research_agents_cost_usd", 0.0)

            cycles.append(
                CycleResponse(
                    id=row["cycle_id"],
                    started_at=started_at,
                    completed_at=completed_at,
                    status=status,
                    focus_node_id=row.get("target_node_id"),
                    target_claim=row.get("target_claim", ""),
                    total_cost_usd=row.get("total_cost_usd", 0.0),
                    lead_llm_cost_usd=lead_llm_cost,
                    research_agents_cost_usd=research_agents_cost,
                    findings_count=findings_count,
                    directions_count=findings_count,
                    agents_used=[],
                    duration_seconds=row.get("duration_seconds"),
                )
            )

        return CyclesListResponse(cycles=cycles, total=total)

    async def get_cycle_detail(self, cycle_id: int) -> CycleDetailResponse | None:
        """
        Get detailed information for a single cycle.

        Args:
            cycle_id: Cycle identifier

        Returns:
            CycleDetailResponse or None if not found
        """
        graph = await self._get_graph()
        data = await graph.get_cycle_output(cycle_id)

        if data is None:
            return None

        agent_outputs = []
        for agent in data.get("agent_outputs", []):
            raw_findings = json.loads(agent["findings"]) if isinstance(agent["findings"], str) else agent["findings"]
            raw_searches = json.loads(agent["searches_performed"]) if isinstance(agent["searches_performed"], str) else agent["searches_performed"]

            findings = []
            for f in raw_findings:
                evidence = []
                for e in f.get("evidence", []):
                    if isinstance(e, dict):
                        evidence.append(FindingEvidence(
                            text=e.get("text", ""),
                            source=e.get("source", ""),
                            date=e.get("date"),
                        ))
                findings.append(AgentFinding(
                    claim=f.get("claim", ""),
                    confidence=f.get("confidence", 0.5),
                    evidence=evidence,
                    tags=f.get("tags", []),
                    finding_type=f.get("finding_type"),
                ))

            searches = []
            for s in raw_searches:
                if isinstance(s, dict):
                    searches.append(AgentSearchRecord(
                        query=s.get("query", ""),
                        engine=s.get("engine", ""),
                        results_count=s.get("results_count", 0),
                    ))

            agent_outputs.append(
                AgentOutputSummary(
                    agent_name=agent["agent_name"],
                    model=agent.get("agent_model", ""),
                    role=agent.get("role", "secondary"),
                    cost_usd=agent.get("cost_usd", 0.0),
                    total_tokens=agent.get("total_tokens", 0),
                    input_tokens=agent.get("input_tokens", 0),
                    output_tokens=agent.get("output_tokens", 0),
                    duration_seconds=agent.get("duration_seconds", 0.0),
                    searches_performed=len(raw_searches),
                    findings_count=len(raw_findings),
                    self_critique=agent.get("self_critique", ""),
                    raw_text=agent.get("raw_text", ""),
                    findings=findings,
                    searches=searches,
                )
            )

        # Parse consensus findings
        raw_consensus = data.get("consensus_findings", [])
        if isinstance(raw_consensus, str):
            try:
                raw_consensus = json.loads(raw_consensus)
            except (json.JSONDecodeError, TypeError):
                raw_consensus = []
        consensus_list = [str(c) for c in raw_consensus] if raw_consensus else []

        # Parse contradictions
        raw_contradictions = data.get("contradictions", [])
        if isinstance(raw_contradictions, str):
            try:
                raw_contradictions = json.loads(raw_contradictions)
            except (json.JSONDecodeError, TypeError):
                raw_contradictions = []
        contradictions = []
        for c in (raw_contradictions or []):
            if isinstance(c, dict):
                contradictions.append(ContradictionItem(
                    claim_a=c.get("claim_a", ""),
                    claim_b=c.get("claim_b", ""),
                    description=c.get("description", str(c)),
                ))
            elif isinstance(c, str):
                contradictions.append(ContradictionItem(description=c))

        direction_node_refs = [
            DirectionNodeRef(
                claim=str(ref.get("claim", "")),
                node_id=str(ref.get("node_id", "")),
                action="created" if str(ref.get("action", "")).lower() == "created" else "updated",
            )
            for ref in (data.get("direction_node_refs", []) or [])
            if isinstance(ref, dict) and ref.get("node_id")
        ]

        # Backfill for legacy cycle rows with no explicit refs:
        # resolve exact-claim matches among target node's current children.
        if not direction_node_refs and consensus_list and data.get("target_node_id"):
            target = await graph.get_node(str(data["target_node_id"]))
            if target:
                children = await graph.get_children(target.id)

                def norm_claim(text: str) -> str:
                    return " ".join(
                        "".join(ch if ch.isalnum() or ch.isspace() else " " for ch in text.lower()).split()
                    )

                child_map = {norm_claim(child.claim): child.id for child in children}
                for claim in consensus_list:
                    node_id = child_map.get(norm_claim(claim))
                    if node_id:
                        direction_node_refs.append(
                            DirectionNodeRef(claim=claim, node_id=node_id, action="updated")
                        )

        return CycleDetailResponse(
            id=data["cycle_id"],
            target_node_id=data.get("target_node_id", ""),
            target_claim=data.get("target_claim", ""),
            research_context=data.get("research_context"),
            findings_created=data.get("findings_created", 0),
            findings_updated=data.get("findings_updated", 0),
            findings_skipped=data.get("findings_skipped", 0),
            directions_created=data.get("findings_created", 0),
            directions_updated=data.get("findings_updated", 0),
            directions_skipped=data.get("findings_skipped", 0),
            consensus_findings=consensus_list,
            consensus_directions=consensus_list,
            contradictions=contradictions,
            direction_node_refs=direction_node_refs,
            synthesis_reasoning=data.get("synthesis_reasoning", "") or "",
            selection_strategy=data.get("selection_strategy"),
            selection_reasoning=data.get("selection_reasoning"),
            total_cost_usd=data.get("total_cost_usd", 0.0),
            lead_llm_cost_usd=data.get("lead_llm_cost_usd", 0.0),
            research_agents_cost_usd=data.get("research_agents_cost_usd", 0.0),
            total_tokens=data.get("total_tokens", 0),
            duration_seconds=data.get("duration_seconds", 0.0),
            agent_count=data.get("agent_count", 0),
            success=bool(data.get("success", True)),
            error_message=data.get("error_message"),
            created_at=data.get("created_at"),
            agent_outputs=agent_outputs,
        )

    async def get_node_type_counts(self) -> dict[str, int]:
        """
        Count nodes by node_type.

        Returns:
            Dict mapping node_type to count (e.g. {"hypothesis": 5, "supporting": 12})
        """
        if not Path(self.db_path).exists():
            return {}

        graph = await self._get_graph()
        nodes = await graph.get_all_active_nodes()

        counts: dict[str, int] = {}
        for node in nodes:
            if node.node_type:
                counts[node.node_type] = counts.get(node.node_type, 0) + 1
        return counts

    async def get_cycle_stats(
        self,
    ) -> tuple[int, int, int, float, float, float, float, dict[str, float]]:
        """
        Get aggregate cycle statistics.

        Returns:
            Tuple of (
                total,
                successful,
                failed,
                avg_duration,
                total_cost,
                total_lead_cost,
                total_research_cost,
                cost_by_agent,
            )
        """
        if not Path(self.db_path).exists():
            return 0, 0, 0, 0.0, 0.0, 0.0, 0.0, {}

        graph = await self._get_graph()

        async with graph._get_db() as db:
            # Aggregate stats from cycle_outputs
            cursor = await db.execute(
                """
                SELECT
                    COUNT(*) as total,
                    SUM(CASE WHEN success = 1 THEN 1 ELSE 0 END) as successful,
                    SUM(CASE WHEN success = 0 THEN 1 ELSE 0 END) as failed,
                    AVG(duration_seconds) as avg_duration,
                    SUM(total_cost_usd) as total_cost,
                    SUM(lead_llm_cost_usd) as total_lead_cost,
                    SUM(research_agents_cost_usd) as total_research_cost
                FROM cycle_outputs
                WHERE workspace_id = ?
                """,
                (self.workspace_id,),
            )
            row = await cursor.fetchone()
            total = row[0] or 0
            successful = row[1] or 0
            failed = row[2] or 0
            avg_duration = row[3] or 0.0
            total_cost = row[4] or 0.0
            total_lead_cost = row[5] or 0.0
            total_research_cost = row[6] or 0.0

            # Cost by agent
            cursor = await db.execute(
                """
                SELECT a.agent_name, SUM(a.cost_usd)
                FROM agent_outputs a
                JOIN cycle_outputs c ON a.cycle_output_id = c.id
                WHERE c.workspace_id = ?
                GROUP BY a.agent_name
                """,
                (self.workspace_id,),
            )
            cost_by_agent = {}
            for agent_row in await cursor.fetchall():
                cost_by_agent[agent_row[0]] = agent_row[1] or 0.0

        return (
            total,
            successful,
            failed,
            avg_duration,
            total_cost,
            total_lead_cost,
            total_research_cost,
            cost_by_agent,
        )

    async def _count_cycle_outputs(self, graph: KnowledgeGraph) -> int:
        """Count total cycle outputs for pagination."""
        async with graph._get_db() as db:
            cursor = await db.execute(
                "SELECT COUNT(*) FROM cycle_outputs WHERE workspace_id = ?",
                (self.workspace_id,),
            )
            row = await cursor.fetchone()
            return row[0] if row else 0
