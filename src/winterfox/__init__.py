"""
Winterfox - Autonomous research system with multi-agent knowledge compounding.

An open-source Python package for running autonomous research cycles that
compound knowledge in a graph structure using multi-agent consensus.

Example:
    import asyncio
    from winterfox import KnowledgeGraph, Orchestrator, AgentPool
    from winterfox.agents.adapters import AnthropicAdapter

    async def main():
        graph = KnowledgeGraph("research.db")
        await graph.initialize()

        agent_pool = AgentPool([
            AnthropicAdapter(model="claude-opus-4-20251120", api_key="...")
        ])

        orchestrator = Orchestrator(
            graph=graph,
            agent_pool=agent_pool,
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
from .agents.pool import AgentPool
from .agents.protocol import AgentAdapter, AgentOutput, Finding
from .config import ResearchConfig, load_config

__all__ = [
    "__version__",
    "KnowledgeGraph",
    "KnowledgeNode",
    "Evidence",
    "Orchestrator",
    "AgentPool",
    "AgentAdapter",
    "AgentOutput",
    "Finding",
    "ResearchConfig",
    "load_config",
]
