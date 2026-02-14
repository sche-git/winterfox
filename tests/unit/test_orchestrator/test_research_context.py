"""
Tests for research context builder.

Verifies that accumulated knowledge from prior cycles is correctly
assembled into a token-budgeted context string for agent prompts.
"""

import pytest
from datetime import datetime

from winterfox.graph.store import KnowledgeGraph
from winterfox.graph.models import Evidence
from winterfox.orchestrator.research_context import (
    ResearchContext,
    ResearchContextBuilder,
    TokenBudget,
)
from winterfox.orchestrator.prompts import generate_research_prompt
from winterfox.agents.protocol import AgentOutput, Finding, SearchRecord


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
async def graph_with_cycles(graph):
    """Graph with root node and 3 completed cycles of data."""
    # Add root node
    root = await graph.add_node(
        claim="What is the market opportunity for legal tech?",
        confidence=0.3,
        importance=1.0,
        created_by_cycle=0,
    )

    # Simulate 3 cycles of research
    for cycle_id in range(1, 4):
        # Add a child node per cycle
        child = await graph.add_node(
            claim=f"Finding from cycle {cycle_id}: legal tech market is growing",
            parent_id=root.id,
            confidence=0.5 + cycle_id * 0.1,
            importance=0.7,
            created_by_cycle=cycle_id,
        )

        # Build agent outputs
        findings = [
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
        ]

        searches = [
            SearchRecord(
                query=f"legal tech market size 202{cycle_id}",
                engine="tavily",
                timestamp=datetime.now(),
                results_summary=f"Found {cycle_id} results",
                urls_visited=[f"https://example.com/{cycle_id}"],
            ),
            SearchRecord(
                query="legal technology TAM Gartner",
                engine="brave",
                timestamp=datetime.now(),
                results_summary="Gartner report found",
                urls_visited=["https://gartner.com/legal"],
            ),
        ]

        agent_output = AgentOutput(
            findings=findings,
            self_critique=f"Gaps remain in Asian market data for cycle {cycle_id}. "
            f"Need more sources on regulatory compliance.",
            raw_text=f"Raw output from cycle {cycle_id}",
            searches_performed=searches,
            cost_usd=0.05 * cycle_id,
            duration_seconds=10.0,
            agent_name="claude-opus-4",
            model="claude-opus-4-20251120",
            total_tokens=1000 * cycle_id,
            input_tokens=800 * cycle_id,
            output_tokens=200 * cycle_id,
        )

        # Build synthesis result with contradictions for cycle 2
        synthesis_result = None
        if cycle_id == 2:
            from winterfox.agents.pool import SynthesisResult

            synthesis_result = SynthesisResult(
                findings=findings,
                synthesis_reasoning="Multiple sources agree on range $2.1-2.8B. "
                "Market growing at 12-15% CAGR.",
                consensus_findings=["Legal tech market size is $2.3-2.6B"],
                contradictions=[
                    {
                        "description": "TAM estimates range $1.9B to $2.8B "
                        "(scope definition differs between sources)"
                    }
                ],
                individual_outputs=[agent_output],
                total_cost_usd=agent_output.cost_usd,
                total_duration_seconds=agent_output.duration_seconds,
            )

        # Save cycle output
        await graph.save_cycle_output(
            cycle_id=cycle_id,
            target_node=root if cycle_id == 1 else child,
            agent_outputs=[agent_output],
            synthesis_result=synthesis_result,
            merge_stats={"created": 1, "updated": 0, "skipped": 0},
            duration_seconds=10.0,
            total_cost_usd=agent_output.cost_usd,
            success=True,
            error_message=None,
        )

    return graph


# --- TokenBudget Tests ---


class TestTokenBudget:
    def test_default_values(self):
        budget = TokenBudget()
        assert budget.summary_view == 3200
        assert budget.prior_cycles == 4800
        assert budget.search_history == 2400
        assert budget.contradictions == 1600
        assert budget.weakest_nodes == 1600
        assert budget.open_questions == 2400

    def test_custom_values(self):
        budget = TokenBudget(summary_view=1000, prior_cycles=2000)
        assert budget.summary_view == 1000
        assert budget.prior_cycles == 2000
        # Others remain default
        assert budget.search_history == 2400


# --- ResearchContext Tests ---


class TestResearchContext:
    def test_empty_context_renders_empty(self):
        ctx = ResearchContext()
        assert ctx.render() == ""
        assert ctx.total_prior_cycles == 0

    def test_render_with_all_sections(self):
        ctx = ResearchContext(
            graph_summary="Graph overview here",
            prior_cycle_summaries="Cycle 1: did stuff",
            search_history='- "legal tech market"',
            contradictions="- TAM estimates differ",
            weakest_nodes="1. Low confidence node",
            open_questions="- Need Asian market data",
            total_prior_cycles=3,
        )
        rendered = ctx.render()

        assert "## Accumulated Research Context (3 prior cycles)" in rendered
        assert "### Knowledge Graph Overview" in rendered
        assert "Graph overview here" in rendered
        assert "### Prior Cycle Summaries" in rendered
        assert "### Prior Searches (avoid repeating these)" in rendered
        assert "### Unresolved Contradictions" in rendered
        assert "### Areas Needing Attention" in rendered
        assert "### Open Questions from Prior Research" in rendered

    def test_render_skips_empty_sections(self):
        ctx = ResearchContext(
            graph_summary="Graph overview",
            total_prior_cycles=1,
        )
        rendered = ctx.render()

        assert "### Knowledge Graph Overview" in rendered
        assert "### Prior Cycle Summaries" not in rendered
        assert "### Prior Searches" not in rendered

    def test_render_requires_prior_cycles(self):
        ctx = ResearchContext(
            graph_summary="Something",
            total_prior_cycles=0,
        )
        assert ctx.render() == ""


# --- ResearchContextBuilder Tests ---


class TestResearchContextBuilder:
    @pytest.mark.asyncio
    async def test_first_cycle_returns_empty(self, graph):
        """First cycle (no prior data) should return empty context."""
        builder = ResearchContextBuilder(graph)
        ctx = await builder.build()

        assert ctx.total_prior_cycles == 0
        assert ctx.render() == ""

    @pytest.mark.asyncio
    async def test_builds_context_from_prior_cycles(self, graph_with_cycles):
        """Context should include data from prior cycles."""
        builder = ResearchContextBuilder(graph_with_cycles)
        ctx = await builder.build()

        assert ctx.total_prior_cycles == 3
        assert ctx.graph_summary != ""
        assert ctx.prior_cycle_summaries != ""

    @pytest.mark.asyncio
    async def test_includes_search_history(self, graph_with_cycles):
        """Search history should include deduplicated prior queries."""
        builder = ResearchContextBuilder(graph_with_cycles)
        ctx = await builder.build()

        assert ctx.search_history != ""
        assert "legal tech market size" in ctx.search_history
        assert "legal technology TAM Gartner" in ctx.search_history
        # Verify deduplication — "legal technology TAM Gartner" appears once despite
        # being in every cycle
        count = ctx.search_history.count("legal technology TAM Gartner")
        assert count == 1

    @pytest.mark.asyncio
    async def test_includes_contradictions(self, graph_with_cycles):
        """Contradictions from synthesis should be surfaced."""
        builder = ResearchContextBuilder(graph_with_cycles)
        ctx = await builder.build()

        assert ctx.contradictions != ""
        assert "TAM estimates range" in ctx.contradictions

    @pytest.mark.asyncio
    async def test_includes_graph_summary(self, graph_with_cycles):
        """Graph summary should render the knowledge tree."""
        builder = ResearchContextBuilder(graph_with_cycles)
        ctx = await builder.build()

        assert "Knowledge Graph Summary" in ctx.graph_summary

    @pytest.mark.asyncio
    async def test_includes_weakest_nodes(self, graph_with_cycles):
        """Weakest nodes should be identified."""
        builder = ResearchContextBuilder(graph_with_cycles)
        ctx = await builder.build()

        assert ctx.weakest_nodes != ""
        assert "Priority" in ctx.weakest_nodes

    @pytest.mark.asyncio
    async def test_includes_open_questions(self, graph_with_cycles):
        """Open questions from self-critiques should be included."""
        builder = ResearchContextBuilder(graph_with_cycles)
        ctx = await builder.build()

        assert ctx.open_questions != ""
        assert "Asian market data" in ctx.open_questions

    @pytest.mark.asyncio
    async def test_truncation_respects_budget(self, graph_with_cycles):
        """Sections should be truncated to respect token budget."""
        tiny_budget = TokenBudget(
            summary_view=50,
            prior_cycles=50,
            search_history=50,
            contradictions=50,
            weakest_nodes=50,
            open_questions=50,
        )
        builder = ResearchContextBuilder(graph_with_cycles, budget=tiny_budget)
        ctx = await builder.build()

        # Each section should be truncated (or short enough already)
        for section in [
            ctx.graph_summary,
            ctx.prior_cycle_summaries,
            ctx.search_history,
        ]:
            if section:
                assert len(section) <= 50 + 50  # budget + truncation suffix

    @pytest.mark.asyncio
    async def test_render_assembles_all_sections(self, graph_with_cycles):
        """render() should combine all non-empty sections."""
        builder = ResearchContextBuilder(graph_with_cycles)
        ctx = await builder.build()
        rendered = ctx.render()

        assert "## Accumulated Research Context" in rendered
        assert "3 prior cycles" in rendered
        assert "### Knowledge Graph Overview" in rendered
        assert "### Prior Cycle Summaries" in rendered
        assert "### Prior Searches" in rendered


# --- Backward Compatibility Tests ---


class TestBackwardCompatibility:
    @pytest.mark.asyncio
    async def test_prompts_work_without_research_context(self, graph):
        """Existing prompts should work with research_context=None."""
        root = await graph.add_node(
            claim="Test claim",
            confidence=0.5,
            importance=0.8,
            created_by_cycle=0,
        )

        system_prompt, user_prompt = await generate_research_prompt(
            graph=graph,
            target_node=root,
            north_star="Test mission",
            max_searches=25,
        )

        # Prompts should generate without error
        assert "Test mission" in system_prompt
        assert "Test claim" in user_prompt
        # No accumulated context section
        assert "Accumulated Research Context" not in user_prompt

    @pytest.mark.asyncio
    async def test_prompts_include_research_context(self, graph):
        """When research_context is provided, it should appear in user prompt."""
        root = await graph.add_node(
            claim="Test claim",
            confidence=0.5,
            importance=0.8,
            created_by_cycle=0,
        )

        mock_context = (
            "## Accumulated Research Context (5 prior cycles)\n\n"
            "### Prior Searches\n- \"test query\""
        )

        system_prompt, user_prompt = await generate_research_prompt(
            graph=graph,
            target_node=root,
            north_star="Test mission",
            research_context=mock_context,
        )

        assert "Accumulated Research Context" in user_prompt
        assert "test query" in user_prompt
        # System prompt should have guideline #6
        assert "Build on prior work" in system_prompt


# --- Store Batch Query Tests ---


class TestStoreBatchQueries:
    @pytest.mark.asyncio
    async def test_get_all_search_queries_empty(self, graph):
        """No cycles means no search queries."""
        results = await graph.get_all_search_queries()
        assert results == []

    @pytest.mark.asyncio
    async def test_get_all_search_queries(self, graph_with_cycles):
        """Should return all search queries from agent outputs."""
        results = await graph_with_cycles.get_all_search_queries()

        assert len(results) > 0
        queries = [r["query"] for r in results]
        assert any("legal tech market" in q for q in queries)
        assert all("engine" in r for r in results)

    @pytest.mark.asyncio
    async def test_get_recent_critiques_empty(self, graph):
        """No cycles means no critiques."""
        results = await graph.get_recent_critiques()
        assert results == []

    @pytest.mark.asyncio
    async def test_get_recent_critiques(self, graph_with_cycles):
        """Should return critiques with agent name and cycle id."""
        results = await graph_with_cycles.get_recent_critiques()

        assert len(results) > 0
        assert all("agent_name" in r for r in results)
        assert all("cycle_id" in r for r in results)
        assert all("self_critique" in r for r in results)
        assert any("Asian market" in r["self_critique"] for r in results)
