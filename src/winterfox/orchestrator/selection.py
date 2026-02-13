"""
Node selection algorithm for choosing research targets.

Uses UCB1-inspired scoring that balances:
- Uncertainty (low confidence nodes need more research)
- Importance (strategic value)
- Exploration (stale nodes need revisiting)
"""

import logging
import math
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..graph.models import KnowledgeNode
    from ..graph.store import KnowledgeGraph

logger = logging.getLogger(__name__)


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
