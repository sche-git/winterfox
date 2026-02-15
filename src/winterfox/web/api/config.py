"""
Config REST API endpoint.

Provides:
- GET /api/config - Project configuration
"""

import logging
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException

from ...config import ResearchConfig, load_config
from ..api.graph import get_graph_service
from ..models.api_models import (
    AgentConfigResponse,
    ConfigResponse,
    ContextDocumentResponse,
    LeadAgentConfigResponse,
    SearchProviderResponse,
)
from ..services.graph_service import GraphService

logger = logging.getLogger(__name__)

router = APIRouter(tags=["config"])


# Global config instance (set by server.py)
_config: ResearchConfig | None = None
_config_path: Path | None = None


def init_config(config_path: Path) -> None:
    """
    Initialize config (called by server.py on startup).

    Args:
        config_path: Path to winterfox.toml
    """
    global _config, _config_path
    _config = load_config(config_path)
    _config_path = config_path
    logger.info(f"Config loaded: {config_path}")


@router.get("", response_model=ConfigResponse)
async def get_config(
    graph_service: Annotated[GraphService, Depends(get_graph_service)],
) -> ConfigResponse:
    """
    Get project configuration (without sensitive data).

    Returns:
        - Project name and north star
        - Workspace ID
        - Agent configurations (without API keys)
        - Search provider configurations
    """
    if _config is None or _config_path is None:
        raise HTTPException(status_code=500, detail="Config not initialized")

    try:
        # Get north star content
        north_star = _config.get_north_star(_config_path.parent)

        # Convert agent configs (remove sensitive data)
        agents = [
            AgentConfigResponse(
                provider=agent.provider,
                model=agent.model,
                supports_native_search=agent.supports_native_search,
            )
            for agent in _config.agents
        ]

        # Convert search provider configs
        search_providers = [
            SearchProviderResponse(
                name=provider.name,
                priority=provider.priority,
                enabled=provider.enabled,
            )
            for provider in _config.search.providers
        ]

        search_instructions = _config.get_search_instructions(_config_path.parent)
        context_documents_raw = await graph_service.get_context_documents()
        if not context_documents_raw:
            context_documents_raw = _config.get_context_files_content(_config_path.parent)

        context_documents = [
            ContextDocumentResponse(
                filename=doc["filename"],
                content=doc["content"],
            )
            for doc in context_documents_raw
        ]

        return ConfigResponse(
            project_name=_config.project.name,
            north_star=north_star,
            workspace_id=_config.multi_tenancy.workspace_id,
            lead_agent=LeadAgentConfigResponse(
                provider=_config.lead_agent.provider,
                model=_config.lead_agent.model,
                supports_native_search=_config.lead_agent.supports_native_search,
            ),
            agents=agents,
            search_providers=search_providers,
            search_instructions=search_instructions,
            context_documents=context_documents,
        )
    except Exception as e:
        logger.error(f"Failed to get config: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
