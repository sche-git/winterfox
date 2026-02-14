"""
Living document report synthesizer.

Reads the full knowledge graph and produces a narrative research document
organized by themes. Uses LLM synthesis to integrate findings into a
cohesive report rather than just listing nodes.
"""

from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..agents.protocol import AgentAdapter
    from ..graph.models import KnowledgeNode
    from ..graph.store import KnowledgeGraph

logger = logging.getLogger(__name__)


@dataclass
class ReportResult:
    """Result of report generation."""

    markdown: str
    cost_usd: float
    duration_seconds: float
    total_tokens: int
    input_tokens: int
    output_tokens: int
    node_count: int
    cycle_count: int


@dataclass
class _ReportTokenBudget:
    """Character limits for report context sections (~4 chars per token)."""

    nodes: int = 40_000
    cycle_summaries: int = 12_000
    contradictions: int = 4_000
    open_questions: int = 4_000


class ReportSynthesizer:
    """Generates a narrative research report from the knowledge graph.

    Uses the primary LLM adapter to synthesize graph contents into a
    cohesive markdown document organized by themes.
    """

    def __init__(
        self,
        graph: KnowledgeGraph,
        agent: AgentAdapter,
        north_star: str,
    ) -> None:
        self.graph = graph
        self.agent = agent
        self.north_star = north_star

    async def generate(self) -> ReportResult:
        """Generate a narrative report from the knowledge graph.

        Returns:
            ReportResult with markdown content and cost metadata.

        Raises:
            ValueError: If the graph has no active nodes.
        """
        nodes = await self.graph.get_all_active_nodes()
        if not nodes:
            raise ValueError(
                "Cannot generate report: knowledge graph is empty. "
                "Run research cycles first."
            )

        cycle_count = await self._get_cycle_count()

        start = time.monotonic()

        context = await self._build_report_context(nodes)
        system_prompt = self._build_system_prompt()
        user_prompt = self._build_user_prompt(context)

        output = await self.agent.run(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            tools=[],
            max_iterations=1,
        )

        duration = time.monotonic() - start

        # Build frontmatter + report body + footer
        now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        avg_confidence = (
            sum(n.confidence for n in nodes) / len(nodes) if nodes else 0.0
        )

        frontmatter = (
            "---\n"
            f"generated: {now}\n"
            f"nodes: {len(nodes)}\n"
            f"cycles: {cycle_count}\n"
            f"avg_confidence: {avg_confidence:.2f}\n"
            "---\n\n"
        )

        footer = (
            "\n\n---\n"
            f"*Report generated {now} from {len(nodes)} nodes "
            f"across {cycle_count} research cycles "
            f"(avg confidence: {avg_confidence:.0%}). "
            "Regenerate with `winterfox report` after running more cycles.*\n"
        )

        markdown = frontmatter + output.raw_text.strip() + footer

        return ReportResult(
            markdown=markdown,
            cost_usd=output.cost_usd,
            duration_seconds=duration,
            total_tokens=output.total_tokens,
            input_tokens=output.input_tokens,
            output_tokens=output.output_tokens,
            node_count=len(nodes),
            cycle_count=cycle_count,
        )

    async def _get_cycle_count(self) -> int:
        """Get total number of successful cycles."""
        cycles = await self.graph.list_cycle_outputs(
            workspace_id=self.graph.workspace_id,
            limit=10000,
            success_only=True,
        )
        return len(cycles)

    async def _build_report_context(
        self,
        nodes: list[KnowledgeNode],
    ) -> _ReportContext:
        """Assemble graph data into context sections for the LLM."""
        budget = _ReportTokenBudget()

        results = await asyncio.gather(
            self._build_nodes_section(nodes, budget.nodes),
            self._build_cycle_summaries(budget.cycle_summaries),
            self._build_contradictions(budget.contradictions),
            self._build_open_questions(budget.open_questions),
            return_exceptions=True,
        )

        section_names = [
            "nodes", "cycle_summaries", "contradictions", "open_questions",
        ]
        sections: list[str] = []
        for i, result in enumerate(results):
            if isinstance(result, BaseException):
                logger.warning(
                    f"Failed to build {section_names[i]} section: {result}"
                )
                sections.append("")
            else:
                sections.append(result)

        return _ReportContext(
            nodes_section=sections[0],
            cycle_summaries=sections[1],
            contradictions=sections[2],
            open_questions=sections[3],
        )

    async def _build_nodes_section(
        self,
        nodes: list[KnowledgeNode],
        max_chars: int,
    ) -> str:
        """Build hierarchical node listing with evidence."""
        roots = await self.graph.get_root_nodes()
        if not roots:
            return ""

        lines: list[str] = []
        chars_used = 0

        # Sort nodes by importance for truncation decisions
        importance_map = {n.id: n.importance for n in nodes}

        for root in roots:
            section = await self._render_node_for_report(
                root, importance_map, max_chars - chars_used, depth=0,
            )
            if not section:
                continue
            lines.append(section)
            chars_used += len(section)
            if chars_used >= max_chars:
                break

        return "\n".join(lines)

    async def _render_node_for_report(
        self,
        node: KnowledgeNode,
        importance_map: dict[str, float],
        remaining_chars: int,
        depth: int,
    ) -> str:
        """Render a node and its children for the report context."""
        if remaining_chars <= 0:
            return ""

        indent = "  " * depth
        type_label = f" [{node.node_type}]" if node.node_type else ""
        importance = importance_map.get(node.id, 0.5)

        # For large graphs with low-importance nodes, use claim-only
        use_brief = importance < 0.4 and len(importance_map) > 100

        lines = [
            f"{indent}- {node.claim} "
            f"(confidence: {node.confidence:.2f}{type_label})"
        ]

        if not use_brief:
            for ev in node.evidence[:2]:
                source_str = f" [{ev.source}]" if ev.source else ""
                text_preview = ev.text[:150] + "..." if len(ev.text) > 150 else ev.text
                lines.append(f"{indent}  Evidence: {text_preview}{source_str}")

        result = "\n".join(lines) + "\n"
        remaining = remaining_chars - len(result)

        # Render children
        children = await self.graph.get_children(node.id)
        for child in children:
            if remaining <= 0:
                break
            child_section = await self._render_node_for_report(
                child, importance_map, remaining, depth + 1,
            )
            if child_section:
                result += child_section
                remaining -= len(child_section)

        return result

    async def _build_cycle_summaries(self, max_chars: int) -> str:
        """Build summaries of past research cycles."""
        cycle_list = await self.graph.list_cycle_outputs(
            workspace_id=self.graph.workspace_id,
            limit=50,
            success_only=True,
        )
        if not cycle_list:
            return ""

        cycle_list.reverse()  # Chronological order

        lines: list[str] = []
        for cycle in cycle_list:
            cycle_id = cycle["cycle_id"]
            claim = cycle["target_claim"]
            claim_preview = claim[:100] + "..." if len(claim) > 100 else claim
            created = cycle["findings_created"]
            updated = cycle["findings_updated"]

            lines.append(f"Cycle {cycle_id}: Researched \"{claim_preview}\"")
            lines.append(f"  Created {created} findings, updated {updated}")

            full_cycle = await self.graph.get_cycle_output(cycle_id)
            if full_cycle:
                if full_cycle.get("synthesis_reasoning"):
                    reasoning = full_cycle["synthesis_reasoning"]
                    reasoning_preview = (
                        reasoning[:300] + "..." if len(reasoning) > 300 else reasoning
                    )
                    lines.append(f"  Synthesis: {reasoning_preview}")

                consensus = full_cycle.get("consensus_findings", [])
                for finding in consensus[:3]:
                    finding_text = finding if isinstance(finding, str) else str(finding)
                    finding_preview = (
                        finding_text[:150] + "..."
                        if len(finding_text) > 150
                        else finding_text
                    )
                    lines.append(f"  Consensus: {finding_preview}")

            lines.append("")

        result = "\n".join(lines)
        return _truncate(result, max_chars)

    async def _build_contradictions(self, max_chars: int) -> str:
        """Extract contradictions from cycle outputs."""
        cycle_list = await self.graph.list_cycle_outputs(
            workspace_id=self.graph.workspace_id,
            limit=50,
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
            for contradiction in contradictions:
                if isinstance(contradiction, dict):
                    desc = contradiction.get("description", str(contradiction))
                else:
                    desc = str(contradiction)
                desc_preview = desc[:200] + "..." if len(desc) > 200 else desc
                lines.append(f"- Cycle {full_cycle['cycle_id']}: {desc_preview}")

        if not lines:
            return ""

        return _truncate("\n".join(lines), max_chars)

    async def _build_open_questions(self, max_chars: int) -> str:
        """Extract open questions from agent self-critiques."""
        critiques = await self.graph.get_recent_critiques(limit=20)
        if not critiques:
            return ""

        lines: list[str] = []
        for critique in critiques:
            agent = critique["agent_name"]
            cycle_id = critique["cycle_id"]
            text = critique["self_critique"]
            text_preview = text[:300] + "..." if len(text) > 300 else text
            lines.append(f"- {agent} (cycle {cycle_id}): {text_preview}")

        return _truncate("\n".join(lines), max_chars)

    def _build_system_prompt(self) -> str:
        """Build system prompt for report generation."""
        return (
            "You are a research report writer. Your task is to synthesize "
            "a knowledge graph into a cohesive, well-organized research report.\n\n"
            "Write the report in markdown with these sections:\n\n"
            "1. **Executive Summary** - Key conclusions with confidence levels. "
            "Lead with the most important findings.\n\n"
            "2. **Key Findings** - Organized by theme (NOT by cycle or node). "
            "For each finding, include:\n"
            "   - The claim and its confidence level "
            "(use labels: Confirmed >80%, Likely 60-80%, Uncertain 40-60%, "
            "Speculative <40%)\n"
            "   - Supporting evidence with source citations\n"
            "   - Note when multiple independent sources confirm a finding\n\n"
            "3. **Contradictions and Debates** - Areas where evidence conflicts. "
            "Present both sides fairly.\n\n"
            "4. **Open Questions and Gaps** - What remains unknown or under-researched.\n\n"
            "5. **Methodology Note** - Brief note on how many nodes/cycles/agents "
            "contributed to this report.\n\n"
            "Guidelines:\n"
            "- Integrate findings into a narrative; do NOT just list nodes\n"
            "- Group related findings by theme, not by their position in the graph\n"
            "- Use inline citations where possible (e.g., [Source Name])\n"
            "- Be honest about uncertainty; label confidence levels clearly\n"
            "- Write for a knowledgeable reader who wants actionable insights\n"
            "- Do NOT include the YAML frontmatter (that will be added automatically)\n"
        )

    def _build_user_prompt(self, context: _ReportContext) -> str:
        """Build user prompt with graph data for report generation."""
        sections = [
            f"# Research Mission\n\n{self.north_star}\n",
        ]

        if context.nodes_section:
            sections.append(
                f"# Knowledge Graph ({context.nodes_section.count(chr(10))} lines)\n\n"
                "The following nodes represent the accumulated research findings, "
                "organized hierarchically:\n\n"
                f"{context.nodes_section}"
            )

        if context.cycle_summaries:
            sections.append(
                f"# Research Cycle History\n\n{context.cycle_summaries}"
            )

        if context.contradictions:
            sections.append(
                f"# Identified Contradictions\n\n{context.contradictions}"
            )

        if context.open_questions:
            sections.append(
                f"# Open Questions from Agent Self-Critiques\n\n"
                f"{context.open_questions}"
            )

        sections.append(
            "# Instructions\n\n"
            "Write a comprehensive research report based on the above data. "
            "Synthesize the findings into a narrative organized by themes."
        )

        return "\n\n".join(sections)


@dataclass
class _ReportContext:
    """Assembled context sections for report generation."""

    nodes_section: str = ""
    cycle_summaries: str = ""
    contradictions: str = ""
    open_questions: str = ""


def _truncate(text: str, max_chars: int) -> str:
    """Truncate text to max_chars, ending at a line boundary."""
    if len(text) <= max_chars:
        return text

    truncated = text[:max_chars]
    last_newline = truncated.rfind("\n")
    if last_newline > max_chars * 0.5:
        truncated = truncated[:last_newline]

    return truncated + "\n\n[...truncated for token budget]"
