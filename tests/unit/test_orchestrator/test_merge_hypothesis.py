"""
Tests for hypothesis-aware merge logic.

Verifies:
- finding_type maps to correct node_type on created nodes
- Importance defaults are set by finding type
- Deduplication respects type boundaries (opposing ≠ supporting)
- Backward compatibility (finding_type=None works as before)
"""

import pytest
import pytest_asyncio

from winterfox.agents.protocol import Evidence, Finding
from winterfox.graph.store import KnowledgeGraph
from winterfox.orchestrator.merge import (
    _importance_for_type,
    _node_type_from_finding,
    merge_findings_into_graph,
)


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


def _make_finding(
    claim: str,
    confidence: float = 0.7,
    finding_type: str | None = None,
) -> Finding:
    """Helper to create a Finding with minimal evidence."""
    return Finding(
        claim=claim,
        confidence=confidence,
        evidence=[
            Evidence(
                text="Test evidence",
                source="https://example.com",
            )
        ],
        finding_type=finding_type,
    )


# --- Unit tests for helpers ---


class TestImportanceForType:
    def test_hypothesis(self):
        assert _importance_for_type("hypothesis") == 0.8

    def test_opposing(self):
        assert _importance_for_type("opposing") == 0.7

    def test_supporting(self):
        assert _importance_for_type("supporting") == 0.5

    def test_none(self):
        assert _importance_for_type(None) == 0.5


class TestNodeTypeFromFinding:
    def test_hypothesis(self):
        assert _node_type_from_finding("hypothesis") == "hypothesis"

    def test_supporting(self):
        assert _node_type_from_finding("supporting") == "supporting"

    def test_opposing(self):
        assert _node_type_from_finding("opposing") == "opposing"

    def test_none(self):
        assert _node_type_from_finding(None) is None

    def test_unknown(self):
        assert _node_type_from_finding("random_value") is None


# --- Integration tests ---


@pytest.mark.asyncio
async def test_merge_supporting_finding(graph):
    """A finding with finding_type='supporting' creates a node with node_type='supporting'."""
    parent = await graph.add_node(
        claim="Build insurance agent",
        confidence=0.5,
        node_type="hypothesis",
        created_by_cycle=1,
    )

    finding = _make_finding(
        "TAM is $50B and growing",
        confidence=0.8,
        finding_type="supporting",
    )

    stats = await merge_findings_into_graph(
        graph, [finding], parent.id, cycle_id=2,
    )
    assert stats["created"] == 1

    # Verify the created node has correct type
    children = await graph.get_children(parent.id)
    assert len(children) == 1
    assert children[0].node_type == "supporting"
    assert children[0].importance == 0.5  # supporting default


@pytest.mark.asyncio
async def test_merge_opposing_finding(graph):
    """A finding with finding_type='opposing' creates a node with node_type='opposing'."""
    parent = await graph.add_node(
        claim="Build insurance agent",
        confidence=0.5,
        node_type="hypothesis",
        created_by_cycle=1,
    )

    finding = _make_finding(
        "Regulatory barriers are insurmountable",
        confidence=0.7,
        finding_type="opposing",
    )

    stats = await merge_findings_into_graph(
        graph, [finding], parent.id, cycle_id=2,
    )
    assert stats["created"] == 1

    children = await graph.get_children(parent.id)
    assert len(children) == 1
    assert children[0].node_type == "opposing"
    assert children[0].importance == 0.7  # opposing default


@pytest.mark.asyncio
async def test_merge_hypothesis_finding(graph):
    """A finding with finding_type='hypothesis' creates a node with node_type='hypothesis'."""
    parent = await graph.add_node(
        claim="How to make startup unicorn?",
        confidence=0.0,
        node_type="question",
        created_by_cycle=0,
    )

    finding = _make_finding(
        "Build a hardware company with 60%+ margins",
        confidence=0.6,
        finding_type="hypothesis",
    )

    stats = await merge_findings_into_graph(
        graph, [finding], parent.id, cycle_id=1,
    )
    assert stats["created"] == 1

    children = await graph.get_children(parent.id)
    assert len(children) == 1
    assert children[0].node_type == "hypothesis"
    assert children[0].importance == 0.8  # hypothesis default


@pytest.mark.asyncio
async def test_merge_no_type_backward_compat(graph):
    """A finding with finding_type=None creates a node with node_type=None (backward compat)."""
    parent = await graph.add_node(
        claim="Research topic",
        confidence=0.0,
        created_by_cycle=0,
    )

    finding = _make_finding(
        "The market is growing at 15% CAGR",
        confidence=0.7,
        finding_type=None,
    )

    stats = await merge_findings_into_graph(
        graph, [finding], parent.id, cycle_id=1,
    )
    assert stats["created"] == 1

    children = await graph.get_children(parent.id)
    assert len(children) == 1
    assert children[0].node_type is None
    assert children[0].importance == 0.5  # default


@pytest.mark.asyncio
async def test_dedup_respects_type(graph):
    """Opposing and supporting findings with similar text should NOT merge."""
    parent = await graph.add_node(
        claim="Build insurance agent",
        confidence=0.5,
        node_type="hypothesis",
        created_by_cycle=1,
    )

    # Create an existing supporting node
    await graph.add_node(
        claim="Market opportunity is significant with $50B TAM",
        parent_id=parent.id,
        confidence=0.7,
        node_type="supporting",
        created_by_cycle=1,
    )

    # Now try to merge an opposing finding with similar text
    opposing_finding = _make_finding(
        "Market opportunity is overstated, actual TAM closer to $10B",
        confidence=0.6,
        finding_type="opposing",
    )

    stats = await merge_findings_into_graph(
        graph, [opposing_finding], parent.id, cycle_id=2,
    )

    # Should create a NEW node, not update the existing supporting one
    assert stats["created"] == 1

    children = await graph.get_children(parent.id)
    assert len(children) == 2

    # Verify we have one of each type
    types = {c.node_type for c in children}
    assert "supporting" in types
    assert "opposing" in types
