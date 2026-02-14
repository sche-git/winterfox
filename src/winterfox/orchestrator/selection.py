"""
Node selection algorithm for choosing research targets.

Provides two strategies:
1. UCB1-inspired scoring (default fallback)
2. LLM-driven selection with EXPLORE/DEEPEN/CHALLENGE strategies
"""

import json
import logging
import math
import re
from dataclasses import dataclass
from typing import TYPE_CHECKING, Literal

if TYPE_CHECKING:
    from ..agents.protocol import AgentAdapter
    from ..graph.models import KnowledgeNode
    from ..graph.store import KnowledgeGraph

logger = logging.getLogger(__name__)


@dataclass
class SelectionDecision:
    """Result of LLM-driven node selection."""

    strategy: Literal["EXPLORE", "DEEPEN", "CHALLENGE"]
    target_node_id: str | None  # existing node (DEEPEN/CHALLENGE), or parent (EXPLORE)
    reasoning: str
    suggested_question: str | None = None  # new hypothesis text (EXPLORE)


async def select_target_node(
    graph: "KnowledgeGraph",
    last_selected_id: str | None = None,
    importance_weight: float = 0.3,
    uncertainty_weight: float = 0.5,
    exploration_weight: float = 0.2,
) -> "KnowledgeNode | None":
    """
    Select the next node to research using UCB1-inspired scoring.

    Selection score formula:
    score = (uncertainty_weight * (1 - confidence)) +
            (importance_weight * importance) +
            (exploration_weight * staleness_bonus)

    Where staleness_bonus = log(1 + staleness_hours / 24)

    Args:
        graph: Knowledge graph
        last_selected_id: ID of last selected node (to avoid repeats)
        importance_weight: Weight for importance score (default: 0.3)
        uncertainty_weight: Weight for uncertainty (1 - confidence) (default: 0.5)
        exploration_weight: Weight for staleness bonus (default: 0.2)

    Returns:
        Selected node, or None if no candidates
    """
    candidates = await graph.get_all_active_nodes()

    if not candidates:
        logger.warning("No active nodes to research")
        return None

    # Calculate selection scores
    scored_nodes = []

    for node in candidates:
        # Skip recently selected node
        if node.id == last_selected_id:
            continue

        # Calculate components
        uncertainty = 1 - node.confidence
        importance = node.importance
        staleness_factor = math.log(1 + node.staleness_hours / 24)  # Log to dampen
        exploration_bonus = staleness_factor * 0.2  # Scale down

        # Total score
        score = (
            uncertainty_weight * uncertainty
            + importance_weight * importance
            + exploration_weight * exploration_bonus
        )

        scored_nodes.append((score, node))

        logger.debug(
            f"Node {node.id[:8]}... score={score:.3f} "
            f"(uncert={uncertainty:.2f}, imp={importance:.2f}, "
            f"stale={node.staleness_hours:.1f}h)"
        )

    if not scored_nodes:
        # All nodes were filtered out (only last_selected left)
        logger.warning("Only last selected node available, reselecting it")
        return candidates[0] if candidates else None

    # Select highest scoring node
    scored_nodes.sort(reverse=True, key=lambda x: x[0])
    best_score, best_node = scored_nodes[0]

    logger.info(
        f"Selected node {best_node.id[:8]}... for research "
        f"(score={best_score:.3f}, conf={best_node.confidence:.2f})"
    )

    return best_node


async def get_priority_nodes(
    graph: "KnowledgeGraph",
    n: int = 5,
    min_confidence: float = 0.0,
    max_confidence: float = 1.0,
) -> list["KnowledgeNode"]:
    """
    Get top N priority nodes for research.

    Args:
        graph: Knowledge graph
        n: Number of nodes to return
        min_confidence: Minimum confidence filter
        max_confidence: Maximum confidence filter

    Returns:
        List of top priority nodes (sorted by selection score)
    """
    candidates = await graph.get_all_active_nodes()

    # Filter by confidence range
    filtered = [
        node
        for node in candidates
        if min_confidence <= node.confidence <= max_confidence
    ]

    if not filtered:
        return []

    # Score all nodes
    scored_nodes = []
    for node in filtered:
        uncertainty = 1 - node.confidence
        importance = node.importance
        staleness_factor = math.log(1 + node.staleness_hours / 24)
        exploration_bonus = staleness_factor * 0.2

        score = uncertainty * 0.5 + importance * 0.3 + exploration_bonus * 0.2

        scored_nodes.append((score, node))

    # Sort and return top N
    scored_nodes.sort(reverse=True, key=lambda x: x[0])
    return [node for _, node in scored_nodes[:n]]


def _build_selection_prompt(nodes: list["KnowledgeNode"]) -> str:
    """Build a lightweight prompt for LLM-driven selection."""
    lines = ["Current knowledge graph state:\n"]

    # Build compact node summary
    hypotheses = []
    questions = []
    evidence_nodes = []

    for node in nodes:
        nt = node.node_type
        entry = f"  id={node.id[:12]} conf={node.confidence:.2f} children={len(node.children_ids)} \"{node.claim[:80]}\""
        if nt == "hypothesis":
            hypotheses.append(entry)
        elif nt == "question":
            questions.append(entry)
        elif nt in ("supporting", "opposing"):
            evidence_nodes.append(entry)
        else:
            questions.append(entry)  # Legacy nodes treated as questions

    if questions:
        lines.append(f"Questions ({len(questions)}):")
        lines.extend(questions[:10])
    if hypotheses:
        lines.append(f"\nHypotheses ({len(hypotheses)}):")
        lines.extend(hypotheses[:10])
    if evidence_nodes:
        lines.append(f"\nEvidence nodes ({len(evidence_nodes)}):")
        lines.extend(evidence_nodes[:10])

    # Strategy guidance
    lines.append("\n---")
    lines.append("Choose ONE strategy:")
    lines.append("- EXPLORE: Propose a new hypothesis (when few hypotheses exist)")
    lines.append("- DEEPEN: Find more evidence for an existing node (when hypotheses are thin)")
    lines.append("- CHALLENGE: Find counter-evidence for a strong hypothesis (stress-test)")
    lines.append("")
    lines.append('Respond with JSON only:')
    lines.append('{')
    lines.append('  "strategy": "EXPLORE" | "DEEPEN" | "CHALLENGE",')
    lines.append('  "target_node_id": "<id of existing node to focus on>",')
    lines.append('  "reasoning": "<1 sentence why>",')
    lines.append('  "suggested_question": "<new hypothesis text, only for EXPLORE>"')
    lines.append('}')

    return "\n".join(lines)


def _parse_selection_response(raw_text: str) -> SelectionDecision | None:
    """Parse LLM response into SelectionDecision. Returns None on failure."""
    # Try direct JSON parse first
    try:
        data = json.loads(raw_text.strip())
        return _decision_from_dict(data)
    except (json.JSONDecodeError, ValueError):
        pass

    # Try extracting JSON from markdown code blocks or surrounding text
    json_match = re.search(r'\{[^{}]*"strategy"[^{}]*\}', raw_text, re.DOTALL)
    if json_match:
        try:
            data = json.loads(json_match.group())
            return _decision_from_dict(data)
        except (json.JSONDecodeError, ValueError):
            pass

    logger.warning(f"Failed to parse selection response: {raw_text[:200]}")
    return None


def _decision_from_dict(data: dict) -> SelectionDecision:
    """Validate and create SelectionDecision from parsed dict."""
    strategy = data.get("strategy", "").upper()
    if strategy not in ("EXPLORE", "DEEPEN", "CHALLENGE"):
        raise ValueError(f"Invalid strategy: {strategy}")

    return SelectionDecision(
        strategy=strategy,  # type: ignore[arg-type]
        target_node_id=data.get("target_node_id"),
        reasoning=data.get("reasoning", ""),
        suggested_question=data.get("suggested_question"),
    )


async def select_target_with_llm(
    graph: "KnowledgeGraph",
    adapter: "AgentAdapter",
    last_selected_id: str | None = None,
) -> tuple["KnowledgeNode | None", SelectionDecision | None]:
    """
    Use LLM to decide what to research next.

    Falls back to UCB1 selection on any failure.

    Args:
        graph: Knowledge graph
        adapter: LLM adapter for the selection call
        last_selected_id: ID of last selected node

    Returns:
        (target_node, decision) — decision is None when falling back to UCB1
    """
    nodes = await graph.get_all_active_nodes()
    if not nodes:
        return None, None

    # Build prompt and call LLM
    prompt = _build_selection_prompt(nodes)

    try:
        output = await adapter.run(
            system_prompt="You are a research strategist. Respond with JSON only, no explanation.",
            user_prompt=prompt,
            tools=[],
            max_iterations=1,
        )

        decision = _parse_selection_response(output.raw_text)
        if decision is None:
            logger.info("LLM selection parse failed, falling back to UCB1")
            fallback = await select_target_node(graph, last_selected_id)
            return fallback, None

        # Validate target_node_id exists
        if decision.target_node_id:
            # Try full id first, then prefix match
            target = await graph.get_node(decision.target_node_id)
            if target is None:
                # Try prefix match (LLM may return truncated IDs)
                for node in nodes:
                    if node.id.startswith(decision.target_node_id):
                        target = node
                        decision.target_node_id = node.id
                        break

            if target is not None:
                logger.info(
                    f"LLM selected {decision.strategy} on node {target.id[:8]}... "
                    f"Reason: {decision.reasoning}"
                )
                return target, decision

        # For EXPLORE, target the first question/root node
        if decision.strategy == "EXPLORE":
            for node in nodes:
                if node.node_type == "question" or node.parent_id is None:
                    logger.info(
                        f"LLM selected EXPLORE under root {node.id[:8]}... "
                        f"Reason: {decision.reasoning}"
                    )
                    decision.target_node_id = node.id
                    return node, decision

        # If we still haven't found a target, fall back
        logger.info("LLM selection target not found, falling back to UCB1")
        fallback = await select_target_node(graph, last_selected_id)
        return fallback, None

    except Exception as e:
        logger.warning(f"LLM selection failed: {e}, falling back to UCB1")
        fallback = await select_target_node(graph, last_selected_id)
        return fallback, None
