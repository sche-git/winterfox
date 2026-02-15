"""
Direction merge logic for integrating Lead LLM synthesis into the knowledge graph.

This is the critical knowledge compounding step for the Lead LLM architecture:
- Merges directions extracted by Lead LLM from raw research outputs
- Deduplicates directions (avoids creating redundant nodes)
- Updates existing directions or creates new ones
- All nodes are "direction" type (unified model)
"""

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..graph.models import Evidence, KnowledgeNode
    from ..graph.store import KnowledgeGraph
    from ..orchestrator.lead import Direction

logger = logging.getLogger(__name__)


async def merge_directions_into_graph(
    graph: "KnowledgeGraph",
    directions: list["Direction"],
    target_node_id: str,
    cycle_id: int,
    similarity_threshold: float = 0.75,
    confidence_discount: float = 0.7,
) -> dict[str, int]:
    """
    Merge Lead LLM directions into the knowledge graph.

    This performs:
    1. Deduplication check (find similar existing directions)
    2. Evidence combination (if updating existing direction)
    3. Confidence recalculation (independent confirmation model)
    4. New direction creation (if no match found)

    Note: No type filtering needed - all nodes are directions.
    No confidence propagation - Lead LLM sets confidence autonomously.

    Args:
        graph: Knowledge graph
        directions: List of directions from Lead LLM synthesis
        target_node_id: ID of direction that was researched
        cycle_id: Current cycle ID
        similarity_threshold: Minimum similarity to consider duplicate (0.75)
        confidence_discount: Discount factor for initial confidence (0.7)

    Returns:
        Stats dict with created/updated/skipped counts
    """
    from ..graph.operations import calculate_claim_similarity

    stats = {
        "created": 0,
        "updated": 0,
        "skipped": 0,
    }

    for direction in directions:
        logger.debug(f"Processing direction: {direction.claim[:60]}...")

        # Search for similar existing directions (no type filtering)
        existing_nodes = await _find_similar_directions(
            graph, direction.claim, target_node_id, similarity_threshold
        )

        if existing_nodes:
            # Update existing direction
            existing = existing_nodes[0]  # Take best match

            logger.info(
                f"Updating existing direction {existing.id[:8]}... "
                f"(similarity: {calculate_claim_similarity(direction.claim, existing.claim):.2f})"
            )

            # Add evidence summary from synthesis
            from ..graph.models import Evidence

            existing.add_evidence(
                Evidence(
                    text=direction.evidence_summary,
                    source=f"lead_llm_synthesis_cycle_{cycle_id}",
                    verified_by=[f"lead_llm_cycle_{cycle_id}"],
                )
            )

            # Recalculate confidence (independent confirmation model)
            # conf = 1 - (1-p1)(1-p2)
            old_conf = existing.confidence
            new_conf = direction.confidence * confidence_discount

            combined = 1 - (1 - old_conf) * (1 - new_conf)
            existing.confidence = min(0.95, combined)  # Cap at 0.95

            logger.debug(
                f"Confidence update: {old_conf:.2f} + {new_conf:.2f} = {existing.confidence:.2f}"
            )

            # Use longer claim if new direction is more detailed
            if len(direction.claim) > len(existing.claim):
                existing.claim = direction.claim

            # Keep the richer description so users can read full context in UI.
            if direction.description and (
                not existing.description or len(direction.description) > len(existing.description)
            ):
                existing.description = direction.description

            # Update importance (Lead LLM may have re-evaluated)
            # Take weighted average: 70% existing, 30% new
            existing.importance = existing.importance * 0.7 + direction.importance * 0.3

            # Add tags from direction
            if direction.tags:
                for tag in direction.tags:
                    if tag not in existing.tags:
                        existing.tags.append(tag)

            # Update cycle tracking
            existing.updated_by_cycle = cycle_id

            await graph.update_node(existing)

            stats["updated"] += 1

        else:
            # Create new direction
            from ..graph.models import Evidence

            # Convert evidence summary to Evidence object
            evidence_list = [
                Evidence(
                    text=direction.evidence_summary,
                    source=f"lead_llm_synthesis_cycle_{cycle_id}",
                    verified_by=[f"lead_llm_cycle_{cycle_id}"],
                )
            ]

            # Apply confidence discount (first-time directions are less certain)
            initial_confidence = direction.confidence * confidence_discount

            # Create direction node
            new_node = await graph.add_node(
                claim=direction.claim,
                description=direction.description or None,
                parent_id=target_node_id,
                confidence=initial_confidence,
                importance=direction.importance,
                depth=0,  # Will be recalculated
                created_by_cycle=cycle_id,
                evidence=evidence_list,
                tags=direction.tags or [],
                node_type="direction",  # All nodes are directions
            )

            logger.info(
                f"Created new direction {new_node.id[:8]}... "
                f"(conf={initial_confidence:.2f}, imp={direction.importance:.2f})"
            )

            stats["created"] += 1

    logger.info(
        f"Merge complete: {stats['created']} created, {stats['updated']} updated, "
        f"{stats['skipped']} skipped"
    )

    return stats


async def _find_similar_directions(
    graph: "KnowledgeGraph",
    claim: str,
    parent_id: str | None,
    threshold: float,
) -> list["KnowledgeNode"]:
    """
    Find directions similar to a claim.

    All nodes are directions - no type filtering needed.

    Args:
        graph: Knowledge graph
        claim: Claim to match
        parent_id: Optional parent to restrict search to siblings
        threshold: Minimum similarity threshold

    Returns:
        List of similar directions (sorted by similarity, best first)
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
    # No type filtering - all nodes are directions
    return [node for _, node in similar]


async def deduplicate_directions(
    graph: "KnowledgeGraph",
    parent_id: str,
    cycle_id: int,
    similarity_threshold: float = 0.85,
) -> int:
    """
    Deduplicate child directions after research cycle.

    This consolidates redundant directions from synthesis.

    Args:
        graph: Knowledge graph
        parent_id: Parent direction ID
        cycle_id: Current cycle ID
        similarity_threshold: Minimum similarity for deduplication (higher than merge)

    Returns:
        Number of directions merged
    """
    from ..graph.operations import deduplicate_children

    merged_count = await deduplicate_children(
        graph,
        parent_id,
        cycle_id,
        similarity_threshold,
    )

    if merged_count > 0:
        logger.info(f"Deduplicated {merged_count} directions under {parent_id[:8]}...")

    return merged_count
