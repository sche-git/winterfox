"""
Tests for AgentPool and multi-agent LLM synthesis.

These tests verify:
- Parallel agent dispatch
- LLM-driven synthesis
- Primary agent selection
- Synthesis result format
"""

import pytest
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

from winterfox.agents.pool import AgentPool, SynthesisResult
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
async def test_single_agent_dispatch():
    """Test dispatching single agent."""
    agent = MockAgent(
        "agent-1",
        [
            Finding(
                claim="Test claim",
                confidence=0.8,
                evidence=[Evidence(text="test", source="source")],
            )
        ],
    )

    pool = AgentPool([agent])

    outputs = await pool.dispatch(
        system_prompt="Test system",
        user_prompt="Test user",
        tools=[],
    )

    assert len(outputs) == 1
    assert outputs[0].agent_name == "agent-1"
    assert len(outputs[0].findings) == 1
    assert outputs[0].findings[0].claim == "Test claim"


@pytest.mark.asyncio
async def test_parallel_dispatch():
    """Test parallel dispatch to multiple agents."""
    agent1 = MockAgent(
        "agent-1",
        [Finding(claim="Finding 1", confidence=0.8, evidence=[])],
    )

    agent2 = MockAgent(
        "agent-2",
        [Finding(claim="Finding 2", confidence=0.75, evidence=[])],
    )

    pool = AgentPool([agent1, agent2])

    outputs = await pool.dispatch(
        system_prompt="Test",
        user_prompt="Test",
        tools=[],
    )

    assert len(outputs) == 2
    assert outputs[0].agent_name == "agent-1"
    assert outputs[1].agent_name == "agent-2"


@pytest.mark.asyncio
async def test_synthesis_single_agent():
    """Test synthesis with single agent (no actual synthesis needed)."""
    agent = MockAgent(
        "agent-1",
        [
            Finding(
                claim="Market size is $2.3B",
                confidence=0.8,
                evidence=[Evidence(text="evidence", source="source")],
            )
        ],
    )

    pool = AgentPool([agent], primary_agent_index=0)

    result = await pool.dispatch_with_synthesis(
        system_prompt="Test system",
        user_prompt="Test user",
        tools=[],
    )

    # Single agent, no synthesis performed
    assert isinstance(result, SynthesisResult)
    assert len(result.findings) == 1
    assert result.findings[0].claim == "Market size is $2.3B"
    assert result.synthesis_reasoning == "Single agent, no synthesis performed"
    assert result.total_cost_usd == 0.01


@pytest.mark.asyncio
async def test_llm_synthesis_multi_agent():
    """Test LLM-driven synthesis with multiple agents."""
    # Create agents with different findings
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
                claim="Market size is approximately $2.2B",
                confidence=0.75,
                evidence=[Evidence(text="evidence2", source="source2")],
            )
        ],
    )

    # Primary agent (agent1) will synthesize
    pool = AgentPool([agent1, agent2], primary_agent_index=0)

    # Mock the synthesis output from primary agent
    synthesized_finding = Finding(
        claim="Market size is $2.2-2.3B (synthesized from multiple sources)",
        confidence=0.85,  # Boosted due to consensus
        evidence=[
            Evidence(text="evidence1", source="source1"),
            Evidence(text="evidence2", source="source2"),
        ],
        tags=["consensus"],
    )

    synthesis_output = AgentOutput(
        findings=[synthesized_finding],
        self_critique="Synthesis: Both agents reported similar market sizes. "
        "Consensus finding: market size ~$2.2-2.3B. "
        "High confidence due to independent confirmation.",
        raw_text="Synthesis complete",
        searches_performed=[],
        cost_usd=0.005,  # Synthesis is cheaper (no search)
        duration_seconds=0.5,
        agent_name="agent-1",
        model="mock-model",
        total_tokens=50,
        input_tokens=40,
        output_tokens=10,
    )

    # Patch the primary agent's run method to return synthesis
    with patch.object(agent1, "run", return_value=synthesis_output):
        result = await pool.dispatch_with_synthesis(
            system_prompt="Test system",
            user_prompt="Test user",
            tools=[],
        )

    # Verify synthesis result
    assert isinstance(result, SynthesisResult)
    assert len(result.findings) == 1
    assert "synthesized" in result.findings[0].claim.lower()
    assert result.findings[0].confidence == 0.85
    assert "consensus" in result.findings[0].tags

    # Verify cost (agent1 patched=0.005, agent2=0.01, synthesis=0.005)
    assert result.total_cost_usd == 0.02

    # Verify synthesis reasoning
    assert "consensus" in result.synthesis_reasoning.lower()

    # Verify consensus findings extracted
    assert len(result.consensus_findings) > 0


@pytest.mark.asyncio
async def test_primary_agent_index():
    """Test primary agent selection."""
    agent1 = MockAgent("agent-1", [])
    agent2 = MockAgent("agent-2", [])
    agent3 = MockAgent("agent-3", [])

    # Agent2 is primary
    pool = AgentPool([agent1, agent2, agent3], primary_agent_index=1)

    assert pool.primary_agent_index == 1
    assert pool.adapters[pool.primary_agent_index].name == "agent-2"


def test_invalid_primary_agent_index():
    """Test validation of primary agent index."""
    agent = MockAgent("agent-1", [])

    # Index out of range
    with pytest.raises(ValueError, match="out of range"):
        AgentPool([agent], primary_agent_index=5)

    # Negative index
    with pytest.raises(ValueError, match="out of range"):
        AgentPool([agent], primary_agent_index=-1)


@pytest.mark.asyncio
async def test_agent_failure_handling():
    """Test handling of failed agents."""

    class FailingAgent:
        @property
        def name(self):
            return "failing-agent"

        @property
        def supports_native_search(self):
            return False

        async def run(self, *args, **kwargs):
            raise Exception("Agent failed!")

    working_agent = MockAgent("working-agent", [Finding(claim="Test", confidence=0.8, evidence=[])])
    failing_agent = FailingAgent()

    pool = AgentPool([working_agent, failing_agent])

    outputs = await pool.dispatch(
        system_prompt="Test",
        user_prompt="Test",
        tools=[],
    )

    # Should get 2 outputs (1 success, 1 failure placeholder)
    assert len(outputs) == 2

    # First agent succeeded
    assert outputs[0].agent_name == "working-agent"
    assert len(outputs[0].findings) == 1

    # Second agent failed gracefully
    assert outputs[1].agent_name == "failing-agent"
    assert len(outputs[1].findings) == 0
    assert "failed" in outputs[1].self_critique.lower()


@pytest.mark.asyncio
async def test_empty_agent_pool():
    """Test that empty agent pool raises error."""
    with pytest.raises(ValueError, match="At least one agent adapter required"):
        AgentPool([])


@pytest.mark.asyncio
async def test_format_agent_outputs():
    """Test formatting agent outputs for synthesis."""
    agent1 = MockAgent(
        "agent-1",
        [
            Finding(
                claim="Test finding",
                confidence=0.8,
                evidence=[Evidence(text="evidence", source="source1")],
            )
        ],
    )

    pool = AgentPool([agent1])

    outputs = await pool.dispatch(
        system_prompt="Test",
        user_prompt="Test",
        tools=[],
    )

    formatted = pool._format_agent_outputs(outputs)

    # Should include agent name, model, findings
    assert "agent-1" in formatted
    assert "mock-model" in formatted
    assert "Test finding" in formatted
    assert "0.8" in formatted.replace("0.80", "0.8")  # Handle formatting
    assert "source1" in formatted
