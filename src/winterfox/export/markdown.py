"""
Markdown export for knowledge graphs.

Produces human-readable nested markdown with:
- Hierarchical structure
- Evidence citations
- Confidence indicators
- Metadata summary
"""

from datetime import datetime
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..graph.models import Evidence, KnowledgeNode
    from ..graph.store import KnowledgeGraph


def _format_confidence(confidence: float) -> str:
    """Format confidence as colored indicator."""
    if confidence >= 0.8:
        return f"✓ {confidence:.0%}"
    elif confidence >= 0.6:
        return f"• {confidence:.0%}"
    elif confidence >= 0.4:
        return f"⚠️ {confidence:.0%}"
    else:
        return f"🔴 {confidence:.0%}"


def _format_evidence(evidence: "Evidence", index: int) -> str:
    """Format single evidence citation."""
    # Extract date if available
    date_str = ""
    if evidence.date:
        date_str = f" ({evidence.date.strftime('%Y-%m-%d')})"

    return f"{index}. **{evidence.source}**{date_str}: {evidence.text}"


def _format_node_markdown(
    node: "KnowledgeNode",
    depth: int = 0,
    include_evidence: bool = True,
) -> str:
    """
    Format a single node as markdown.

    Args:
        node: Node to format
        depth: Nesting depth (for indentation)
        include_evidence: Include evidence citations

    Returns:
        Markdown string
    """
    indent = "  " * depth
    marker = "#" * min(depth + 2, 6)  # H2-H6

    # Header with confidence
    confidence_str = _format_confidence(node.confidence)
    lines = [f"{indent}{marker} {node.claim} {confidence_str}\n"]

    # Metadata
    metadata_parts = []
    if node.importance > 0.7:
        metadata_parts.append(f"**Important** ({node.importance:.0%})")
    if node.depth > 0:
        metadata_parts.append(f"Researched {node.depth} cycle{'s' if node.depth != 1 else ''}")
    if node.tags:
        metadata_parts.append(f"Tags: {', '.join(node.tags)}")

    if metadata_parts:
        lines.append(f"{indent}*{' | '.join(metadata_parts)}*\n\n")

    # Evidence
    if include_evidence and node.evidence:
        lines.append(f"{indent}**Evidence:**\n")
        for i, evidence in enumerate(node.evidence, 1):
            lines.append(f"{indent}{_format_evidence(evidence, i)}\n")
        lines.append("\n")

    return "".join(lines)


async def _export_subtree_markdown(
    graph: "KnowledgeGraph",
    node_id: str,
    depth: int = 0,
    max_depth: int = 10,
    include_evidence: bool = True,
) -> str:
    """
    Recursively export a node and its children as markdown.

    Args:
        graph: Knowledge graph
        node_id: Root node ID
        depth: Current depth
        max_depth: Maximum recursion depth
        include_evidence: Include evidence citations

    Returns:
        Markdown string
    """
    if depth >= max_depth:
        return ""

    # Get node
    node = await graph.get_node(node_id)
    if not node:
        return ""

    # Format this node
    lines = [_format_node_markdown(node, depth, include_evidence)]

    # Recursively format children
    children = await graph.get_children(node_id)
    for child in children:
        child_markdown = await _export_subtree_markdown(
            graph, child.id, depth + 1, max_depth, include_evidence
        )
        lines.append(child_markdown)

    return "".join(lines)


async def export_to_markdown(
    graph: "KnowledgeGraph",
    output_path: str,
    title: str | None = None,
    include_metadata: bool = True,
    include_evidence: bool = True,
    max_depth: int = 10,
) -> None:
    """
    Export knowledge graph to markdown file.

    Args:
        graph: Knowledge graph to export
        output_path: Output file path
        title: Document title (defaults to "Knowledge Graph")
        include_metadata: Include summary metadata at top
        include_evidence: Include evidence citations
        max_depth: Maximum nesting depth

    Example output:
        # Market Research Knowledge Graph

        **Summary**
        - Total nodes: 47
        - Average confidence: 72%
        - Last updated: 2024-01-15

        ## Market Opportunity ✓ 82%
        *Important (90%) | Researched 5 cycles*

        **Evidence:**
        1. **McKinsey Report** (2023-12-01): Legal tech market projected...

        ### Legal Tech TAM ✓ 88%
        ...
    """
    from pathlib import Path

    output_file = Path(output_path)

    # Document header
    doc_title = title or "Knowledge Graph"
    lines = [f"# {doc_title}\n\n"]

    # Metadata summary
    if include_metadata:
        nodes = await graph.get_all_active_nodes()
        total_nodes = len(nodes)
        avg_confidence = sum(n.confidence for n in nodes) / total_nodes if total_nodes else 0
        low_confidence = sum(1 for n in nodes if n.confidence < 0.5)

        lines.append("**Summary**\n")
        lines.append(f"- Total nodes: {total_nodes}\n")
        lines.append(f"- Average confidence: {avg_confidence:.0%}\n")
        lines.append(f"- Low confidence nodes: {low_confidence}\n")
        lines.append(f"- Exported: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        lines.append("---\n\n")

    # Export all root nodes and their subtrees
    roots = await graph.get_root_nodes()
    for root in roots:
        root_markdown = await _export_subtree_markdown(
            graph, root.id, depth=0, max_depth=max_depth, include_evidence=include_evidence
        )
        lines.append(root_markdown)
        lines.append("\n")

    # Write to file
    output_file.parent.mkdir(parents=True, exist_ok=True)
    output_file.write_text("".join(lines), encoding="utf-8")


async def export_node_to_markdown(
    graph: "KnowledgeGraph",
    node_id: str,
    output_path: str,
    include_evidence: bool = True,
    max_depth: int = 5,
) -> None:
    """
    Export a specific node and its subtree to markdown.

    Args:
        graph: Knowledge graph
        node_id: Root node ID to export
        output_path: Output file path
        include_evidence: Include evidence citations
        max_depth: Maximum depth for children
    """
    from pathlib import Path

    output_file = Path(output_path)

    # Get node
    node = await graph.get_node(node_id)
    if not node:
        raise ValueError(f"Node not found: {node_id}")

    # Export subtree
    markdown = await _export_subtree_markdown(
        graph, node_id, depth=0, max_depth=max_depth, include_evidence=include_evidence
    )

    # Write to file
    output_file.parent.mkdir(parents=True, exist_ok=True)
    output_file.write_text(markdown, encoding="utf-8")
