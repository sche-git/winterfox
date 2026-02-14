"""
Pydantic models for API requests and responses.
"""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


# Graph API models


class EvidenceItem(BaseModel):
    """Single piece of evidence for a claim."""

    text: str
    source: str
    date: datetime | None = None
    verified_by: list[str] = Field(default_factory=list)


class NodeResponse(BaseModel):
    """Complete node information."""

    id: str
    claim: str
    confidence: float = Field(ge=0.0, le=1.0)
    importance: float = Field(ge=0.0, le=1.0)
    depth: int = Field(ge=0)
    parent_id: str | None = None
    children_ids: list[str] = Field(default_factory=list)
    evidence: list[EvidenceItem] = Field(default_factory=list)
    status: Literal["active", "archived", "merged"] = "active"
    created_at: datetime
    updated_at: datetime


class GraphSummaryResponse(BaseModel):
    """High-level graph statistics."""

    total_nodes: int = Field(ge=0)
    avg_confidence: float = Field(ge=0.0, le=1.0)
    avg_importance: float = Field(ge=0.0, le=1.0)
    root_nodes: int = Field(ge=0)
    low_confidence_count: int = Field(ge=0)
    last_cycle_at: datetime | None = None
    workspace_id: str


class NodesListResponse(BaseModel):
    """Paginated list of nodes."""

    nodes: list[NodeResponse]
    total: int = Field(ge=0)
    limit: int = Field(ge=1)
    offset: int = Field(ge=0)


class NodeTreeItem(BaseModel):
    """Nested node structure for tree view."""

    id: str
    claim: str
    confidence: float = Field(ge=0.0, le=1.0)
    importance: float = Field(ge=0.0, le=1.0)
    children: list["NodeTreeItem"] = Field(default_factory=list)


class GraphTreeResponse(BaseModel):
    """Hierarchical graph structure."""

    roots: list[NodeTreeItem]


class SearchResultItem(BaseModel):
    """Single search result."""

    node_id: str
    claim: str
    snippet: str
    relevance_score: float = Field(ge=0.0, le=1.0)


class SearchResponse(BaseModel):
    """Search results."""

    results: list[SearchResultItem]


# Cycle API models


class CycleResponse(BaseModel):
    """Research cycle metadata."""

    id: int
    started_at: datetime
    completed_at: datetime | None = None
    status: Literal["running", "completed", "failed"] = "running"
    focus_node_id: str | None = None
    total_cost_usd: float = Field(ge=0.0)
    findings_count: int = Field(ge=0)
    agents_used: list[str] = Field(default_factory=list)
    duration_seconds: float | None = None


class CyclesListResponse(BaseModel):
    """List of cycles."""

    cycles: list[CycleResponse]
    total: int = Field(ge=0)


class AgentOutputSummary(BaseModel):
    """Summary of agent's work in a cycle."""

    agent_name: str
    cost_usd: float = Field(ge=0.0)
    searches_performed: int = Field(ge=0)
    findings_count: int = Field(ge=0)


class CycleDetailResponse(BaseModel):
    """Detailed cycle information."""

    id: int
    findings_created: int = Field(ge=0)
    findings_updated: int = Field(ge=0)
    consensus_findings: int = Field(ge=0)
    divergent_findings: int = Field(ge=0)
    agent_outputs: list[AgentOutputSummary]


class RunCycleRequest(BaseModel):
    """Request to run a new cycle."""

    target_node_id: str | None = None
    use_consensus: bool = True


class RunCycleResponse(BaseModel):
    """Response after starting a cycle."""

    cycle_id: int
    status: Literal["running"] = "running"
    started_at: datetime


class ActiveCycleResponse(BaseModel):
    """Currently running cycle status."""

    cycle_id: int | None = None
    status: Literal["running", "idle"] = "idle"
    focus_node_id: str | None = None
    current_step: str | None = None
    progress_percent: int = Field(ge=0, le=100, default=0)


# Stats API models


class GraphStats(BaseModel):
    """Graph-level statistics."""

    total_nodes: int = Field(ge=0)
    avg_confidence: float = Field(ge=0.0, le=1.0)
    avg_importance: float = Field(ge=0.0, le=1.0)


class CycleStats(BaseModel):
    """Cycle-level statistics."""

    total: int = Field(ge=0)
    successful: int = Field(ge=0)
    failed: int = Field(ge=0)
    avg_duration_seconds: float = Field(ge=0.0)


class CostStats(BaseModel):
    """Cost statistics."""

    total_usd: float = Field(ge=0.0)
    by_agent: dict[str, float] = Field(default_factory=dict)


class ActivityStats(BaseModel):
    """Recent activity statistics."""

    last_cycle_at: datetime | None = None
    nodes_created_today: int = Field(ge=0)


class OverviewStatsResponse(BaseModel):
    """Comprehensive statistics overview."""

    graph: GraphStats
    cycles: CycleStats
    cost: CostStats
    activity: ActivityStats


class TimelineEntry(BaseModel):
    """Single timeline data point."""

    timestamp: datetime
    nodes_created: int = Field(ge=0)
    cycles_run: int = Field(ge=0)
    cost_usd: float = Field(ge=0.0)


class TimelineResponse(BaseModel):
    """Historical timeline data."""

    timeline: list[TimelineEntry]


# Config API models


class AgentConfigResponse(BaseModel):
    """Agent configuration (without API keys)."""

    provider: str
    model: str
    role: Literal["primary", "secondary"] = "secondary"
    supports_native_search: bool = False


class SearchProviderResponse(BaseModel):
    """Search provider configuration."""

    name: str
    priority: int = Field(ge=1)
    enabled: bool = True


class ConfigResponse(BaseModel):
    """Project configuration."""

    project_name: str
    north_star: str
    workspace_id: str
    agents: list[AgentConfigResponse]
    search_providers: list[SearchProviderResponse]
