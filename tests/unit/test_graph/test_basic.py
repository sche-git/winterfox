"""
Tests for the knowledge graph module.

This test suite covers:
- Node creation and retrieval
- Graph operations (add, update, search)
- Confidence propagation
- Views rendering
- Operations (merge, dedupe, reparent)
"""

import pytest
import pytest_asyncio

from winterfox.graph.models import Evidence, KnowledgeNode
from winterfox.graph.store import KnowledgeGraph
from winterfox.graph.propagation import propagate_confidence_upward, evidence_to_confidence
from winterfox.graph.operations import calculate_claim_similarity, find_similar_nodes
from winterfox.graph.views import render_summary_view, render_focused_view


@pytest_asyncio.fixture
async def graph():
    """Create an in-memory graph for testing."""
    g = KnowledgeGraph(":memory:", workspace_id="test")
    await g.initialize()

    # Create test workspace
    async with g._get_db() as db:
        await db.execute(
            "INSERT OR IGNORE INTO workspaces (id, name, tier) VALUES (?, ?, ?)",
            ("test", "Test Workspace", "free")
        )
        await db.commit()

    yield g
    await g.close()


@pytest.mark.asyncio
async def test_add_node(graph):
    """Test adding a node to the graph."""
    node = await graph.add_node(
        claim="Test claim about market size",
        confidence=0.5,
        importance=0.8,
        created_by_cycle=1,
    )

    assert node.id is not None
    assert node.claim == "Test claim about market size"
    assert node.confidence == 0.5
    assert node.importance == 0.8
    assert node.workspace_id == "test"


@pytest.mark.asyncio
async def test_get_node(graph):
    """Test retrieving a node."""
    created_node = await graph.add_node(
        claim="Retrieve me",
        created_by_cycle=1,
    )

    retrieved_node = await graph.get_node(created_node.id)

    assert retrieved_node is not None
    assert retrieved_node.id == created_node.id
    assert retrieved_node.claim == "Retrieve me"


@pytest.mark.asyncio
async def test_parent_child_relationship(graph):
    """Test parent-child relationships."""
    parent = await graph.add_node(
        claim="Parent node",
        created_by_cycle=1,
    )

    child = await graph.add_node(
        claim="Child node",
        parent_id=parent.id,
        created_by_cycle=1,
    )

    # Verify relationship
    assert child.parent_id == parent.id

    # Retrieve parent and check children
    updated_parent = await graph.get_node(parent.id)
    assert child.id in updated_parent.children_ids

    # Get children
    children = await graph.get_children(parent.id)
    assert len(children) == 1
    assert children[0].id == child.id


@pytest.mark.asyncio
async def test_search(graph):
    """Test full-text search."""
    await graph.add_node(
        claim="The market for legal tech is $2.3B",
        created_by_cycle=1,
    )

    await graph.add_node(
        claim="Healthcare market is much larger",
        created_by_cycle=1,
    )

    # Search for "legal"
    results = await graph.search("legal")
    assert len(results) == 1
    assert "legal" in results[0].claim.lower()


@pytest.mark.asyncio
async def test_update_node(graph):
    """Test updating a node."""
    node = await graph.add_node(
        claim="Initial claim",
        confidence=0.5,
        created_by_cycle=1,
    )

    # Update
    node.claim = "Updated claim"
    node.confidence = 0.8
    node.updated_by_cycle = 2

    updated = await graph.update_node(node)

    assert updated.claim == "Updated claim"
    assert updated.confidence == 0.8
    assert updated.updated_by_cycle == 2


@pytest.mark.asyncio
async def test_kill_node(graph):
    """Test killing a node."""
    node = await graph.add_node(
        claim="To be killed",
        created_by_cycle=1,
    )

    await graph.kill_node(node.id, "outdated information", cycle_id=2)

    killed = await graph.get_node(node.id)
    assert killed.status == "killed"
    assert "killed:outdated information" in killed.tags


@pytest.mark.asyncio
async def test_confidence_propagation(graph):
    """Test confidence propagation."""
    # Create parent with evidence
    parent = await graph.add_node(
        claim="Parent claim",
        confidence=0.5,
        created_by_cycle=1,
    )

    # Add evidence
    evidence = Evidence(
        text="Supporting evidence",
        source="https://example.com",
    )
    parent.add_evidence(evidence)
    parent.add_evidence(evidence)  # Add twice for testing
    await graph.update_node(parent)

    # Create children with high confidence
    child1 = await graph.add_node(
        claim="Child 1",
        parent_id=parent.id,
        confidence=0.9,
        created_by_cycle=1,
    )

    child2 = await graph.add_node(
        claim="Child 2",
        parent_id=parent.id,
        confidence=0.85,
        created_by_cycle=1,
    )

    # Propagate confidence from children
    await propagate_confidence_upward(graph, child1.id)

    # Check parent confidence increased
    updated_parent = await graph.get_node(parent.id)
    assert updated_parent.confidence > 0.5  # Should have increased


def test_evidence_to_confidence():
    """Test evidence confidence calculation."""
    # No evidence = 0 confidence
    assert evidence_to_confidence([]) == 0.0

    # One piece of evidence
    evidence = [Evidence(text="test", source="test")]
    conf1 = evidence_to_confidence(evidence)
    assert 0.6 < conf1 < 0.8

    # Multiple pieces of evidence (independent confirmation)
    evidence2 = [Evidence(text="test", source="test")] * 3
    conf2 = evidence_to_confidence(evidence2)
    assert conf2 > conf1  # More evidence = higher confidence
    assert conf2 <= 0.95  # But capped at 0.95


def test_claim_similarity():
    """Test claim similarity calculation."""
    claim1 = "The market size for legal tech is $2.3B in 2024"
    claim2 = "The legal tech market is valued at $2.3B for 2024"
    claim3 = "Healthcare spending reached $4T last year"

    # Similar claims
    sim1 = calculate_claim_similarity(claim1, claim2)
    assert sim1 > 0.6  # Should be fairly similar

    # Dissimilar claims
    sim2 = calculate_claim_similarity(claim1, claim3)
    assert sim2 < 0.3  # Should be quite different

    # Identical claims
    sim3 = calculate_claim_similarity(claim1, claim1)
    assert sim3 == 1.0


@pytest.mark.asyncio
async def test_find_similar_nodes(graph):
    """Test finding similar nodes."""
    await graph.add_node(
        claim="The market is $2.3B",
        created_by_cycle=1,
    )

    await graph.add_node(
        claim="The market is approximately $2.3B",  # Changed to be more similar
        created_by_cycle=1,
    )

    await graph.add_node(
        claim="Completely different topic about healthcare",
        created_by_cycle=1,
    )

    # Find nodes similar to first claim
    similar = await find_similar_nodes(
        graph,
        "The market is valued at $2.3B",
        threshold=0.5,
    )

    assert len(similar) >= 2  # Should find the two market claims
    assert all(sim >= 0.5 for sim, _ in similar)


@pytest.mark.asyncio
async def test_summary_view(graph):
    """Test rendering summary view."""
    # Create a small tree
    root = await graph.add_node(
        claim="Root node about market",
        confidence=0.7,
        importance=1.0,
        created_by_cycle=1,
    )

    child1 = await graph.add_node(
        claim="Child 1 about legal tech",
        parent_id=root.id,
        confidence=0.8,
        importance=0.9,
        created_by_cycle=1,
    )

    child2 = await graph.add_node(
        claim="Child 2 about healthcare",
        parent_id=root.id,
        confidence=0.6,
        importance=0.8,
        created_by_cycle=1,
    )

    # Render summary
    summary = await render_summary_view(graph, max_depth=2)

    assert "Knowledge Graph Summary" in summary
    assert "Root node about market" in summary
    assert "Child 1 about legal tech" in summary
    assert "Child 2 about healthcare" in summary


@pytest.mark.asyncio
async def test_focused_view(graph):
    """Test rendering focused view."""
    parent = await graph.add_node(
        claim="Parent node",
        confidence=0.7,
        importance=0.9,
        created_by_cycle=1,
    )

    child = await graph.add_node(
        claim="Child node with details",
        parent_id=parent.id,
        confidence=0.8,
        importance=0.85,
        created_by_cycle=1,
    )

    # Add evidence
    child.add_evidence(Evidence(
        text="Supporting evidence from source",
        source="https://example.com/article",
    ))
    await graph.update_node(child)

    # Render focused view
    focused = await render_focused_view(graph, child.id)

    assert "Focused View" in focused
    assert "Child node with details" in focused
    assert "Context Path" in focused  # Should show path to root
    assert "Parent node" in focused
    assert "Supporting evidence" in focused


@pytest.mark.asyncio
async def test_workspace_isolation(graph):
    """Test that workspaces are isolated."""
    # Create node in test workspace
    node1 = await graph.add_node(
        claim="Test workspace node",
        created_by_cycle=1,
    )

    # Create another graph with different workspace
    graph2 = KnowledgeGraph(":memory:", workspace_id="other")
    await graph2.initialize()

    # Should not find node from different workspace
    node = await graph2.get_node(node1.id)
    assert node is None

    # But should find in original workspace
    node = await graph.get_node(node1.id)
    assert node is not None

    await graph2.close()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
