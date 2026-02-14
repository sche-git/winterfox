"""
Tests for hypothesis-aware confidence propagation.

Verifies that nodes with node_type="hypothesis" use the
supporting/opposing ratio formula, while legacy nodes use
the default propagation.
"""

import pytest
import pytest_asyncio

from winterfox.graph.models import KnowledgeNode
from winterfox.graph.propagation import (
    _recalculate_hypothesis_confidence,
    propagate_confidence_upward,
)
from winterfox.graph.store import KnowledgeGraph


@pytest_asyncio.fixture
async def graph():
    """Create an in-memory graph for testing."""
    g = KnowledgeGraph(":memory:", workspace_id="test")
    await g.initialize()

    async with g._get_db() as db:
        await db.execute(
            "INSERT OR IGNORE INTO workspaces (id, name, tier) VALUES (?, ?, ?)",
            ("test", "Test Workspace", "free"),
        )
        await db.commit()

    yield g
    await g.close()


# --- Unit tests for _recalculate_hypothesis_confidence ---


def _make_child(node_type: str, confidence: float) -> KnowledgeNode:
    """Helper to create a minimal child node."""
    return KnowledgeNode(
        claim="test",
        node_type=node_type,
        confidence=confidence,
        created_by_cycle=1,
        updated_by_cycle=1,
    )


class TestHypothesisConfidence:
    """Tests for the pure _recalculate_hypothesis_confidence function."""

    def test_all_supporting(self):
        """All supporting evidence → confidence near 1.0."""
        children = [
            _make_child("supporting", 0.8),
            _make_child("supporting", 0.7),
            _make_child("supporting", 0.9),
        ]
        result = _recalculate_hypothesis_confidence(children)
        assert result is not None
        assert result >= 0.9  # Clamped to max 0.95

    def test_all_opposing(self):
        """All opposing evidence → confidence near 0.0."""
        children = [
            _make_child("opposing", 0.8),
            _make_child("opposing", 0.7),
        ]
        result = _recalculate_hypothesis_confidence(children)
        assert result is not None
        assert result <= 0.1  # Close to minimum

    def test_mixed_equal(self):
        """Equal supporting and opposing → confidence ≈ 0.5."""
        children = [
            _make_child("supporting", 0.8),
            _make_child("opposing", 0.8),
        ]
        result = _recalculate_hypothesis_confidence(children)
        assert result is not None
        assert 0.45 <= result <= 0.55

    def test_weighted_by_confidence(self):
        """High-confidence opposing outweighs low-confidence supporting."""
        children = [
            _make_child("supporting", 0.3),  # Weak support
            _make_child("opposing", 0.9),  # Strong opposition
        ]
        result = _recalculate_hypothesis_confidence(children)
        assert result is not None
        assert result < 0.35  # Opposing dominates

    def test_no_typed_children_returns_none(self):
        """If no children have supporting/opposing type, returns None (fallback)."""
        children = [
            _make_child("hypothesis", 0.5),  # Not supporting/opposing
            KnowledgeNode(
                claim="legacy",
                confidence=0.6,
                created_by_cycle=1,
                updated_by_cycle=1,
            ),  # node_type=None
        ]
        result = _recalculate_hypothesis_confidence(children)
        assert result is None

    def test_clamped_to_range(self):
        """Result is always in [0.05, 0.95]."""
        # All strong support
        children = [_make_child("supporting", 1.0)]
        result = _recalculate_hypothesis_confidence(children)
        assert result == 0.95

        # All strong opposition
        children = [_make_child("opposing", 1.0)]
        result = _recalculate_hypothesis_confidence(children)
        assert result == 0.05

    def test_mixed_with_untyped_children(self):
        """Untyped children are ignored in hypothesis calculation."""
        children = [
            _make_child("supporting", 0.8),
            _make_child("opposing", 0.2),
            KnowledgeNode(
                claim="untyped",
                confidence=0.9,
                created_by_cycle=1,
                updated_by_cycle=1,
            ),
        ]
        result = _recalculate_hypothesis_confidence(children)
        assert result is not None
        assert result > 0.7  # Supporting dominates (0.8 vs 0.2)


# --- Integration tests with full graph ---


@pytest.mark.asyncio
async def test_legacy_nodes_unchanged(graph):
    """Nodes with node_type=None use the default propagation (not hypothesis)."""
    parent = await graph.add_node(
        claim="Legacy parent",
        confidence=0.0,
        created_by_cycle=1,
    )

    child1 = await graph.add_node(
        claim="Child 1",
        parent_id=parent.id,
        confidence=0.8,
        created_by_cycle=1,
    )

    child2 = await graph.add_node(
        claim="Child 2",
        parent_id=parent.id,
        confidence=0.6,
        created_by_cycle=1,
    )

    # Propagate
    await propagate_confidence_upward(graph, child1.id)

    # Verify parent uses default formula (weighted average), not hypothesis formula
    updated_parent = await graph.get_node(parent.id)
    assert updated_parent is not None
    assert updated_parent.node_type is None
    # Should be non-zero since children have confidence
    assert updated_parent.confidence > 0


@pytest.mark.asyncio
async def test_hypothesis_propagation_integration(graph):
    """Hypothesis node confidence reflects support/oppose ratio."""
    from winterfox.graph.models import Evidence as GraphEvidence

    hypothesis = await graph.add_node(
        claim="Build insurance agent",
        confidence=0.5,
        node_type="hypothesis",
        created_by_cycle=1,
    )

    # Add supporting evidence (with graph Evidence so propagation doesn't wipe conf)
    supporting = await graph.add_node(
        claim="TAM is $50B",
        parent_id=hypothesis.id,
        confidence=0.8,
        node_type="supporting",
        created_by_cycle=1,
        evidence=[GraphEvidence(text="McKinsey report", source="https://mckinsey.com")],
    )

    # Propagate from the hypothesis node directly (recalculates it from children)
    await propagate_confidence_upward(graph, hypothesis.id)

    updated = await graph.get_node(hypothesis.id)
    assert updated is not None
    # Supporting child has evidence → its conf stays ~0.7 from evidence_to_confidence
    # Hypothesis formula: supporting / (supporting + opposing) = 1.0 → clamped to 0.95
    assert updated.confidence >= 0.8  # Only supporting → high confidence

    # Now add opposing evidence
    opposing = await graph.add_node(
        claim="Regulatory barriers too high",
        parent_id=hypothesis.id,
        confidence=0.9,
        node_type="opposing",
        created_by_cycle=2,
        evidence=[
            GraphEvidence(text="FDA report", source="https://fda.gov"),
            GraphEvidence(text="Industry analysis", source="https://analysis.com"),
        ],
    )

    # Propagate from hypothesis (recalculates from both children)
    await propagate_confidence_upward(graph, hypothesis.id)

    updated = await graph.get_node(hypothesis.id)
    assert updated is not None
    # Now have both supporting and opposing evidence
    # Hypothesis confidence should reflect the ratio
    assert updated.confidence < 0.7  # Strong opposition pulls it down
