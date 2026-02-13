"""
Research cycle execution logic.

A research cycle:
1. Selects a target node to research
2. Generates research prompts
3. Dispatches agents (with consensus if multi-agent)
4. Merges findings into graph
5. Propagates confidence changes
6. Deduplicates subtree
"""

import logging
import time
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..agents.pool import AgentPool, SynthesisResult
    from ..agents.protocol import AgentOutput, ToolDefinition
    from ..graph.models import KnowledgeNode
    from ..graph.store import KnowledgeGraph

logger = logging.getLogger(__name__)


@dataclass
class CycleResult:
    """Result of a single research cycle."""

    cycle_id: int
    target_node_id: str
    target_claim: str
    findings_created: int
    findings_updated: int
    consensus_findings: int
    divergent_findings: int
    total_cost_usd: float
    duration_seconds: float
    agent_outputs: list["AgentOutput"]
    success: bool
    error_message: str | None = None


class ResearchCycle:
    """Executes a single research cycle."""

    def __init__(
        self,
        graph: "KnowledgeGraph",
        agent_pool: "AgentPool",
        tools: list["ToolDefinition"],
        north_star: str,
        cycle_id: int,
    ):
        """
        Initialize research cycle.

        Args:
            graph: Knowledge graph
            agent_pool: Agent pool for research
            tools: Available tools for agents
            north_star: Project mission/north star
            cycle_id: Current cycle number
        """
        self.graph = graph
        self.agent_pool = agent_pool
        self.tools = tools
        self.north_star = north_star
        self.cycle_id = cycle_id
        self.last_selected_id: str | None = None

    async def execute(
        self,
        target_node_id: str | None = None,
        max_searches: int = 25,
        use_consensus: bool = True,
    ) -> CycleResult:
        """
        Execute a single research cycle.

        Args:
            target_node_id: Specific node to research (or None for auto-select)
            max_searches: Maximum web searches per agent
            use_consensus: Use multi-agent consensus (if pool has >1 agent)

        Returns:
            CycleResult with stats and outputs
        """
        from .selection import select_target_node
        from .prompts import generate_research_prompt
        from .merge import merge_findings_into_graph, merge_and_deduplicate_subtree

        start_time = time.time()

        try:
            # Step 1: Select target node
            if target_node_id:
                target = await self.graph.get_node(target_node_id)
                if not target:
                    raise ValueError(f"Target node {target_node_id} not found")
            else:
                target = await select_target_node(self.graph, self.last_selected_id)
                if not target:
                    raise ValueError("No nodes available for research")

            self.last_selected_id = target.id

            logger.info(
                f"[Cycle {self.cycle_id}] Target: {target.claim[:60]}... "
                f"(conf={target.confidence:.2f}, depth={target.depth})"
            )

            # Step 2: Generate prompts
            system_prompt, user_prompt = await generate_research_prompt(
                self.graph,
                target,
                self.north_star,
                max_searches,
            )

            # Step 3: Dispatch agents
            if use_consensus and len(self.agent_pool.adapters) > 1:
                # Multi-agent with LLM synthesis
                logger.info(
                    f"Dispatching {len(self.agent_pool.adapters)} agents with LLM synthesis"
                )

                result: "SynthesisResult" = await self.agent_pool.dispatch_with_synthesis(
                    system_prompt,
                    user_prompt,
                    self.tools,
                    max_iterations=30,
                )

                findings = result.findings
                agent_outputs = result.individual_outputs
                total_cost = result.total_cost_usd
                consensus_count = len(result.consensus_findings)
                divergent_count = len(findings) - consensus_count

            else:
                # Single agent or parallel without consensus
                logger.info("Dispatching single agent (no consensus)")

                outputs = await self.agent_pool.dispatch(
                    system_prompt,
                    user_prompt,
                    self.tools,
                    max_iterations=30,
                )

                # Combine findings from all agents
                findings = []
                for output in outputs:
                    findings.extend(output.findings)

                agent_outputs = outputs
                total_cost = sum(o.cost_usd for o in outputs)
                consensus_count = 0
                divergent_count = len(findings)

            logger.info(
                f"[Cycle {self.cycle_id}] Agents complete: {len(findings)} findings, "
                f"${total_cost:.4f} cost"
            )

            # Step 4: Merge findings into graph
            merge_stats = await merge_findings_into_graph(
                self.graph,
                findings,
                target.id,
                self.cycle_id,
                similarity_threshold=0.75,
                confidence_discount=0.7,
            )

            # Step 5: Deduplicate subtree (consolidate redundant findings)
            await merge_and_deduplicate_subtree(
                self.graph,
                target.id,
                self.cycle_id,
                similarity_threshold=0.85,
            )

            # Calculate duration
            duration = time.time() - start_time

            # Build result
            result = CycleResult(
                cycle_id=self.cycle_id,
                target_node_id=target.id,
                target_claim=target.claim,
                findings_created=merge_stats["created"],
                findings_updated=merge_stats["updated"],
                consensus_findings=consensus_count,
                divergent_findings=divergent_count,
                total_cost_usd=total_cost,
                duration_seconds=duration,
                agent_outputs=agent_outputs,
                success=True,
            )

            logger.info(
                f"[Cycle {self.cycle_id}] Complete in {duration:.1f}s: "
                f"{merge_stats['created']} created, {merge_stats['updated']} updated"
            )

            return result

        except Exception as e:
            logger.error(f"[Cycle {self.cycle_id}] Failed: {e}", exc_info=True)

            duration = time.time() - start_time

            return CycleResult(
                cycle_id=self.cycle_id,
                target_node_id=target.id if 'target' in locals() else "unknown",
                target_claim=target.claim if 'target' in locals() else "unknown",
                findings_created=0,
                findings_updated=0,
                consensus_findings=0,
                divergent_findings=0,
                total_cost_usd=0.0,
                duration_seconds=duration,
                agent_outputs=[],
                success=False,
                error_message=str(e),
            )
