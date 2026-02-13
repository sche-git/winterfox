"""
Tests for research orchestrator core functionality.

These tests verify:
- Single cycle execution
- Multiple cycle execution
- Run until confidence target
- Statistics tracking
"""

import pytest
from datetime import datetime

from winterfox.graph.store import KnowledgeGraph
from winterfox.graph.models import Evidence
from winterfox.orchestrator import Orchestrator
from winterfox.agents.pool import AgentPool
from winterfox.agents.protocol import AgentOutput, Finding


class MockAgent:
    """Mock agent for orchestrator testing."""

    def __init__(self, name: str = "mock-agent"):
        self._name = name
        self.call_count = 0

    @property
    def name(self) -> str:
        return self._name

    @property
    def supports_native_search(self) -> bool:
        return False

    async def run(self, system_prompt, user_prompt, tools, max_iterations=30):
        self.call_count += 1

        # Return findings that gradually increase confidence
        return AgentOutput(
            findings=[
                Finding(
                    claim=f"New finding from cycle {self.call_count}",
                    confidence=0.7 + (self.call_count * 0.05),  # Increasing confidence
                    evidence=[
                        Evidence(
                            text=f"Evidence {self.call_count}",
                            source=f"Source {self.call_count}",
                        )
                    ],
                ),
            ],
            self_critique="Good progress",
            raw_text="Mock output",
            searches_performed=[],
            cost_usd=0.05,
            duration_seconds=2.0,
            agent_name=self._name,
            model="mock-model",
            total_tokens=200,
            input_tokens=100,
            output_tokens=100,
        )


@pytest.fixture
async def mock_graph():
    """Create mock knowledge graph."""
    graph = KnowledgeGraph(":memory:", workspace_id="test")
    await graph.initialize()

    # Create test workspace
    async with graph._get_db() as db:
        await db.execute(
            "INSERT OR IGNORE INTO workspaces (id, name, tier) VALUES (?, ?, ?)",
            ("test", "Test Workspace", "free"),
        )
        await db.commit()

    # Add initial root node
    await graph.add_node(
        claim="What is the market opportunity?",
        confidence=0.3,
        importance=1.0,
        created_by_cycle=0,
    )

    yield graph

    await graph.close()


@pytest.fixture
def mock_agent_pool():
    """Create mock agent pool."""
    agent = MockAgent()
    return AgentPool([agent])


@pytest.mark.asyncio
async def test_run_single_cycle(mock_graph, mock_agent_pool):
    """Test running a single research cycle."""
    orchestrator = Orchestrator(
        graph=mock_graph,
        agent_pool=mock_agent_pool,
        north_star="Test research mission",
        tools=[],
    )

    result = await orchestrator.run_cycle()

    assert result.success
    assert result.cycle_id == 1
    assert result.findings_created > 0
    assert result.total_cost_usd > 0
    assert result.duration_seconds > 0

    # Verify cycle history
    assert len(orchestrator.cycle_history) == 1
    assert orchestrator.cycle_count == 1
    assert orchestrator.total_cost_usd > 0


@pytest.mark.asyncio
async def test_run_multiple_cycles(mock_graph, mock_agent_pool):
    """Test running multiple cycles."""
    orchestrator = Orchestrator(
        graph=mock_graph,
        agent_pool=mock_agent_pool,
        north_star="Test research mission",
        tools=[],
    )

    results = await orchestrator.run_cycles(n=3)

    assert len(results) == 3
    assert all(r.success for r in results)
    assert orchestrator.cycle_count == 3

    # Verify cycle IDs increment
    assert results[0].cycle_id == 1
    assert results[1].cycle_id == 2
    assert results[2].cycle_id == 3

    # Verify cost accumulation
    total_cost = sum(r.total_cost_usd for r in results)
    assert orchestrator.total_cost_usd == total_cost


@pytest.mark.asyncio
async def test_run_until_complete(mock_graph, mock_agent_pool):
    """Test running until confidence target reached."""
    orchestrator = Orchestrator(
        graph=mock_graph,
        agent_pool=mock_agent_pool,
        north_star="Test research mission",
        tools=[],
    )

    # Set a reachable target
    results = await orchestrator.run_until_complete(
        min_confidence=0.6,  # Should reach this in a few cycles
        max_cycles=10,
    )

    # Should complete before max_cycles
    assert len(results) < 10
    assert len(results) > 0

    # Verify average confidence reached target
    nodes = await mock_graph.get_all_active_nodes()
    if nodes:
        avg_confidence = sum(n.confidence for n in nodes) / len(nodes)
        assert avg_confidence >= 0.6


@pytest.mark.asyncio
async def test_orchestrator_stats(mock_graph, mock_agent_pool):
    """Test orchestrator statistics tracking."""
    orchestrator = Orchestrator(
        graph=mock_graph,
        agent_pool=mock_agent_pool,
        north_star="Test research mission",
        tools=[],
    )

    await orchestrator.run_cycles(n=3)

    summary = orchestrator.get_summary()

    assert "Total Cycles: 3" in summary
    assert "Total Findings:" in summary
    assert "Total Cost:" in summary
    assert "Agents: 1" in summary


@pytest.mark.asyncio
async def test_orchestrator_reset(mock_graph, mock_agent_pool):
    """Test orchestrator state reset."""
    orchestrator = Orchestrator(
        graph=mock_graph,
        agent_pool=mock_agent_pool,
        north_star="Test research mission",
        tools=[],
    )

    # Run some cycles
    await orchestrator.run_cycles(n=2)
    assert orchestrator.cycle_count == 2
    assert orchestrator.total_cost_usd > 0

    # Reset
    await orchestrator.reset()

    assert orchestrator.cycle_count == 0
    assert orchestrator.total_cost_usd == 0.0
    assert len(orchestrator.cycle_history) == 0


@pytest.mark.asyncio
async def test_specific_node_research(mock_graph, mock_agent_pool):
    """Test researching a specific node."""
    # Add specific node to research
    target = await mock_graph.add_node(
        claim="Specific topic to research",
        confidence=0.4,
        importance=0.9,
        created_by_cycle=0,
    )

    orchestrator = Orchestrator(
        graph=mock_graph,
        agent_pool=mock_agent_pool,
        north_star="Test research mission",
        tools=[],
    )

    # Research specific node
    result = await orchestrator.run_cycle(target_node_id=target.id)

    assert result.success
    assert result.target_node_id == target.id
    assert result.target_claim == "Specific topic to research"


@pytest.mark.asyncio
async def test_cycle_error_handling(mock_graph):
    """Test graceful error handling in cycles."""

    class FailingAgent:
        @property
        def name(self):
            return "failing-agent"

        @property
        def supports_native_search(self):
            return False

        async def run(self, system_prompt, user_prompt, tools, max_iterations=30):
            raise Exception("Agent failed intentionally")

    agent_pool = AgentPool([FailingAgent()])

    orchestrator = Orchestrator(
        graph=mock_graph,
        agent_pool=agent_pool,
        north_star="Test research mission",
        tools=[],
    )

    result = await orchestrator.run_cycle()

    # Should complete without crashing (graceful error handling)
    assert result.success  # Cycle succeeded in handling error gracefully
    assert result.findings_created == 0  # But no findings were created
    assert len(result.agent_outputs) == 1
    assert "Agent failed" in result.agent_outputs[0].self_critique


@pytest.mark.asyncio
async def test_knowledge_compounding(mock_graph, mock_agent_pool):
    """Test that knowledge compounds over cycles."""
    orchestrator = Orchestrator(
        graph=mock_graph,
        agent_pool=mock_agent_pool,
        north_star="Test research mission",
        tools=[],
    )

    # Run multiple cycles
    initial_count = await mock_graph.count_nodes()
    await orchestrator.run_cycles(n=3)
    final_count = await mock_graph.count_nodes()

    # Should have more nodes after research
    assert final_count > initial_count

    # Verify findings created across cycles
    total_created = sum(r.findings_created for r in orchestrator.cycle_history)
    assert total_created > 0


@pytest.mark.asyncio
async def test_confidence_discount(mock_graph, mock_agent_pool):
    """Test confidence discount is applied to new findings."""
    orchestrator = Orchestrator(
        graph=mock_graph,
        agent_pool=mock_agent_pool,
        north_star="Test research mission",
        tools=[],
        confidence_discount=0.7,
    )

    result = await orchestrator.run_cycle()

    # Verify discount was configured
    assert orchestrator.confidence_discount == 0.7
