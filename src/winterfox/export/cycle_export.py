"""Export cycle outputs to markdown format on-demand."""

import json
import logging
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from ..graph.store import KnowledgeGraph

logger = logging.getLogger(__name__)


class CycleExportService:
    """Export cycle data to markdown format."""

    def __init__(self, graph: "KnowledgeGraph"):
        """
        Initialize export service.

        Args:
            graph: KnowledgeGraph instance
        """
        self.graph = graph

    async def export_cycle_markdown(self, cycle_id: int) -> str:
        """
        Generate markdown for a single cycle.

        Args:
            cycle_id: Cycle ID to export

        Returns:
            Formatted markdown string

        Raises:
            ValueError: If cycle not found
        """
        # Fetch from database
        cycle = await self.graph.get_cycle_output(cycle_id)
        if not cycle:
            raise ValueError(f"Cycle {cycle_id} not found")

        # Generate markdown sections
        header = self._format_header(cycle)
        agents = self._format_agent_outputs(cycle["agent_outputs"])
        synthesis = self._format_synthesis(cycle) if cycle.get("synthesis_reasoning") else ""
        merge = self._format_merge_stats(cycle)
        metadata = self._format_metadata(cycle)

        return f"{header}\n\n{agents}\n\n{synthesis}\n\n{merge}\n\n{metadata}"

    async def export_cycles_range(
        self,
        cycle_ids: list[int],
        title: str = "Research Cycles Report",
    ) -> str:
        """
        Combine multiple cycles into single markdown report.

        Args:
            cycle_ids: List of cycle IDs to export
            title: Report title

        Returns:
            Combined markdown string
        """
        sections = [f"# {title}\n\n"]

        for cycle_id in cycle_ids:
            try:
                cycle_md = await self.export_cycle_markdown(cycle_id)
                sections.append(cycle_md)
                sections.append("\n\n---\n\n")  # Separator
            except ValueError as e:
                logger.warning(f"Skipping cycle {cycle_id}: {e}")

        return "".join(sections)

    def _format_header(self, cycle: dict[str, Any]) -> str:
        """Format cycle header section."""
        from datetime import datetime

        created_at = datetime.fromisoformat(cycle["created_at"])
        date_str = created_at.strftime("%Y-%m-%d")
        time_str = created_at.strftime("%H:%M:%S")

        error_line = ""
        if cycle.get("error_message"):
            error_line = f"\n**Error**: {cycle['error_message']}"

        return f"""# Cycle {cycle['cycle_id']} - {date_str} {time_str}

**Target Node**: {cycle['target_node_id']}
**Claim**: {cycle['target_claim']}
**Duration**: {cycle['duration_seconds']:.1f}s | **Cost**: ${cycle['total_cost_usd']:.4f} | **Tokens**: {cycle['total_tokens']:,}
**Status**: {'✅ Success' if cycle['success'] else '❌ Failed'}{error_line}

---"""

    def _format_agent_outputs(self, agent_outputs: list[dict[str, Any]]) -> str:
        """Format agent outputs section."""
        sections = ["## Agent Outputs\n"]

        for i, agent in enumerate(agent_outputs, 1):
            role_badge = "(primary)" if agent["role"] == "primary" else "(secondary)"

            sections.append(f"""
### Agent {i}: {agent['agent_name']} {role_badge}

**Model**: {agent['agent_model']}
**Searches**: {len(agent.get('searches_performed', []))} | **Tokens**: {agent['total_tokens']:,} (in: {agent['input_tokens']:,}, out: {agent['output_tokens']:,}) | **Cost**: ${agent['cost_usd']:.4f}

#### Findings ({len(agent.get('findings', []))})

""")

            # Format findings
            findings = agent.get("findings", [])
            if findings:
                for j, finding in enumerate(findings, 1):
                    sections.append(f"{j}. **{finding['claim']}** (confidence: {finding['confidence']:.2f})\n")

                    # Evidence
                    for evidence in finding.get("evidence", []):
                        evidence_text = evidence['text'][:200] + "..." if len(evidence['text']) > 200 else evidence['text']
                        sections.append(f"   - Evidence: {evidence_text}\n")
                        sections.append(f"   - Source: {evidence['source']}\n")

                    # Tags
                    if finding.get("tags"):
                        sections.append(f"   - Tags: [{', '.join(finding['tags'])}]\n")

                    sections.append("\n")
            else:
                sections.append("*No findings*\n\n")

            # Searches
            searches = agent.get("searches_performed", [])
            if searches:
                sections.append("#### Searches Performed\n\n")
                for k, search in enumerate(searches, 1):
                    sections.append(f"{k}. Query: \"{search['query']}\" via {search['engine']}\n")
                    urls = search.get("urls_visited", [])
                    if urls:
                        urls_preview = ', '.join(urls[:3])
                        if len(urls) > 3:
                            urls_preview += "..."
                        sections.append(f"   - URLs: {urls_preview}\n")
                sections.append("\n")

            # Self-critique
            sections.append(f"""#### Agent Self-Critique

{agent['self_critique']}

---
""")

        return "".join(sections)

    def _format_synthesis(self, cycle: dict[str, Any]) -> str:
        """Format synthesis section."""
        if not cycle.get("synthesis_reasoning"):
            return ""

        sections = [f"""## Synthesis

{cycle['synthesis_reasoning']}

"""]

        # Relationship breakdown (if available)
        merge_stats = cycle.get("merge_stats", {})
        if isinstance(merge_stats, str):
            try:
                import json
                merge_stats = json.loads(merge_stats)
            except (json.JSONDecodeError, ValueError):
                merge_stats = {}

        breakdown = merge_stats.get("relationship_breakdown", {})
        if breakdown and (breakdown.get("extended_parent") or breakdown.get("alternative_approaches")):
            extended = breakdown.get("extended_parent", 0)
            alternatives = breakdown.get("alternative_approaches", 0)
            sections.append(f"""**Relationship Breakdown:**
- Extended parent (sequential depth): {extended}
- Alternative approaches (siblings): {alternatives}

""")

        # Consensus findings
        consensus = cycle.get("consensus_findings", [])
        if consensus:
            sections.append(f"""### Consensus Findings ({len(consensus)})

Claims all agents agreed on:

""")
            for i, claim in enumerate(consensus, 1):
                sections.append(f"{i}. {claim}\n")
            sections.append("\n")

        # Contradictions
        contradictions = cycle.get("contradictions", [])
        if contradictions:
            sections.append(f"""### Contradictions ({len(contradictions)})

Conflicting findings that need investigation:

""")
            for i, contradiction in enumerate(contradictions, 1):
                if isinstance(contradiction, dict):
                    desc = contradiction.get("description", "N/A")
                    claim_a = contradiction.get("claim_a", "N/A")
                    claim_b = contradiction.get("claim_b", "N/A")
                else:
                    desc = str(contradiction)
                    claim_a = "N/A"
                    claim_b = "N/A"

                sections.append(f"{i}. **{desc}**\n")
                sections.append(f"   - Agent A: {claim_a}\n")
                sections.append(f"   - Agent B: {claim_b}\n")
            sections.append("\n")

        sections.append("---\n")
        return "".join(sections)

    def _format_merge_stats(self, cycle: dict[str, Any]) -> str:
        """Format graph integration section."""
        return f"""## Graph Integration

### Findings Merged

**Created** ({cycle.get('findings_created', 0)} new nodes)

**Updated** ({cycle.get('findings_updated', 0)} existing nodes)

**Skipped** ({cycle.get('findings_skipped', 0)} duplicates)

---"""

    def _format_metadata(self, cycle: dict[str, Any]) -> str:
        """Format metadata section."""
        return f"""## Metadata

**Workspace**: {cycle['workspace_id']}
**Cycle ID**: {cycle['cycle_id']}
**Created**: {cycle['created_at']}
**Agent Count**: {cycle['agent_count']}
**Total Cost**: ${cycle['total_cost_usd']:.4f}
**Duration**: {cycle['duration_seconds']:.1f}s
"""


async def export_cycle_to_markdown(
    graph: "KnowledgeGraph",
    cycle_id: int,
    output_path: str,
) -> None:
    """
    Export a single cycle to markdown file.

    Args:
        graph: KnowledgeGraph instance
        cycle_id: Cycle ID to export
        output_path: Output file path
    """
    service = CycleExportService(graph)
    markdown = await service.export_cycle_markdown(cycle_id)

    from pathlib import Path
    Path(output_path).write_text(markdown, encoding="utf-8")


async def export_cycles_to_markdown(
    graph: "KnowledgeGraph",
    cycle_ids: list[int],
    output_path: str,
    title: str = "Research Cycles Report",
) -> None:
    """
    Export multiple cycles to combined markdown file.

    Args:
        graph: KnowledgeGraph instance
        cycle_ids: List of cycle IDs to export
        output_path: Output file path
        title: Report title
    """
    service = CycleExportService(graph)
    markdown = await service.export_cycles_range(cycle_ids, title)

    from pathlib import Path
    Path(output_path).write_text(markdown, encoding="utf-8")
