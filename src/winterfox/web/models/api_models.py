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
    description: str | None = None
    confidence: float = Field(ge=0.0, le=1.0)
    importance: float = Field(ge=0.0, le=1.0)
    depth: int = Field(ge=0)
    parent_id: str | None = None
    children_ids: list[str] = Field(default_factory=list)
    evidence: list[EvidenceItem] = Field(default_factory=list)
    status: Literal["active", "archived", "merged"] = "active"
    node_type: str | None = None
    created_by_cycle: int = 0
    updated_by_cycle: int = 0
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
    description: str | None = None
    status: Literal["active", "archived", "merged"] = "active"
    confidence: float = Field(ge=0.0, le=1.0)
    importance: float = Field(ge=0.0, le=1.0)
    node_type: str | None = None
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
    target_claim: str = ""
    total_cost_usd: float = Field(ge=0.0)
    lead_llm_cost_usd: float = Field(ge=0.0, default=0.0)
    research_agents_cost_usd: float = Field(ge=0.0, default=0.0)
    findings_count: int = Field(ge=0)
    directions_count: int = Field(ge=0, default=0)
    agents_used: list[str] = Field(default_factory=list)
    duration_seconds: float | None = None


class CyclesListResponse(BaseModel):
    """List of cycles."""

    cycles: list[CycleResponse]
    total: int = Field(ge=0)


class FindingEvidence(BaseModel):
    """Evidence attached to a finding."""

    text: str
    source: str = ""
    date: str | None = None


class AgentFinding(BaseModel):
    """Single finding from an agent."""

    claim: str
    confidence: float = Field(ge=0.0, le=1.0, default=0.5)
    evidence: list[FindingEvidence] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)
    finding_type: str | None = None


class AgentSearchRecord(BaseModel):
    """Record of a search performed by an agent."""

    query: str
    engine: str = ""
    results_count: int = Field(ge=0, default=0)


class AgentOutputSummary(BaseModel):
    """Summary of agent's work in a cycle."""

    agent_name: str
    model: str = ""
    role: str = "secondary"
    cost_usd: float = Field(ge=0.0)
    total_tokens: int = Field(ge=0, default=0)
    input_tokens: int = Field(ge=0, default=0)
    output_tokens: int = Field(ge=0, default=0)
    duration_seconds: float = Field(ge=0.0, default=0.0)
    searches_performed: int = Field(ge=0)
    findings_count: int = Field(ge=0)
    self_critique: str = ""
    raw_text: str = ""
    findings: list[AgentFinding] = Field(default_factory=list)
    searches: list[AgentSearchRecord] = Field(default_factory=list)


class ContradictionItem(BaseModel):
    """A contradiction between agent findings."""

    claim_a: str = ""
    claim_b: str = ""
    description: str = ""


class DirectionNodeRef(BaseModel):
    """Resolved graph node reference for a synthesized direction."""

    claim: str
    node_id: str
    action: Literal["created", "updated"]


class CycleDetailResponse(BaseModel):
    """Detailed cycle information."""

    id: int
    target_node_id: str = ""
    target_claim: str = ""
    research_context: str | None = None
    findings_created: int = Field(ge=0)
    findings_updated: int = Field(ge=0)
    findings_skipped: int = Field(ge=0, default=0)
    directions_created: int = Field(ge=0, default=0)
    directions_updated: int = Field(ge=0, default=0)
    directions_skipped: int = Field(ge=0, default=0)
    consensus_findings: list[str] = Field(default_factory=list)
    consensus_directions: list[str] = Field(default_factory=list)
    contradictions: list[ContradictionItem] = Field(default_factory=list)
    direction_node_refs: list[DirectionNodeRef] = Field(default_factory=list)
    synthesis_reasoning: str = ""
    selection_strategy: str | None = None
    selection_reasoning: str | None = None
    total_cost_usd: float = Field(ge=0.0, default=0.0)
    lead_llm_cost_usd: float = Field(ge=0.0, default=0.0)
    research_agents_cost_usd: float = Field(ge=0.0, default=0.0)
    total_tokens: int = Field(ge=0, default=0)
    duration_seconds: float = Field(ge=0.0, default=0.0)
    agent_count: int = Field(ge=0, default=0)
    success: bool = True
    error_message: str | None = None
    created_at: str | None = None
    agent_outputs: list[AgentOutputSummary]


class RunCycleRequest(BaseModel):
    """Request to run a new cycle."""

    target_node_id: str | None = None
    cycle_instruction: str | None = None


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
    direction_count: int = Field(ge=0, default=0)
    avg_confidence: float = Field(ge=0.0, le=1.0)
    avg_importance: float = Field(ge=0.0, le=1.0)
    hypothesis_count: int = Field(ge=0, default=0)
    supporting_count: int = Field(ge=0, default=0)
    opposing_count: int = Field(ge=0, default=0)


class CycleStats(BaseModel):
    """Cycle-level statistics."""

    total: int = Field(ge=0)
    successful: int = Field(ge=0)
    failed: int = Field(ge=0)
    avg_duration_seconds: float = Field(ge=0.0)


class CostStats(BaseModel):
    """Cost statistics."""

    total_usd: float = Field(ge=0.0)
    lead_llm_usd: float = Field(ge=0.0, default=0.0)
    research_agents_usd: float = Field(ge=0.0, default=0.0)
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
    supports_native_search: bool = False


class LeadAgentConfigResponse(BaseModel):
    """Lead LLM configuration (without API keys)."""

    provider: str
    model: str
    supports_native_search: bool = False


class SearchProviderResponse(BaseModel):
    """Search provider configuration."""

    name: str
    priority: int = Field(ge=1)
    enabled: bool = True


class ContextDocumentResponse(BaseModel):
    """Context document exposed to frontend."""

    filename: str
    content: str


class ConfigResponse(BaseModel):
    """Project configuration."""

    project_name: str
    north_star: str
    workspace_id: str
    lead_agent: LeadAgentConfigResponse
    agents: list[AgentConfigResponse]
    search_providers: list[SearchProviderResponse]
    search_instructions: str | None = None
    context_documents: list[ContextDocumentResponse] = Field(default_factory=list)


# Report API models


class ReportResponse(BaseModel):
    """Generated research report."""

    markdown: str
    node_count: int = Field(ge=0)
    cycle_count: int = Field(ge=0)
    avg_confidence: float = Field(ge=0.0, le=1.0)
    cost_usd: float = Field(ge=0.0)
    duration_seconds: float = Field(ge=0.0)
    total_tokens: int = Field(ge=0)
    generated_at: str
