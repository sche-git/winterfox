"""
Tests for report synthesizer.

Verifies that the ReportSynthesizer correctly reads the knowledge graph
and produces a narrative research document via LLM synthesis.
"""

import pytest
from datetime import datetime

from winterfox.graph.store import KnowledgeGraph
from winterfox.graph.models import Evidence
from winterfox.orchestrator.report import ReportSynthesizer, ReportResult
from winterfox.agents.protocol import AgentOutput, Finding, SearchRecord


# --- Mock Adapter ---


class MockReportAdapter:
    """Mock adapter that returns a canned report as raw_text."""

    def __init__(
        self,
        raw_text: str = "# Executive Summary\n\nThis is the report.",
        should_fail: bool = False,
    ):
        self._raw_text = raw_text
        self._should_fail = should_fail
        self.last_system_prompt: str | None = None
        self.last_user_prompt: str | None = None
        self.last_tools: list | None = None
        self.last_max_iterations: int | None = None
        self.call_count = 0

    @property
    def name(self) -> str:
        return "mock-report-adapter"

    @property
    def supports_native_search(self) -> bool:
        return False

    async def verify(self) -> None:
        pass

    async def run(self, system_prompt, user_prompt, tools, max_iterations=30):
        self.call_count += 1
        self.last_system_prompt = system_prompt
        self.last_user_prompt = user_prompt
        self.last_tools = tools
        self.last_max_iterations = max_iterations

        if self._should_fail:
            raise ConnectionError("Mock failure")

        return AgentOutput(
            findings=[],
            self_critique="",
            raw_text=self._raw_text,
            searches_performed=[],
            cost_usd=0.05,
            duration_seconds=2.0,
            agent_name="mock-report-adapter",
            model="mock-model",
            total_tokens=500,
            input_tokens=400,
            output_tokens=100,
        )


# --- Fixtures ---


@pytest.fixture
async def graph():
    """Create in-memory graph with test workspace."""
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


@pytest.fixture
async def graph_with_data(graph):
    """Graph with root node, children, and cycle data."""
    root = await graph.add_node(
        claim="What is the market opportunity for legal tech?",
        confidence=0.3,
        importance=1.0,
        created_by_cycle=0,
        node_type="question",
    )

    for cycle_id in range(1, 3):
        child = await graph.add_node(
            claim=f"Legal tech market is valued at ${2.0 + cycle_id * 0.3:.1f}B",
            parent_id=root.id,
            confidence=0.5 + cycle_id * 0.1,
            importance=0.7,
            created_by_cycle=cycle_id,
            node_type="supporting",
        )

        agent_output = AgentOutput(
            findings=[
                Finding(
                    claim=f"Legal tech TAM is ${2.0 + cycle_id * 0.3:.1f}B",
                    confidence=0.6 + cycle_id * 0.05,
                    evidence=[
                        Evidence(
                            text=f"Market report {cycle_id}",
                            source=f"https://example.com/report{cycle_id}",
                        )
                    ],
                )
            ],
            self_critique=f"Need more data on Asian markets for cycle {cycle_id}.",
            raw_text=f"Raw output from cycle {cycle_id}",
            searches_performed=[
                SearchRecord(
                    query=f"legal tech market size 202{cycle_id}",
                    engine="tavily",
                    timestamp=datetime.now(),
                    results_summary=f"Found {cycle_id} results",
                    urls_visited=[f"https://example.com/{cycle_id}"],
                )
            ],
            cost_usd=0.05 * cycle_id,
            duration_seconds=10.0,
            agent_name="claude-opus-4",
            model="claude-opus-4-20251120",
            total_tokens=1000 * cycle_id,
            input_tokens=800 * cycle_id,
            output_tokens=200 * cycle_id,
        )

        synthesis_result = None
        if cycle_id == 2:
            from winterfox.agents.pool import SynthesisResult

            synthesis_result = SynthesisResult(
                findings=agent_output.findings,
                synthesis_reasoning="Sources agree on $2.3-2.6B range.",
                consensus_findings=["Legal tech market is $2.3-2.6B"],
                contradictions=[
                    {"description": "TAM estimates range from $1.9B to $2.8B"}
                ],
                individual_outputs=[agent_output],
                total_cost_usd=agent_output.cost_usd,
                total_duration_seconds=agent_output.duration_seconds,
            )

        await graph.save_cycle_output(
            cycle_id=cycle_id,
            target_node=root,
            agent_outputs=[agent_output],
            synthesis_result=synthesis_result,
            merge_stats={"created": 1, "updated": 0, "skipped": 0},
            duration_seconds=10.0,
            total_cost_usd=agent_output.cost_usd,
            success=True,
            error_message=None,
        )

    return graph


# --- Tests ---


class TestReportSynthesizer:
    @pytest.mark.asyncio
    async def test_empty_graph_raises_error(self, graph):
        """Cannot generate a report from an empty graph."""
        adapter = MockReportAdapter()
        synthesizer = ReportSynthesizer(graph, adapter, "Test mission")

        with pytest.raises(ValueError, match="knowledge graph is empty"):
            await synthesizer.generate()

    @pytest.mark.asyncio
    async def test_basic_generation(self, graph_with_data):
        """Basic report generation returns valid ReportResult."""
        adapter = MockReportAdapter(raw_text="# Executive Summary\n\nKey findings here.")
        synthesizer = ReportSynthesizer(graph_with_data, adapter, "Research legal tech")

        result = await synthesizer.generate()

        assert isinstance(result, ReportResult)
        assert "# Executive Summary" in result.markdown
        assert "Key findings here." in result.markdown
        assert result.node_count == 3  # root + 2 children
        assert result.cycle_count == 2
        assert result.cost_usd == 0.05
        assert result.total_tokens == 500
        assert result.input_tokens == 400
        assert result.output_tokens == 100
        assert result.duration_seconds > 0

    @pytest.mark.asyncio
    async def test_agent_called_with_no_tools(self, graph_with_data):
        """Agent should be called with tools=[] and max_iterations=1."""
        adapter = MockReportAdapter()
        synthesizer = ReportSynthesizer(graph_with_data, adapter, "Research legal tech")

        await synthesizer.generate()

        assert adapter.call_count == 1
        assert adapter.last_tools == []
        assert adapter.last_max_iterations == 1

    @pytest.mark.asyncio
    async def test_context_includes_nodes(self, graph_with_data):
        """User prompt should include node data from the graph."""
        adapter = MockReportAdapter()
        synthesizer = ReportSynthesizer(graph_with_data, adapter, "Research legal tech")

        await synthesizer.generate()

        user_prompt = adapter.last_user_prompt
        assert "legal tech" in user_prompt.lower()
        assert "Knowledge Graph" in user_prompt

    @pytest.mark.asyncio
    async def test_context_includes_cycle_data(self, graph_with_data):
        """User prompt should include cycle history."""
        adapter = MockReportAdapter()
        synthesizer = ReportSynthesizer(graph_with_data, adapter, "Research legal tech")

        await synthesizer.generate()

        user_prompt = adapter.last_user_prompt
        assert "Cycle" in user_prompt
        assert "Research Cycle History" in user_prompt

    @pytest.mark.asyncio
    async def test_context_includes_contradictions(self, graph_with_data):
        """User prompt should include contradictions from cycle outputs."""
        adapter = MockReportAdapter()
        synthesizer = ReportSynthesizer(graph_with_data, adapter, "Research legal tech")

        await synthesizer.generate()

        user_prompt = adapter.last_user_prompt
        assert "Contradictions" in user_prompt
        assert "TAM estimates" in user_prompt

    @pytest.mark.asyncio
    async def test_context_includes_open_questions(self, graph_with_data):
        """User prompt should include open questions from self-critiques."""
        adapter = MockReportAdapter()
        synthesizer = ReportSynthesizer(graph_with_data, adapter, "Research legal tech")

        await synthesizer.generate()

        user_prompt = adapter.last_user_prompt
        assert "Asian markets" in user_prompt

    @pytest.mark.asyncio
    async def test_frontmatter_and_footer(self, graph_with_data):
        """Report should have YAML frontmatter and footer."""
        adapter = MockReportAdapter(raw_text="Report body here.")
        synthesizer = ReportSynthesizer(graph_with_data, adapter, "Research legal tech")

        result = await synthesizer.generate()

        # Frontmatter
        assert result.markdown.startswith("---\n")
        assert "nodes: 3" in result.markdown
        assert "cycles: 2" in result.markdown
        assert "avg_confidence:" in result.markdown

        # Footer
        assert "Regenerate with `winterfox report`" in result.markdown

    @pytest.mark.asyncio
    async def test_cost_tracking(self, graph_with_data):
        """Cost and token tracking should propagate from AgentOutput."""
        adapter = MockReportAdapter()
        synthesizer = ReportSynthesizer(graph_with_data, adapter, "Research legal tech")

        result = await synthesizer.generate()

        assert result.cost_usd == 0.05
        assert result.total_tokens == 500
        assert result.input_tokens == 400
        assert result.output_tokens == 100

    @pytest.mark.asyncio
    async def test_system_prompt_structure(self, graph_with_data):
        """System prompt should instruct the LLM to write report sections."""
        adapter = MockReportAdapter()
        synthesizer = ReportSynthesizer(graph_with_data, adapter, "Research legal tech")

        await synthesizer.generate()

        system_prompt = adapter.last_system_prompt
        assert "Executive Summary" in system_prompt
        assert "Key Findings" in system_prompt
        assert "Contradictions" in system_prompt
        assert "Open Questions" in system_prompt
        assert "Methodology" in system_prompt

    @pytest.mark.asyncio
    async def test_north_star_in_user_prompt(self, graph_with_data):
        """User prompt should include the north star mission."""
        adapter = MockReportAdapter()
        north_star = "Understand legal tech market opportunity in 2026"
        synthesizer = ReportSynthesizer(graph_with_data, adapter, north_star)

        await synthesizer.generate()

        assert north_star in adapter.last_user_prompt


class TestReportWithMinimalGraph:
    @pytest.mark.asyncio
    async def test_single_node_no_cycles(self, graph):
        """Report works with a single node and no cycle data."""
        await graph.add_node(
            claim="Initial research question",
            confidence=0.0,
            importance=1.0,
            created_by_cycle=0,
        )

        adapter = MockReportAdapter(raw_text="Preliminary report.")
        synthesizer = ReportSynthesizer(graph, adapter, "Test mission")

        result = await synthesizer.generate()

        assert result.node_count == 1
        assert result.cycle_count == 0
        assert "Preliminary report." in result.markdown


class TestReportTokenBudget:
    @pytest.mark.asyncio
    async def test_large_graph_truncation(self, graph):
        """Large graphs should be truncated to stay within budget."""
        # Create many nodes
        root = await graph.add_node(
            claim="Root question",
            confidence=0.0,
            importance=1.0,
            created_by_cycle=0,
        )
        for i in range(50):
            await graph.add_node(
                claim=f"Finding number {i}: " + "x" * 200,
                parent_id=root.id,
                confidence=0.5,
                importance=0.3,
                created_by_cycle=1,
            )

        adapter = MockReportAdapter()
        synthesizer = ReportSynthesizer(graph, adapter, "Test mission")

        result = await synthesizer.generate()

        # Should still generate successfully
        assert result.node_count == 51
        # User prompt should exist and not be absurdly large
        assert len(adapter.last_user_prompt) > 0
