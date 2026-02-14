"""
Winterfox - Autonomous research system with multi-agent knowledge compounding.

An open-source Python package for running autonomous research cycles that
compound knowledge in a graph structure using multi-agent consensus.

Example:
    import asyncio
    from winterfox import KnowledgeGraph, Orchestrator
    from winterfox.agents.adapters import AnthropicAdapter
    from winterfox.orchestrator.lead import LeadLLM

    async def main():
        graph = KnowledgeGraph(".winterfox/graph.db")
        await graph.initialize()

        lead = LeadLLM(
            adapter=AnthropicAdapter(model="claude-sonnet-4-20250514"),
            graph=graph,
            north_star="Your research mission",
        )
        agents = [AnthropicAdapter(model="claude-sonnet-4-20250514")]

        orchestrator = Orchestrator(
            graph=graph,
            lead_llm=lead,
            research_agents=agents,
            north_star="Your research mission",
            tools=[],
        )

        results = await orchestrator.run_cycles(n=10)
        print(orchestrator.get_summary())

    asyncio.run(main())
"""

__version__ = "0.1.0"

# Core exports
from .graph.store import KnowledgeGraph
from .graph.models import KnowledgeNode, Evidence
from .orchestrator import Orchestrator
from .agents.protocol import AgentAdapter, AgentOutput

__all__ = [
    "__version__",
    "KnowledgeGraph",
    "KnowledgeNode",
    "Evidence",
    "Orchestrator",
    "AgentAdapter",
    "AgentOutput",
]
