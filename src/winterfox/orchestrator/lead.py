"""
Lead LLM orchestrator for autonomous research cycle management.

The LeadLLM class owns the entire research cycle lifecycle:
- Selects which direction to pursue (no hardcoded formulas)
- Dispatches research agents for parallel investigation
- Synthesizes raw outputs into strategic directions

This replaces the old multi-agent consensus system with a unified Lead LLM
that makes all strategic decisions autonomously.
"""

from __future__ import annotations

import asyncio
import json
import logging
import re
from dataclasses import dataclass
from typing import TYPE_CHECKING, Sequence

if TYPE_CHECKING:
    from ..agents.protocol import AgentAdapter, AgentOutput
    from ..graph.models import Evidence, KnowledgeNode
    from ..graph.store import KnowledgeGraph

logger = logging.getLogger(__name__)


def _render_cycle_instruction(cycle_instruction: str | None) -> str:
    """Render optional cycle-specific steering guidance."""
    if not cycle_instruction:
        return ""

    text = cycle_instruction.strip()
    if not text:
        return ""

    return (
        "\n## Cycle Override Instruction (Highest Priority This Cycle)\n\n"
        f"{text}\n\n"
        "This comes from user-provided steering for this cycle. "
        "Honor it as the primary directive unless it conflicts with safety or factual integrity.\n"
    )


def _compact_text(text: str | None, max_chars: int = 220) -> str:
    """Normalize and truncate text for compact prompt context."""
    if not text:
        return ""
    normalized = " ".join(text.strip().split())
    if len(normalized) <= max_chars:
        return normalized
    return normalized[:max_chars] + "..."


def _extract_markdown_section(text: str | None, heading: str) -> str:
    """Extract markdown section body by heading (e.g. 'Next Actions')."""
    if not text:
        return ""

    lines = text.splitlines()
    target = heading.strip().lower()
    in_section = False
    collected: list[str] = []

    for line in lines:
        stripped = line.strip()
        lower = stripped.lower()

        if lower.startswith("## "):
            current_heading = lower[3:].strip()
            if in_section:
                break
            if current_heading == target:
                in_section = True
            continue

        if in_section:
            collected.append(line)

    return "\n".join(collected).strip()


def _extract_next_actions(description: str | None, max_items: int = 3) -> list[str]:
    """Extract bullet items from a node description 'Next Actions' section."""
    section = _extract_markdown_section(description, "Next Actions")
    if not section:
        return []

    actions: list[str] = []
    for line in section.splitlines():
        stripped = line.strip()
        if stripped.startswith(("- ", "* ")):
            item = stripped[2:].strip()
            if item:
                actions.append(_compact_text(item, max_chars=140))
        if len(actions) >= max_items:
            break

    return actions


@dataclass
class Direction:
    """
    A research direction extracted by Lead LLM from raw outputs.

    Directions are strategic paths to explore, not individual facts.
    """
    claim: str
    confidence: float  # 0.0 to 1.0
    importance: float  # 0.0 to 1.0
    reasoning: str  # Why this direction matters
    description: str  # Detailed narrative for users/UI (simplified: Proposal + Next Actions)
    stance: str = "mixed"  # support|mixed|disconfirm evidence alignment for this direction claim
    direction_outcome: str = "pursue"  # pursue|complete lifecycle recommendation for this direction
    relationship_type: str = "extends_parent"  # extends_parent|alternative_approach - relationship to target direction
    # Optional fields (not required in simplified output format):
    evidence_summary: str | None = None  # Deprecated - folded into description
    tags: list[str] | None = None


@dataclass
class DirectionSynthesis:
    """Result of Lead LLM synthesizing research into directions."""
    directions: list[Direction]
    synthesis_reasoning: str  # Now includes consensus/contradictions info
    # Optional fields (deprecated - info folded into synthesis_reasoning):
    consensus_directions: list[str] | None = None
    contradictions: list[str] | None = None


@dataclass
class ResearchDispatchResult:
    """Result of dispatching research agents plus prompt context snapshot."""

    outputs: list[AgentOutput]
    focused_view: str
    system_prompt: str
    user_prompt: str


@dataclass
class TargetReassessment:
    """Lead LLM reassessment of a target direction after a research cycle."""

    confidence: float
    importance: float
    status: str
    reasoning: str
    cost_usd: float = 0.0


class LeadLLM:
    """
    Orchestrates research cycles with maximum autonomy.

    The Lead LLM is the strategic intelligence that:
    - Analyzes graph state and decides which direction to pursue
    - Dispatches research agents for parallel investigation
    - Synthesizes raw outputs into meaningful directions

    This replaces hardcoded selection formulas (UCB1) and structured
    findings with pure LLM strategic reasoning.
    """

    def __init__(
        self,
        adapter: AgentAdapter,
        graph: KnowledgeGraph,
        north_star: str,
        report_content: str | None = None,
    ):
        """
        Initialize Lead LLM.

        Args:
            adapter: LLM adapter for Lead agent
            graph: Knowledge graph
            north_star: Project mission/research objective
            report_content: Optional report for context (auto-updated)
        """
        self.adapter = adapter
        self.graph = graph
        self.north_star = north_star
        self.report_content = report_content
        logger.info(f"Initialized Lead LLM: {adapter.name}")

    def _build_selection_brief(self, node: "KnowledgeNode", detailed: bool = False) -> str:
        """Build a compact, structured context brief for selection prompts."""
        claim_preview = _compact_text(node.claim, max_chars=140 if detailed else 110)
        context_preview = _compact_text(node.description, max_chars=360 if detailed else 180)
        next_actions = _extract_next_actions(node.description, max_items=4 if detailed else 2)
        actions_preview = "; ".join(next_actions) if next_actions else "none captured"
        return (
            f"- ID: {node.id[:8]}\n"
            f"  Summary: {claim_preview}\n"
            f"  Context: {context_preview or 'none'}\n"
            f"  Next Actions: {actions_preview}\n"
            f"  Metrics: conf={node.confidence:.2f} imp={node.importance:.2f} depth={node.depth} "
            f"stale={node.staleness_hours:.1f}h children={len(node.children_ids)} status={node.status}"
        )

    def _build_direction_reference_brief(self, node: "KnowledgeNode") -> str:
        """Build compact reference line for duplicate-avoidance context in synthesis."""
        return (
            f"- {node.id[:8]} | {_compact_text(node.claim, max_chars=140)} | "
            f"conf={node.confidence:.2f} imp={node.importance:.2f} depth={node.depth} status={node.status}"
        )

    async def _build_ancestry_chain(self, node: "KnowledgeNode") -> str:
        """Build full path from root to this node showing depth progression."""
        path = []
        current = node
        while current:
            path.insert(0, f"Depth {current.depth}: {_compact_text(current.claim, max_chars=100)}")
            if not current.parent_id:
                break
            current = await self.graph.get_node(current.parent_id)

        if len(path) <= 1:
            return path[0] if path else "Root"

        return "\n  └─ ".join(path)

    async def _build_synthesis_graph_context(self, target_node: "KnowledgeNode") -> str:
        """
        Build nearby-graph context for synthesis duplicate avoidance.

        Includes:
        - Existing children of target node (what already exists under this branch)
        - Peer branches under target's parent (sibling directions at current level)
        """
        existing_children = await self.graph.get_children(target_node.id)
        existing_children_lines = (
            [self._build_direction_reference_brief(node) for node in existing_children]
            if existing_children
            else ["- none"]
        )

        sibling_lines: list[str] = ["- none"]
        if target_node.parent_id:
            parent_children = await self.graph.get_children(target_node.parent_id)
            siblings = [node for node in parent_children if node.id != target_node.id]
            if siblings:
                sibling_lines = [self._build_direction_reference_brief(node) for node in siblings]

        return (
            "## Existing Child Directions Under Target\n\n"
            + "\n".join(existing_children_lines)
            + "\n\n## Sibling Directions In Parent Branch\n\n"
            + "\n".join(sibling_lines)
        )

    def _build_report_section(self) -> str:
        """Render optional report context section for selection prompts."""
        if not self.report_content:
            return ""
        report_preview = (
            self.report_content[:2000] + "\n\n[Report truncated...]"
            if len(self.report_content) > 2000
            else self.report_content
        )
        return f"\n## Current Research Report\n\n{report_preview}\n"

    async def _build_last_selected_section(self, last_selected_id: str | None) -> str:
        """Render optional last-selected node section for selection prompts."""
        if not last_selected_id:
            return ""
        last_node = await self.graph.get_node(last_selected_id)
        if not last_node:
            return ""
        return (
            "\n## Last Selected Direction\n\n"
            f"{self._build_selection_brief(last_node, detailed=False)}\n\n"
            "Consider whether to continue this branch or pivot.\n"
        )

    def _build_excluded_section(self, excluded_node_ids: set[str]) -> str:
        """Render excluded-node section for selection prompts."""
        if not excluded_node_ids:
            return ""
        excluded_list = "\n".join(f"- {node_id}" for node_id in sorted(excluded_node_ids)[:50])
        return (
            "\n## Excluded Directions (Do Not Select)\n\n"
            f"{excluded_list}\n"
        )

    @staticmethod
    def _resolve_candidate(
        node_id: str,
        candidate_nodes: Sequence["KnowledgeNode"],
        candidate_lookup: dict[str, "KnowledgeNode"],
    ) -> "KnowledgeNode" | None:
        """Resolve full or prefix node IDs to a candidate node."""
        direct = candidate_lookup.get(node_id)
        if direct:
            return direct
        for node in candidate_nodes:
            if node.id.startswith(node_id):
                return node
        return None

    @staticmethod
    def _extract_json_payload(raw_text: str, required_key: str) -> dict | None:
        """Extract and parse a JSON object that contains a required key."""
        match = re.search(rf"\{{.*\"{re.escape(required_key)}\".*\}}", raw_text, re.DOTALL)
        if not match:
            return None
        try:
            parsed = json.loads(match.group())
        except json.JSONDecodeError:
            return None
        return parsed if isinstance(parsed, dict) else None

    def _build_shortlist_system_prompt(self, cycle_instruction_section: str) -> str:
        """Build stage-1 shortlist system prompt."""
        return f"""You are the Lead LLM orchestrating an autonomous research project:

{self.north_star}

Your role is to shortlist the most strategically promising directions to work on next.

## Selection Priority (Ranked - Follow This Order)

1. **User steering instruction first** (if present in cycle override)
2. **DEPTH over breadth**: Favor nodes that will produce the DEEPEST/most concrete next level
   - Prioritize nodes at depth 3-4 that can go to 4-5+ (toward execution specifics)
   - **STRONGLY deprioritize nodes with 5+ children** (breadth explosion alert!)
   - **Avoid nodes with 8+ children** unless absolutely necessary
   - Prefer continuing narrow branches over widening broad branches
3. **Decision-useful progress**: Which node will most improve GO/NO-GO decision clarity when researched?
4. **Confidence gaps**: Lower confidence nodes need validation (but only if also high importance)

## Strategic Considerations

- **Concreteness ladder goal**: Reach execution-ready specifics (named people, concrete validation steps)
- Use confidence/importance/staleness as soft signals, not deterministic rules
- Avoid selecting near-identical directions as separate threads
{cycle_instruction_section}

## Output Format

Respond with ONLY this JSON structure:
{{
  "top_candidate_ids": ["abc123...", "def456...", "ghi789..."],
  "reasoning": "2-4 sentences explaining why these candidates maximize depth progression"
}}
"""

    def _build_shortlist_user_prompt(
        self,
        graph_summary: str,
        all_node_briefs: str,
        report_section: str,
        last_selected_section: str,
        excluded_section: str,
    ) -> str:
        """Build stage-1 shortlist user prompt."""
        return f"""## Graph State

{graph_summary}

## All Active Direction Briefs

{all_node_briefs}
{report_section}{last_selected_section}{excluded_section}
---

Shortlist the best candidate directions for the next cycle.
Return 3-6 candidates unless there are fewer eligible nodes.

Respond with ONLY the JSON structure specified.
"""

    def _build_final_system_prompt(self, cycle_instruction_section: str) -> str:
        """Build stage-2 final selection system prompt."""
        return f"""You are the Lead LLM orchestrating an autonomous research project:

{self.north_star}

Select ONE direction to pursue next from the shortlist.

## Decision Principles (Ranked Priority)

1. **Honor cycle override instruction first** (if present)
2. **Maximize depth progression**: Choose the node that will produce the most concrete next level
   - Prefer nodes at higher depth (3-4) over shallow nodes (0-1)
   - **STRONGLY prefer nodes with fewer children** (1-4 children is ideal)
   - **Avoid nodes with 5+ children** (breadth explosion - select their children instead)
   - Favor continuing a narrow branch over widening a broad one
3. **Decision impact**: Choose the node that maximizes GO/NO-GO clarity for the mission
4. **Avoid duplicates**: Don't select overlapping directions
5. **Use metrics as signals only**: confidence/importance/staleness inform but don't dictate
{cycle_instruction_section}

## Output Format

Respond with ONLY this JSON structure:
{{
  "selected_node_id": "abc123...",
  "reasoning": "2-3 sentences explaining why this choice maximizes depth progression and decision clarity"
}}
"""

    def _build_final_user_prompt(
        self,
        graph_summary: str,
        shortlisted_nodes: Sequence["KnowledgeNode"],
        shortlist_reasoning: str,
        report_section: str,
        last_selected_section: str,
        excluded_section: str,
    ) -> str:
        """Build stage-2 final selection user prompt."""
        shortlist_briefs = "\n\n".join(
            self._build_selection_brief(node, detailed=True) for node in shortlisted_nodes
        )
        shortlist_ids = ", ".join(node.id[:8] for node in shortlisted_nodes)
        return f"""## Graph State

{graph_summary}

## Shortlist IDs

{shortlist_ids}

## Shortlist Direction Briefs

{shortlist_briefs}

## Shortlist Rationale From Stage 1

{shortlist_reasoning}
{report_section}{last_selected_section}{excluded_section}
---

Select the best next direction from the shortlist.
Respond with ONLY the JSON structure specified.
"""

    def _parse_shortlist_response(
        self,
        raw_text: str,
        candidate_nodes: Sequence["KnowledgeNode"],
        candidate_lookup: dict[str, "KnowledgeNode"],
        excluded_node_ids: set[str],
    ) -> tuple["KnowledgeNode" | None, str, list["KnowledgeNode"], str]:
        """
        Parse stage-1 response.

        Returns:
            (direct_selected, direct_reasoning, shortlisted_nodes, shortlist_reasoning)
        """
        fallback_reasoning = "Fallback shortlist (parse failed)"
        raw_text = raw_text.strip()

        # Compatibility path: single-stage format from older prompts/tests.
        any_payload = self._extract_json_payload(raw_text, required_key="selected_node_id")
        if any_payload:
            selected_id = str(any_payload.get("selected_node_id", "")).strip()
            reasoning = str(any_payload.get("reasoning", "")).strip() or (
                "Lead selected direction in single-stage mode"
            )
            selected = self._resolve_candidate(selected_id, candidate_nodes, candidate_lookup)
            if selected and selected.id not in excluded_node_ids:
                return selected, reasoning, [], fallback_reasoning

        shortlist_payload = self._extract_json_payload(raw_text, required_key="top_candidate_ids")
        if not shortlist_payload:
            logger.warning("Failed to parse shortlist response: response not in expected JSON format")
            logger.warning(f"Raw shortlist response: {raw_text[:300]}")
            return None, "", [], fallback_reasoning

        shortlist_reasoning = str(shortlist_payload.get("reasoning", "")).strip() or fallback_reasoning
        top_ids = shortlist_payload.get("top_candidate_ids", [])
        if not isinstance(top_ids, list):
            top_ids = []

        shortlisted_nodes: list[KnowledgeNode] = []
        seen_ids: set[str] = set()
        for raw_id in top_ids:
            if not isinstance(raw_id, str):
                continue
            resolved = self._resolve_candidate(raw_id.strip(), candidate_nodes, candidate_lookup)
            if not resolved or resolved.id in seen_ids:
                continue
            seen_ids.add(resolved.id)
            shortlisted_nodes.append(resolved)
            if len(shortlisted_nodes) >= 6:
                break

        return None, "", shortlisted_nodes, shortlist_reasoning

    def _parse_final_selection_response(
        self,
        raw_text: str,
        candidate_nodes: Sequence["KnowledgeNode"],
        candidate_lookup: dict[str, "KnowledgeNode"],
        excluded_node_ids: set[str],
        fallback_node: "KnowledgeNode",
    ) -> tuple["KnowledgeNode", str]:
        """Parse stage-2 final response with robust fallbacks."""
        payload = self._extract_json_payload(raw_text.strip(), required_key="selected_node_id")
        if not payload:
            logger.warning(f"Lead LLM final response not in JSON format: {raw_text[:200]}")
            return fallback_node, "Fallback selection (final response parse failed)"

        selected_id = str(payload.get("selected_node_id", "")).strip()
        reasoning = str(payload.get("reasoning", "")).strip()
        target = self._resolve_candidate(selected_id, candidate_nodes, candidate_lookup)

        if not target:
            logger.warning(f"Lead LLM selected invalid node ID: {selected_id}")
            return fallback_node, f"Fallback selection (invalid ID: {selected_id})"

        if target.id in excluded_node_ids:
            logger.warning(f"Lead LLM selected excluded node ID: {selected_id}")
            return fallback_node, f"Fallback selection (excluded ID: {selected_id})"

        return target, reasoning

    def _programmatic_prefilter(
        self,
        nodes: list["KnowledgeNode"],
        max_candidates: int = 12,
    ) -> list["KnowledgeNode"]:
        """
        Programmatically pre-filter nodes to reduce LLM burden (Phase 1 simplification).

        Scoring heuristic:
        - Depth value: Higher depth = higher priority (reach execution specifics)
        - Child count penalty: More children = lower priority (avoid breadth)
        - Confidence gap: Lower confidence = higher priority (resolve uncertainty)
        - Importance multiplier: Higher importance = higher priority
        """
        def score_node(node: "KnowledgeNode") -> float:
            # Depth value (prefer deeper nodes 2-4)
            depth_score = min(node.depth / 5.0, 1.0) * 0.35

            # Child count penalty (prefer nodes with fewer children)
            child_count = len(node.children_ids) if node.children_ids else 0
            if child_count >= 8:
                child_penalty = 0.0  # Avoid breadth explosion
            elif child_count >= 5:
                child_penalty = 0.3
            else:
                child_penalty = 1.0
            child_score = child_penalty * 0.30

            # Confidence gap (prefer lower confidence for validation)
            confidence_gap = (1.0 - node.confidence) * 0.20

            # Importance multiplier
            importance_score = node.importance * 0.15

            return depth_score + child_score + confidence_gap + importance_score

        # Score and sort
        scored_nodes = [(node, score_node(node)) for node in nodes]
        scored_nodes.sort(key=lambda x: x[1], reverse=True)

        # Return top candidates
        return [node for node, score in scored_nodes[:max_candidates]]

    async def select_direction(
        self,
        last_selected_id: str | None = None,
        cycle_instruction: str | None = None,
        excluded_node_ids: set[str] | None = None,
    ) -> tuple[KnowledgeNode, str]:
        """
        Lead LLM strategically selects which direction to pursue next.

        Replaces hardcoded UCB1 formula with LLM strategic thinking.
        The Lead analyzes:
        - Graph structure and confidence gaps
        - Research history and prior cycles
        - Report context if available
        - Exploration/exploitation balance

        Args:
            last_selected_id: ID of previously selected node (optional)
            cycle_instruction: Optional cycle-specific steering guidance
            excluded_node_ids: Optional node IDs that must not be selected

        Returns:
            (target_node, selection_reasoning) tuple
        """
        from ..graph.views import render_summary_view

        logger.info("Lead LLM selecting direction...")

        # Build shared context
        graph_summary = await render_summary_view(self.graph, max_depth=3, max_nodes=80)
        all_nodes = await self.graph.get_all_active_nodes()
        excluded = excluded_node_ids or set()
        candidate_nodes = [node for node in all_nodes if node.id not in excluded]

        if not all_nodes:
            raise ValueError("No active nodes in graph - cannot select direction")
        if not candidate_nodes:
            raise ValueError("No eligible active nodes remain after exclusions")

        cycle_instruction_section = _render_cycle_instruction(cycle_instruction)
        report_section = self._build_report_section()
        last_selected_section = await self._build_last_selected_section(last_selected_id)
        excluded_section = self._build_excluded_section(excluded)

        # Phase 1 simplification: Programmatic pre-filter to reduce LLM burden
        logger.info(f"Programmatically pre-filtering {len(candidate_nodes)} candidates...")
        top_candidates = self._programmatic_prefilter(candidate_nodes, max_candidates=12)
        logger.info(f"Pre-filtered to top {len(top_candidates)} candidates for LLM review")

        # Build briefs only for top candidates (more efficient)
        candidate_briefs = "\n\n".join(
            self._build_selection_brief(node, detailed=True) for node in top_candidates
        )
        candidate_lookup: dict[str, KnowledgeNode] = {node.id: node for node in top_candidates}

        # Single-stage selection: Pick ONE from pre-filtered candidates
        output = await self.adapter.run(
            system_prompt=self._build_final_system_prompt(cycle_instruction_section),
            user_prompt=self._build_final_user_prompt(
                graph_summary=graph_summary,
                shortlisted_nodes=top_candidates,
                shortlist_reasoning="Programmatically pre-filtered based on depth, child count, confidence gap, and importance",
                report_section=report_section,
                last_selected_section=last_selected_section,
                excluded_section=excluded_section,
            ),
            tools=[],
            max_iterations=1,
        )

        target, reasoning = self._parse_final_selection_response(
            raw_text=output.raw_text,
            candidate_nodes=top_candidates,
            candidate_lookup=candidate_lookup,
            excluded_node_ids=excluded,
            fallback_node=top_candidates[0],  # Fallback to top-scored node
        )
        logger.info(f"Lead LLM selected: {target.claim[:50]}... (Reason: {reasoning[:100]}...)")
        return target, reasoning

    async def dispatch_research(
        self,
        target_node: KnowledgeNode,
        research_agents: list[AgentAdapter],
        tools: list,
        max_searches: int,
        cycle_instruction: str | None = None,
    ) -> ResearchDispatchResult:
        """
        Lead LLM dispatches research agents in parallel.

        Generates research prompts and coordinates parallel investigation.
        Research agents return raw outputs (no structured findings).

        Args:
            target_node: Direction to research
            research_agents: List of research agent adapters
            tools: Available research tools
            max_searches: Maximum searches per agent
            cycle_instruction: Optional cycle-specific steering guidance

        Returns:
            ResearchDispatchResult containing agent outputs and prompt context
        """
        from ..graph.views import render_focused_view

        logger.info(f"Lead LLM dispatching {len(research_agents)} research agents...")

        # Generate focused view of target direction
        focused_view = await render_focused_view(self.graph, target_node.id, max_depth=3)
        cycle_instruction_section = _render_cycle_instruction(cycle_instruction)

        # Build research system prompt (no note_finding tool)
        system_prompt = f"""You are an expert research agent working on:

{self.north_star}

Your task is to research a specific direction thoroughly using web search and content fetching.

## Research Guidelines

1. **Evidence-Based**: Find concrete facts, numbers, quotes, examples
2. **Multiple Sources**: Verify claims with independent sources
3. **Skeptical**: Look for contradicting viewpoints
4. **Comprehensive**: Cover all aspects of the research direction
5. **Budget**: You have {max_searches} web searches - use them effectively
6. **Stay broad enough**: Test adjacent hypotheses and alternatives, not just the first promising thread
7. **Align with user steering**: If a cycle override instruction is present, treat it as the primary objective for this cycle

## Important Changes

- **No structured findings**: Just do thorough research
- **Raw output is primary**: Your full reasoning and discoveries will be analyzed by the Lead LLM
- **Focus on quality**: Better to deeply investigate fewer aspects than superficially cover many

## Tools Available

- `web_search`: Search the web for information
- `web_fetch`: Read full content from URLs
- `read_graph_node`: Read other nodes in the knowledge graph
- `search_graph`: Search the knowledge graph
{cycle_instruction_section}

After your research, you'll be asked for a brief self-critique."""

        # Build research user prompt
        user_prompt = f"""## Research Direction

{focused_view}

## Your Research Task

Thoroughly investigate this direction. Find evidence, verify claims, explore sub-topics.

- Use web_search to find relevant sources
- Use web_fetch to read full content
- Look for specific data, quotes, examples, and statistics
- Consider multiple perspectives
- Note any contradictions or uncertainties you find

Begin your research. Remember: your raw output will be analyzed by the Lead LLM to extract strategic directions."""

        # Dispatch all research agents in parallel
        tasks = [
            agent.run(system_prompt, user_prompt, tools, max_iterations=30)
            for agent in research_agents
        ]

        outputs = await asyncio.gather(*tasks, return_exceptions=True)

        # Handle errors
        results = []
        for i, output in enumerate(outputs):
            if isinstance(output, Exception):
                logger.error(f"Research agent {research_agents[i].name} failed: {output}")
                # Continue with other agents
            else:
                results.append(output)

        if not results:
            raise ValueError("All research agents failed")

        logger.info(f"Research complete: {len(results)} agents returned outputs")
        return ResearchDispatchResult(
            outputs=results,
            focused_view=focused_view,
            system_prompt=system_prompt,
            user_prompt=user_prompt,
        )

    async def synthesize_directions(
        self,
        agent_outputs: list[AgentOutput],
        target_node: KnowledgeNode,
        cycle_instruction: str | None = None,
    ) -> DirectionSynthesis:
        """
        Lead LLM extracts strategic directions from raw research outputs.

        Replaces note_finding tool - LLM decides what matters.
        Synthesizes multiple raw outputs into strategic next-step directions.

        Args:
            agent_outputs: Raw outputs from research agents
            target_node: Direction that was researched
            cycle_instruction: Optional cycle-specific steering guidance

        Returns:
            DirectionSynthesis with extracted directions
        """
        logger.info(f"Lead LLM synthesizing {len(agent_outputs)} raw outputs...")

        # Format agent outputs for synthesis
        formatted_outputs = []
        for i, output in enumerate(agent_outputs, 1):
            searches_summary = f"{len(output.searches_performed)} searches performed"
            formatted_outputs.append(
                f"## Research Agent {i}: {output.agent_name}\n\n"
                f"**Searches**: {searches_summary}\n"
                f"**Duration**: {output.duration_seconds:.1f}s\n"
                f"**Cost**: ${output.cost_usd:.4f}\n\n"
                f"### Research Output:\n\n{output.raw_text}\n\n"
                f"### Self-Critique:\n\n{output.self_critique}\n\n"
                "---\n\n"
            )

        combined_outputs = "".join(formatted_outputs)
        cycle_instruction_section = _render_cycle_instruction(cycle_instruction)
        synthesis_graph_context = await self._build_synthesis_graph_context(target_node)

        # Build synthesis system prompt
        ancestry_chain = await self._build_ancestry_chain(target_node)
        system_prompt = f"""You are the Lead LLM synthesizing research for:

{self.north_star}

## CRITICAL: You Are Building Children in a Tree Structure

**Your synthesized directions will become CHILDREN of the target direction.**

Current tree position (this is where you are in the hierarchy):
{ancestry_chain}

**Your output will be placed here:**
  └─ Depth {target_node.depth + 1}: [YOUR SYNTHESIZED DIRECTIONS]

This means:
- You are NOT creating alternative directions at the same level as the target
- You ARE creating the next level down in the hierarchy
- Each direction you create MUST be MORE CONCRETE/SPECIFIC than the target direction
- Think: if target says "WHAT", children should say "WHO/WHERE/WHEN/HOW"

## MANDATORY Depth Progression (Non-Negotiable)

**Before synthesizing each direction, verify:**

1. **Specificity Test**: Is this direction MORE SPECIFIC than target?
   - Target (depth {target_node.depth}): "{_compact_text(target_node.claim, max_chars=120)}"
   - Proposed direction (depth {target_node.depth + 1}): "[your claim]"
   - ✓ Drills deeper into target / ✗ Lateral topic jump / ✗ More abstract

2. **Concreteness Level Required**:
   - Depth 0→1: Target is strategic thesis → Output must be specific wedge + market segment
   - Depth 1→2: Target is wedge + segment → Output must be specific buyer persona + workflow + measurable pain
   - Depth 2→3: Target is buyer + workflow → Output must be named companies/people + procurement path + constraints
   - Depth 3→4+: Target is named targets → Output must be execution-ready (meeting agenda, demo scope, integration steps)

3. **Parent-Child Coherence**:
   - Does this direction drill into an aspect OF the target?
   - Or does it jump to a different but related topic? (❌ REJECT - that's a sibling, not a child)

**RULE**: Reject any proposed direction that fails these tests. Revise until it's truly deeper/more concrete.

## Concrete Examples: Good vs Bad Depth Progression

**BAD** (lateral branching - same abstraction level):
```
Depth 1: "Chevron represents viable pilot customer for LLM fine-tuning services"
  Depth 2: "Quantum molecular dynamics simulation..." ❌ DIFFERENT TOPIC!
  Depth 2: "Noble AI competitive positioning" ❌ DIFFERENT TOPIC!
  Depth 2: "Azure OpenAI limitations" ❌ LATERAL DETAIL, NOT DEEPER!
```

**GOOD** (drilling down - increasing concreteness):
```
Depth 0: "Industrial safety-critical AI adoption opportunity"
  Depth 1: "Energy sector process engineering teams need ASME-compliant LLM tools"
    Depth 2: "Chevron Project Designs engineers use Azure OpenAI for code gen, face hallucination risks costing $X/incident"
      Depth 3: "Target: Luis Niño (CTV Director), demo ASME B31.3 verifier to ENGINE Center Bengaluru team; proof = pilot MOU by Q2 2026"
        Depth 4: "Validate via: interview procurement Sarah Chen 555-0123; review Q3 2024 incident logs; benchmark vs Noble AI tool adoption rate"
```

**Another BAD Example** (going sideways or up):
```
Depth 2: "Chevron Project Designs has ASME compliance needs"
  Depth 3: "LLM hallucinations are a general problem" ❌ MORE ABSTRACT!
  Depth 3: "Microsoft also has engineering teams" ❌ DIFFERENT COMPANY!
```

**Another GOOD Example**:
```
Depth 2: "Chevron Project Designs needs ASME B31.3 compliance verification"
  Depth 3: "Project Designs uses Azure OpenAI daily for piping specs; 15% hallucination rate causes 40hrs/month rework; team of 12 engineers in Houston HQ"
    Depth 4: "Contact Alex Rodriguez (Lead Engineer, 281-555-0199); demo constraint-based verifier on live B31.3 spec; success = <5% error rate on benchmark suite"
```

## FORBIDDEN PATTERNS (Auto-Reject These)

When synthesizing, immediately REJECT these anti-patterns:

### ❌ Pattern 1: Different Person/Team Switch
```
Parent: "Target Justin Lo's Enterprise AI team"
Child: "Target Bill Braun's engineering team"  ← WRONG! Different person = SIBLING, not child
Child: "Target carbon sequestration team"      ← WRONG! Different team = SIBLING, not child
```

**Rule**: If parent mentions person/team X, children MUST drill into X (not switch to person/team Y).

### ❌ Pattern 2: Aspect Enumeration (Creating List of Siblings)
```
Parent: "Deploy FNO-LoRA fine-tuning technology"
Child 1: "Procurement path for FNO-LoRA"        ← These are all lateral aspects
Child 2: "Competitive analysis vs NobleAI"      ← at the same abstraction level
Child 3: "Legal validation of approach"        ← They are SIBLINGS to each other,
Child 4: "Technical architecture details"      ← not children of the parent!
Child 5: "Integration with Azure"
Child 6: "Use case validation"
```

**Rule**: If you're creating a list of "aspects" or "approaches", you're creating SIBLINGS. Pick ONE aspect and drill into it.

### ✅ Correct Pattern: Pick ONE Aspect and Drill
```
Parent: "Deploy FNO-LoRA fine-tuning technology"
Child: "Validate FNO-LoRA efficacy using Volve field dataset to establish benchmark proof"
  Grandchild: "Configure Azure ML pipeline for Volve dataset processing with 90% accuracy threshold"
    Great-grandchild: "Execute benchmark run by Feb 28, 2026; document results in technical report for CTV"
```

### ❌ Pattern 3: Research Discovery Expansion
If research about target X incidentally discovers information about Y, Z, and W:
- ✓ Create directions drilling into X (the target)
- ✗ Do NOT create directions for Y, Z, W (those are potential future targets, not children of X)

**Rule**: Research discoveries are inputs for drilling deeper into the TARGET, not prompts to branch sideways.

### ❌ Pattern 4: Topic Jump Under Same Parent
```
Parent: "Chevron Project Designs ASME B31.3 compliance needs"
Child 1: "ASME B31.3 verification demo for Project Designs team"  ✓ Drills into parent
Child 2: "Carbon capture reservoir simulation for different team" ✗ Different topic!
Child 3: "Quantum optimization for LNG operations"                ✗ Different topic!
```

**Rule**: All children must share the core topic/entity of the parent. If topics diverge, that's breadth, not depth.

### Detection Heuristic

Before finalizing each direction, ask:
1. Does this direction mention the same person/team/entity as the parent?
2. Is this direction MORE SPECIFIC about the parent's topic?
3. Or is this direction exploring a RELATED BUT DIFFERENT topic?

If #3, REJECT IT. That's a sibling candidate for future cycles, not a child of this target.

## Relationship Type Classification

For EACH direction you synthesize, classify its relationship to the target direction.

### "extends_parent" (default) - Sequential Depth Progression

Use when the direction is a **logical next step** that drills deeper into the parent:
- Same person/team/entity as parent
- More concrete/specific execution of parent's approach
- Answers "HOW" or "WHAT SPECIFICALLY" about parent
- Cannot proceed without parent context

**Examples:**
- Parent: "Target Akshay Sahni at ENGINE Bengaluru"
  - Child (extends): "Secure meeting with Sahni via Rice Alliance introduction" ✓
  - Child (extends): "Draft ENGINE-specific pitch deck for Sahni" ✓

- Parent: "Develop classical LoRA fine-tuning pipeline"
  - Child (extends): "Configure rank-8 LoRA adapters for Volve dataset" ✓
  - Child (extends): "Benchmark LoRA vs full fine-tuning on seismic data" ✓

### "alternative_approach" - Different Strategic Path

Use when the direction is a **fundamentally different approach** to achieving the same goal:
- Different technical method for same outcome
- Different market entry path for same customer
- Different buyer persona for same value prop
- Mutually exclusive with other approaches (pick one)

**Examples:**
- Parent: "Execute CTV Catalyst Program entry"
  - Child (alternative): "Classical LoRA baseline pilot" ✓ (one approach)
  - Child (alternative): "Quantum-ready OQC architecture pilot" ✓ (different approach)
  - Child (alternative): "Direct sales to Jim Gable bypassing Catalyst" ✓ (different entry)

- Parent: "Validate technical approach for Chevron"
  - Child (alternative): "Volve dataset public benchmark" ✓ (one validation method)
  - Child (alternative): "Proprietary Chevron seismic data pilot" ✓ (different method)

**Key Test:**
- If directions can/should be pursued **in parallel** or require **choosing between them** → `alternative_approach`
- If direction must come **after** parent or **depends on** parent → `extends_parent`

## What Are Directions?

Directions are meaningful paths to explore - NOT individual facts. Examples:
- "Investigate B2B vs B2C market fit for legal tech startups"
- "Explore funding strategies: VC vs bootstrapping vs strategic partnerships"
- "Analyze competitive advantages in the AI-powered contract review space"

NOT directions (too granular):
- "Legal tech market is $50B" (this is just a fact)
- "YC funded 10 legal tech companies" (just a data point)

## Synthesis Guidelines

1. **Extract Directions** (that are children of target):
   - Look for strategic questions, approaches, or hypotheses that DRILL DEEPER into the target
   - **Group related findings about THE TARGET** into coherent directions
     * "Related findings" = findings about the SAME entity/topic as the target
     * NOT "findings about different but related entities" (those are siblings, not children!)
   - Each direction should suggest a more specific path than the target
   - **Critical Rule**: If research discovered info about multiple different people/teams/topics:
     * Create directions for THE TARGET ONLY
     * Other discoveries are candidates for FUTURE cycles, not children of this target
   - For each direction, provide:
     - `claim`: concise one-line summary (MORE CONCRETE than target!)
     - `description`: long-form Markdown narrative (at least 220 words; target 350-700 words)
       - Use Markdown structure with short sections and bullets where helpful
       - Preserve meaningful line breaks between sections/points
       - Include concrete items: context, key evidence, assumptions/risks, and Winterfox-executable next actions
     - `stance`: one of:
       - `support`: evidence supports this direction claim
       - `mixed`: evidence is mixed/uncertain
       - `disconfirm`: evidence undermines this direction claim
     - `direction_outcome`: one of:
       - `pursue`: keep active for future investigation
       - `complete`: treat as sufficiently concluded/dead-end for now
   - STRONGLY prefer deepening existing paths over creating parallel branches
   - Only create genuinely new branches when evidence reveals a distinct, non-overlapping sub-aspect
   - Do not branch for its own sake; avoid direction inflation
   - EVERY direction must pass the specificity test above

2. **Depth-Appropriate Concreteness**:
   - Your output depth is {target_node.depth + 1}
   - At this depth, directions should include the concreteness elements listed in "Concreteness Level Required" above
   - Actively avoid lateral rewording at same abstraction level
3. **Assess Confidence**:
   - Interpret confidence as confidence in THIS direction claim.
   - High (0.8-1.0): Strong corroboration for the claim
   - Medium (0.5-0.7): Mixed but direction still plausible
   - Low (0.0-0.4): Weak or contradictory support for this claim
   - If stance is `disconfirm`, confidence should usually be low unless disconfirmation itself is strongly evidenced.

4. **Determine Importance**:
   - High (0.8-1.0): Critical to mission, high impact
   - Medium (0.5-0.7): Relevant, moderate impact
   - Low (0.0-0.4): Tangential, low impact

5. **Identify Consensus**:
   - What did multiple agents agree on?
   - Where is there strong corroboration?

6. **Spot Contradictions**:
   - What disagreements exist?
   - Which claims conflict?
   - If most evidence is negative against a direction claim, label stance=`disconfirm` and prefer direction_outcome=`complete`

7. **Respect User Steering**:
   - If a cycle override instruction is present, bias synthesis priorities to that instruction
   - Keep conclusions evidence-grounded and avoid overfitting to a single narrative
{cycle_instruction_section}

8. **Branching Discipline & Child Count Limits**:
   - **Default: Create 1-3 directions per cycle** (not 8-12!)
   - **Maximum: 5 directions** only if there are genuinely distinct sub-aspects that ALL pass specificity test
   - **Typical: 2 directions** that drill into different execution paths of the SAME target entity/topic
   - You are NOT required to create multiple directions every cycle
   - It is valid and often BETTER to return 1-2 highly focused directions
   - Prioritize depth and clarity over quantity
   - **Self-Check**: If you drafted >5 directions, review each:
     * Does it drill into the TARGET (parent node)?
     * Or does it explore a "related topic" discovered during research? (← REJECT those as future siblings)

9. **Next Actions Must Be Winterfox-Executable**:
   - In each direction description, the `## Next Actions` section must include ONLY actions
     that can be executed in a future Winterfox cycle via web-based research.
   - Allowed action types:
     - Investigate a sub-direction with targeted web searches
     - Assess feasibility by reviewing academic papers, benchmarks, standards, docs, filings, or technical reports
     - Resolve contradictions across independent sources
     - Gather specific missing evidence needed to raise/lower confidence
   - Disallowed action types:
     - Talk to customers, interviews, surveys, or sales calls
     - Run product experiments, build prototypes, or engineering implementation
     - Hiring, partnerships, procurement, or other offline operational tasks
   - For each next action include:
     - Objective: what the research action should prove/disprove
     - Query seeds: 2-5 concrete web search query ideas
     - Source targets: what source types to prioritize
     - Completion signal: explicit evidence threshold for considering the action done

10. **Duplicate Avoidance Against Existing Graph**:
   - You will receive existing child directions under the target, plus sibling directions in the parent branch.
   - Do NOT create a new direction that is materially the same as an existing child or sibling direction.
   - Treat title-level paraphrases as duplicates if intent, scope, and decision objective overlap.
   - If new evidence maps to an existing direction, deepen it with more concrete framing instead of creating a parallel duplicate.
   - Only propose a truly new direction when it has a distinct decision objective and non-overlapping evidence plan.

## Output Format (SIMPLIFIED)

Respond with ONLY this JSON structure:
{{
  "directions": [
    {{
      "claim": "Short summary (one line, <=120 chars)",
      "description": "Markdown narrative (target 250-400 words) with ONLY these 2 required sections:
        - ## Proposal: What this direction proposes, why it matters, how it connects to parent, and key evidence supporting it (3-5 sentences)
        - ## Next Actions: Winterfox-executable research tasks only (each with: objective, 2-5 query seed examples, source targets, completion signal)",
      "stance": "support|mixed|disconfirm",
      "direction_outcome": "pursue|complete",
      "relationship_type": "extends_parent|alternative_approach",
      "confidence": 0.85,
      "importance": 0.9,
      "reasoning": "Why this direction matters and what it builds on"
    }}
  ],
  "synthesis_reasoning": "2-4 sentences: (1) your synthesis approach, (2) why you limited to this number of directions, (3) what consensus/agreements you found across agents, (4) what contradictions/disagreements exist"
}}

Be strategic - extract directions that move research forward, not just facts."""

        user_prompt = f"""## Target Direction Researched

**{target_node.claim}**

**Target Depth**: {target_node.depth}

## Raw Research Outputs

{combined_outputs}

## Nearby Graph Context (Use To Avoid Duplicates)

{synthesis_graph_context}

---

Analyze all outputs and extract strategic DIRECTIONS (not facts).
Identify consensus and contradictions.
Respond with ONLY the JSON structure (no markdown, no extra text).
"""

        # Call Lead LLM for synthesis
        output = await self.adapter.run(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            tools=[],  # No tools, pure synthesis
            max_iterations=1,
        )

        # Parse JSON response
        import json
        import re

        raw_text = output.raw_text.strip()
        json_match = re.search(r'\{.*"directions".*\}', raw_text, re.DOTALL)

        if not json_match:
            logger.error(f"Lead LLM synthesis not in JSON format: {raw_text[:500]}")
            # Fallback: create default direction
            return DirectionSynthesis(
                directions=[
                    Direction(
                        claim=f"Continue investigating: {target_node.claim}",
                        description=(
                            "This fallback direction is intentionally comprehensive because synthesis output "
                            "could not be parsed. The next cycle should restate the target direction and "
                            "establish the precise decision objective it informs, then enumerate the key "
                            "unknowns that currently block confident judgment. Research should map the "
                            "assumptions behind the current direction, identify which assumptions are most "
                            "fragile, and prioritize evidence collection that can falsify or confirm those "
                            "assumptions quickly. Include both supporting and contradicting signals from "
                            "independent sources, with explicit source quality assessment and recency checks. "
                            "Quantify where possible: market sizes, rates of change, comparative benchmarks, "
                            "and confidence intervals or uncertainty bounds when data quality is limited. "
                            "If contradictory claims appear, isolate the disagreement drivers such as scope "
                            "differences, stale data, or methodological inconsistencies, and propose targeted "
                            "queries to resolve each contradiction. The output should also define practical next "
                            "steps: what to test in the next cycle, what can be deprioritized, and which "
                            "conditions would justify re-scoring confidence or importance for this direction."
                        ),
                        confidence=0.5,
                        importance=0.7,
                        reasoning="Fallback direction (synthesis parse failed)",
                        stance="mixed",
                        direction_outcome="pursue",
                    )
                ],
                synthesis_reasoning="Synthesis parse failed - using fallback direction",
            )

        try:
            synthesis_data = json.loads(json_match.group())

            # Parse directions
            directions = []
            for dir_data in synthesis_data.get("directions", []):
                description = str(dir_data["description"]).strip()
                if not description:
                    raise ValueError("Direction description must be non-empty")
                stance = str(dir_data.get("stance", "mixed")).strip().lower()
                if stance not in {"support", "mixed", "disconfirm"}:
                    stance = "mixed"
                outcome = str(dir_data.get("direction_outcome", "pursue")).strip().lower()
                if outcome not in {"pursue", "complete"}:
                    outcome = "pursue"
                if "direction_outcome" not in dir_data and stance == "disconfirm":
                    # Bias toward faithful closure when model explicitly disconfirms a claim.
                    outcome = "complete"
                # Extract and validate relationship_type
                relationship_type = str(dir_data.get("relationship_type", "extends_parent")).strip().lower()
                if relationship_type not in {"extends_parent", "alternative_approach"}:
                    relationship_type = "extends_parent"  # Default fallback
                directions.append(Direction(
                    claim=dir_data["claim"],
                    description=description,
                    stance=stance,
                    direction_outcome=outcome,
                    relationship_type=relationship_type,
                    confidence=float(dir_data["confidence"]),
                    importance=float(dir_data["importance"]),
                    reasoning=dir_data["reasoning"],
                    evidence_summary=dir_data.get("evidence_summary"),  # Optional
                    tags=dir_data.get("tags"),  # Optional
                ))

            result = DirectionSynthesis(
                directions=directions,
                synthesis_reasoning=synthesis_data.get("synthesis_reasoning", ""),
                consensus_directions=synthesis_data.get("consensus_directions"),  # Optional
                contradictions=synthesis_data.get("contradictions"),  # Optional
            )

            # Programmatic child count limit (Phase 1 simplification)
            if len(result.directions) > 5:
                logger.warning(
                    f"Synthesis produced {len(result.directions)} directions, limiting to top 5 by importance"
                )
                result.directions = sorted(
                    result.directions,
                    key=lambda d: d.importance,
                    reverse=True
                )[:5]

            # Log only if consensus/contradictions present
            consensus_count = len(result.consensus_directions) if result.consensus_directions else 0
            contradictions_count = len(result.contradictions) if result.contradictions else 0
            logger.info(
                f"Lead LLM extracted {len(result.directions)} directions"
                + (f", {consensus_count} consensus" if consensus_count else "")
                + (f", {contradictions_count} contradictions" if contradictions_count else "")
            )

            return result

        except (json.JSONDecodeError, KeyError, ValueError) as e:
            logger.error(f"Failed to parse Lead LLM synthesis: {e}")
            logger.error(f"Raw response: {raw_text[:500]}")

            # Fallback
            return DirectionSynthesis(
                directions=[
                    Direction(
                        claim=f"Continue investigating: {target_node.claim}",
                        description=(
                            "This fallback direction is intentionally comprehensive because synthesis output "
                            "failed schema validation. The next cycle should restate the target direction and "
                            "define the operational question to be answered, including how the answer will alter "
                            "decisions in the project roadmap. Build a structured evidence plan with independent "
                            "sources across primary data, reputable secondary analysis, and recent market signals. "
                            "Explicitly track assumptions, then test the highest-impact assumptions first using "
                            "queries designed to disconfirm weak narratives rather than reinforce prior beliefs. "
                            "Require quantitative support where possible, including ranges and source dates, and "
                            "separate descriptive facts from strategic implications so downstream synthesis can "
                            "evaluate confidence correctly. When evidence conflicts, categorize each conflict by "
                            "scope, geography, cohort, or timeframe, and specify follow-up checks needed to close "
                            "those gaps. The cycle output should finish with concrete next actions: what branch "
                            "to deepen, what branch to challenge, and what threshold of corroboration is required "
                            "before upgrading confidence or importance for this direction."
                        ),
                        confidence=0.5,
                        importance=0.7,
                        reasoning=f"Fallback direction (synthesis parse error: {e})",
                        stance="mixed",
                        direction_outcome="pursue",
                    )
                ],
                synthesis_reasoning=f"Synthesis parse error: {e}. Research agents completed investigation but output could not be parsed.",
            )

    async def reassess_target_direction(
        self,
        target_node: KnowledgeNode,
        agent_outputs: list[AgentOutput],
        synthesis: DirectionSynthesis,
    ) -> TargetReassessment:
        """
        Reassess target direction confidence/importance after new research.

        This is a pure LLM judgment step. No heuristic blending is applied.
        """
        logger.info(f"Lead LLM reassessing target direction {target_node.id[:8]}...")

        # Keep prompt compact but informative.
        agent_summaries: list[str] = []
        for i, output in enumerate(agent_outputs, 1):
            raw_excerpt = output.raw_text[:1400]
            critique_excerpt = output.self_critique[:400] if output.self_critique else ""
            agent_summaries.append(
                f"## Agent {i}: {output.agent_name}\n"
                f"- Searches: {len(output.searches_performed)}\n"
                f"- Cost: ${output.cost_usd:.4f}\n"
                f"- Raw excerpt:\n{raw_excerpt}\n\n"
                f"- Self-critique:\n{critique_excerpt}\n"
            )

        directions_preview = "\n".join(
            [
                f"- {d.claim} (conf={d.confidence:.2f}, imp={d.importance:.2f})"
                for d in synthesis.directions[:12]
            ]
        )
        # Handle optional consensus_directions and contradictions (Phase 1 simplifications)
        if synthesis.consensus_directions:
            consensus_preview = "\n".join(f"- {c}" for c in synthesis.consensus_directions[:10])
        else:
            consensus_preview = "- none (see synthesis_reasoning for consensus info)"

        if synthesis.contradictions:
            contradiction_preview = "\n".join(f"- {c}" for c in synthesis.contradictions[:10])
        else:
            contradiction_preview = "- none (see synthesis_reasoning for contradiction info)"

        system_prompt = f"""You are the Lead LLM for this research mission:

{self.north_star}

You must reassess ONE target direction after a completed research cycle.

Rules:
- Use only the provided cycle evidence and synthesis.
- Provide direct judgment (no averaging formula, no blending instructions).
- Keep scores in [0.0, 1.0].
- Confidence reflects how strongly the direction is now validated.
- Importance reflects strategic relevance to the mission now.
- Choose exactly ONE strategic action for this target:
  - diverge: keep this direction active and branch into additional related directions
  - deepen: keep this direction active and continue focused investigation on this same path
  - close: this path is a dead end or sufficiently concluded for now; mark as completed
- Decide lifecycle status:
  - active: continue investing (for `diverge` or `deepen`)
  - completed: sufficiently answered / dead end for now (for `close`)
  - closed: not viable / low strategic value now

Return ONLY JSON:
{{
  "action": "diverge|deepen|close",
  "confidence": 0.0,
  "importance": 0.0,
  "status": "active|completed|closed",
  "reasoning": "2-4 sentences justifying the chosen action and updated scores."
}}"""

        agent_evidence_summary = "\n\n".join(agent_summaries)

        user_prompt = f"""## Target Direction
- ID: {target_node.id}
- Claim: {target_node.claim}
- Previous confidence: {target_node.confidence:.2f}
- Previous importance: {target_node.importance:.2f}

## Synthesized Directions From This Cycle
{directions_preview if directions_preview else "- none"}

## Consensus
{consensus_preview}

## Contradictions
{contradiction_preview}

## Agent Evidence Summary
{agent_evidence_summary}

Reassess the target direction and return ONLY the JSON schema.
You must choose one action: diverge, deepen, or close."""

        output = await self.adapter.run(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            tools=[],
            max_iterations=1,
        )

        import json
        import re

        raw_text = output.raw_text.strip()
        json_match = re.search(r"\{.*\"confidence\".*\"importance\".*\}", raw_text, re.DOTALL)

        if not json_match:
            logger.warning("Target reassessment response not valid JSON; keeping existing scores")
            return TargetReassessment(
                confidence=target_node.confidence,
                importance=target_node.importance,
                status=target_node.status,
                reasoning="Reassessment parse failed; retained previous scores.",
                cost_usd=output.cost_usd,
            )

        try:
            data = json.loads(json_match.group())
            action = str(data.get("action", "")).strip().lower()
            confidence = float(data["confidence"])
            importance = float(data["importance"])
            status = str(data.get("status", target_node.status)).strip().lower()
            reasoning = str(data.get("reasoning", "")).strip()

            # Hard bounds for data integrity only (not heuristic scoring logic).
            confidence = max(0.0, min(1.0, confidence))
            importance = max(0.0, min(1.0, importance))
            if action == "close":
                # Explicit policy: dead-end/closed action maps to completed lifecycle state.
                status = "completed"
            if status not in {"active", "completed", "closed"}:
                status = target_node.status

            return TargetReassessment(
                confidence=confidence,
                importance=importance,
                status=status,
                reasoning=reasoning,
                cost_usd=output.cost_usd,
            )
        except (json.JSONDecodeError, KeyError, ValueError) as e:
            logger.warning(f"Failed to parse target reassessment JSON: {e}")
            return TargetReassessment(
                confidence=target_node.confidence,
                importance=target_node.importance,
                status=target_node.status,
                reasoning=f"Reassessment parse error: {e}; retained previous scores.",
                cost_usd=output.cost_usd,
            )
