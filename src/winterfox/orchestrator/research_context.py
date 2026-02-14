"""
Research context builder for feeding accumulated knowledge to agents.

Assembles prior cycle data, search history, contradictions, and graph state
into a token-budgeted context string that agents receive alongside their
research prompts. This ensures each cycle builds on everything that came before.
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..graph.store import KnowledgeGraph

logger = logging.getLogger(__name__)


@dataclass
class TokenBudget:
    """Character limits for each context section (~4 chars per token)."""

    summary_view: int = 3200
    prior_cycles: int = 4800
    search_history: int = 2400
    contradictions: int = 1600
    weakest_nodes: int = 1600
    open_questions: int = 2400


@dataclass
class ResearchContext:
    """Pre-rendered context sections ready for injection into agent prompts."""

    graph_summary: str = ""
    prior_cycle_summaries: str = ""
    search_history: str = ""
    contradictions: str = ""
    weakest_nodes: str = ""
    open_questions: str = ""
    total_prior_cycles: int = 0

    def render(self) -> str:
        """Combine all non-empty sections into a single context string."""
        if self.total_prior_cycles == 0:
            return ""

        sections: list[str] = []

        sections.append(
            f"## Accumulated Research Context ({self.total_prior_cycles} prior cycles)\n\n"
            "You have access to everything discovered in prior cycles. "
            "Use this to avoid redundant work and build on existing knowledge."
        )

        if self.graph_summary:
            sections.append(f"### Knowledge Graph Overview\n\n{self.graph_summary}")

        if self.prior_cycle_summaries:
            sections.append(f"### Prior Cycle Summaries\n\n{self.prior_cycle_summaries}")

        if self.search_history:
            sections.append(
                f"### Prior Searches (avoid repeating these)\n\n{self.search_history}"
            )

        if self.contradictions:
            sections.append(f"### Unresolved Contradictions\n\n{self.contradictions}")

        if self.weakest_nodes:
            sections.append(f"### Areas Needing Attention\n\n{self.weakest_nodes}")

        if self.open_questions:
            sections.append(
                f"### Open Questions from Prior Research\n\n{self.open_questions}"
            )

        return "\n\n".join(sections)


class ResearchContextBuilder:
    """Builds token-budgeted research context from graph and cycle history."""

    def __init__(
        self,
        graph: "KnowledgeGraph",
        budget: TokenBudget | None = None,
    ):
        self.graph = graph
        self.budget = budget or TokenBudget()

    async def build(self) -> ResearchContext:
        """
        Build research context from accumulated data.

        Returns empty context if no prior cycles exist (first cycle).
        """
        # Check if any prior cycles exist
        cycle_outputs = await self.graph.list_cycle_outputs(
            workspace_id=self.graph.workspace_id,
            limit=1,
            success_only=True,
        )
        if not cycle_outputs:
            return ResearchContext()

        total_cycles = len(
            await self.graph.list_cycle_outputs(
                workspace_id=self.graph.workspace_id,
                limit=200,
                success_only=True,
            )
        )

        # Build all sections in parallel
        results = await asyncio.gather(
            self._build_graph_summary(),
            self._build_prior_cycle_summaries(),
            self._build_search_history(),
            self._build_contradictions(),
            self._build_weakest_nodes(),
            self._build_open_questions(),
            return_exceptions=True,
        )

        # Unpack results, using empty string on failure
        sections = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                section_names = [
                    "graph_summary", "prior_cycles", "search_history",
                    "contradictions", "weakest_nodes", "open_questions",
                ]
                logger.warning(
                    f"Failed to build {section_names[i]} section: {result}"
                )
                sections.append("")
            else:
                sections.append(result)

        return ResearchContext(
            graph_summary=sections[0],
            prior_cycle_summaries=sections[1],
            search_history=sections[2],
            contradictions=sections[3],
            weakest_nodes=sections[4],
            open_questions=sections[5],
            total_prior_cycles=total_cycles,
        )

    async def _build_graph_summary(self) -> str:
        """Render compact graph summary using existing view."""
        from ..graph.views import render_summary_view

        summary = await render_summary_view(self.graph, max_depth=2, max_nodes=50)
        return self._truncate(summary, self.budget.summary_view)

    async def _build_prior_cycle_summaries(self) -> str:
        """Summarize recent cycles: target, findings, synthesis reasoning."""
        cycle_list = await self.graph.list_cycle_outputs(
            workspace_id=self.graph.workspace_id,
            limit=10,
            success_only=True,
        )

        if not cycle_list:
            return ""

        # Reverse so oldest is first (chronological order)
        cycle_list.reverse()

        lines: list[str] = []
        for cycle in cycle_list:
            cycle_id = cycle["cycle_id"]
            claim = cycle["target_claim"]
            claim_preview = claim[:80] + "..." if len(claim) > 80 else claim
            created = cycle["findings_created"]
            updated = cycle["findings_updated"]

            lines.append(f"Cycle {cycle_id}: Researched \"{claim_preview}\"")
            lines.append(f"  - Created {created} findings, updated {updated}")

            # Fetch full cycle data for synthesis reasoning and consensus
            full_cycle = await self.graph.get_cycle_output(cycle_id)
            if full_cycle:
                if full_cycle.get("synthesis_reasoning"):
                    reasoning = full_cycle["synthesis_reasoning"]
                    reasoning_preview = (
                        reasoning[:200] + "..." if len(reasoning) > 200 else reasoning
                    )
                    lines.append(f"  - Synthesis: {reasoning_preview}")

                consensus = full_cycle.get("consensus_findings", [])
                if consensus:
                    for finding in consensus[:3]:
                        finding_text = finding if isinstance(finding, str) else str(finding)
                        finding_preview = (
                            finding_text[:100] + "..."
                            if len(finding_text) > 100
                            else finding_text
                        )
                        lines.append(f"  - Consensus: {finding_preview}")

            lines.append("")

        result = "\n".join(lines)
        return self._truncate(result, self.budget.prior_cycles)

    async def _build_search_history(self) -> str:
        """Build deduplicated list of prior searches."""
        search_records = await self.graph.get_all_search_queries(limit=200)

        if not search_records:
            return ""

        # Deduplicate by normalized query
        seen: set[str] = set()
        unique_queries: list[str] = []
        for record in search_records:
            normalized = record["query"].strip().lower()
            if normalized not in seen:
                seen.add(normalized)
                unique_queries.append(record["query"])

        lines = [f"({len(unique_queries)} unique searches performed so far)"]
        for query in unique_queries:
            lines.append(f"- \"{query}\"")

        result = "\n".join(lines)
        return self._truncate(result, self.budget.search_history)

    async def _build_contradictions(self) -> str:
        """Extract unresolved contradictions from cycle outputs."""
        cycle_list = await self.graph.list_cycle_outputs(
            workspace_id=self.graph.workspace_id,
            limit=20,
            success_only=True,
        )

        if not cycle_list:
            return ""

        lines: list[str] = []
        for cycle in cycle_list:
            full_cycle = await self.graph.get_cycle_output(cycle["cycle_id"])
            if not full_cycle:
                continue

            contradictions = full_cycle.get("contradictions", [])
            if not contradictions:
                continue

            cycle_id = full_cycle["cycle_id"]
            for contradiction in contradictions:
                if isinstance(contradiction, dict):
                    desc = contradiction.get("description", str(contradiction))
                else:
                    desc = str(contradiction)
                desc_preview = desc[:150] + "..." if len(desc) > 150 else desc
                lines.append(f"- Cycle {cycle_id}: {desc_preview}")

        if not lines:
            return ""

        result = "\n".join(lines)
        return self._truncate(result, self.budget.contradictions)

    async def _build_weakest_nodes(self) -> str:
        """Render weakest nodes using existing view."""
        from ..graph.views import render_weakest_nodes

        weakest = await render_weakest_nodes(self.graph, n=5)
        return self._truncate(weakest, self.budget.weakest_nodes)

    async def _build_open_questions(self) -> str:
        """Extract open questions from agent self-critiques."""
        critiques = await self.graph.get_recent_critiques(limit=10)

        if not critiques:
            return ""

        lines: list[str] = []
        for critique in critiques:
            agent = critique["agent_name"]
            cycle_id = critique["cycle_id"]
            text = critique["self_critique"]

            # Extract the most relevant snippet
            text_preview = text[:200] + "..." if len(text) > 200 else text
            lines.append(f"- {agent} (cycle {cycle_id}): {text_preview}")

        result = "\n".join(lines)
        return self._truncate(result, self.budget.open_questions)

    @staticmethod
    def _truncate(text: str, max_chars: int) -> str:
        """Truncate text to max_chars, ending at a line boundary."""
        if len(text) <= max_chars:
            return text

        truncated = text[:max_chars]
        # Find last newline to avoid cutting mid-line
        last_newline = truncated.rfind("\n")
        if last_newline > max_chars * 0.5:
            truncated = truncated[:last_newline]

        return truncated + "\n\n[...truncated for token budget]"
