"""
Tests for Lead LLM orchestrator.

These tests verify:
- Direction selection with LLM strategic reasoning
- Research agent dispatch (parallel)
- Raw output synthesis into directions
- JSON parsing and error handling
- Fallback behavior
"""

import json
import pytest
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

from winterfox.orchestrator.lead import LeadLLM, Direction, DirectionSynthesis
from winterfox.agents.protocol import AgentOutput, SearchRecord
from winterfox.graph.models import KnowledgeNode, Evidence


class MockAdapter:
    """Mock LLM adapter for Lead LLM testing."""

    def __init__(self, name: str = "mock-lead"):
        self._name = name
        self.call_count = 0
        self.last_system_prompt = None
        self.last_user_prompt = None
        self.mock_response = None  # Set this before calling

    @property
    def name(self) -> str:
        return self._name

    async def run(self, system_prompt, user_prompt, tools, max_iterations=30):
        self.call_count += 1
        self.last_system_prompt = system_prompt
        self.last_user_prompt = user_prompt

        # Return mock response
        return AgentOutput(
            raw_text=self.mock_response if self.mock_response else "{}",
            self_critique="Mock critique",
            searches_performed=[],
            cost_usd=0.05,
            duration_seconds=1.0,
            agent_name=self._name,
            model="mock-model",
            total_tokens=100,
            input_tokens=50,
            output_tokens=50,
        )


class MockGraph:
    """Mock knowledge graph for Lead LLM testing."""

    def __init__(self):
        self.nodes = []
        self.get_node_calls = []

    async def get_all_active_nodes(self):
        return self.nodes

    async def get_node(self, node_id):
        self.get_node_calls.append(node_id)
        for node in self.nodes:
            if node.id == node_id or node.id.startswith(node_id):
                return node
        return None

    async def get_children(self, node_id):
        return [n for n in self.nodes if n.parent_id == node_id]


def create_mock_node(
    node_id: str = "abc123",
    claim: str = "Test claim",
    confidence: float = 0.5,
    importance: float = 0.8,
    depth: int = 1,
    children_count: int = 0,
) -> KnowledgeNode:
    """Helper to create mock knowledge nodes."""
    node = KnowledgeNode(
        id=node_id,
        workspace_id="test",
        parent_id=None,
        claim=claim,
        confidence=confidence,
        importance=importance,
        depth=depth,
        status="active",
        node_type="direction",
        children_ids=[f"child_{i}" for i in range(children_count)],
        tags=[],
        evidence=[],
        created_at=datetime.now(),
        updated_at=datetime.now(),
        created_by_cycle=1,
        updated_by_cycle=1,
    )
    return node


@pytest.mark.asyncio
async def test_select_direction_success():
    """Test Lead LLM successfully selects a direction."""
    # Setup
    adapter = MockAdapter()
    graph = MockGraph()

    # Add test nodes
    node1 = create_mock_node("node_1", "First direction", confidence=0.3, importance=0.9)
    node2 = create_mock_node("node_2", "Second direction", confidence=0.7, importance=0.5)
    graph.nodes = [node1, node2]

    # Mock LLM response (valid JSON)
    adapter.mock_response = json.dumps({
        "selected_node_id": "node_1",
        "reasoning": "This direction has low confidence but high importance, making it a priority"
    })

    lead = LeadLLM(
        adapter=adapter,
        graph=graph,
        north_star="Test mission",
    )

    # Execute
    with patch("winterfox.orchestrator.lead.render_summary_view", return_value="Graph summary"):
        with patch("winterfox.orchestrator.lead.render_weakest_nodes", return_value="Weakest nodes"):
            target, reasoning = await lead.select_direction()

    # Verify
    assert target.id == "node_1"
    assert "low confidence but high importance" in reasoning
    assert adapter.call_count == 1
    assert "Strategic Considerations" in adapter.last_system_prompt
    assert "Test mission" in adapter.last_system_prompt


@pytest.mark.asyncio
async def test_select_direction_partial_id_match():
    """Test Lead LLM selecting with shortened node ID."""
    adapter = MockAdapter()
    graph = MockGraph()

    node = create_mock_node("abc123def456", "Test direction")
    graph.nodes = [node]

    # Mock LLM response with shortened ID
    adapter.mock_response = json.dumps({
        "selected_node_id": "abc123",  # Shortened
        "reasoning": "Testing partial match"
    })

    lead = LeadLLM(adapter=adapter, graph=graph, north_star="Test")

    with patch("winterfox.orchestrator.lead.render_summary_view", return_value="Summary"):
        with patch("winterfox.orchestrator.lead.render_weakest_nodes", return_value="Weak"):
            target, reasoning = await lead.select_direction()

    # Should match by prefix
    assert target.id == "abc123def456"
    assert reasoning == "Testing partial match"


@pytest.mark.asyncio
async def test_select_direction_fallback_invalid_json():
    """Test Lead LLM fallback when JSON is invalid."""
    adapter = MockAdapter()
    graph = MockGraph()

    node = create_mock_node("fallback_node", "Fallback direction")
    graph.nodes = [node]

    # Mock invalid JSON response
    adapter.mock_response = "This is not valid JSON at all"

    lead = LeadLLM(adapter=adapter, graph=graph, north_star="Test")

    with patch("winterfox.orchestrator.lead.render_summary_view", return_value="Summary"):
        with patch("winterfox.orchestrator.lead.render_weakest_nodes", return_value="Weak"):
            target, reasoning = await lead.select_direction()

    # Should fall back to first node
    assert target.id == "fallback_node"
    assert "Fallback selection" in reasoning
    assert "parse failed" in reasoning


@pytest.mark.asyncio
async def test_select_direction_fallback_invalid_node_id():
    """Test Lead LLM fallback when selected node ID doesn't exist."""
    adapter = MockAdapter()
    graph = MockGraph()

    node = create_mock_node("valid_node", "Valid direction")
    graph.nodes = [node]

    # Mock response with non-existent node ID
    adapter.mock_response = json.dumps({
        "selected_node_id": "nonexistent_id",
        "reasoning": "This node doesn't exist"
    })

    lead = LeadLLM(adapter=adapter, graph=graph, north_star="Test")

    with patch("winterfox.orchestrator.lead.render_summary_view", return_value="Summary"):
        with patch("winterfox.orchestrator.lead.render_weakest_nodes", return_value="Weak"):
            target, reasoning = await lead.select_direction()

    # Should fall back to first node
    assert target.id == "valid_node"
    assert "Fallback selection" in reasoning
    assert "invalid ID" in reasoning


@pytest.mark.asyncio
async def test_select_direction_with_report_context():
    """Test Lead LLM selection uses report context when available."""
    adapter = MockAdapter()
    graph = MockGraph()

    node = create_mock_node("node_1", "Direction with report")
    graph.nodes = [node]

    adapter.mock_response = json.dumps({
        "selected_node_id": "node_1",
        "reasoning": "Based on report context"
    })

    # Initialize Lead LLM with report content
    lead = LeadLLM(
        adapter=adapter,
        graph=graph,
        north_star="Test mission",
        report_content="This is a research report with important context" * 100,  # Long report
    )

    with patch("winterfox.orchestrator.lead.render_summary_view", return_value="Summary"):
        with patch("winterfox.orchestrator.lead.render_weakest_nodes", return_value="Weak"):
            target, reasoning = await lead.select_direction()

    # Verify report content was included in prompt
    assert "Current Research Report" in adapter.last_user_prompt
    assert "research report" in adapter.last_user_prompt.lower()


@pytest.mark.asyncio
async def test_select_direction_empty_graph_raises():
    """Test Lead LLM raises error when graph is empty."""
    adapter = MockAdapter()
    graph = MockGraph()
    graph.nodes = []  # Empty graph

    lead = LeadLLM(adapter=adapter, graph=graph, north_star="Test")

    with patch("winterfox.orchestrator.lead.render_summary_view", return_value="Summary"):
        with patch("winterfox.orchestrator.lead.render_weakest_nodes", return_value="Weak"):
            with pytest.raises(ValueError, match="No active nodes"):
                await lead.select_direction()


@pytest.mark.asyncio
async def test_dispatch_research_success():
    """Test Lead LLM dispatches research agents successfully."""
    adapter = MockAdapter()
    graph = MockGraph()

    target_node = create_mock_node("target", "Research this direction")

    # Create mock research agents
    agent1 = MockAdapter("agent-1")
    agent1.mock_response = "Agent 1 found evidence A, B, C..."

    agent2 = MockAdapter("agent-2")
    agent2.mock_response = "Agent 2 found evidence X, Y, Z..."

    lead = LeadLLM(adapter=adapter, graph=graph, north_star="Test mission")

    tools = []  # Mock tools

    with patch("winterfox.orchestrator.lead.render_focused_view", return_value="Focused view"):
        outputs = await lead.dispatch_research(
            target_node=target_node,
            research_agents=[agent1, agent2],
            tools=tools,
            max_searches=10,
        )

    # Verify
    assert len(outputs) == 2
    assert outputs[0].agent_name == "agent-1"
    assert outputs[1].agent_name == "agent-2"
    assert agent1.call_count == 1
    assert agent2.call_count == 1

    # Verify prompts contained key info
    assert "Research this direction" in agent1.last_user_prompt or "Focused view" in agent1.last_user_prompt
    assert "Research Guidelines" in agent1.last_system_prompt
    assert "10 web searches" in agent1.last_system_prompt


@pytest.mark.asyncio
async def test_dispatch_research_agent_failure_continues():
    """Test Lead LLM continues when one agent fails."""
    adapter = MockAdapter()
    graph = MockGraph()

    target_node = create_mock_node("target", "Research direction")

    # Create mock research agents - one will fail
    agent1 = MockAdapter("agent-1")
    agent1.mock_response = "Agent 1 completed successfully"

    async def failing_run(*args, **kwargs):
        raise RuntimeError("Agent 2 failed intentionally")

    agent2 = MockAdapter("agent-2")
    agent2.run = failing_run

    lead = LeadLLM(adapter=adapter, graph=graph, north_star="Test")

    with patch("winterfox.orchestrator.lead.render_focused_view", return_value="Focused"):
        outputs = await lead.dispatch_research(
            target_node=target_node,
            research_agents=[agent1, agent2],
            tools=[],
            max_searches=5,
        )

    # Should continue with successful agent
    assert len(outputs) == 1
    assert outputs[0].agent_name == "agent-1"


@pytest.mark.asyncio
async def test_dispatch_research_all_fail_raises():
    """Test Lead LLM raises error when all agents fail."""
    adapter = MockAdapter()
    graph = MockGraph()

    target_node = create_mock_node("target", "Research direction")

    async def failing_run(*args, **kwargs):
        raise RuntimeError("Agent failed")

    agent = MockAdapter("failing-agent")
    agent.run = failing_run

    lead = LeadLLM(adapter=adapter, graph=graph, north_star="Test")

    with patch("winterfox.orchestrator.lead.render_focused_view", return_value="Focused"):
        with pytest.raises(ValueError, match="All research agents failed"):
            await lead.dispatch_research(
                target_node=target_node,
                research_agents=[agent],
                tools=[],
                max_searches=5,
            )


@pytest.mark.asyncio
async def test_synthesize_directions_success():
    """Test Lead LLM successfully synthesizes directions."""
    adapter = MockAdapter()
    graph = MockGraph()

    target_node = create_mock_node("target", "Researched direction")

    # Create mock agent outputs
    output1 = AgentOutput(
        raw_text="Found evidence about market size: $50B by 2025. Growth rate 15%.",
        self_critique="Good research, multiple sources verified",
        searches_performed=[SearchRecord(
            query="market size",
            engine="tavily",
            timestamp=datetime.now(),
            results_summary="Found 10 results",
            urls_visited=[],
        )],
        cost_usd=0.10,
        duration_seconds=30.0,
        agent_name="agent-1",
        model="claude-opus",
        total_tokens=1000,
        input_tokens=500,
        output_tokens=500,
    )

    output2 = AgentOutput(
        raw_text="Market analysis confirms ~$50B estimate. Key players: Company A, B, C.",
        self_critique="Consensus with other research",
        searches_performed=[],
        cost_usd=0.08,
        duration_seconds=25.0,
        agent_name="agent-2",
        model="kimi-2.5",
        total_tokens=800,
        input_tokens=400,
        output_tokens=400,
    )

    # Mock synthesis response
    adapter.mock_response = json.dumps({
        "directions": [
            {
                "claim": "Investigate B2B vs B2C market fit",
                "confidence": 0.85,
                "importance": 0.9,
                "reasoning": "Both agents confirmed market size, need to understand segments",
                "evidence_summary": "Market size estimates aligned at ~$50B",
                "tags": ["market", "segmentation"]
            },
            {
                "claim": "Analyze competitive landscape of key players",
                "confidence": 0.75,
                "importance": 0.8,
                "reasoning": "Multiple companies identified, need deeper analysis",
                "evidence_summary": "Companies A, B, C mentioned as leaders",
                "tags": ["competition"]
            }
        ],
        "synthesis_reasoning": "Both agents agreed on market size, providing strong consensus",
        "consensus_directions": ["Market size ~$50B"],
        "contradictions": []
    })

    lead = LeadLLM(adapter=adapter, graph=graph, north_star="Test mission")

    # Execute
    synthesis = await lead.synthesize_directions(
        agent_outputs=[output1, output2],
        target_node=target_node,
    )

    # Verify
    assert len(synthesis.directions) == 2
    assert synthesis.directions[0].claim == "Investigate B2B vs B2C market fit"
    assert synthesis.directions[0].confidence == 0.85
    assert synthesis.directions[0].importance == 0.9
    assert len(synthesis.directions[0].tags) == 2

    assert synthesis.directions[1].claim == "Analyze competitive landscape of key players"
    assert len(synthesis.consensus_directions) == 1
    assert "Market size ~$50B" in synthesis.consensus_directions
    assert len(synthesis.contradictions) == 0

    # Verify synthesis reasoning was captured
    assert "Both agents agreed" in synthesis.synthesis_reasoning

    # Verify adapter was called correctly
    assert adapter.call_count == 1
    assert "Extract Directions" in adapter.last_system_prompt
    assert "$50B" in adapter.last_user_prompt


@pytest.mark.asyncio
async def test_synthesize_directions_fallback_invalid_json():
    """Test Lead LLM fallback when synthesis JSON is invalid."""
    adapter = MockAdapter()
    graph = MockGraph()

    target_node = create_mock_node("target", "Test direction")

    output = AgentOutput(
        raw_text="Research output",
        self_critique="Critique",
        searches_performed=[],
        cost_usd=0.05,
        duration_seconds=10.0,
        agent_name="agent-1",
        model="test",
        total_tokens=100,
        input_tokens=50,
        output_tokens=50,
    )

    # Mock invalid JSON
    adapter.mock_response = "This is not valid JSON"

    lead = LeadLLM(adapter=adapter, graph=graph, north_star="Test")

    synthesis = await lead.synthesize_directions(
        agent_outputs=[output],
        target_node=target_node,
    )

    # Should return fallback direction
    assert len(synthesis.directions) == 1
    assert "Continue investigating" in synthesis.directions[0].claim
    assert "Test direction" in synthesis.directions[0].claim
    assert synthesis.directions[0].confidence == 0.5
    assert "Fallback" in synthesis.directions[0].reasoning
    assert "parse failed" in synthesis.synthesis_reasoning.lower()


@pytest.mark.asyncio
async def test_synthesize_directions_fallback_parse_error():
    """Test Lead LLM fallback when JSON parsing fails."""
    adapter = MockAdapter()
    graph = MockGraph()

    target_node = create_mock_node("target", "Test direction")

    output = AgentOutput(
        raw_text="Research output",
        self_critique="Critique",
        searches_performed=[],
        cost_usd=0.05,
        duration_seconds=10.0,
        agent_name="agent-1",
        model="test",
        total_tokens=100,
        input_tokens=50,
        output_tokens=50,
    )

    # Mock malformed JSON (missing required fields)
    adapter.mock_response = json.dumps({
        "directions": [
            {"claim": "Missing required fields"}  # Missing confidence, importance, etc.
        ]
    })

    lead = LeadLLM(adapter=adapter, graph=graph, north_star="Test")

    synthesis = await lead.synthesize_directions(
        agent_outputs=[output],
        target_node=target_node,
    )

    # Should return fallback direction
    assert len(synthesis.directions) == 1
    assert "Continue investigating" in synthesis.directions[0].claim
    assert "Fallback" in synthesis.directions[0].reasoning
    assert "parse error" in synthesis.synthesis_reasoning.lower()


@pytest.mark.asyncio
async def test_synthesize_directions_with_contradictions():
    """Test Lead LLM correctly identifies contradictions."""
    adapter = MockAdapter()
    graph = MockGraph()

    target_node = create_mock_node("target", "Market size research")

    output1 = AgentOutput(
        raw_text="Market size is $50B",
        self_critique="Confident",
        searches_performed=[],
        cost_usd=0.05,
        duration_seconds=10.0,
        agent_name="agent-1",
        model="test",
        total_tokens=100,
        input_tokens=50,
        output_tokens=50,
    )

    output2 = AgentOutput(
        raw_text="Market size is only $30B",
        self_critique="Different estimate",
        searches_performed=[],
        cost_usd=0.05,
        duration_seconds=10.0,
        agent_name="agent-2",
        model="test",
        total_tokens=100,
        input_tokens=50,
        output_tokens=50,
    )

    # Mock synthesis with contradictions
    adapter.mock_response = json.dumps({
        "directions": [
            {
                "claim": "Verify actual market size estimate",
                "confidence": 0.4,
                "importance": 0.9,
                "reasoning": "Conflicting estimates need resolution",
                "evidence_summary": "One source says $50B, another says $30B",
                "tags": ["market-size"]
            }
        ],
        "synthesis_reasoning": "Agents disagreed on market size, need more research",
        "consensus_directions": [],
        "contradictions": ["Market size: $50B vs $30B"]
    })

    lead = LeadLLM(adapter=adapter, graph=graph, north_star="Test")

    synthesis = await lead.synthesize_directions(
        agent_outputs=[output1, output2],
        target_node=target_node,
    )

    # Verify contradictions captured
    assert len(synthesis.contradictions) == 1
    assert "Market size" in synthesis.contradictions[0]
    assert "$50B" in synthesis.contradictions[0] or "$30B" in synthesis.contradictions[0]

    # Verify direction has low confidence due to contradiction
    assert synthesis.directions[0].confidence < 0.5


@pytest.mark.asyncio
async def test_lead_llm_initialization():
    """Test Lead LLM initializes with correct properties."""
    adapter = MockAdapter("test-adapter")
    graph = MockGraph()
    north_star = "Test research mission"
    report = "Initial report content"

    lead = LeadLLM(
        adapter=adapter,
        graph=graph,
        north_star=north_star,
        report_content=report,
    )

    assert lead.adapter == adapter
    assert lead.graph == graph
    assert lead.north_star == north_star
    assert lead.report_content == report


@pytest.mark.asyncio
async def test_synthesize_multiple_agents():
    """Test synthesis handles multiple research agents correctly."""
    adapter = MockAdapter()
    graph = MockGraph()

    target_node = create_mock_node("target", "Multi-agent research")

    # Create 3 agent outputs
    outputs = []
    for i in range(3):
        outputs.append(AgentOutput(
            raw_text=f"Agent {i+1} research findings...",
            self_critique=f"Agent {i+1} critique",
            searches_performed=[],
            cost_usd=0.05,
            duration_seconds=10.0,
            agent_name=f"agent-{i+1}",
            model="test",
            total_tokens=100,
            input_tokens=50,
            output_tokens=50,
        ))

    # Mock synthesis response
    adapter.mock_response = json.dumps({
        "directions": [
            {
                "claim": "Direction synthesized from all 3 agents",
                "confidence": 0.9,
                "importance": 0.85,
                "reasoning": "Strong consensus across all agents",
                "evidence_summary": "All agents corroborated findings",
                "tags": ["consensus"]
            }
        ],
        "synthesis_reasoning": "All 3 agents provided consistent findings",
        "consensus_directions": ["Direction synthesized from all 3 agents"],
        "contradictions": []
    })

    lead = LeadLLM(adapter=adapter, graph=graph, north_star="Test")

    synthesis = await lead.synthesize_directions(
        agent_outputs=outputs,
        target_node=target_node,
    )

    # Verify synthesis included all agents
    assert "Agent 1" in adapter.last_user_prompt
    assert "Agent 2" in adapter.last_user_prompt
    assert "Agent 3" in adapter.last_user_prompt

    # Verify high confidence from consensus
    assert synthesis.directions[0].confidence >= 0.9
