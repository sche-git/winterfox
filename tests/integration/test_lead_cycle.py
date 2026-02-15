"""
Integration tests for full research cycle with Lead LLM architecture.

These tests verify end-to-end cycle execution:
- Complete cycle from selection to merge
- Lead LLM + research agents coordination
- Direction synthesis and graph updates
- Database persistence
- Cost tracking
"""

import json
import pytest
from datetime import datetime
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

from winterfox.graph.store import KnowledgeGraph
from winterfox.graph.models import Evidence, KnowledgeNode
from winterfox.orchestrator import Orchestrator
from winterfox.orchestrator.lead import LeadLLM, Direction
from winterfox.orchestrator.cycle import ResearchCycle
from winterfox.agents.protocol import AgentOutput, SearchRecord


class MockAdapter:
    """Mock LLM adapter for integration testing."""

    def __init__(self, name: str = "mock-agent", responses: list[str] = None):
        self._name = name
        self.call_count = 0
        self.responses = responses or []
        self.response_index = 0

    @property
    def name(self) -> str:
        return self._name

    async def verify(self):
        """Mock verification - always succeeds."""
        pass

    async def run(self, system_prompt, user_prompt, tools, max_iterations=30):
        self.call_count += 1

        # Return next response from list
        if self.response_index < len(self.responses):
            response_text = self.responses[self.response_index]
            self.response_index += 1
        else:
            response_text = "Mock response"

        return AgentOutput(
            raw_text=response_text,
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


@pytest.fixture
async def test_graph(tmp_path):
    """Create test knowledge graph with initial node."""
    db_path = tmp_path / "test.db"
    graph = KnowledgeGraph(str(db_path), workspace_id="test")
    await graph.initialize()

    # Create test workspace
    async with graph._get_db() as db:
        await db.execute(
            "INSERT OR IGNORE INTO workspaces (id, name, tier) VALUES (?, ?, ?)",
            ("test", "Test Workspace", "free"),
        )
        await db.commit()

    # Add initial research direction
    await graph.add_node(
        claim="What is the AI startup landscape?",
        confidence=0.3,
        importance=1.0,
        depth=0,
        node_type="direction",
        created_by_cycle=0,
    )

    yield graph

    await graph.close()


@pytest.mark.asyncio
async def test_full_cycle_execution(test_graph, tmp_path):
    """Test complete cycle execution with Lead LLM architecture."""
    initial_node = (await test_graph.get_all_active_nodes())[0]

    # Setup Lead LLM adapter with predetermined responses
    lead_responses = [
        # Response 1: Node selection
        json.dumps({
            "selected_node_id": initial_node.id[:8],
            "reasoning": "This direction has low confidence and needs investigation"
        }),
        # Response 2: Direction synthesis
        json.dumps({
            "directions": [
                {
                    "claim": "Investigate AI startup funding trends",
                    "description": "Develop a full landscape of AI startup funding by stage, geography, and sector to understand where capital concentration is strongest and where whitespace remains. Compare year-over-year momentum, average round sizes, investor mix, and graduation rates between seed, Series A, and growth rounds. Identify structural drivers behind funding acceleration, such as enterprise demand, model cost curves, and platform distribution leverage. Clarify which patterns appear durable versus cyclical, and map the implications for strategic positioning in the next research cycles.",
                    "confidence": 0.8,
                    "importance": 0.9,
                    "reasoning": "Multiple agents found consistent data on funding",
                    "evidence_summary": "VC funding increased 30% YoY",
                    "tags": ["funding", "trends"]
                },
                {
                    "claim": "Explore top AI startup categories",
                    "description": "Break down AI startup activity into category-level segments and evaluate which categories are producing the strongest evidence of product-market fit and scalable economics. Compare adoption patterns, technical defensibility, and go-to-market friction across NLP, computer vision, robotics, and adjacent vertical applications. Distinguish categories with short-term hype from categories with repeatable enterprise value capture. Use this direction to prioritize which category hypotheses should be deepened first and which should be challenged with counter-evidence.",
                    "confidence": 0.75,
                    "importance": 0.85,
                    "reasoning": "Clear patterns in successful categories",
                    "evidence_summary": "NLP and computer vision leading",
                    "tags": ["categories"]
                }
            ],
            "synthesis_reasoning": "Both agents provided complementary insights",
            "consensus_directions": ["AI funding increased"],
            "contradictions": []
        })
    ]

    lead_adapter = MockAdapter("lead-llm", responses=lead_responses)

    # Setup research agents with mock research outputs
    agent1_responses = [
        "Research findings: AI startup funding reached $50B in 2024. "
        "VC investment increased 30% year-over-year. "
        "Key sectors: NLP (40%), Computer Vision (30%), Robotics (20%). "
        "Sources: TechCrunch, CB Insights."
    ]

    agent2_responses = [
        "Market analysis: Top AI startup categories are NLP and CV. "
        "Funding rounds average $10M Series A, $30M Series B. "
        "Success rate: 15% reach Series B. "
        "Sources: PitchBook, VentureBeat."
    ]

    agent1 = MockAdapter("research-agent-1", responses=agent1_responses)
    agent2 = MockAdapter("research-agent-2", responses=agent2_responses)

    # Create Lead LLM
    lead_llm = LeadLLM(
        adapter=lead_adapter,
        graph=test_graph,
        north_star="Understand the AI startup landscape",
    )

    # Create Orchestrator
    orchestrator = Orchestrator(
        graph=test_graph,
        lead_llm=lead_llm,
        research_agents=[agent1, agent2],
        north_star="Understand the AI startup landscape",
        tools=[],  # Mock tools
        max_searches_per_cycle=10,
        report_interval=10,
        raw_output_dir=tmp_path / "raw",
    )

    # Run one cycle
    result = await orchestrator.run_cycle()

    # Verify cycle completed successfully
    assert result.success, f"Cycle failed: {result.error_message}"
    assert result.cycle_id == 1
    assert result.directions_created > 0 or result.directions_updated > 0

    # Verify Lead LLM was called for selection and synthesis
    assert lead_adapter.call_count >= 2  # At least selection + synthesis

    # Verify research agents were called
    assert agent1.call_count >= 1
    assert agent2.call_count >= 1

    # Verify directions were created in graph
    all_nodes = await test_graph.get_all_active_nodes()
    assert len(all_nodes) > 1  # Initial node + new directions
    assert any(
        node.parent_id == initial_node.id and node.depth == 1
        for node in all_nodes
    ), "Child directions should be persisted at parent depth + 1"

    # Verify costs tracked
    assert result.total_cost_usd > 0
    assert result.lead_llm_cost_usd > 0 or result.research_cost_usd > 0

    # Verify orchestrator state updated
    assert orchestrator.cycle_count == 1
    assert len(orchestrator.cycle_history) == 1


@pytest.mark.asyncio
async def test_multiple_cycles(test_graph, tmp_path):
    """Test running multiple research cycles."""

    # Setup mock adapters with multiple responses
    lead_responses = [
        # Cycle 1 selection
        json.dumps({
            "selected_node_id": (await test_graph.get_all_active_nodes())[0].id[:8],
            "reasoning": "First cycle selection"
        }),
        # Cycle 1 synthesis
        json.dumps({
            "directions": [{
                "claim": "Direction from cycle 1",
                "description": "Create a comprehensive first-cycle framing that captures the strongest initial signals, unresolved questions, and assumptions requiring independent validation. This direction should establish a durable baseline for subsequent cycles by separating observed facts from interpretation and by documenting where evidence density is currently weak. Include concrete follow-up avenues for both depth and breadth exploration so future cycles can compound knowledge without repeating low-value searches.",
                "confidence": 0.7,
                "importance": 0.8,
                "reasoning": "First investigation",
                "evidence_summary": "Initial findings",
                "tags": []
            }],
            "synthesis_reasoning": "Cycle 1 synthesis",
            "consensus_directions": [],
            "contradictions": []
        }),
        # Cycle 2 selection
        json.dumps({
            "selected_node_id": (await test_graph.get_all_active_nodes())[0].id[:8],
            "reasoning": "Second cycle selection"
        }),
        # Cycle 2 synthesis
        json.dumps({
            "directions": [{
                "claim": "Direction from cycle 2",
                "description": "Refine the first-cycle baseline with additional corroboration, stronger counterfactual analysis, and clearer decision implications. This direction should capture what changed after follow-up research, which assumptions were strengthened or weakened, and where contradictions still require targeted resolution. Document next-cycle priorities that maximize learning velocity while maintaining evidence quality standards.",
                "confidence": 0.75,
                "importance": 0.85,
                "reasoning": "Second investigation",
                "evidence_summary": "Follow-up findings",
                "tags": []
            }],
            "synthesis_reasoning": "Cycle 2 synthesis",
            "consensus_directions": [],
            "contradictions": []
        })
    ]

    lead_adapter = MockAdapter("lead-llm", responses=lead_responses)

    agent_responses = [
        "Research output cycle 1",
        "Research output cycle 2"
    ]
    research_agent = MockAdapter("research-agent", responses=agent_responses)

    lead_llm = LeadLLM(
        adapter=lead_adapter,
        graph=test_graph,
        north_star="Test mission",
    )

    orchestrator = Orchestrator(
        graph=test_graph,
        lead_llm=lead_llm,
        research_agents=[research_agent],
        north_star="Test mission",
        tools=[],
        raw_output_dir=tmp_path / "raw",
    )

    # Run 2 cycles
    results = await orchestrator.run_cycles(n=2)

    # Verify both cycles completed
    assert len(results) == 2
    assert all(r.success for r in results)

    # Verify cycle IDs increment
    assert results[0].cycle_id == 1
    assert results[1].cycle_id == 2

    # Verify orchestrator state
    assert orchestrator.cycle_count == 2
    assert len(orchestrator.cycle_history) == 2

    # Verify cumulative cost
    total_cost = sum(r.total_cost_usd for r in results)
    assert orchestrator.total_cost_usd == pytest.approx(total_cost, rel=0.01)


@pytest.mark.asyncio
async def test_cycle_with_consensus(test_graph, tmp_path):
    """Test cycle with multi-agent consensus detection."""

    lead_responses = [
        # Selection
        json.dumps({
            "selected_node_id": (await test_graph.get_all_active_nodes())[0].id[:8],
            "reasoning": "Testing consensus"
        }),
        # Synthesis with consensus
        json.dumps({
            "directions": [
                {
                    "claim": "Consensus direction",
                    "description": "Synthesize a high-confidence direction supported independently by multiple agents and source pathways. Detail the specific agreement points, why those points are strategically important, and which parts of the consensus are robust versus still conditional. Translate the consensus into practical next decisions, including what should be prioritized immediately and what should remain under active monitoring for potential reversals.",
                    "confidence": 0.9,  # High confidence from consensus
                    "importance": 0.95,
                    "reasoning": "All agents agreed on this",
                    "evidence_summary": "Corroborated by multiple sources",
                    "tags": ["consensus"]
                }
            ],
            "synthesis_reasoning": "Strong consensus across all agents",
            "consensus_directions": ["All agents agree on market trend"],
            "contradictions": []
        })
    ]

    lead_adapter = MockAdapter("lead-llm", responses=lead_responses)

    # Multiple agents with similar findings
    agent1 = MockAdapter("agent-1", responses=["Finding: Market is $50B"])
    agent2 = MockAdapter("agent-2", responses=["Finding: Market ~$50B"])
    agent3 = MockAdapter("agent-3", responses=["Finding: $50B market size"])

    lead_llm = LeadLLM(
        adapter=lead_adapter,
        graph=test_graph,
        north_star="Test mission",
    )

    orchestrator = Orchestrator(
        graph=test_graph,
        lead_llm=lead_llm,
        research_agents=[agent1, agent2, agent3],
        north_star="Test mission",
        tools=[],
        raw_output_dir=tmp_path / "raw",
    )

    result = await orchestrator.run_cycle()

    # Verify consensus was detected
    assert result.success
    assert len(result.consensus_directions) > 0
    assert "All agents agree" in result.consensus_directions[0]

    # Verify high confidence from consensus
    nodes = await test_graph.get_all_active_nodes()
    consensus_node = next((n for n in nodes if "Consensus" in n.claim), None)
    if consensus_node:
        assert consensus_node.confidence >= 0.6


@pytest.mark.asyncio
async def test_cycle_with_contradictions(test_graph, tmp_path):
    """Test cycle detecting contradictions between agents."""

    lead_responses = [
        # Selection
        json.dumps({
            "selected_node_id": (await test_graph.get_all_active_nodes())[0].id[:8],
            "reasoning": "Testing contradictions"
        }),
        # Synthesis with contradictions
        json.dumps({
            "directions": [
                {
                    "claim": "Verify conflicting market size estimates",
                    "description": "Run a structured reconciliation of conflicting market size claims by decomposing each estimate into scope, timeframe, methodology, and data provenance. Identify whether disagreement is caused by definitional boundaries, outdated baselines, top-down versus bottom-up modeling, or selective sampling effects. Establish a transparent comparison framework and define the minimum evidence needed to converge on a defensible range. Use this direction to reduce uncertainty before making downstream strategic commitments.",
                    "confidence": 0.4,  # Low confidence due to contradiction
                    "importance": 0.9,
                    "reasoning": "Agents disagreed, needs resolution",
                    "evidence_summary": "Estimates range from $30B to $60B",
                    "tags": ["conflict"]
                }
            ],
            "synthesis_reasoning": "Agents provided conflicting estimates",
            "consensus_directions": [],
            "contradictions": ["Market size: $30B vs $50B vs $60B"]
        })
    ]

    lead_adapter = MockAdapter("lead-llm", responses=lead_responses)

    # Agents with conflicting findings
    agent1 = MockAdapter("agent-1", responses=["Market is $30B"])
    agent2 = MockAdapter("agent-2", responses=["Market is $50B"])
    agent3 = MockAdapter("agent-3", responses=["Market is $60B"])

    lead_llm = LeadLLM(
        adapter=lead_adapter,
        graph=test_graph,
        north_star="Test mission",
    )

    orchestrator = Orchestrator(
        graph=test_graph,
        lead_llm=lead_llm,
        research_agents=[agent1, agent2, agent3],
        north_star="Test mission",
        tools=[],
        raw_output_dir=tmp_path / "raw",
    )

    result = await orchestrator.run_cycle()

    # Verify contradictions were detected
    assert result.success
    assert len(result.contradictions) > 0
    assert "Market size" in result.contradictions[0]


@pytest.mark.asyncio
async def test_cycle_cost_tracking(test_graph, tmp_path):
    """Test separate cost tracking for Lead LLM vs Research agents."""

    lead_responses = [
        json.dumps({"selected_node_id": (await test_graph.get_all_active_nodes())[0].id[:8], "reasoning": "Test"}),
        json.dumps({
            "directions": [{
                "claim": "Test direction",
                "description": "Construct a robust test direction that verifies core claims with independent evidence and captures edge cases that could overturn initial conclusions. The goal is to stress-test assumptions, confirm data recency, and surface hidden dependencies that affect decision quality. The result should leave a clear audit trail for why confidence and importance were scored as they were.",
                "confidence": 0.7,
                "importance": 0.8,
                "reasoning": "Test",
                "evidence_summary": "Test",
                "tags": []
            }],
            "synthesis_reasoning": "Test",
            "consensus_directions": [],
            "contradictions": []
        })
    ]

    # Lead LLM with specific cost
    lead_adapter = MockAdapter("lead-llm", responses=lead_responses)

    # Research agents with different costs
    agent1 = MockAdapter("agent-1", responses=["Research 1"])
    agent2 = MockAdapter("agent-2", responses=["Research 2"])

    lead_llm = LeadLLM(adapter=lead_adapter, graph=test_graph, north_star="Test")

    orchestrator = Orchestrator(
        graph=test_graph,
        lead_llm=lead_llm,
        research_agents=[agent1, agent2],
        north_star="Test",
        tools=[],
        raw_output_dir=tmp_path / "raw",
    )

    result = await orchestrator.run_cycle()

    # Verify separate cost tracking
    assert result.lead_llm_cost_usd >= 0
    assert result.research_cost_usd >= 0
    assert result.total_cost_usd == pytest.approx(
        result.lead_llm_cost_usd + result.research_cost_usd,
        rel=0.01
    )


@pytest.mark.asyncio
async def test_cycle_database_persistence(test_graph, tmp_path):
    """Test that cycle outputs are persisted to database."""

    lead_responses = [
        json.dumps({"selected_node_id": (await test_graph.get_all_active_nodes())[0].id[:8], "reasoning": "Persistence test"}),
        json.dumps({
            "directions": [{
                "claim": "Persisted direction",
                "description": "Define a direction specifically designed to verify persistence behavior and end-to-end traceability across cycle output, synthesized insight, and graph updates. It should include enough context to confirm that rich narrative content survives storage, retrieval, and API serialization without loss. This direction also validates that historical reconstruction remains possible from saved records.",
                "confidence": 0.8,
                "importance": 0.9,
                "reasoning": "Testing persistence",
                "evidence_summary": "Should be saved",
                "tags": ["persistence"]
            }],
            "synthesis_reasoning": "Testing DB persistence",
            "consensus_directions": ["Consensus item"],
            "contradictions": ["Contradiction item"]
        })
    ]

    lead_adapter = MockAdapter("lead-llm", responses=lead_responses)
    research_agent = MockAdapter("research-agent", responses=["Research output"])

    lead_llm = LeadLLM(adapter=lead_adapter, graph=test_graph, north_star="Test")

    orchestrator = Orchestrator(
        graph=test_graph,
        lead_llm=lead_llm,
        research_agents=[research_agent],
        north_star="Test",
        tools=[],
        raw_output_dir=tmp_path / "raw",
    )

    result = await orchestrator.run_cycle()

    # Verify cycle was persisted
    cycle_output = await test_graph.get_cycle_output(result.cycle_id)
    assert cycle_output is not None
    assert cycle_output["cycle_id"] == result.cycle_id
    assert cycle_output["success"] == True
    assert cycle_output["total_cost_usd"] > 0

    # Verify consensus and contradictions saved
    assert len(cycle_output.get("consensus_findings", [])) > 0
    assert len(cycle_output.get("contradictions", [])) > 0


@pytest.mark.asyncio
async def test_cycle_error_handling(test_graph, tmp_path):
    """Test graceful error handling when synthesis fails."""

    lead_responses = [
        # Selection succeeds
        json.dumps({
            "selected_node_id": (await test_graph.get_all_active_nodes())[0].id[:8],
            "reasoning": "Testing error handling"
        }),
        # Synthesis returns invalid JSON
        "This is not valid JSON at all"
    ]

    lead_adapter = MockAdapter("lead-llm", responses=lead_responses)
    research_agent = MockAdapter("research-agent", responses=["Research completed"])

    lead_llm = LeadLLM(adapter=lead_adapter, graph=test_graph, north_star="Test")

    orchestrator = Orchestrator(
        graph=test_graph,
        lead_llm=lead_llm,
        research_agents=[research_agent],
        north_star="Test",
        tools=[],
        raw_output_dir=tmp_path / "raw",
    )

    result = await orchestrator.run_cycle()

    # Cycle should still succeed with fallback direction
    assert result.success
    assert result.directions_created >= 1  # Fallback direction created

    # Verify fallback direction exists
    nodes = await test_graph.get_all_active_nodes()
    fallback_node = next((n for n in nodes if "Continue investigating" in n.claim), None)
    assert fallback_node is not None


@pytest.mark.asyncio
async def test_orchestrator_summary(test_graph, tmp_path):
    """Test orchestrator summary after multiple cycles."""

    lead_responses = [
        json.dumps({"selected_node_id": (await test_graph.get_all_active_nodes())[0].id[:8], "reasoning": "Cycle 1"}),
        json.dumps({
            "directions": [{
                "claim": "Direction 1",
                "description": "Capture the first storyline direction with enough narrative depth to explain strategic context, evidentiary basis, and immediate next actions. This should act as an anchor for multi-cycle comparison so later updates can show what changed and why.",
                "confidence": 0.7,
                "importance": 0.8,
                "reasoning": "Test",
                "evidence_summary": "Test",
                "tags": []
            }],
            "synthesis_reasoning": "Test",
            "consensus_directions": [],
            "contradictions": []
        }),
        json.dumps({"selected_node_id": (await test_graph.get_all_active_nodes())[0].id[:8], "reasoning": "Cycle 2"}),
        json.dumps({
            "directions": [{
                "claim": "Direction 2",
                "description": "Capture the second storyline direction as an evolution of prior work, highlighting newly validated claims, unresolved contradictions, and revised priorities. The narrative should be explicit about causal factors driving any confidence or importance changes.",
                "confidence": 0.75,
                "importance": 0.85,
                "reasoning": "Test",
                "evidence_summary": "Test",
                "tags": []
            }],
            "synthesis_reasoning": "Test",
            "consensus_directions": [],
            "contradictions": []
        })
    ]

    lead_adapter = MockAdapter("lead-llm", responses=lead_responses)
    research_agent = MockAdapter("research-agent", responses=["Output 1", "Output 2"])

    lead_llm = LeadLLM(adapter=lead_adapter, graph=test_graph, north_star="Test mission")

    orchestrator = Orchestrator(
        graph=test_graph,
        lead_llm=lead_llm,
        research_agents=[research_agent],
        north_star="Test mission",
        tools=[],
        raw_output_dir=tmp_path / "raw",
    )

    await orchestrator.run_cycles(n=2)

    summary = orchestrator.get_summary()

    # Verify summary contains key info
    assert "Total Cycles: 2" in summary
    assert "Lead LLM Architecture" in summary
    assert "Lead LLM:" in summary
    assert "Research Agents: 1" in summary
    assert "Total Cost:" in summary
    assert "Test mission" in summary
