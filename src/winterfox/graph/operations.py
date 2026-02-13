"""
Graph operations for merging, deduplicating, and restructuring nodes.

These operations are critical for knowledge compounding:
- Merge: Combine redundant nodes
- Deduplicate: Find and merge similar claims
- Reparent: Move nodes in the tree
"""

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .models import KnowledgeNode
    from .store import KnowledgeGraph

logger = logging.getLogger(__name__)


def calculate_claim_similarity(claim1: str, claim2: str) -> float:
    """
    Calculate similarity between two claims using Jaccard similarity.

    This is a simple token-based similarity measure.
    For production, consider using semantic embeddings.

    Args:
        claim1: First claim
        claim2: Second claim

    Returns:
        Similarity score [0.0, 1.0]
    """
    # Tokenize (simple whitespace split, lowercase)
    tokens1 = set(claim1.lower().split())
    tokens2 = set(claim2.lower().split())

    if not tokens1 or not tokens2:
        return 0.0

    # Jaccard similarity: intersection / union
    intersection = tokens1 & tokens2
    union = tokens1 | tokens2

    return len(intersection) / len(union)


async def find_similar_nodes(
    graph: "KnowledgeGraph",
    claim: str,
    parent_id: str | None = None,
    threshold: float = 0.75,
    limit: int = 5,
) -> list[tuple[float, "KnowledgeNode"]]:
    """
    Find nodes with similar claims.

    Args:
        graph: The knowledge graph
        claim: Claim to match against
        parent_id: Optional parent ID to restrict search to siblings
        threshold: Minimum similarity score
        limit: Maximum results to return

    Returns:
        List of (similarity_score, node) tuples, sorted by similarity
    """
    # Get candidate nodes
    if parent_id:
        # Only check siblings (same parent)
        candidates = await graph.get_children(parent_id)
    else:
        # Check all active nodes
        candidates = await graph.get_all_active_nodes()

    # Calculate similarities
    similar = []
    for node in candidates:
        similarity = calculate_claim_similarity(claim, node.claim)
        if similarity >= threshold:
            similar.append((similarity, node))

    # Sort by similarity (descending)
    similar.sort(reverse=True, key=lambda x: x[0])

    return similar[:limit]


async def merge_nodes(
    graph: "KnowledgeGraph",
    node_ids: list[str],
    merged_claim: str,
    cycle_id: int,
) -> "KnowledgeNode":
    """
    Merge multiple nodes into a single node.

    This combines evidence from all nodes and marks the originals as merged.

    Args:
        graph: The knowledge graph
        node_ids: List of node IDs to merge
        merged_claim: The claim for the merged node
        cycle_id: Current cycle ID

    Returns:
        The new merged node
    """
    if len(node_ids) < 2:
        raise ValueError("Must provide at least 2 nodes to merge")

    # Get all nodes
    nodes = []
    for node_id in node_ids:
        node = await graph.get_node(node_id)
        if node:
            nodes.append(node)

    if not nodes:
        raise ValueError("No valid nodes found to merge")

    # Use the first node as base
    base_node = nodes[0]

    # Combine evidence from all nodes
    all_evidence = []
    all_sources = []
    for node in nodes:
        all_evidence.extend(node.evidence)
        all_sources.extend(node.sources)

    # Calculate merged confidence (independent confirmation model)
    from .propagation import evidence_to_confidence

    merged_confidence = evidence_to_confidence(all_evidence)

    # Take highest importance
    merged_importance = max(node.importance for node in nodes)

    # Take maximum depth
    merged_depth = max(node.depth for node in nodes)

    # Create new merged node
    merged_node = await graph.add_node(
        claim=merged_claim,
        parent_id=base_node.parent_id,
        confidence=merged_confidence,
        importance=merged_importance,
        depth=merged_depth,
        created_by_cycle=cycle_id,
        evidence=all_evidence,
        sources=list(set(all_sources)),  # Deduplicate sources
        tags=["merged"] + base_node.tags,
    )

    # Transfer all children to merged node
    for node in nodes:
        for child_id in node.children_ids:
            await reparent_node(graph, child_id, merged_node.id, cycle_id)

    # Mark original nodes as merged
    for node in nodes:
        await graph.kill_node(
            node.id,
            f"merged_into:{merged_node.id}",
            cycle_id,
        )

    logger.info(
        f"Merged {len(nodes)} nodes into {merged_node.id}: {merged_claim[:50]}..."
    )

    return merged_node


async def deduplicate_children(
    graph: "KnowledgeGraph",
    parent_id: str,
    cycle_id: int,
    similarity_threshold: float = 0.85,
) -> int:
    """
    Find and merge duplicate children of a node.

    Args:
        graph: The knowledge graph
        parent_id: Parent node ID
        cycle_id: Current cycle ID
        similarity_threshold: Minimum similarity to consider duplicate

    Returns:
        Number of nodes merged
    """
    children = await graph.get_children(parent_id)

    if len(children) < 2:
        return 0

    merged_count = 0
    processed = set()

    for i, child1 in enumerate(children):
        if child1.id in processed:
            continue

        # Find similar children
        duplicates = []
        for j, child2 in enumerate(children[i + 1:], start=i + 1):
            if child2.id in processed:
                continue

            similarity = calculate_claim_similarity(child1.claim, child2.claim)
            if similarity >= similarity_threshold:
                duplicates.append(child2)

        if duplicates:
            # Merge child1 with all its duplicates
            to_merge = [child1.id] + [dup.id for dup in duplicates]

            # Use the longest claim as the merged claim
            claims = [child1.claim] + [dup.claim for dup in duplicates]
            merged_claim = max(claims, key=len)

            merged_node = await merge_nodes(graph, to_merge, merged_claim, cycle_id)

            # Mark all as processed
            processed.add(child1.id)
            for dup in duplicates:
                processed.add(dup.id)

            merged_count += len(duplicates)

            logger.info(
                f"Dedup: Merged {len(duplicates) + 1} similar children under {parent_id}"
            )

    return merged_count


async def reparent_node(
    graph: "KnowledgeGraph",
    node_id: str,
    new_parent_id: str,
    cycle_id: int,
) -> None:
    """
    Move a node to a new parent.

    Args:
        graph: The knowledge graph
        node_id: Node to move
        new_parent_id: New parent ID
        cycle_id: Current cycle ID
    """
    node = await graph.get_node(node_id)
    if not node:
        raise ValueError(f"Node {node_id} not found")

    old_parent_id = node.parent_id

    # Remove from old parent's children
    if old_parent_id:
        old_parent = await graph.get_node(old_parent_id)
        if old_parent and node_id in old_parent.children_ids:
            old_parent.children_ids.remove(node_id)
            await graph.update_node(old_parent)

    # Update node's parent
    node.parent_id = new_parent_id
    node.updated_by_cycle = cycle_id
    await graph.update_node(node)

    # Add to new parent's children
    new_parent = await graph.get_node(new_parent_id)
    if new_parent:
        new_parent.add_child(node_id)
        await graph.update_node(new_parent)

    logger.info(
        f"Reparented {node_id} from {old_parent_id} to {new_parent_id}"
    )


async def split_node(
    graph: "KnowledgeGraph",
    node_id: str,
    sub_claims: list[str],
    cycle_id: int,
) -> list["KnowledgeNode"]:
    """
    Split a complex node into multiple sub-nodes.

    The original node becomes the parent, and sub-claims become children.

    Args:
        graph: The knowledge graph
        node_id: Node to split
        sub_claims: List of sub-claims to create
        cycle_id: Current cycle ID

    Returns:
        List of new child nodes
    """
    node = await graph.get_node(node_id)
    if not node:
        raise ValueError(f"Node {node_id} not found")

    # Create child nodes for each sub-claim
    new_nodes = []
    for sub_claim in sub_claims:
        child = await graph.add_node(
            claim=sub_claim,
            parent_id=node_id,
            confidence=node.confidence,  # Inherit parent confidence initially
            importance=node.importance,
            depth=node.depth,
            created_by_cycle=cycle_id,
            tags=node.tags + ["split-from-parent"],
        )
        new_nodes.append(child)

    # Update parent
    node.updated_by_cycle = cycle_id
    node.tags.append("split-into-children")
    await graph.update_node(node)

    logger.info(
        f"Split {node_id} into {len(new_nodes)} children"
    )

    return new_nodes


async def find_contradictions(
    graph: "KnowledgeGraph",
    parent_id: str | None = None,
) -> list[tuple["KnowledgeNode", "KnowledgeNode"]]:
    """
    Find nodes with contradictory claims.

    This uses simple heuristics:
    - Claims with opposite words (not, no, vs yes)
    - Claims about same topic with different values

    For production, use semantic similarity to detect contradictions.

    Args:
        graph: The knowledge graph
        parent_id: Optional parent to restrict search to siblings

    Returns:
        List of (node1, node2) contradiction pairs
    """
    # Get candidate nodes
    if parent_id:
        nodes = await graph.get_children(parent_id)
    else:
        nodes = await graph.get_all_active_nodes()

    contradictions = []

    for i, node1 in enumerate(nodes):
        for node2 in nodes[i + 1:]:
            if _is_contradiction(node1.claim, node2.claim):
                contradictions.append((node1, node2))

    return contradictions


def _is_contradiction(claim1: str, claim2: str) -> bool:
    """
    Simple heuristic to detect contradictions.

    Looks for:
    - One claim has "not" or "no", the other doesn't
    - Same topic but different numeric values

    Args:
        claim1: First claim
        claim2: Second claim

    Returns:
        True if likely contradiction
    """
    claim1_lower = claim1.lower()
    claim2_lower = claim2.lower()

    # Check for negation differences
    negations = ["not", "no", "never", "none", "doesn't", "don't", "isn't", "aren't"]

    has_negation_1 = any(neg in claim1_lower for neg in negations)
    has_negation_2 = any(neg in claim2_lower for neg in negations)

    # If one has negation and they're similar otherwise, likely contradiction
    if has_negation_1 != has_negation_2:
        # Check if the rest is similar
        similarity = calculate_claim_similarity(claim1, claim2)
        if similarity > 0.6:
            return True

    return False
