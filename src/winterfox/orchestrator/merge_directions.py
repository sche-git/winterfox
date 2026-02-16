"""
Direction merge logic for integrating Lead LLM synthesis into the knowledge graph.

This is the critical knowledge compounding step for the Lead LLM architecture:
- Merges directions extracted by Lead LLM from raw research outputs
- Deduplicates directions (avoids creating redundant nodes)
- Updates existing directions or creates new ones
- All nodes are "direction" type (unified model)
"""

import logging
from typing import Any
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
) -> dict[str, Any]:
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
        Stats dict with created/updated/skipped counts and node refs
    """
    from ..graph.operations import calculate_claim_similarity

    stats: dict[str, Any] = {
        "created": 0,
        "updated": 0,
        "skipped": 0,
        "direction_node_refs": [],
    }
    target_node = await graph.get_node(target_node_id)
    target_depth = target_node.depth if target_node else 0

    for direction in directions:
        logger.debug(f"Processing direction: {direction.claim[:60]}...")

        # Determine parent and depth based on relationship type
        if direction.relationship_type == "alternative_approach":
            # Make this a SIBLING of the target, not a child
            # Siblings share the same parent and same depth
            if target_node.parent_id is None:
                # Target is root - alternatives become top-level siblings
                actual_parent_id = None
                actual_depth = target_node.depth
            else:
                # Target has a parent - alternatives become siblings under that parent
                actual_parent_id = target_node.parent_id
                actual_depth = target_node.depth

            logger.info(
                f"Direction '{direction.claim[:60]}...' marked as alternative_approach, "
                f"creating as sibling at depth {actual_depth}"
            )
        else:
            # Default: extends_parent - becomes child at depth+1
            actual_parent_id = target_node_id
            actual_depth = target_node.depth + 1

            logger.debug(
                f"Direction '{direction.claim[:60]}...' extends parent, "
                f"creating as child at depth {actual_depth}"
            )

        # Search for similar existing directions under the actual parent (not always target)
        existing_nodes = await _find_similar_directions(
            graph, direction.claim, actual_parent_id, similarity_threshold
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

            old_conf = existing.confidence
            new_conf = direction.confidence * confidence_discount
            if direction.stance == "support":
                # Independent confirmation model: conf = 1 - (1-p1)(1-p2)
                combined = 1 - (1 - old_conf) * (1 - new_conf)
                existing.confidence = min(0.95, combined)
            elif direction.stance == "disconfirm":
                # Penalize confidence when evidence undermines this claim.
                # Stronger disconfirm confidence produces larger reductions.
                penalty = new_conf * 0.8
                existing.confidence = max(0.05, old_conf * (1 - penalty))
            else:
                # Mixed evidence: gentle mean reversion toward new signal.
                existing.confidence = min(0.95, max(0.05, old_conf * 0.8 + new_conf * 0.2))

            logger.debug(
                f"Confidence update ({direction.stance}): "
                f"{old_conf:.2f} with signal {new_conf:.2f} -> {existing.confidence:.2f}"
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
            if direction.direction_outcome == "complete":
                existing.status = "completed"

            await graph.update_node(existing)

            stats["updated"] += 1
            stats["direction_node_refs"].append({
                "claim": direction.claim,
                "node_id": existing.id,
                "action": "updated",
            })

        else:
            # Create new direction
            from ..graph.models import Evidence

            # Convert evidence summary to Evidence object (if present)
            # Note: evidence_summary is deprecated in Phase 1 simplifications
            evidence_list = []
            if direction.evidence_summary:
                evidence_list.append(
                    Evidence(
                        text=direction.evidence_summary,
                        source=f"lead_llm_synthesis_cycle_{cycle_id}",
                        verified_by=[f"lead_llm_cycle_{cycle_id}"],
                    )
                )
            else:
                # For simplified format: create generic evidence entry from cycle
                evidence_list.append(
                    Evidence(
                        text=f"Synthesized from research cycle {cycle_id}. See direction description for details.",
                        source=f"lead_llm_synthesis_cycle_{cycle_id}",
                        verified_by=[f"lead_llm_cycle_{cycle_id}"],
                    )
                )

            # Apply confidence discount (first-time directions are less certain)
            initial_confidence = direction.confidence * confidence_discount

            # Create direction node
            new_node = await graph.add_node(
                claim=direction.claim,
                description=direction.description or None,
                parent_id=actual_parent_id,
                confidence=initial_confidence,
                importance=direction.importance,
                depth=actual_depth,  # Use computed depth based on relationship type
                created_by_cycle=cycle_id,
                evidence=evidence_list,
                tags=direction.tags or [],
                status="completed" if direction.direction_outcome == "complete" else "active",
                node_type="direction",  # All nodes are directions
            )

            logger.info(
                f"Created new direction {new_node.id[:8]}... "
                f"(conf={initial_confidence:.2f}, imp={direction.importance:.2f})"
            )

            stats["created"] += 1
            stats["direction_node_refs"].append({
                "claim": direction.claim,
                "node_id": new_node.id,
                "action": "created",
            })

    logger.info(
        f"Merge complete: {stats['created']} created, {stats['updated']} updated, "
        f"{stats['skipped']} skipped"
    )

    # Add relationship breakdown stats
    stats["relationship_breakdown"] = {
        "extended_parent": sum(1 for d in directions if d.relationship_type == "extends_parent"),
        "alternative_approaches": sum(1 for d in directions if d.relationship_type == "alternative_approach"),
    }

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
