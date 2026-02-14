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
from collections.abc import Callable, Coroutine
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from ..agents.pool import AgentPool, SynthesisResult
    from ..agents.protocol import AgentOutput, ToolDefinition
    from ..graph.models import KnowledgeNode
    from ..graph.store import KnowledgeGraph

logger = logging.getLogger(__name__)

# Type alias for event callback
EventCallback = Callable[[dict[str, Any]], Coroutine[Any, Any, None]]


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
        search_instructions: str | None = None,
        context_files: list[dict[str, str]] | None = None,
        event_callback: EventCallback | None = None,
    ):
        """
        Initialize research cycle.

        Args:
            graph: Knowledge graph
            agent_pool: Agent pool for research
            tools: Available tools for agents
            north_star: Project mission/north star
            cycle_id: Current cycle number
            search_instructions: Optional custom search guidance
            context_files: Optional prior research documents
            event_callback: Optional async callback for real-time events
        """
        self.graph = graph
        self.agent_pool = agent_pool
        self.tools = tools
        self.north_star = north_star
        self.cycle_id = cycle_id
        self.search_instructions = search_instructions
        self.context_files = context_files or []
        self.last_selected_id: str | None = None

        # Event callback for real-time updates
        self.event_callback = event_callback

    async def _emit_event(self, event: dict[str, Any]) -> None:
        """
        Emit event if callback is registered.

        Args:
            event: Event data to emit
        """
        if self.event_callback:
            try:
                await self.event_callback(event)
            except Exception as e:
                logger.warning(f"Event callback failed: {e}")

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
            await self._emit_event({
                "type": "cycle.step",
                "data": {
                    "cycle_id": self.cycle_id,
                    "step": "node_selection",
                    "progress_percent": 10,
                }
            })

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

            # Emit cycle started event
            await self._emit_event({
                "type": "cycle.started",
                "data": {
                    "cycle_id": self.cycle_id,
                    "focus_node_id": target.id,
                    "focus_claim": target.claim,
                }
            })

            # Step 2: Generate prompts
            await self._emit_event({
                "type": "cycle.step",
                "data": {
                    "cycle_id": self.cycle_id,
                    "step": "prompt_generation",
                    "progress_percent": 20,
                }
            })
            system_prompt, user_prompt = await generate_research_prompt(
                self.graph,
                target,
                self.north_star,
                max_searches,
                search_instructions=self.search_instructions,
                context_files=self.context_files,
            )

            # Step 3: Dispatch agents
            await self._emit_event({
                "type": "cycle.step",
                "data": {
                    "cycle_id": self.cycle_id,
                    "step": "agent_dispatch",
                    "progress_percent": 30,
                }
            })

            if use_consensus and len(self.agent_pool.adapters) > 1:
                # Multi-agent with LLM synthesis
                logger.info(
                    f"Dispatching {len(self.agent_pool.adapters)} agents with LLM synthesis"
                )

                # Emit agent started events
                for adapter in self.agent_pool.adapters:
                    await self._emit_event({
                        "type": "agent.started",
                        "data": {
                            "cycle_id": self.cycle_id,
                            "agent_name": adapter.name,
                            "prompt_preview": user_prompt[:200],
                        }
                    })

                result: "SynthesisResult" = await self.agent_pool.dispatch_with_synthesis(
                    system_prompt,
                    user_prompt,
                    self.tools,
                    max_iterations=30,
                )

                # Emit agent completed events
                for output in result.individual_outputs:
                    await self._emit_event({
                        "type": "agent.completed",
                        "data": {
                            "cycle_id": self.cycle_id,
                            "agent_name": output.agent_name,
                            "findings_count": len(output.findings),
                            "cost_usd": output.cost_usd,
                            "duration_seconds": output.duration_seconds,
                        }
                    })

                # Emit synthesis started
                await self._emit_event({
                    "type": "synthesis.started",
                    "data": {
                        "cycle_id": self.cycle_id,
                        "agent_count": len(self.agent_pool.adapters),
                    }
                })

                findings = result.findings
                agent_outputs = result.individual_outputs
                total_cost = result.total_cost_usd
                consensus_count = len(result.consensus_findings)
                divergent_count = len(findings) - consensus_count
                synthesis_result = result  # Store for later use

                # Emit synthesis completed
                await self._emit_event({
                    "type": "synthesis.completed",
                    "data": {
                        "cycle_id": self.cycle_id,
                        "consensus_count": consensus_count,
                        "divergent_count": divergent_count,
                    }
                })

            else:
                # Single agent or parallel without consensus
                logger.info("Dispatching single agent (no consensus)")

                # Emit agent started events
                for adapter in self.agent_pool.adapters:
                    await self._emit_event({
                        "type": "agent.started",
                        "data": {
                            "cycle_id": self.cycle_id,
                            "agent_name": adapter.name,
                            "prompt_preview": user_prompt[:200],
                        }
                    })

                outputs = await self.agent_pool.dispatch(
                    system_prompt,
                    user_prompt,
                    self.tools,
                    max_iterations=30,
                )

                # Emit agent completed events
                for output in outputs:
                    await self._emit_event({
                        "type": "agent.completed",
                        "data": {
                            "cycle_id": self.cycle_id,
                            "agent_name": output.agent_name,
                            "findings_count": len(output.findings),
                            "cost_usd": output.cost_usd,
                            "duration_seconds": output.duration_seconds,
                        }
                    })

                # Combine findings from all agents
                findings = []
                for output in outputs:
                    findings.extend(output.findings)

                agent_outputs = outputs
                total_cost = sum(o.cost_usd for o in outputs)
                consensus_count = 0
                divergent_count = len(findings)
                synthesis_result = None  # No synthesis for single agent

            logger.info(
                f"[Cycle {self.cycle_id}] Agents complete: {len(findings)} findings, "
                f"${total_cost:.4f} cost"
            )

            # Step 4: Merge findings into graph
            await self._emit_event({
                "type": "cycle.step",
                "data": {
                    "cycle_id": self.cycle_id,
                    "step": "merge_findings",
                    "progress_percent": 70,
                }
            })

            merge_stats = await merge_findings_into_graph(
                self.graph,
                findings,
                target.id,
                self.cycle_id,
                similarity_threshold=0.75,
                confidence_discount=0.7,
            )

            # Step 5: Deduplicate subtree (consolidate redundant findings)
            await self._emit_event({
                "type": "cycle.step",
                "data": {
                    "cycle_id": self.cycle_id,
                    "step": "deduplication",
                    "progress_percent": 90,
                }
            })

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

            # Emit cycle completed event
            await self._emit_event({
                "type": "cycle.completed",
                "data": {
                    "cycle_id": self.cycle_id,
                    "findings_created": merge_stats["created"],
                    "findings_updated": merge_stats["updated"],
                    "total_cost_usd": total_cost,
                    "duration_seconds": duration,
                }
            })

            # Save cycle output to database
            await self._save_cycle_output(
                result=result,
                synthesis_result=synthesis_result,
                merge_stats=merge_stats,
                target=target,
            )

            return result

        except Exception as e:
            logger.error(f"[Cycle {self.cycle_id}] Failed: {e}", exc_info=True)

            duration = time.time() - start_time

            # Emit cycle failed event
            await self._emit_event({
                "type": "cycle.failed",
                "data": {
                    "cycle_id": self.cycle_id,
                    "error_message": str(e),
                    "step": "unknown",  # TODO: Track current step
                }
            })

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

    async def _save_cycle_output(
        self,
        result: CycleResult,
        synthesis_result: "SynthesisResult | None",
        merge_stats: dict,
        target: KnowledgeNode,
    ) -> None:
        """
        Save cycle output to database.

        Args:
            result: CycleResult with all outputs
            synthesis_result: SynthesisResult if multi-agent mode
            merge_stats: Merge statistics from graph integration
            target: Target node that was researched
        """
        try:
            # Save to database
            cycle_output_id = await self.graph.save_cycle_output(
                cycle_id=self.cycle_id,
                target_node=target,
                agent_outputs=result.agent_outputs,
                synthesis_result=synthesis_result,
                merge_stats=merge_stats,
                duration_seconds=result.duration_seconds,
                total_cost_usd=result.total_cost_usd,
                success=result.success,
                error_message=result.error_message,
            )

            logger.info(f"Saved cycle {self.cycle_id} output to database (id={cycle_output_id})")

        except Exception as e:
            logger.error(f"Failed to save cycle output: {e}", exc_info=True)
            # Don't fail the cycle if output saving fails
