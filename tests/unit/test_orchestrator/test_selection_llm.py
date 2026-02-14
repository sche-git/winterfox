"""
Tests for LLM-driven node selection.

Verifies:
- JSON parsing of LLM responses (valid and invalid)
- Graceful fallback to UCB1
- End-to-end selection with mock adapter
"""

import pytest
import pytest_asyncio
from dataclasses import dataclass, field

from winterfox.agents.protocol import AgentOutput, Finding, SearchRecord
from winterfox.graph.store import KnowledgeGraph
from winterfox.orchestrator.selection import (
    SelectionDecision,
    _parse_selection_response,
    select_target_with_llm,
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


class MockAdapter:
    """Mock adapter that returns a fixed response."""

    def __init__(self, raw_text: str, should_fail: bool = False):
        self._raw_text = raw_text
        self._should_fail = should_fail

    @property
    def name(self) -> str:
        return "mock-adapter"

    @property
    def supports_native_search(self) -> bool:
        return False

    async def verify(self) -> None:
        pass

    async def run(self, system_prompt, user_prompt, tools, max_iterations=30):
        if self._should_fail:
            raise ConnectionError("Mock failure")
        return AgentOutput(
            findings=[],
            self_critique="",
            raw_text=self._raw_text,
            searches_performed=[],
            cost_usd=0.001,
            duration_seconds=0.5,
            agent_name="mock-adapter",
            model="mock-model",
            total_tokens=100,
            input_tokens=80,
            output_tokens=20,
        )


# --- Parsing Tests ---


class TestParseSelectionResponse:
    """Test JSON parsing of LLM selection responses."""

    def test_parse_explore(self):
        """Parse valid EXPLORE response."""
        raw = '{"strategy": "EXPLORE", "target_node_id": "abc123", "reasoning": "Few hypotheses", "suggested_question": "What about hardware?"}'
        result = _parse_selection_response(raw)
        assert result is not None
        assert result.strategy == "EXPLORE"
        assert result.target_node_id == "abc123"
        assert result.reasoning == "Few hypotheses"
        assert result.suggested_question == "What about hardware?"

    def test_parse_deepen(self):
        """Parse valid DEEPEN response."""
        raw = '{"strategy": "DEEPEN", "target_node_id": "node-456", "reasoning": "Need more evidence"}'
        result = _parse_selection_response(raw)
        assert result is not None
        assert result.strategy == "DEEPEN"
        assert result.target_node_id == "node-456"

    def test_parse_challenge(self):
        """Parse valid CHALLENGE response."""
        raw = '{"strategy": "CHALLENGE", "target_node_id": "hyp-789", "reasoning": "Strong hypothesis needs stress-test"}'
        result = _parse_selection_response(raw)
        assert result is not None
        assert result.strategy == "CHALLENGE"

    def test_parse_with_markdown_wrapper(self):
        """Parse JSON wrapped in markdown code block."""
        raw = '```json\n{"strategy": "DEEPEN", "target_node_id": "abc", "reasoning": "test"}\n```'
        result = _parse_selection_response(raw)
        assert result is not None
        assert result.strategy == "DEEPEN"

    def test_parse_with_surrounding_text(self):
        """Parse JSON embedded in explanation text."""
        raw = 'Based on my analysis:\n{"strategy": "EXPLORE", "target_node_id": "xyz", "reasoning": "need more"}\nThis is the best approach.'
        result = _parse_selection_response(raw)
        assert result is not None
        assert result.strategy == "EXPLORE"

    def test_parse_invalid_json(self):
        """Invalid JSON returns None."""
        result = _parse_selection_response("this is not json at all")
        assert result is None

    def test_parse_invalid_strategy(self):
        """Invalid strategy value returns None."""
        raw = '{"strategy": "INVALID", "target_node_id": "abc", "reasoning": "test"}'
        result = _parse_selection_response(raw)
        assert result is None

    def test_parse_empty_string(self):
        """Empty string returns None."""
        result = _parse_selection_response("")
        assert result is None

    def test_parse_lowercase_strategy(self):
        """Strategy is case-insensitive (uppercased internally)."""
        raw = '{"strategy": "explore", "target_node_id": "abc", "reasoning": "test"}'
        result = _parse_selection_response(raw)
        assert result is not None
        assert result.strategy == "EXPLORE"


# --- Integration Tests ---


@pytest.mark.asyncio
async def test_select_with_mock_llm_deepen(graph):
    """LLM returns DEEPEN for an existing node."""
    # Create nodes
    root = await graph.add_node(
        claim="How to make startup unicorn?",
        confidence=0.0,
        importance=1.0,
        node_type="question",
        created_by_cycle=0,
    )

    hypothesis = await graph.add_node(
        claim="Build insurance agent",
        parent_id=root.id,
        confidence=0.4,
        importance=0.8,
        node_type="hypothesis",
        created_by_cycle=1,
    )

    # Mock adapter returns DEEPEN targeting the hypothesis
    adapter = MockAdapter(
        f'{{"strategy": "DEEPEN", "target_node_id": "{hypothesis.id}", "reasoning": "Need more evidence"}}'
    )

    target, decision = await select_target_with_llm(graph, adapter)
    assert target is not None
    assert target.id == hypothesis.id
    assert decision is not None
    assert decision.strategy == "DEEPEN"


@pytest.mark.asyncio
async def test_select_with_mock_llm_explore(graph):
    """LLM returns EXPLORE, targets root question node."""
    root = await graph.add_node(
        claim="How to make startup unicorn?",
        confidence=0.0,
        importance=1.0,
        node_type="question",
        created_by_cycle=0,
    )

    adapter = MockAdapter(
        '{"strategy": "EXPLORE", "target_node_id": null, "reasoning": "Need new hypotheses", "suggested_question": "What about SaaS?"}'
    )

    target, decision = await select_target_with_llm(graph, adapter)
    assert target is not None
    assert target.id == root.id  # Falls back to root for EXPLORE
    assert decision is not None
    assert decision.strategy == "EXPLORE"
    assert decision.suggested_question == "What about SaaS?"


@pytest.mark.asyncio
async def test_fallback_to_ucb1_on_failure(graph):
    """When LLM fails, falls back to UCB1 selection."""
    root = await graph.add_node(
        claim="Research question",
        confidence=0.0,
        importance=1.0,
        created_by_cycle=0,
    )

    adapter = MockAdapter("", should_fail=True)

    target, decision = await select_target_with_llm(graph, adapter)
    assert target is not None  # UCB1 should still return the node
    assert decision is None  # No LLM decision


@pytest.mark.asyncio
async def test_fallback_on_invalid_response(graph):
    """When LLM returns unparseable response, falls back to UCB1."""
    root = await graph.add_node(
        claim="Research question",
        confidence=0.0,
        importance=1.0,
        created_by_cycle=0,
    )

    adapter = MockAdapter("I think you should research more about markets.")

    target, decision = await select_target_with_llm(graph, adapter)
    assert target is not None  # UCB1 fallback
    assert decision is None


@pytest.mark.asyncio
async def test_prefix_match_for_truncated_ids(graph):
    """LLM may return truncated node IDs — should still match."""
    node = await graph.add_node(
        claim="Some research node",
        confidence=0.3,
        importance=0.7,
        created_by_cycle=1,
    )

    # Use first 12 chars of the UUID as truncated ID
    truncated_id = node.id[:12]
    adapter = MockAdapter(
        f'{{"strategy": "DEEPEN", "target_node_id": "{truncated_id}", "reasoning": "Need evidence"}}'
    )

    target, decision = await select_target_with_llm(graph, adapter)
    assert target is not None
    assert target.id == node.id  # Full ID matched via prefix
    assert decision is not None
