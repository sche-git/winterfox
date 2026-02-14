"""
Main research orchestrator coordinating agent cycles.

The Orchestrator is the high-level coordinator that:
- Manages the knowledge graph evolution across cycles
- Coordinates agent pool for multi-agent research
- Tracks research progress and statistics
- Provides APIs for running single or multiple cycles
"""

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..agents.pool import AgentPool
    from ..agents.protocol import ToolDefinition
    from ..graph.store import KnowledgeGraph
    from .cycle import CycleResult

logger = logging.getLogger(__name__)


class Orchestrator:
    """
    Main research orchestrator that coordinates iterative knowledge building.

    Manages:
    - Knowledge graph evolution across cycles
    - Agent pool coordination
    - Tool availability and context
    - Research cycle execution
    - Progress tracking and statistics
    """

    def __init__(
        self,
        graph: "KnowledgeGraph",
        agent_pool: "AgentPool",
        north_star: str,
        tools: list["ToolDefinition"],
        max_searches_per_cycle: int = 25,
        confidence_discount: float = 0.7,
        consensus_boost: float = 0.15,
        search_instructions: str | None = None,
        context_files: list[dict[str, str]] | None = None,
    ):
        """
        Initialize orchestrator.

        Args:
            graph: Knowledge graph
            agent_pool: Agent pool for research
            north_star: Project mission/north star statement
            tools: Available tools for agents
            max_searches_per_cycle: Max web searches per agent per cycle
            confidence_discount: Discount for initial finding confidence (0.7)
            consensus_boost: Boost when agents agree (0.15)
            search_instructions: Optional custom search guidance
            context_files: Optional prior research documents
        """
        self.graph = graph
        self.agent_pool = agent_pool
        self.north_star = north_star
        self.tools = tools
        self.max_searches_per_cycle = max_searches_per_cycle
        self.confidence_discount = confidence_discount
        self.consensus_boost = consensus_boost
        self.search_instructions = search_instructions
        self.context_files = context_files or []

        self.cycle_count = 0
        self.total_cost_usd = 0.0
        self.cycle_history: list["CycleResult"] = []

    async def run_cycle(
        self,
        target_node_id: str | None = None,
        use_consensus: bool = True,
    ) -> "CycleResult":
        """
        Run a single research cycle.

        Args:
            target_node_id: Specific node to research (or None for auto-select)
            use_consensus: Use multi-agent consensus (if pool has >1 agent)

        Returns:
            CycleResult with stats and outputs
        """
        from .cycle import ResearchCycle

        self.cycle_count += 1

        logger.info(f"=== Starting Cycle {self.cycle_count} ===")

        # Create cycle executor
        cycle = ResearchCycle(
            graph=self.graph,
            agent_pool=self.agent_pool,
            tools=self.tools,
            north_star=self.north_star,
            cycle_id=self.cycle_count,
            search_instructions=self.search_instructions,
            context_files=self.context_files,
        )

        # Execute cycle
        result = await cycle.execute(
            target_node_id=target_node_id,
            max_searches=self.max_searches_per_cycle,
            use_consensus=use_consensus,
        )

        # Update statistics
        self.total_cost_usd += result.total_cost_usd
        self.cycle_history.append(result)

        logger.info(
            f"=== Cycle {self.cycle_count} Complete === "
            f"Cost: ${result.total_cost_usd:.4f} | "
            f"Total: ${self.total_cost_usd:.4f}"
        )

        return result

    async def run_cycles(
        self,
        n: int,
        use_consensus: bool = True,
        stop_on_error: bool = False,
    ) -> list["CycleResult"]:
        """
        Run multiple research cycles.

        Args:
            n: Number of cycles to run
            use_consensus: Use multi-agent consensus
            stop_on_error: Stop if a cycle fails (vs. continue)

        Returns:
            List of CycleResults
        """
        results = []

        for i in range(n):
            logger.info(f"Running cycle {i + 1}/{n}")

            result = await self.run_cycle(use_consensus=use_consensus)
            results.append(result)

            if not result.success and stop_on_error:
                logger.error(f"Cycle {result.cycle_id} failed, stopping")
                break

        return results

    async def run_until_complete(
        self,
        min_confidence: float = 0.8,
        max_cycles: int = 50,
        use_consensus: bool = True,
    ) -> list["CycleResult"]:
        """
        Run cycles until graph reaches target confidence.

        Args:
            min_confidence: Minimum average confidence to reach
            max_cycles: Maximum cycles to run
            use_consensus: Use multi-agent consensus

        Returns:
            List of CycleResults
        """
        results = []

        for i in range(max_cycles):
            # Check if we've reached target confidence
            stats = await self._get_graph_stats()
            avg_confidence = stats["avg_confidence"]

            logger.info(
                f"Cycle {i + 1}/{max_cycles} | "
                f"Avg confidence: {avg_confidence:.2f} / {min_confidence:.2f}"
            )

            if avg_confidence >= min_confidence:
                logger.info(
                    f"Target confidence {min_confidence:.2f} reached "
                    f"after {i} cycles"
                )
                break

            result = await self.run_cycle(use_consensus=use_consensus)
            results.append(result)

            if not result.success:
                logger.warning(f"Cycle {result.cycle_id} failed, continuing")

        return results

    async def _get_graph_stats(self) -> dict:
        """Get current graph statistics."""
        nodes = await self.graph.get_all_active_nodes()

        if not nodes:
            return {
                "total_nodes": 0,
                "avg_confidence": 0.0,
                "avg_importance": 0.0,
                "low_confidence_count": 0,
            }

        total = len(nodes)
        avg_confidence = sum(n.confidence for n in nodes) / total
        avg_importance = sum(n.importance for n in nodes) / total
        low_confidence_count = sum(1 for n in nodes if n.confidence < 0.5)

        return {
            "total_nodes": total,
            "avg_confidence": avg_confidence,
            "avg_importance": avg_importance,
            "low_confidence_count": low_confidence_count,
        }

    def get_summary(self) -> str:
        """
        Get human-readable orchestrator summary.

        Returns:
            Formatted summary string
        """
        successful_cycles = sum(1 for c in self.cycle_history if c.success)
        failed_cycles = sum(1 for c in self.cycle_history if not c.success)
        total_findings = sum(
            c.findings_created + c.findings_updated for c in self.cycle_history
        )

        return f"""Research Orchestrator Summary
================================
Total Cycles: {self.cycle_count} ({successful_cycles} successful, {failed_cycles} failed)
Total Findings: {total_findings} (created + updated)
Total Cost: ${self.total_cost_usd:.4f}
Agents: {len(self.agent_pool.adapters)}
North Star: {self.north_star[:100]}...
"""

    async def reset(self):
        """Reset orchestrator state (does not clear graph)."""
        self.cycle_count = 0
        self.total_cost_usd = 0.0
        self.cycle_history = []
        logger.info("Orchestrator state reset")
