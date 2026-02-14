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
    CycleResponse,
    CyclesListResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter(tags=["cycles"])


# TODO: Implement CycleService in Phase 2
# For Phase 1, provide stub responses


@router.get("", response_model=CyclesListResponse)
async def get_cycles(
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
    # TODO: Implement actual cycle history retrieval
    # For Phase 1, return empty list
    logger.warning("Cycles endpoint not yet implemented (Phase 1)")
    return CyclesListResponse(cycles=[], total=0)


@router.get("/{cycle_id}", response_model=CycleDetailResponse)
async def get_cycle(cycle_id: int) -> CycleDetailResponse:
    """
    Get detailed information for a single cycle.

    Path Parameters:
        - cycle_id: Cycle identifier

    Returns:
        Complete cycle details including agent outputs

    Raises:
        404: Cycle not found
    """
    # TODO: Implement actual cycle detail retrieval
    # For Phase 1, return 404
    logger.warning(f"Cycle detail endpoint not yet implemented (Phase 1): {cycle_id}")
    raise HTTPException(status_code=404, detail="Cycle details not yet implemented")


@router.get("/active", response_model=ActiveCycleResponse)
async def get_active_cycle() -> ActiveCycleResponse:
    """
    Get currently running cycle status.

    Returns:
        Active cycle information or idle status
    """
    # TODO: Implement actual active cycle tracking
    # For Phase 1, always return idle
    logger.debug("Active cycle check (always idle in Phase 1)")
    return ActiveCycleResponse(
        cycle_id=None,
        status="idle",
        focus_node_id=None,
        current_step=None,
        progress_percent=0,
    )
