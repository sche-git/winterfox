"""
Cycle runner service for browser-initiated research execution.
"""

from __future__ import annotations

import asyncio
import logging
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from ...agents.tools import get_research_tools
from ...agents.tools.search import configure_search
from ...agents.tools.search.brave import BraveSearchProvider
from ...agents.tools.search.serper import SerperSearchProvider
from ...agents.tools.search.tavily import TavilySearchProvider
from ...config import ResearchConfig, load_config
from ...graph.store import KnowledgeGraph
from ...orchestrator import Orchestrator
from ...orchestrator.lead import LeadLLM
from ..models.api_models import ActiveCycleResponse, RunCycleRequest, RunCycleResponse
from ..websocket import get_connection_manager

logger = logging.getLogger(__name__)


class CycleAlreadyRunningError(RuntimeError):
    """Raised when a cycle start is requested while another cycle is active."""

    def __init__(self, cycle_id: int | None):
        self.cycle_id = cycle_id
        super().__init__("A cycle is already running")


class CycleRunner:
    """Runs cycles asynchronously and exposes active execution state."""

    def __init__(self, config_path: Path, db_path: str, workspace_id: str):
        self.config_path = config_path
        self.db_path = db_path
        self.workspace_id = workspace_id
        self._lock = asyncio.Lock()
        self._active_cycle = ActiveCycleResponse()
        self._active_task: asyncio.Task[None] | None = None

    async def close(self) -> None:
        """Cancel any active cycle task during app shutdown."""
        if self._active_task and not self._active_task.done():
            self._active_task.cancel()
            try:
                await self._active_task
            except asyncio.CancelledError:
                pass
        self._active_task = None
        self._active_cycle = ActiveCycleResponse()

    async def get_active_cycle(self) -> ActiveCycleResponse:
        """Get current active cycle status."""
        return self._active_cycle

    async def start_cycle(self, request: RunCycleRequest) -> RunCycleResponse:
        """
        Start a cycle asynchronously.

        Raises:
            CycleAlreadyRunningError: if another cycle is in progress
        """
        if self._lock.locked():
            raise CycleAlreadyRunningError(self._active_cycle.cycle_id)

        await self._lock.acquire()
        try:
            cycle_id = await self._get_next_cycle_id()
            started_at = datetime.now(UTC)

            self._active_cycle = ActiveCycleResponse(
                cycle_id=cycle_id,
                status="running",
                focus_node_id=request.target_node_id,
                current_step="queued",
                progress_percent=0,
            )

            self._active_task = asyncio.create_task(self._run_cycle(cycle_id, request))

            return RunCycleResponse(
                cycle_id=cycle_id,
                status="running",
                started_at=started_at,
            )
        except Exception:
            self._lock.release()
            raise

    async def _run_cycle(self, cycle_id: int, request: RunCycleRequest) -> None:
        """Execute one cycle end-to-end."""
        try:
            await self._execute_cycle(cycle_id, request)
        except Exception as e:
            logger.error("Web cycle %s failed before completion: %s", cycle_id, e, exc_info=True)
            await self._broadcast_event(
                {
                    "type": "cycle.failed",
                    "data": {
                        "cycle_id": cycle_id,
                        "error_message": str(e),
                    },
                }
            )
        finally:
            self._active_cycle = ActiveCycleResponse()
            self._lock.release()

    async def _execute_cycle(self, cycle_id: int, request: RunCycleRequest) -> None:
        """Build runtime dependencies and run a cycle."""
        config = load_config(self.config_path)
        graph = KnowledgeGraph(self.db_path, workspace_id=self.workspace_id)
        await graph.initialize()

        try:
            await self._sync_context_documents_to_db(graph, config)
            await self._bootstrap_graph_if_empty(graph, config)

            lead_adapter = self._create_adapter(config.lead_agent, config)
            research_adapters = [self._create_adapter(agent, config) for agent in config.agents]

            self._configure_search(config)

            lead_llm = LeadLLM(
                adapter=lead_adapter,
                graph=graph,
                north_star=config.get_north_star(self.config_path.parent),
                report_content=None,
            )

            orchestrator = Orchestrator(
                graph=graph,
                lead_llm=lead_llm,
                research_agents=research_adapters,
                north_star=config.get_north_star(self.config_path.parent),
                tools=get_research_tools(graph),
                max_searches_per_cycle=config.orchestrator.max_searches_per_agent,
                report_interval=config.orchestrator.report_interval,
                search_instructions=config.get_search_instructions(self.config_path.parent),
                context_files=config.get_context_files_content(self.config_path.parent),
                raw_output_dir=self.config_path.parent / config.storage.raw_output_dir,
                event_callback=self._handle_cycle_event,
            )

            result = await orchestrator.run_cycle(
                target_node_id=request.target_node_id,
                cycle_instruction=request.cycle_instruction,
            )

            if not result.success:
                raise RuntimeError(result.error_message or f"Cycle {cycle_id} failed")
        finally:
            await graph.close()

    async def _get_next_cycle_id(self) -> int:
        """Compute the next cycle id for this workspace."""
        graph = KnowledgeGraph(self.db_path, workspace_id=self.workspace_id)
        await graph.initialize()
        try:
            return (await graph.get_max_cycle_id()) + 1
        finally:
            await graph.close()

    async def _handle_cycle_event(self, event: dict[str, Any]) -> None:
        """Update active state and forward events to websocket subscribers."""
        event_type = event.get("type", "")
        data = event.get("data", {})

        if event_type == "cycle.started":
            self._active_cycle.focus_node_id = data.get("focus_node_id")
            self._active_cycle.current_step = "started"
            self._active_cycle.progress_percent = 5
        elif event_type == "cycle.step":
            self._active_cycle.current_step = data.get("step")
            self._active_cycle.progress_percent = int(data.get("progress_percent", 0))
        elif event_type in {"cycle.completed", "cycle.failed"}:
            self._active_cycle.progress_percent = 100

        await self._broadcast_event(event)

    async def _broadcast_event(self, event: dict[str, Any]) -> None:
        manager = get_connection_manager()
        await manager.broadcast(event, self.workspace_id)

    async def _bootstrap_graph_if_empty(
        self,
        graph: KnowledgeGraph,
        config: ResearchConfig,
    ) -> None:
        nodes = await graph.get_all_active_nodes()
        if nodes:
            return

        north_star = config.get_north_star(self.config_path.parent)
        initial_claim = self._derive_initial_direction_claim(north_star)
        await graph.add_node(
            claim=initial_claim,
            confidence=0.0,
            importance=1.0,
            depth=0,
            created_by_cycle=0,
            node_type="direction",
        )

    async def _sync_context_documents_to_db(
        self,
        graph: KnowledgeGraph,
        config: ResearchConfig,
    ) -> None:
        try:
            context_documents = config.get_context_files_content(self.config_path.parent)
            await graph.upsert_context_documents(context_documents, clear_existing=True)
        except Exception as e:
            logger.warning("Failed to sync context documents to DB: %s", e)

    def _create_adapter(self, agent_config: Any, config: ResearchConfig) -> Any:
        from ...agents.adapters.anthropic import AnthropicAdapter
        from ...agents.adapters.kimi import KimiAdapter
        from ...agents.adapters.openrouter import OpenRouterAdapter

        api_keys = config.get_agent_api_keys()
        key = f"{agent_config.provider}:{agent_config.model}"
        api_key = api_keys.get(key, "")

        if agent_config.provider == "anthropic":
            return AnthropicAdapter(
                model=agent_config.model,
                api_key=api_key if not agent_config.use_subscription else None,
                use_subscription=agent_config.use_subscription,
                timeout=agent_config.timeout_seconds,
            )
        if agent_config.provider == "moonshot":
            return KimiAdapter(
                model=agent_config.model,
                api_key=api_key,
                timeout=agent_config.timeout_seconds,
            )
        if agent_config.provider == "openrouter":
            return OpenRouterAdapter(
                model=agent_config.model,
                api_key=api_key,
                timeout=agent_config.timeout_seconds,
                supports_native_search=agent_config.supports_native_search,
            )

        raise ValueError(f"Unsupported provider: {agent_config.provider}")

    def _configure_search(self, config: ResearchConfig) -> None:
        search_api_keys = config.get_search_api_keys()
        search_providers: list[Any] = []

        provider_classes = {
            "tavily": TavilySearchProvider,
            "brave": BraveSearchProvider,
            "serper": SerperSearchProvider,
        }

        for provider in sorted(config.search.providers, key=lambda p: p.priority):
            if not provider.enabled:
                continue

            provider_class = provider_classes.get(provider.name)
            if provider_class is None:
                continue

            api_key = search_api_keys.get(provider.name)
            if api_key is None and provider.name != "duckduckgo":
                continue

            search_providers.append(provider_class(api_key=api_key))

        if not search_providers:
            raise ValueError("No search providers configured with valid API keys")

        configure_search(
            search_providers,
            fallback_enabled=config.search.fallback_enabled,
        )

    def _derive_initial_direction_claim(self, north_star: str) -> str:
        text = north_star.strip()
        if not text:
            return "Clarify the highest-impact direction for this research mission."

        first_sentence = text.split(".", 1)[0].strip()
        if first_sentence:
            if first_sentence.endswith("?"):
                return first_sentence
            return f"What is the best way to validate: {first_sentence}?"

        return "Clarify the highest-impact direction for this research mission."
