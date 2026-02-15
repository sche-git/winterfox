"""
Main research orchestrator coordinating agent cycles with Lead LLM architecture.

The Orchestrator is the high-level coordinator that:
- Manages the knowledge graph evolution across cycles
- Coordinates Lead LLM and research agents
- Tracks research progress and statistics
- Provides APIs for running single or multiple cycles
"""

from __future__ import annotations

import logging
import asyncio
from collections.abc import Awaitable, Callable
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from ..agents.protocol import AgentAdapter, ToolDefinition
    from ..graph.store import KnowledgeGraph
    from .cycle import CycleResult
    from .lead import LeadLLM

logger = logging.getLogger(__name__)


class ParallelTargetShortageError(ValueError):
    """Raised when requested parallel targets exceed eligible nodes."""


class Orchestrator:
    """
    Main research orchestrator with Lead LLM architecture.

    Manages:
    - Knowledge graph evolution across cycles
    - Lead LLM and research agent coordination
    - Tool availability and context
    - Research cycle execution
    - Progress tracking and statistics
    """

    def __init__(
        self,
        graph: KnowledgeGraph,
        lead_llm: LeadLLM,
        research_agents: list[AgentAdapter],
        north_star: str,
        tools: list[ToolDefinition],
        max_searches_per_cycle: int = 25,
        report_interval: int = 10,
        search_instructions: str | None = None,
        context_files: list[dict[str, str]] | None = None,
        raw_output_dir: Path | None = None,
        event_callback: Callable[[dict[str, Any]], Awaitable[None]] | None = None,
    ):
        """
        Initialize orchestrator.

        Args:
            graph: Knowledge graph
            lead_llm: Lead LLM for orchestration (selection + synthesis)
            research_agents: Research agents for parallel investigation
            north_star: Project mission/north star statement
            tools: Available tools for agents
            max_searches_per_cycle: Max web searches per agent per cycle
            report_interval: Regenerate report every N cycles (default: 10)
            search_instructions: Optional custom search guidance
            context_files: Optional prior research documents
            raw_output_dir: Directory for markdown cycle exports
            event_callback: Optional callback for cycle lifecycle events
        """
        self.graph = graph
        self.lead_llm = lead_llm
        self.research_agents = research_agents
        self.north_star = north_star
        self.tools = tools
        self.max_searches_per_cycle = max_searches_per_cycle
        self.report_interval = report_interval
        self.search_instructions = search_instructions
        self.context_files = context_files or []
        self.raw_output_dir = raw_output_dir
        self.event_callback = event_callback

        self.cycle_count = 0  # Initialized from DB in _init_cycle_count()
        self.total_cost_usd = 0.0
        self.cycle_history: list[CycleResult] = []
        self._cycle_count_initialized = False

    async def _init_cycle_count(self) -> None:
        """Initialize cycle_count from database to continue numbering across runs."""
        if not self._cycle_count_initialized:
            self.cycle_count = await self.graph.get_max_cycle_id()
            self._cycle_count_initialized = True

    async def _allocate_cycle_ids(self, count: int) -> list[int]:
        """Allocate monotonically increasing cycle IDs."""
        await self._init_cycle_count()
        start = self.cycle_count + 1
        self.cycle_count += count
        return list(range(start, start + count))

    async def _select_distinct_targets(
        self,
        count: int,
        cycle_instruction: str | None = None,
    ) -> list[str]:
        """Select distinct target node IDs via Lead LLM with exclusions."""
        selected_ids: list[str] = []
        excluded: set[str] = set()

        for _ in range(count):
            target, _reasoning = await self.lead_llm.select_direction(
                cycle_instruction=cycle_instruction,
                excluded_node_ids=excluded,
            )
            selected_ids.append(target.id)
            excluded.add(target.id)

        return selected_ids

    async def run_cycle(
        self,
        target_node_id: str | None = None,
        cycle_instruction: str | None = None,
    ) -> CycleResult:
        """
        Run a single research cycle with Lead LLM architecture.

        Args:
            target_node_id: Specific node to research (or None for Lead LLM selection)
            cycle_instruction: Optional one-off instruction to bias this cycle

        Returns:
            CycleResult with stats and outputs
        """
        from .cycle import ResearchCycle

        await self._init_cycle_count()
        self.cycle_count += 1

        logger.info(f"=== Starting Cycle {self.cycle_count} ===")

        # Create cycle executor
        cycle = ResearchCycle(
            graph=self.graph,
            lead_llm=self.lead_llm,
            research_agents=self.research_agents,
            tools=self.tools,
            north_star=self.north_star,
            cycle_id=self.cycle_count,
            report_interval=self.report_interval,
            search_instructions=self.search_instructions,
            context_files=self.context_files,
            event_callback=self.event_callback,
            raw_output_dir=self.raw_output_dir,
        )

        # Execute cycle
        result = await cycle.execute(
            target_node_id=target_node_id,
            max_searches=self.max_searches_per_cycle,
            cycle_instruction=cycle_instruction,
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
        stop_on_error: bool = False,
    ) -> list[CycleResult]:
        """
        Run multiple research cycles.

        Args:
            n: Number of cycles to run
            stop_on_error: Stop if a cycle fails (vs. continue)

        Returns:
            List of CycleResults
        """
        results = []

        for i in range(n):
            logger.info(f"Running cycle {i + 1}/{n}")

            result = await self.run_cycle()
            results.append(result)

            if not result.success and stop_on_error:
                logger.error(f"Cycle {result.cycle_id} failed, stopping")
                break

        return results

    async def run_parallel_round(
        self,
        parallel_targets: int,
        cycle_instruction: str | None = None,
        shortage_policy: str = "fail",
    ) -> list[CycleResult]:
        """
        Run one parallel round across distinct target nodes.

        Args:
            parallel_targets: Number of distinct nodes to process in parallel
            cycle_instruction: Optional one-off instruction for this round
            shortage_policy: Behavior if eligible nodes < requested
                - "fail": raise ParallelTargetShortageError
                - "shrink": reduce to available node count
                - "single_fallback": run one node if any are available

        Returns:
            List of CycleResults, one per selected target
        """
        from .cycle import ResearchCycle

        if parallel_targets <= 0:
            raise ValueError("parallel_targets must be >= 1")
        if shortage_policy not in {"fail", "shrink", "single_fallback"}:
            raise ValueError(f"Unknown shortage_policy: {shortage_policy}")

        all_nodes = await self.graph.get_all_active_nodes()
        eligible_count = len(all_nodes)
        if eligible_count == 0:
            raise ValueError("No active nodes in graph - cannot run parallel round")

        target_count = parallel_targets
        if eligible_count < parallel_targets:
            if shortage_policy == "fail":
                raise ParallelTargetShortageError(
                    f"Requested parallel_targets={parallel_targets}, "
                    f"but only {eligible_count} eligible node(s) available."
                )
            if shortage_policy == "shrink":
                target_count = eligible_count
            else:
                target_count = 1

        target_node_ids = await self._select_distinct_targets(
            count=target_count,
            cycle_instruction=cycle_instruction,
        )
        cycle_ids = await self._allocate_cycle_ids(target_count)

        cycles = [
            ResearchCycle(
                graph=self.graph,
                lead_llm=self.lead_llm,
                research_agents=self.research_agents,
                tools=self.tools,
                north_star=self.north_star,
                cycle_id=cycle_id,
                report_interval=self.report_interval,
                search_instructions=self.search_instructions,
                context_files=self.context_files,
                event_callback=self.event_callback,
                raw_output_dir=self.raw_output_dir,
            )
            for cycle_id in cycle_ids
        ]

        tasks = [
            cycle.execute(
                target_node_id=target_node_id,
                max_searches=self.max_searches_per_cycle,
                cycle_instruction=cycle_instruction,
            )
            for cycle, target_node_id in zip(cycles, target_node_ids, strict=False)
        ]
        results = await asyncio.gather(*tasks)
        results = sorted(results, key=lambda r: r.cycle_id)

        for result in results:
            self.total_cost_usd += result.total_cost_usd
            self.cycle_history.append(result)

        logger.info(
            "Parallel round complete: %s cycle(s), +$%.4f",
            len(results),
            sum(r.total_cost_usd for r in results),
        )

        return results

    async def run_until_complete(
        self,
        min_confidence: float = 0.8,
        max_cycles: int = 50,
    ) -> list[CycleResult]:
        """
        Run cycles until graph reaches target confidence.

        Args:
            min_confidence: Minimum average confidence to reach
            max_cycles: Maximum cycles to run

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

            result = await self.run_cycle()
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
        total_directions = sum(
            c.directions_created + c.directions_updated for c in self.cycle_history
        )

        return f"""Research Orchestrator Summary (Lead LLM Architecture)
================================================================
Total Cycles: {self.cycle_count} ({successful_cycles} successful, {failed_cycles} failed)
Total Directions: {total_directions} (created + updated)
Total Cost: ${self.total_cost_usd:.4f}
Lead LLM: {self.lead_llm.adapter.name}
Research Agents: {len(self.research_agents)}
North Star: {self.north_star[:100]}...
"""

    async def reset(self):
        """Reset orchestrator state (does not clear graph)."""
        self.cycle_count = 0
        self.total_cost_usd = 0.0
        self.cycle_history = []
        logger.info("Orchestrator state reset")
