"""
Cycles REST API endpoints.

Provides:
- POST /api/cycles - Start a research cycle
- GET /api/cycles - List of research cycles
- GET /api/cycles/{cycle_id} - Cycle details
- GET /api/cycles/active - Currently running cycle
"""

import logging
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query

from ..models.api_models import (
    ActiveCycleResponse,
    CycleDetailResponse,
    CyclesListResponse,
    RunCycleRequest,
    RunCycleResponse,
)
from ..services.cycle_runner import CycleAlreadyRunningError, CycleRunner
from ..services.graph_service import GraphService
from .graph import get_graph_service

logger = logging.getLogger(__name__)

router = APIRouter(tags=["cycles"])

_cycle_runner: CycleRunner | None = None


def init_cycle_runner(config_path: Path, db_path: str, workspace_id: str) -> None:
    """Initialize cycle runner (called by server.py on startup)."""
    global _cycle_runner
    _cycle_runner = CycleRunner(config_path=config_path, db_path=db_path, workspace_id=workspace_id)


async def shutdown_cycle_runner() -> None:
    """Shutdown cycle runner (called by server.py on shutdown)."""
    global _cycle_runner
    if _cycle_runner:
        await _cycle_runner.close()
        _cycle_runner = None


def get_cycle_runner() -> CycleRunner:
    """Get initialized cycle runner dependency."""
    if _cycle_runner is None:
        raise HTTPException(status_code=500, detail="Cycle runner not initialized")
    return _cycle_runner


@router.post("", response_model=RunCycleResponse, status_code=202)
async def run_cycle(
    request: RunCycleRequest,
    runner: Annotated[CycleRunner, Depends(get_cycle_runner)],
) -> RunCycleResponse:
    """
    Start a new research cycle asynchronously.

    Request Body:
        - target_node_id: Optional node to focus this cycle on
        - cycle_instruction: Optional one-off cycle steering instruction
    """
    try:
        return await runner.start_cycle(request)
    except CycleAlreadyRunningError as e:
        raise HTTPException(
            status_code=409,
            detail={
                "message": "A cycle is already running",
                "active_cycle_id": e.cycle_id,
            },
        ) from e
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to start cycle: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get("/active", response_model=ActiveCycleResponse)
async def get_active_cycle(
    runner: Annotated[CycleRunner, Depends(get_cycle_runner)],
) -> ActiveCycleResponse:
    """
    Get currently running cycle status.

    Returns:
        Active cycle information or idle status
    """
    return await runner.get_active_cycle()


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
        raise HTTPException(status_code=500, detail=str(e)) from e


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
        raise HTTPException(status_code=500, detail=str(e)) from e
