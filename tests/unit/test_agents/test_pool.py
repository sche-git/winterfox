"""
Tests for AgentPool and multi-agent consensus.

These tests verify:
- Parallel agent dispatch
- Finding grouping by similarity
- Confidence boosting for consensus
- Finding merging logic
"""

import pytest
from datetime import datetime
from unittest.mock import AsyncMock

from winterfox.agents.pool import AgentPool, ConsensusResult
from winterfox.agents.protocol import AgentOutput, Finding, Evidence


class MockAgent:
    """Mock agent for testing."""

    def __init__(self, name: str, findings: list[Finding]):
        self._name = name
        self._findings = findings

    @property
    def name(self) -> str:
        return self._name

    @property
    def supports_native_search(self) -> bool:
        return False

    async def run(self, system_prompt, user_prompt, tools, max_iterations=30):
        return AgentOutput(
            findings=self._findings,
            self_critique="Mock critique",
            raw_text="Mock output",
            searches_performed=[],
            cost_usd=0.01,
            duration_seconds=1.0,
            agent_name=self._name,
            model="mock-model",
            total_tokens=100,
            input_tokens=50,
            output_tokens=50,
        )


@pytest.mark.asyncio
async def test_parallel_dispatch():
    """Test parallel agent execution."""
    agent1 = MockAgent(
        "agent-1",
        [
            Finding(
                claim="Finding from agent 1",
                confidence=0.8,
                evidence=[Evidence(text="evidence", source="source")],
            )
        ],
    )

    agent2 = MockAgent(
        "agent-2",
        [
            Finding(
                claim="Finding from agent 2",
                confidence=0.85,
                evidence=[Evidence(text="evidence", source="source")],
            )
        ],
    )

    pool = AgentPool([agent1, agent2])

    # Dispatch to all agents in parallel
    outputs = await pool.dispatch(
        system_prompt="Test system",
        user_prompt="Test user",
        tools=[],
    )

    assert len(outputs) == 2
    assert outputs[0].agent_name == "agent-1"
    assert outputs[1].agent_name == "agent-2"


@pytest.mark.asyncio
async def test_consensus_detection():
    """Test finding grouping by similarity."""
    # Two agents with similar findings
    agent1 = MockAgent(
        "agent-1",
        [
            Finding(
                claim="The market is worth $2.3B",
                confidence=0.8,
                evidence=[Evidence(text="evidence1", source="source1")],
            )
        ],
    )

    agent2 = MockAgent(
        "agent-2",
        [
            Finding(
                claim="Market size is $2.3B",  # Similar to agent1
                confidence=0.85,
                evidence=[Evidence(text="evidence2", source="source2")],
            )
        ],
    )

    pool = AgentPool([agent1, agent2])

    # Dispatch with consensus analysis
    result = await pool.dispatch_with_consensus(
        system_prompt="Test system",
        user_prompt="Test user",
        tools=[],
        similarity_threshold=0.5,  # Lower threshold to detect similarity
    )

    # Should detect consensus (2 similar findings merged into 1)
    assert result.consensus_count > 0
    assert len(result.findings) == 1  # Merged into single finding
    assert result.total_cost_usd == 0.02  # 0.01 * 2 agents


@pytest.mark.asyncio
async def test_confidence_boosting():
    """Test consensus confidence boost."""
    # Two agents agree on same finding
    agent1 = MockAgent(
        "agent-1",
        [
            Finding(
                claim="The market is $2.3B",
                confidence=0.7,
                evidence=[Evidence(text="evidence1", source="source1")],
            )
        ],
    )

    agent2 = MockAgent(
        "agent-2",
        [
            Finding(
                claim="The market is $2.3B",  # Exact match
                confidence=0.75,
                evidence=[Evidence(text="evidence2", source="source2")],
            )
        ],
    )

    pool = AgentPool([agent1, agent2])

    result = await pool.dispatch_with_consensus(
        system_prompt="Test",
        user_prompt="Test",
        tools=[],
        consensus_boost=0.15,
    )

    # Merged finding should have boosted confidence
    merged_finding = result.findings[0]

    # Base confidence would be ~0.725 (average), boosted by 0.15
    assert merged_finding.confidence > 0.75
    assert merged_finding.confidence <= 0.95  # Capped


@pytest.mark.asyncio
async def test_divergent_findings():
    """Test handling of divergent findings."""
    # Two agents with completely different findings
    agent1 = MockAgent(
        "agent-1",
        [
            Finding(
                claim="Market size is $2.3B",
                confidence=0.8,
                evidence=[Evidence(text="evidence1", source="source1")],
            )
        ],
    )

    agent2 = MockAgent(
        "agent-2",
        [
            Finding(
                claim="Healthcare spending is $4T",  # Completely different
                confidence=0.85,
                evidence=[Evidence(text="evidence2", source="source2")],
            )
        ],
    )

    pool = AgentPool([agent1, agent2])

    result = await pool.dispatch_with_consensus(
        system_prompt="Test",
        user_prompt="Test",
        tools=[],
    )

    # Should have 2 separate findings (no consensus)
    assert result.consensus_count == 0
    assert result.divergent_count == 2
    assert len(result.findings) == 2


@pytest.mark.asyncio
async def test_finding_merge():
    """Test merging similar findings."""
    finding1 = Finding(
        claim="The market is worth $2.3B",
        confidence=0.7,
        evidence=[Evidence(text="evidence1", source="source1")],
        tags=["market", "size"],
    )

    finding2 = Finding(
        claim="Market is valued at $2.3B",
        confidence=0.75,
        evidence=[Evidence(text="evidence2", source="source2")],
        tags=["market", "valuation"],
    )

    # Create pool with dummy agent to test merge method
    dummy_agent = MockAgent("dummy", [])
    pool = AgentPool([dummy_agent])

    # Use internal merge method
    merged = pool._merge_findings([finding1, finding2])

    # Should combine evidence
    assert len(merged.evidence) == 2

    # Should average confidence (0.7 + 0.75) / 2 = 0.725
    assert merged.confidence == 0.725

    # Should combine tags
    assert "market" in merged.tags
    assert "size" in merged.tags or "valuation" in merged.tags


@pytest.mark.asyncio
async def test_single_agent_no_consensus():
    """Test single agent (no consensus analysis)."""
    agent = MockAgent(
        "agent-1",
        [
            Finding(
                claim="Test finding",
                confidence=0.8,
                evidence=[Evidence(text="evidence", source="source")],
            )
        ],
    )

    pool = AgentPool([agent])

    # With single agent, should skip consensus
    result = await pool.dispatch_with_consensus(
        system_prompt="Test",
        user_prompt="Test",
        tools=[],
    )

    assert len(result.findings) == 1
    assert result.consensus_count == 0
    assert result.divergent_count == 1


@pytest.mark.asyncio
async def test_empty_agent_pool():
    """Test error handling for empty agent pool."""
    with pytest.raises(ValueError, match="At least one agent adapter required"):
        pool = AgentPool([])


@pytest.mark.asyncio
async def test_cost_accumulation():
    """Test total cost calculation across agents."""
    agent1 = MockAgent("agent-1", [])
    agent2 = MockAgent("agent-2", [])
    agent3 = MockAgent("agent-3", [])

    pool = AgentPool([agent1, agent2, agent3])

    result = await pool.dispatch_with_consensus(
        system_prompt="Test",
        user_prompt="Test",
        tools=[],
    )

    # Each mock agent costs 0.01
    assert result.total_cost_usd == 0.03
