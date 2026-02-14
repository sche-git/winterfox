"""
Research cycle execution logic for Lead LLM architecture.

A research cycle with Lead LLM:
1. Lead LLM selects direction (or user-specified)
2. Check report regeneration (auto-regenerate every N cycles)
3. Lead LLM dispatches research agents
4. Lead LLM synthesizes directions from raw outputs
5. Merge directions into graph
6. Deduplicate subtree
"""

from __future__ import annotations

import logging
import time
from collections.abc import Callable, Coroutine
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from ..agents.protocol import AgentAdapter, AgentOutput, ToolDefinition
    from ..graph.models import KnowledgeNode
    from ..graph.store import KnowledgeGraph
    from .lead import LeadLLM, DirectionSynthesis

logger = logging.getLogger(__name__)

# Type alias for event callback
EventCallback = Callable[[dict[str, Any]], Coroutine[Any, Any, None]]


@dataclass
class CycleResult:
    """Result of a single research cycle with Lead LLM architecture."""

    cycle_id: int
    target_node_id: str
    target_claim: str
    directions_created: int
    directions_updated: int
    consensus_directions: list[str]
    contradictions: list[str]
    total_cost_usd: float
    lead_llm_cost_usd: float
    research_cost_usd: float
    duration_seconds: float
    agent_outputs: list["AgentOutput"]
    synthesis_reasoning: str | None
    selection_reasoning: str | None
    research_context: str | None
    success: bool
    error_message: str | None = None


class ResearchCycle:
    """Executes a single research cycle with Lead LLM architecture."""

    def __init__(
        self,
        graph: "KnowledgeGraph",
        lead_llm: "LeadLLM",
        research_agents: list["AgentAdapter"],
        tools: list["ToolDefinition"],
        north_star: str,
        cycle_id: int,
        report_interval: int = 10,
        search_instructions: str | None = None,
        context_files: list[dict[str, str]] | None = None,
        event_callback: EventCallback | None = None,
        raw_output_dir: Path | None = None,
    ):
        """
        Initialize research cycle with Lead LLM architecture.

        Args:
            graph: Knowledge graph
            lead_llm: Lead LLM for orchestration
            research_agents: Research agent adapters
            tools: Available tools for agents
            north_star: Project mission/north star
            cycle_id: Current cycle number
            report_interval: Regenerate report every N cycles (default: 10)
            search_instructions: Optional custom search guidance
            context_files: Optional prior research documents
            event_callback: Optional async callback for real-time events
            raw_output_dir: Directory for markdown cycle exports
        """
        self.graph = graph
        self.lead_llm = lead_llm
        self.research_agents = research_agents
        self.tools = tools
        self.north_star = north_star
        self.cycle_id = cycle_id
        self.report_interval = report_interval
        self.search_instructions = search_instructions
        self.context_files = context_files or []
        self.raw_output_dir = raw_output_dir

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
    ) -> CycleResult:
        """
        Execute a single research cycle with Lead LLM architecture.

        Args:
            target_node_id: Specific node to research (or None for Lead LLM selection)
            max_searches: Maximum web searches per agent

        Returns:
            CycleResult with directions and cost tracking
        """
        from .merge_directions import merge_directions_into_graph, deduplicate_directions

        start_time = time.time()

        try:
            # ═══════════════════════════════════════════════════════════
            # STEP 1: Lead LLM selects direction (10% progress)
            # ═══════════════════════════════════════════════════════════
            await self._emit_event({
                "type": "cycle.step",
                "data": {
                    "cycle_id": self.cycle_id,
                    "step": "lead_selection",
                    "progress_percent": 10,
                }
            })

            if target_node_id:
                # User-specified target
                target = await self.graph.get_node(target_node_id)
                if not target:
                    raise ValueError(f"Target node {target_node_id} not found")
                selection_reasoning = "User-specified target"
            else:
                # Lead LLM selects direction autonomously
                target, selection_reasoning = await self.lead_llm.select_direction()

            logger.info(
                f"[Cycle {self.cycle_id}] Target: {target.claim[:60]}... "
                f"(conf={target.confidence:.2f}, imp={target.importance:.2f})"
            )
            logger.info(f"[Cycle {self.cycle_id}] Reasoning: {selection_reasoning}")

            # Emit cycle started event
            await self._emit_event({
                "type": "cycle.started",
                "data": {
                    "cycle_id": self.cycle_id,
                    "focus_node_id": target.id,
                    "focus_claim": target.claim,
                    "selection_reasoning": selection_reasoning,
                }
            })

            # ═══════════════════════════════════════════════════════════
            # STEP 2: Check report regeneration (15% progress)
            # ═══════════════════════════════════════════════════════════
            if self.cycle_id % self.report_interval == 0:
                await self._emit_event({
                    "type": "cycle.step",
                    "data": {
                        "cycle_id": self.cycle_id,
                        "step": "report_regeneration",
                        "progress_percent": 15,
                    }
                })

                logger.info(f"[Cycle {self.cycle_id}] Regenerating report for fresh context")
                report_content = await self._regenerate_report()
                self.lead_llm.report_content = report_content

            # ═══════════════════════════════════════════════════════════
            # STEP 3: Lead LLM dispatches research (30% progress)
            # ═══════════════════════════════════════════════════════════
            await self._emit_event({
                "type": "cycle.step",
                "data": {
                    "cycle_id": self.cycle_id,
                    "step": "research_dispatch",
                    "progress_percent": 30,
                }
            })

            logger.info(
                f"[Cycle {self.cycle_id}] Dispatching {len(self.research_agents)} research agent(s)"
            )

            dispatch_result = await self.lead_llm.dispatch_research(
                target_node=target,
                research_agents=self.research_agents,
                tools=self.tools,
                max_searches=max_searches,
            )
            agent_outputs = dispatch_result.outputs

            # Calculate costs
            lead_llm_cost = sum(
                output.cost_usd for output in agent_outputs
                if output.agent_name == self.lead_llm.adapter.name
            )
            # Research outputs here are already from dispatched research agents only.
            # Do not filter by adapter name; lead and research may intentionally share a model.
            research_cost = sum(output.cost_usd for output in agent_outputs)

            logger.info(
                f"[Cycle {self.cycle_id}] Research complete: "
                f"Lead ${lead_llm_cost:.4f}, Research ${research_cost:.4f}"
            )

            # ═══════════════════════════════════════════════════════════
            # STEP 4: Lead LLM synthesizes directions (60% progress)
            # ═══════════════════════════════════════════════════════════
            await self._emit_event({
                "type": "cycle.step",
                "data": {
                    "cycle_id": self.cycle_id,
                    "step": "synthesis",
                    "progress_percent": 60,
                }
            })

            synthesis: DirectionSynthesis = await self.lead_llm.synthesize_directions(
                agent_outputs=agent_outputs,
                target_node=target,
            )

            logger.info(
                f"[Cycle {self.cycle_id}] Synthesis: {len(synthesis.directions)} directions, "
                f"{len(synthesis.consensus_directions)} consensus, "
                f"{len(synthesis.contradictions)} contradictions"
            )

            # ═══════════════════════════════════════════════════════════
            # STEP 5: Merge directions into graph (80% progress)
            # ═══════════════════════════════════════════════════════════
            await self._emit_event({
                "type": "cycle.step",
                "data": {
                    "cycle_id": self.cycle_id,
                    "step": "merge_directions",
                    "progress_percent": 80,
                }
            })

            merge_stats = await merge_directions_into_graph(
                graph=self.graph,
                directions=synthesis.directions,
                target_node_id=target.id,
                cycle_id=self.cycle_id,
                similarity_threshold=0.75,
                confidence_discount=0.7,
            )

            # ═══════════════════════════════════════════════════════════
            # STEP 6: Deduplicate directions (90% progress)
            # ═══════════════════════════════════════════════════════════
            await self._emit_event({
                "type": "cycle.step",
                "data": {
                    "cycle_id": self.cycle_id,
                    "step": "deduplication",
                    "progress_percent": 90,
                }
            })

            merged_count = await deduplicate_directions(
                graph=self.graph,
                parent_id=target.id,
                cycle_id=self.cycle_id,
                similarity_threshold=0.85,
            )

            if merged_count > 0:
                logger.info(f"[Cycle {self.cycle_id}] Deduplicated {merged_count} directions")

            # ═══════════════════════════════════════════════════════════
            # Calculate final stats
            # ═══════════════════════════════════════════════════════════
            duration = time.time() - start_time
            total_cost = lead_llm_cost + research_cost

            # Build result
            context_snapshot = (
                "## Focused View\n\n"
                f"{dispatch_result.focused_view}\n\n"
                "## Research System Prompt\n\n"
                f"{dispatch_result.system_prompt}\n\n"
                "## Research User Prompt\n\n"
                f"{dispatch_result.user_prompt}"
            )
            result = CycleResult(
                cycle_id=self.cycle_id,
                target_node_id=target.id,
                target_claim=target.claim,
                directions_created=merge_stats["created"],
                directions_updated=merge_stats["updated"],
                consensus_directions=synthesis.consensus_directions,
                contradictions=synthesis.contradictions,
                total_cost_usd=total_cost,
                lead_llm_cost_usd=lead_llm_cost,
                research_cost_usd=research_cost,
                duration_seconds=duration,
                agent_outputs=agent_outputs,
                synthesis_reasoning=synthesis.synthesis_reasoning,
                selection_reasoning=selection_reasoning,
                research_context=context_snapshot,
                success=True,
            )

            logger.info(
                f"[Cycle {self.cycle_id}] Complete in {duration:.1f}s: "
                f"{merge_stats['created']} created, {merge_stats['updated']} updated, "
                f"${total_cost:.4f} cost"
            )

            # Emit cycle completed event
            await self._emit_event({
                "type": "cycle.completed",
                "data": {
                    "cycle_id": self.cycle_id,
                    "directions_created": merge_stats["created"],
                    "directions_updated": merge_stats["updated"],
                    # Legacy keys kept for dashboard/API compatibility.
                    "findings_created": merge_stats["created"],
                    "findings_updated": merge_stats["updated"],
                    "total_cost_usd": total_cost,
                    "duration_seconds": duration,
                }
            })

            # Save cycle output to database
            await self._save_cycle_output(
                result=result,
                synthesis=synthesis,
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
                }
            })

            return CycleResult(
                cycle_id=self.cycle_id,
                target_node_id=target.id if 'target' in locals() else "unknown",
                target_claim=target.claim if 'target' in locals() else "unknown",
                directions_created=0,
                directions_updated=0,
                consensus_directions=[],
                contradictions=[],
                total_cost_usd=0.0,
                lead_llm_cost_usd=0.0,
                research_cost_usd=0.0,
                duration_seconds=duration,
                agent_outputs=[],
                synthesis_reasoning=None,
                selection_reasoning=None,
                research_context=None,
                success=False,
                error_message=str(e),
            )

    async def _regenerate_report(self) -> str:
        """
        Regenerate research report for Lead LLM context.

        Returns:
            Markdown report content
        """
        try:
            from .report import ReportSynthesizer

            synthesizer = ReportSynthesizer(
                graph=self.graph,
                adapter=self.lead_llm.adapter,
                north_star=self.north_star,
            )

            # Generate sync/async compatible
            result = synthesizer.generate()
            if hasattr(result, '__await__'):
                result = await result

            logger.info(
                f"[Cycle {self.cycle_id}] Regenerated report: "
                f"{result.node_count} nodes, {result.cycle_count} cycles"
            )

            return result.markdown

        except Exception as e:
            logger.warning(f"Report regeneration failed: {e}")
            return ""

    async def _save_cycle_output(
        self,
        result: CycleResult,
        synthesis: "DirectionSynthesis",
        merge_stats: dict,
        target: "KnowledgeNode",
    ) -> None:
        """
        Save cycle output to database and export to markdown.

        Args:
            result: CycleResult with all outputs
            synthesis: DirectionSynthesis from Lead LLM
            merge_stats: Merge statistics from graph integration
            target: Target node that was researched
        """
        try:
            # Save to database
            cycle_output_id = await self.graph.save_cycle_output(
                cycle_id=self.cycle_id,
                target_node=target,
                agent_outputs=result.agent_outputs,
                synthesis_result=synthesis,
                merge_stats=merge_stats,
                duration_seconds=result.duration_seconds,
                total_cost_usd=result.total_cost_usd,
                lead_llm_cost_usd=result.lead_llm_cost_usd,
                research_agents_cost_usd=result.research_cost_usd,
                success=result.success,
                error_message=result.error_message,
                selection_strategy=None,  # Lead LLM makes strategic decisions
                selection_reasoning=result.selection_reasoning,
                research_context=result.research_context,
            )

            logger.info(f"Saved cycle {self.cycle_id} output to database (id={cycle_output_id})")

        except Exception as e:
            logger.error(f"Failed to save cycle output: {e}", exc_info=True)

        # Export to markdown (independent of DB save)
        if self.raw_output_dir:
            try:
                await self._export_cycle_markdown()
            except Exception as e:
                logger.error(f"Failed to export cycle markdown: {e}", exc_info=True)

    async def _export_cycle_markdown(self) -> None:
        """Export cycle output to markdown file at raw/{date}/cycle_{id}.md."""
        from datetime import datetime, timezone

        from ..export.cycle_export import CycleExportService

        export_service = CycleExportService(self.graph)
        markdown = await export_service.export_cycle_markdown(self.cycle_id)

        # Build date-nested path: raw/{YYYY-MM-DD}/cycle_{id}.md
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        date_dir = self.raw_output_dir / today
        date_dir.mkdir(parents=True, exist_ok=True)

        output_path = date_dir / f"cycle_{self.cycle_id}.md"
        output_path.write_text(markdown, encoding="utf-8")

        logger.info(f"Exported cycle {self.cycle_id} to {output_path}")
