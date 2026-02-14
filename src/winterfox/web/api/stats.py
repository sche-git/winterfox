"""
Stats REST API endpoints.

Provides:
- GET /api/stats/overview - Comprehensive statistics
- GET /api/stats/timeline - Historical timeline data
"""

import logging
from typing import Annotated

from fastapi import APIRouter, Depends, Query

from ..models.api_models import (
    ActivityStats,
    CostStats,
    CycleStats,
    GraphStats,
    OverviewStatsResponse,
    TimelineResponse,
)
from ..services.graph_service import GraphService
from .graph import get_graph_service

logger = logging.getLogger(__name__)

router = APIRouter(tags=["stats"])


@router.get("/overview", response_model=OverviewStatsResponse)
async def get_overview_stats(
    service: Annotated[GraphService, Depends(get_graph_service)],
) -> OverviewStatsResponse:
    """
    Get comprehensive statistics overview.

    Returns:
        - Graph statistics (nodes, confidence, importance)
        - Cycle statistics (total, successful, failed)
        - Cost statistics (total and by agent)
        - Activity statistics (recent activity)
    """
    try:
        # Get graph summary
        summary = await service.get_summary()

        # Count nodes by type
        type_counts = await service.get_node_type_counts()

        # Build response
        graph_stats = GraphStats(
            total_nodes=summary.total_nodes,
            avg_confidence=summary.avg_confidence,
            avg_importance=summary.avg_importance,
            hypothesis_count=type_counts.get("hypothesis", 0),
            supporting_count=type_counts.get("supporting", 0),
            opposing_count=type_counts.get("opposing", 0),
        )

        # Get cycle statistics from database
        total, successful, failed, avg_duration, total_cost, cost_by_agent = (
            await service.get_cycle_stats()
        )

        cycle_stats = CycleStats(
            total=total,
            successful=successful,
            failed=failed,
            avg_duration_seconds=avg_duration,
        )

        cost_stats = CostStats(
            total_usd=total_cost,
            by_agent=cost_by_agent,
        )

        activity_stats = ActivityStats(
            last_cycle_at=summary.last_cycle_at,
            nodes_created_today=0,  # TODO: Calculate from created_at
        )

        return OverviewStatsResponse(
            graph=graph_stats,
            cycles=cycle_stats,
            cost=cost_stats,
            activity=activity_stats,
        )
    except Exception as e:
        logger.error(f"Failed to get overview stats: {e}", exc_info=True)
        from fastapi import HTTPException

        raise HTTPException(status_code=500, detail=str(e))


@router.get("/timeline", response_model=TimelineResponse)
async def get_timeline_stats(
    period: Annotated[str, Query()] = "day",
    limit: Annotated[int, Query(ge=1, le=100)] = 30,
) -> TimelineResponse:
    """
    Get historical timeline data.

    Query Parameters:
        - period: Time period (hour, day, week) (default: day)
        - limit: Number of data points (1-100, default: 30)

    Returns:
        Timeline data with nodes created, cycles run, and costs
    """
    # TODO: Implement timeline data in Phase 2
    logger.warning("Timeline endpoint not yet implemented (Phase 1)")
    return TimelineResponse(timeline=[])
