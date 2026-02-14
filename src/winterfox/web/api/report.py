"""
Report REST API endpoints.

Provides:
- POST /api/report/generate - Generate narrative report via LLM
- GET /api/report/latest - Get most recently saved report
"""

import asyncio
import logging
import re

from fastapi import APIRouter, HTTPException

from ..models.api_models import ReportResponse
from .config import _config, _config_path

logger = logging.getLogger(__name__)

router = APIRouter(tags=["report"])

# Prevent concurrent report generation (expensive LLM call)
_generation_lock = asyncio.Lock()


def _parse_frontmatter(markdown: str) -> dict[str, str]:
    """Extract YAML frontmatter values from markdown."""
    match = re.match(r"^---\n(.*?)\n---", markdown, re.DOTALL)
    if not match:
        return {}

    result: dict[str, str] = {}
    for line in match.group(1).strip().splitlines():
        if ":" in line:
            key, _, value = line.partition(":")
            result[key.strip()] = value.strip()
    return result


def _get_config_and_path() -> tuple:
    """Get current config and path, raising 500 if not initialized."""
    if _config is None or _config_path is None:
        raise HTTPException(status_code=500, detail="Config not initialized")
    return _config, _config_path


def _create_primary_adapter(config):
    """Create the primary agent adapter (same pattern as cli.py)."""
    from ...agents.adapters.anthropic import AnthropicAdapter
    from ...agents.adapters.kimi import KimiAdapter
    from ...agents.adapters.openrouter import OpenRouterAdapter

    # Find primary agent config
    primary_config = None
    for agent_config in config.agents:
        if agent_config.role == "primary":
            primary_config = agent_config
            break
    if primary_config is None:
        primary_config = config.agents[0]

    api_keys = config.get_agent_api_keys()
    key = f"{primary_config.provider}:{primary_config.model}"
    api_key = api_keys.get(key, "")

    if primary_config.provider == "anthropic":
        return AnthropicAdapter(
            model=primary_config.model,
            api_key=api_key if not primary_config.use_subscription else None,
            use_subscription=primary_config.use_subscription,
            timeout=primary_config.timeout_seconds,
        )
    elif primary_config.provider == "moonshot":
        return KimiAdapter(
            model=primary_config.model,
            api_key=api_key,
            timeout=primary_config.timeout_seconds,
        )
    elif primary_config.provider == "openrouter":
        return OpenRouterAdapter(
            model=primary_config.model,
            api_key=api_key,
            timeout=primary_config.timeout_seconds,
            supports_native_search=primary_config.supports_native_search,
        )
    else:
        raise HTTPException(
            status_code=500,
            detail=f"Unsupported provider: {primary_config.provider}",
        )


@router.post("/generate", response_model=ReportResponse)
async def generate_report() -> ReportResponse:
    """
    Generate a narrative research report via LLM synthesis.

    This is an expensive operation (~30-60 seconds) that uses the primary
    agent to synthesize the knowledge graph into a cohesive document.
    Only one generation can run at a time.

    Returns:
        ReportResponse with markdown content and metadata

    Raises:
        409: Report generation already in progress
        500: Generation failed
    """
    if _generation_lock.locked():
        raise HTTPException(
            status_code=409,
            detail="Report generation already in progress",
        )

    config, config_path = _get_config_and_path()

    async with _generation_lock:
        try:
            from ...graph.store import KnowledgeGraph
            from ...orchestrator.report import ReportSynthesizer

            graph = KnowledgeGraph(
                str(config.storage.db_path),
                workspace_id=config.multi_tenancy.workspace_id,
            )
            await graph.initialize()

            try:
                adapter = _create_primary_adapter(config)
                north_star = config.get_north_star(config_path.parent)

                synthesizer = ReportSynthesizer(graph, adapter, north_star)
                result = await synthesizer.generate()

                # Save report to .winterfox/report.md
                report_path = config_path.parent / ".winterfox" / "report.md"
                report_path.parent.mkdir(parents=True, exist_ok=True)
                report_path.write_text(result.markdown, encoding="utf-8")

                # Parse frontmatter for avg_confidence and generated_at
                frontmatter = _parse_frontmatter(result.markdown)

                return ReportResponse(
                    markdown=result.markdown,
                    node_count=result.node_count,
                    cycle_count=result.cycle_count,
                    avg_confidence=float(
                        frontmatter.get("avg_confidence", "0.0")
                    ),
                    cost_usd=result.cost_usd,
                    duration_seconds=result.duration_seconds,
                    total_tokens=result.total_tokens,
                    generated_at=frontmatter.get(
                        "generated", ""
                    ),
                )
            finally:
                await graph.close()

        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
        except Exception as e:
            logger.error(f"Report generation failed: {e}", exc_info=True)
            raise HTTPException(status_code=500, detail=str(e))


@router.get("/latest", response_model=ReportResponse)
async def get_latest_report() -> ReportResponse:
    """
    Get the most recently generated report from disk.

    Fast operation (no LLM call). Reads .winterfox/report.md and parses
    YAML frontmatter for metadata.

    Returns:
        ReportResponse with markdown content and metadata

    Raises:
        404: No report has been generated yet
    """
    _, config_path = _get_config_and_path()

    report_path = config_path.parent / ".winterfox" / "report.md"
    if not report_path.exists():
        raise HTTPException(status_code=404, detail="No report generated yet")

    try:
        markdown = report_path.read_text(encoding="utf-8")
        frontmatter = _parse_frontmatter(markdown)

        return ReportResponse(
            markdown=markdown,
            node_count=int(frontmatter.get("nodes", "0")),
            cycle_count=int(frontmatter.get("cycles", "0")),
            avg_confidence=float(frontmatter.get("avg_confidence", "0.0")),
            cost_usd=0.0,
            duration_seconds=0.0,
            total_tokens=0,
            generated_at=frontmatter.get("generated", ""),
        )
    except Exception as e:
        logger.error(f"Failed to read report: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
