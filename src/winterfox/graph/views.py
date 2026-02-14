"""
Token-efficient views of the knowledge graph.

This module provides different views of the graph optimized for token efficiency:
- summary_view: Compact overview of top N levels (~500 tokens for 100 nodes)
- focused_view: Detailed view of a subtree + path to root (for agent context)
"""

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .models import KnowledgeNode
    from .store import KnowledgeGraph

logger = logging.getLogger(__name__)


def _format_confidence(conf: float) -> str:
    """Format confidence score with color indicators."""
    if conf >= 0.8:
        return f"✓ {conf:.2f}"
    elif conf >= 0.6:
        return f"• {conf:.2f}"
    elif conf >= 0.4:
        return f"⚠️  {conf:.2f}"
    else:
        return f"🔴 {conf:.2f}"


def _get_type_indicator(node: "KnowledgeNode") -> str:
    """Get type indicator prefix for hypothesis tree nodes."""
    type_map = {
        "question": "? ",
        "hypothesis": "H ",
        "supporting": "+ ",
        "opposing": "- ",
    }
    return type_map.get(node.node_type, "") if node.node_type else ""


def _get_status_indicator(node: "KnowledgeNode") -> str:
    """Get status indicator for a node."""
    indicators = []

    # Low confidence
    if node.confidence < 0.4:
        indicators.append("LOW CONF")

    # Stale (>72 hours)
    if node.staleness_hours > 72:
        indicators.append(f"STALE ({int(node.staleness_hours / 24)}d)")

    # Shallow (depth < 2)
    if node.depth < 2 and len(node.children_ids) == 0:
        indicators.append("SHALLOW")

    # Disputed (has disputed tag)
    if any("disputed" in tag.lower() for tag in node.tags):
        indicators.append("DISPUTED")

    return " | ".join(indicators) if indicators else ""


async def render_summary_view(
    graph: "KnowledgeGraph",
    max_depth: int = 2,
    max_nodes: int = 50,
) -> str:
    """
    Render a token-efficient summary of the knowledge graph.

    This view shows the top N levels of the tree with critical metadata.
    Target: <500 tokens for 100 nodes.

    Args:
        graph: The knowledge graph
        max_depth: Maximum depth to render (default: 2)
        max_nodes: Maximum nodes to include (default: 50)

    Returns:
        Formatted string representation
    """
    roots = await graph.get_root_nodes()

    if not roots:
        return "📊 Knowledge Graph (Empty)\n\nNo nodes yet. Run a research cycle to get started."

    # Count total nodes
    total_nodes = await graph.count_nodes()

    # Build tree representation
    lines = [
        "📊 Knowledge Graph Summary",
        "=" * 50,
        f"Total Nodes: {total_nodes} | Max Depth: {max_depth}",
        "",
    ]

    nodes_rendered = 0

    for root in roots:
        if nodes_rendered >= max_nodes:
            lines.append(f"... and {total_nodes - nodes_rendered} more nodes")
            break

        await _render_node_tree(graph, root, lines, "", True, max_depth, 0, max_nodes, nodes_rendered)
        nodes_rendered += 1
        lines.append("")  # Blank line between root trees

    return "\n".join(lines)


async def _render_node_tree(
    graph: "KnowledgeGraph",
    node: "KnowledgeNode",
    lines: list[str],
    prefix: str,
    is_last: bool,
    max_depth: int,
    current_depth: int,
    max_nodes: int,
    nodes_rendered: int,
) -> int:
    """Recursively render a node and its children as a tree."""
    # Tree characters
    connector = "└─ " if is_last else "├─ "
    extension = "   " if is_last else "│  "

    # Truncate claim for display
    claim_preview = node.claim[:60] + "..." if len(node.claim) > 60 else node.claim

    # Build node line
    type_indicator = _get_type_indicator(node)
    conf_str = _format_confidence(node.confidence)
    status_str = _get_status_indicator(node)
    status_suffix = f" ({status_str})" if status_str else ""

    node_line = f"{prefix}{connector}{type_indicator}[{claim_preview}] conf:{conf_str} depth:{node.depth} children:{len(node.children_ids)}{status_suffix}"
    lines.append(node_line)

    nodes_rendered += 1

    # Render children if within depth limit
    if current_depth < max_depth and node.children_ids and nodes_rendered < max_nodes:
        children = await graph.get_children(node.id)

        for i, child in enumerate(children):
            if nodes_rendered >= max_nodes:
                break

            is_last_child = i == len(children) - 1
            new_prefix = prefix + extension

            nodes_rendered = await _render_node_tree(
                graph,
                child,
                lines,
                new_prefix,
                is_last_child,
                max_depth,
                current_depth + 1,
                max_nodes,
                nodes_rendered,
            )

    return nodes_rendered


async def render_focused_view(
    graph: "KnowledgeGraph",
    node_id: str,
    max_depth: int = 3,
) -> str:
    """
    Render a focused view of a specific node and its subtree.

    This includes:
    1. Path from node to root (for context)
    2. The target node and all its details
    3. Full subtree under the target node

    This is what agents get when researching a specific area.

    Args:
        graph: The knowledge graph
        node_id: ID of the node to focus on
        max_depth: Maximum depth of subtree to include

    Returns:
        Formatted string representation
    """
    node = await graph.get_node(node_id)
    if not node:
        return f"❌ Node {node_id} not found"

    lines = [
        "🔍 Focused View",
        "=" * 50,
        "",
    ]

    # 1. Path to root (for context)
    path = await _get_path_to_root(graph, node)
    if len(path) > 1:
        lines.append("📍 Context Path (node → root):")
        for i, ancestor in enumerate(path):
            indent = "  " * i
            conf_str = _format_confidence(ancestor.confidence)
            claim_preview = ancestor.claim[:80] + "..." if len(ancestor.claim) > 80 else ancestor.claim
            lines.append(f"{indent}↑ [{claim_preview}] conf:{conf_str}")
        lines.append("")

    # 2. Target node details
    lines.append("🎯 Target Node:")
    lines.append(f"  ID: {node.id}")
    lines.append(f"  Claim: {node.claim}")
    if node.node_type:
        lines.append(f"  Type: {node.node_type}")
    lines.append(f"  Confidence: {_format_confidence(node.confidence)}")
    lines.append(f"  Importance: {node.importance:.2f}")
    lines.append(f"  Depth: {node.depth} cycles")
    lines.append(f"  Status: {node.status}")
    lines.append(f"  Staleness: {node.staleness_hours:.1f} hours")
    lines.append(f"  Children: {len(node.children_ids)}")

    if node.evidence:
        lines.append(f"  Evidence: {len(node.evidence)} items")
        for i, ev in enumerate(node.evidence[:3], 1):  # Show first 3
            lines.append(f"    {i}. {ev.text[:100]}... ({ev.source})")

    if node.tags:
        lines.append(f"  Tags: {', '.join(node.tags)}")

    lines.append("")

    # 3. Subtree
    if node.children_ids:
        lines.append("📂 Subtree:")
        await _render_node_tree(graph, node, lines, "  ", True, max_depth, 0, 100, 0)
    else:
        lines.append("📂 No children yet (leaf node)")

    return "\n".join(lines)


async def _get_path_to_root(
    graph: "KnowledgeGraph",
    node: "KnowledgeNode",
) -> list["KnowledgeNode"]:
    """Get the path from a node to the root."""
    path = [node]
    current = node

    while current.parent_id:
        parent = await graph.get_node(current.parent_id)
        if not parent:
            break
        path.append(parent)
        current = parent

    return path


async def render_weakest_nodes(
    graph: "KnowledgeGraph",
    n: int = 5,
) -> str:
    """
    Render the N weakest nodes (highest priority for next research).

    Selection score = (1 - confidence) * importance * staleness_factor

    Args:
        graph: The knowledge graph
        n: Number of nodes to return

    Returns:
        Formatted string with weakest nodes
    """
    import math

    nodes = await graph.get_all_active_nodes()

    if not nodes:
        return "No active nodes found."

    # Calculate selection scores
    scored_nodes = []
    for node in nodes:
        staleness_factor = math.log(1 + node.staleness_hours / 24)
        exploration_bonus = staleness_factor * 0.2

        score = (
            (1 - node.confidence) * 0.5 +  # Uncertainty
            node.importance * 0.3 +  # Strategic value
            exploration_bonus * 0.2  # Exploration
        )

        scored_nodes.append((score, node))

    # Sort by score (descending)
    scored_nodes.sort(reverse=True, key=lambda x: x[0])

    # Take top N
    top_nodes = scored_nodes[:n]

    lines = [
        f"🎯 Top {n} Priority Nodes for Next Cycle",
        "=" * 50,
        "",
    ]

    for i, (score, node) in enumerate(top_nodes, 1):
        conf_str = _format_confidence(node.confidence)
        claim_preview = node.claim[:70] + "..." if len(node.claim) > 70 else node.claim
        status = _get_status_indicator(node)

        lines.append(f"{i}. Score: {score:.3f}")
        lines.append(f"   {claim_preview}")
        lines.append(f"   Conf: {conf_str} | Imp: {node.importance:.2f} | Depth: {node.depth}")
        if status:
            lines.append(f"   Status: {status}")
        lines.append("")

    return "\n".join(lines)
