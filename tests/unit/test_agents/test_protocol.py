"""
Tests for agent protocol and basic adapter functionality.

These tests verify:
- Protocol compliance
- Base adapter utilities (cost tracking, retry logic)
- Mock agent behavior
"""

import pytest
from unittest.mock import AsyncMock, Mock, patch
from datetime import datetime

from winterfox.agents.protocol import (
    AgentAdapter,
    AgentOutput,
    Finding,
    Evidence,
    SearchRecord,
    ToolDefinition,
)
from winterfox.agents.adapters.base import BaseAdapter


def test_finding_validation():
    """Test Finding dataclass validation."""
    # Valid finding
    finding = Finding(
        claim="Test claim",
        confidence=0.8,
        evidence=[
            Evidence(text="Evidence text", source="Source", date=datetime.now())
        ],
        suggested_parent_id="parent-123",
        suggested_children=["child-1", "child-2"],
        tags=["test", "validation"],
    )

    assert finding.claim == "Test claim"
    assert finding.confidence == 0.8
    assert len(finding.evidence) == 1
    assert finding.tags == ["test", "validation"]


def test_agent_output_structure():
    """Test AgentOutput structure."""
    output = AgentOutput(
        findings=[
            Finding(
                claim="Test claim",
                confidence=0.8,
                evidence=[Evidence(text="test", source="source", date=None)],
            )
        ],
        self_critique="Good work",
        raw_text="Raw agent output",
        searches_performed=[
            SearchRecord(
                query="test query",
                engine="tavily",
                timestamp=datetime.now(),
                results_summary="Found 5 results",
                urls_visited=["http://example.com"],
            )
        ],
        cost_usd=0.1234,
        duration_seconds=45.2,
        agent_name="claude-opus-4",
        model="claude-opus-4-20251120",
        total_tokens=1000,
        input_tokens=800,
        output_tokens=200,
    )

    assert len(output.findings) == 1
    assert output.cost_usd == 0.1234
    assert output.duration_seconds == 45.2
    assert len(output.searches_performed) == 1
    assert output.model == "claude-opus-4-20251120"
    assert output.total_tokens == 1000


def test_base_adapter_cost_calculation():
    """Test cost calculation for different models."""
    # Test pricing for known models
    assert "claude-opus-4-20251120" in BaseAdapter.PRICING
    assert "kimi-2.5" in BaseAdapter.PRICING

    # Claude Opus 4.6 pricing
    claude_pricing = BaseAdapter.PRICING["claude-opus-4-20251120"]
    assert claude_pricing["input"] == 15.0  # $15 per 1M tokens
    assert claude_pricing["output"] == 75.0  # $75 per 1M tokens

    # Kimi 2.5 pricing (cheaper)
    kimi_pricing = BaseAdapter.PRICING["kimi-2.5"]
    assert kimi_pricing["input"] == 0.2
    assert kimi_pricing["output"] == 0.2


def test_tool_definition():
    """Test ToolDefinition structure."""

    def mock_execute(query: str) -> str:
        return f"Results for {query}"

    tool = ToolDefinition(
        name="web_search",
        description="Search the web",
        parameters={
            "type": "object",
            "properties": {
                "query": {"type": "string"},
            },
            "required": ["query"],
        },
        execute=mock_execute,
    )

    assert tool.name == "web_search"
    assert "query" in tool.parameters["properties"]
    result = tool.execute("test query")
    assert result == "Results for test query"


@pytest.mark.asyncio
async def test_base_adapter_retry_logic():
    """Test exponential backoff retry with tenacity."""

    class MockAdapter(BaseAdapter):
        def __init__(self):
            self.attempt_count = 0

        async def failing_operation(self):
            self.attempt_count += 1
            if self.attempt_count < 2:
                raise ConnectionError("Temporary failure")  # Use ConnectionError which is retried
            return "Success"

    adapter = MockAdapter()

    # Test retry with max_retries=3 (up to 3 attempts)
    result = await adapter._with_retry(
        adapter.failing_operation,
        max_retries=3,
    )

    assert result == "Success"
    assert adapter.attempt_count == 2  # Failed once, succeeded on 2nd attempt


@pytest.mark.asyncio
async def test_mock_agent_adapter():
    """Test mock agent adapter for testing."""

    class MockAgent:
        @property
        def name(self) -> str:
            return "mock-agent"

        @property
        def supports_native_search(self) -> bool:
            return False

        async def verify(self) -> None:
            pass

        async def run(
            self,
            system_prompt: str,
            user_prompt: str,
            tools: list[ToolDefinition],
            max_iterations: int = 30,
        ) -> AgentOutput:
            # Mock agent that returns predefined findings
            return AgentOutput(
                findings=[
                    Finding(
                        claim="Mock finding about test topic",
                        confidence=0.85,
                        evidence=[
                            Evidence(
                                text="Mock evidence",
                                source="Mock Source",
                                date=datetime.now(),
                            )
                        ],
                    )
                ],
                self_critique="Mock critique",
                raw_text="Mock raw output",
                searches_performed=[],
                cost_usd=0.01,
                duration_seconds=1.0,
                agent_name="mock-agent",
                model="mock-model",
                total_tokens=100,
                input_tokens=50,
                output_tokens=50,
            )

    # Test that mock agent conforms to protocol
    agent = MockAgent()
    assert isinstance(agent, AgentAdapter)

    # Test running mock agent
    output = await agent.run(
        system_prompt="Test system",
        user_prompt="Test user",
        tools=[],
    )

    assert len(output.findings) == 1
    assert output.findings[0].claim == "Mock finding about test topic"
    assert output.cost_usd == 0.01


def test_protocol_type_checking():
    """Test that protocol type checking works."""

    class InvalidAgent:
        """Missing required methods"""
        pass

    agent = InvalidAgent()

    # Should not be considered an AgentAdapter
    assert not isinstance(agent, AgentAdapter)


def test_evidence_with_verified_by():
    """Test Evidence with verified_by field."""
    evidence = Evidence(
        text="Test evidence",
        source="Test source",
        date=datetime.now(),
        verified_by=["agent-1", "agent-2"],
    )

    assert len(evidence.verified_by) == 2
    assert "agent-1" in evidence.verified_by
