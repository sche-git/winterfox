"""
Cycles REST API endpoints.

Provides:
- GET /api/cycles - List of research cycles
- GET /api/cycles/{cycle_id} - Cycle details
- GET /api/cycles/active - Currently running cycle
"""

import logging
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query

from ..models.api_models import (
    ActiveCycleResponse,
    CycleDetailResponse,
    CyclesListResponse,
)
from ..services.graph_service import GraphService
from .graph import get_graph_service

logger = logging.getLogger(__name__)

router = APIRouter(tags=["cycles"])


@router.get("/active", response_model=ActiveCycleResponse)
async def get_active_cycle() -> ActiveCycleResponse:
    """
    Get currently running cycle status.

    Returns:
        Active cycle information or idle status
    """
    # Active cycle tracking is done via WebSocket events in real-time.
    # This endpoint reports idle since cycles are driven by CLI.
    return ActiveCycleResponse(
        cycle_id=None,
        status="idle",
        focus_node_id=None,
        current_step=None,
        progress_percent=0,
    )


@router.get("", response_model=CyclesListResponse)
async def get_cycles(
    service: Annotated[GraphService, Depends(get_graph_service)],
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> CyclesListResponse:
    """
    Get list of research cycles.

    Query Parameters:
        - limit: Max cycles to return (1-100, default: 20)
        - offset: Offset for pagination (default: 0)

    Returns:
        List of cycles with metadata
    """
    try:
        return await service.get_cycles(limit=limit, offset=offset)
    except Exception as e:
        logger.error(f"Failed to get cycles: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{cycle_id}", response_model=CycleDetailResponse)
async def get_cycle(
    cycle_id: int,
    service: Annotated[GraphService, Depends(get_graph_service)],
) -> CycleDetailResponse:
    """
    Get detailed information for a single cycle.

    Path Parameters:
        - cycle_id: Cycle identifier

    Returns:
        Complete cycle details including agent outputs

    Raises:
        404: Cycle not found
    """
    try:
        detail = await service.get_cycle_detail(cycle_id)
        if detail is None:
            raise HTTPException(status_code=404, detail=f"Cycle not found: {cycle_id}")
        return detail
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get cycle {cycle_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
