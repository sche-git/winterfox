"""
Finding merge logic for integrating agent research into the knowledge graph.

This is the critical knowledge compounding step:
- Deduplicates findings (avoids creating redundant nodes)
- Combines evidence from multiple sources
- Updates existing nodes or creates new ones
- Propagates confidence changes upward
"""

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..agents.protocol import Finding
    from ..graph.models import Evidence, KnowledgeNode
    from ..graph.store import KnowledgeGraph

logger = logging.getLogger(__name__)


async def merge_findings_into_graph(
    graph: "KnowledgeGraph",
    findings: list["Finding"],
    target_node_id: str | None,
    cycle_id: int,
    similarity_threshold: float = 0.75,
    confidence_discount: float = 0.7,
) -> dict[str, int]:
    """
    Merge agent findings into the knowledge graph.

    This performs:
    1. Deduplication check (find similar existing nodes)
    2. Evidence combination (if updating existing node)
    3. Confidence recalculation (independent confirmation model)
    4. New node creation (if no match found)
    5. Confidence propagation upward

    Args:
        graph: Knowledge graph
        findings: List of findings from agents
        target_node_id: ID of node that was researched
        cycle_id: Current cycle ID
        similarity_threshold: Minimum similarity to consider duplicate (0.75)
        confidence_discount: Discount factor for initial confidence (0.7)

    Returns:
        Stats dict with created/updated/skipped counts
    """
    from ..graph.operations import calculate_claim_similarity
    from ..graph.propagation import propagate_confidence_upward

    stats = {
        "created": 0,
        "updated": 0,
        "skipped": 0,
    }

    for finding in findings:
        logger.debug(f"Processing finding: {finding.claim[:60]}...")

        # Search for similar existing nodes
        existing_nodes = await _find_similar_nodes(
            graph, finding.claim, target_node_id, similarity_threshold
        )

        if existing_nodes:
            # Update existing node
            existing = existing_nodes[0]  # Take best match

            logger.info(
                f"Updating existing node {existing.id[:8]}... "
                f"(similarity: {calculate_claim_similarity(finding.claim, existing.claim):.2f})"
            )

            # Add new evidence
            for evidence_dict in finding.evidence:
                from ..graph.models import Evidence

                existing.add_evidence(
                    Evidence(
                        text=evidence_dict.text,
                        source=evidence_dict.source,
                        date=evidence_dict.date,
                    )
                )

            # Recalculate confidence (independent confirmation model)
            # If finding has similar confidence, boost existing
            # If finding contradicts (lower confidence), average them
            from ..graph.propagation import evidence_to_confidence

            evidence_conf = evidence_to_confidence(existing.evidence)

            # Combine finding confidence with evidence confidence
            # Independent confirmation: conf = 1 - (1-p1)(1-p2)
            finding_conf_discounted = finding.confidence * confidence_discount
            combined = 1 - (1 - evidence_conf) * (1 - finding_conf_discounted)

            existing.confidence = min(0.95, combined)  # Cap at 0.95

            # Use longer claim if finding is more detailed
            if len(finding.claim) > len(existing.claim):
                existing.claim = finding.claim

            # Add tags from finding
            for tag in finding.tags:
                if tag not in existing.tags:
                    existing.tags.append(tag)

            # Update cycle tracking
            existing.updated_by_cycle = cycle_id

            await graph.update_node(existing)

            # Propagate confidence upward
            if existing.parent_id:
                await propagate_confidence_upward(graph, existing.parent_id, max_depth=10)

            stats["updated"] += 1

        else:
            # Create new node
            # Determine parent
            parent_id = finding.suggested_parent_id or target_node_id

            # Convert finding evidence to graph evidence
            from ..graph.models import Evidence

            evidence_list = [
                Evidence(
                    text=e.text,
                    source=e.source,
                    date=e.date,
                )
                for e in finding.evidence
            ]

            # Apply confidence discount (first-time findings are less certain)
            initial_confidence = finding.confidence * confidence_discount

            # Create node
            new_node = await graph.add_node(
                claim=finding.claim,
                parent_id=parent_id,
                confidence=initial_confidence,
                importance=0.5,  # Default importance, can be adjusted
                depth=0,  # Will be recalculated
                created_by_cycle=cycle_id,
                evidence=evidence_list,
                tags=finding.tags,
            )

            logger.info(
                f"Created new node {new_node.id[:8]}... "
                f"(conf={initial_confidence:.2f}, parent={parent_id[:8] if parent_id else 'none'}...)"
            )

            # Propagate confidence upward
            if new_node.parent_id:
                await propagate_confidence_upward(graph, new_node.parent_id, max_depth=10)

            stats["created"] += 1

    logger.info(
        f"Merge complete: {stats['created']} created, {stats['updated']} updated, "
        f"{stats['skipped']} skipped"
    )

    return stats


async def _find_similar_nodes(
    graph: "KnowledgeGraph",
    claim: str,
    parent_id: str | None,
    threshold: float,
) -> list["KnowledgeNode"]:
    """
    Find nodes similar to a claim.

    Args:
        graph: Knowledge graph
        claim: Claim to match
        parent_id: Optional parent to restrict search to siblings
        threshold: Minimum similarity threshold

    Returns:
        List of similar nodes (sorted by similarity, best first)
    """
    from ..graph.operations import find_similar_nodes

    similar = await find_similar_nodes(
        graph,
        claim,
        parent_id=parent_id,
        threshold=threshold,
        limit=5,
    )

    # Return just the nodes (not the scores)
    return [node for _, node in similar]


async def merge_and_deduplicate_subtree(
    graph: "KnowledgeGraph",
    parent_id: str,
    cycle_id: int,
    similarity_threshold: float = 0.85,
) -> int:
    """
    Deduplicate children of a node after research cycle.

    This consolidates redundant findings from multiple agents.

    Args:
        graph: Knowledge graph
        parent_id: Parent node ID
        cycle_id: Current cycle ID
        similarity_threshold: Minimum similarity for deduplication

    Returns:
        Number of nodes merged
    """
    from ..graph.operations import deduplicate_children

    merged_count = await deduplicate_children(
        graph,
        parent_id,
        cycle_id,
        similarity_threshold,
    )

    if merged_count > 0:
        logger.info(f"Deduplicated {merged_count} nodes under {parent_id[:8]}...")

    return merged_count
