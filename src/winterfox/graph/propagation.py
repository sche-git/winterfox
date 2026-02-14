"""
Confidence propagation algorithms for the knowledge graph.

When a node's confidence changes, we need to propagate that change upward
through the tree. This module implements the propagation logic.

Key principle: Parent confidence is weighted average of:
1. Own evidence confidence
2. Children confidence (weighted by number of children)
"""

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .models import KnowledgeNode
    from .store import KnowledgeGraph

logger = logging.getLogger(__name__)


def evidence_to_confidence(evidence_list: list) -> float:
    """
    Calculate confidence from a list of evidence.

    Uses independent confirmation model:
    confidence = 1 - product(1 - e.confidence for e in evidence)

    This gives higher confidence when multiple independent sources confirm.

    Args:
        evidence_list: List of Evidence objects (each has implicit confidence of 0.7)

    Returns:
        Confidence score [0.0, 1.0]
    """
    if not evidence_list:
        return 0.0

    # Each piece of evidence contributes 0.7 confidence (can be parameterized)
    evidence_conf = 0.7

    # Independent confirmation: 1 - product(1 - p_i)
    conf = 1.0
    for _ in evidence_list:
        conf *= (1 - evidence_conf)

    return min(1 - conf, 0.95)  # Cap at 0.95 (nothing is 100% certain)


async def propagate_confidence_upward(
    graph: "KnowledgeGraph",
    node_id: str,
    max_depth: int = 10,
) -> None:
    """
    Propagate confidence changes upward through the tree.

    This recursively updates parent confidence based on:
    1. Parent's own evidence
    2. Mean confidence of all children

    The weighting shifts toward children as more children accumulate.

    Args:
        graph: The knowledge graph
        node_id: Starting node ID
        max_depth: Maximum depth to propagate (prevent infinite loops)
    """
    if max_depth <= 0:
        return

    node = await graph.get_node(node_id)
    if not node:
        return

    # Recalculate this node's confidence
    await _recalculate_node_confidence(graph, node)
    await graph.update_node(node)

    # Recursively update parent
    if node.parent_id:
        await propagate_confidence_upward(graph, node.parent_id, max_depth - 1)


async def _recalculate_node_confidence(
    graph: "KnowledgeGraph",
    node: "KnowledgeNode",
) -> None:
    """
    Recalculate a node's confidence based on evidence and children.

    Dispatches to hypothesis-aware propagation when node_type == "hypothesis".

    Formula (default):
    - If no children: confidence = evidence_confidence
    - If has children:
        child_weight = min(0.7, len(children) / 10)
        own_weight = 1 - child_weight
        confidence = own_weight * evidence_conf + child_weight * children_mean_conf
    """
    # Dispatch to hypothesis-aware propagation when applicable
    if node.node_type == "hypothesis" and node.children_ids:
        children = await graph.get_children(node.id)
        if children:
            result = _recalculate_hypothesis_confidence(children)
            if result is not None:
                node.confidence = result
                logger.debug(
                    f"Hypothesis confidence for {node.id}: {node.confidence:.2f} "
                    f"(support/oppose ratio)"
                )
                return

    # Default propagation for legacy nodes and non-hypothesis types
    # Calculate own confidence from evidence
    own_confidence = evidence_to_confidence(node.evidence)

    # If no children, use own confidence
    if not node.children_ids:
        node.confidence = own_confidence
        return

    # Get children
    children = await graph.get_children(node.id)

    if not children:
        node.confidence = own_confidence
        return

    # Calculate children mean confidence
    children_confidence = sum(child.confidence for child in children) / len(children)

    # Weight toward children as evidence accumulates
    # More children = more weight on children confidence
    child_weight = min(0.7, len(children) / 10.0)
    own_weight = 1 - child_weight

    # Weighted average
    node.confidence = own_weight * own_confidence + child_weight * children_confidence

    logger.debug(
        f"Recalculated confidence for {node.id}: "
        f"own={own_confidence:.2f} (weight={own_weight:.2f}), "
        f"children={children_confidence:.2f} (weight={child_weight:.2f}), "
        f"final={node.confidence:.2f}"
    )


def _recalculate_hypothesis_confidence(
    children: list["KnowledgeNode"],
) -> float | None:
    """
    Calculate hypothesis confidence from supporting vs. opposing evidence.

    Formula:
        supporting_total = sum(child.confidence for supporting children)
        opposing_total = sum(child.confidence for opposing children)
        confidence = supporting_total / (supporting_total + opposing_total)

    Returns None if no typed children exist (falls back to default propagation).
    """
    supporting_total = 0.0
    opposing_total = 0.0

    for child in children:
        if child.node_type == "supporting":
            supporting_total += child.confidence
        elif child.node_type == "opposing":
            opposing_total += child.confidence

    # If no typed children, fall back to default propagation
    if supporting_total == 0.0 and opposing_total == 0.0:
        return None

    # Avoid division by zero: all supporting → 0.95, all opposing → 0.05
    total = supporting_total + opposing_total
    confidence = supporting_total / total

    # Clamp to [0.05, 0.95] — nothing is 100% certain
    return max(0.05, min(0.95, confidence))


async def propagate_confidence_downward(
    graph: "KnowledgeGraph",
    node_id: str,
    max_depth: int = 10,
) -> None:
    """
    Propagate confidence changes downward through the tree.

    This is less common but useful when a parent's confidence changes
    and we want to update all descendants.

    Args:
        graph: The knowledge graph
        node_id: Starting node ID
        max_depth: Maximum depth to propagate
    """
    if max_depth <= 0:
        return

    node = await graph.get_node(node_id)
    if not node:
        return

    # Recalculate this node's confidence
    await _recalculate_node_confidence(graph, node)
    await graph.update_node(node)

    # Recursively update children
    for child_id in node.children_ids:
        await propagate_confidence_downward(graph, child_id, max_depth - 1)


async def recalculate_all_confidence(
    graph: "KnowledgeGraph",
) -> int:
    """
    Recalculate confidence for all nodes in the graph.

    This does a bottom-up traversal (leaves first, then parents).
    Useful after bulk updates or graph restructuring.

    Returns:
        Number of nodes updated
    """
    # Get all active nodes
    nodes = await graph.get_all_active_nodes()

    # Sort by depth (deepest first, so we process leaves before parents)
    nodes_by_depth = {}
    for node in nodes:
        depth = node.depth
        if depth not in nodes_by_depth:
            nodes_by_depth[depth] = []
        nodes_by_depth[depth].append(node)

    # Process from deepest to shallowest
    updated_count = 0
    for depth in sorted(nodes_by_depth.keys(), reverse=True):
        for node in nodes_by_depth[depth]:
            old_conf = node.confidence
            await _recalculate_node_confidence(graph, node)

            if abs(node.confidence - old_conf) > 0.01:  # Only update if significant change
                await graph.update_node(node)
                updated_count += 1
                logger.debug(
                    f"Updated confidence for {node.id}: {old_conf:.2f} → {node.confidence:.2f}"
                )

    logger.info(f"Recalculated confidence for {updated_count} nodes")
    return updated_count


async def boost_confidence(
    graph: "KnowledgeGraph",
    node_id: str,
    boost_factor: float = 0.15,
) -> None:
    """
    Boost a node's confidence (used for consensus agreement).

    When multiple agents independently arrive at the same finding,
    we boost the confidence.

    Args:
        graph: The knowledge graph
        node_id: Node to boost
        boost_factor: Amount to boost (default: 0.15)
    """
    node = await graph.get_node(node_id)
    if not node:
        return

    old_conf = node.confidence
    node.confidence = min(0.95, node.confidence + boost_factor)  # Cap at 0.95

    await graph.update_node(node)

    logger.info(
        f"Boosted confidence for {node.id}: {old_conf:.2f} → {node.confidence:.2f}"
    )

    # Propagate upward
    if node.parent_id:
        await propagate_confidence_upward(graph, node.parent_id)
