"""
WebSocket event models for real-time updates.

Event Types:
- Cycle lifecycle: cycle.started, cycle.step, cycle.completed, cycle.failed
- Agent activity: agent.started, agent.search, agent.completed
- Graph updates: node.created, node.updated
- Synthesis: synthesis.started, synthesis.completed
"""

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field


# Base event model


class BaseEvent(BaseModel):
    """Base event with common fields."""

    type: str
    timestamp: datetime = Field(default_factory=datetime.now)
    workspace_id: str = "default"
    data: dict[str, Any] = Field(default_factory=dict)


# Cycle lifecycle events


class CycleStartedEvent(BaseModel):
    """Cycle has started."""

    type: Literal["cycle.started"] = "cycle.started"
    timestamp: datetime = Field(default_factory=datetime.now)
    workspace_id: str = "default"
    data: dict[str, Any] = Field(default_factory=dict)

    @classmethod
    def create(
        cls,
        cycle_id: int,
        focus_node_id: str,
        focus_claim: str,
        workspace_id: str = "default",
    ):
        """Create cycle started event."""
        return cls(
            workspace_id=workspace_id,
            data={
                "cycle_id": cycle_id,
                "focus_node_id": focus_node_id,
                "focus_claim": focus_claim,
            },
        )


class CycleStepEvent(BaseModel):
    """Cycle progressed to a new step."""

    type: Literal["cycle.step"] = "cycle.step"
    timestamp: datetime = Field(default_factory=datetime.now)
    workspace_id: str = "default"
    data: dict[str, Any] = Field(default_factory=dict)

    @classmethod
    def create(
        cls,
        cycle_id: int,
        step: str,
        progress_percent: int,
        workspace_id: str = "default",
    ):
        """Create cycle step event."""
        return cls(
            workspace_id=workspace_id,
            data={
                "cycle_id": cycle_id,
                "step": step,
                "progress_percent": progress_percent,
            },
        )


class CycleCompletedEvent(BaseModel):
    """Cycle completed successfully."""

    type: Literal["cycle.completed"] = "cycle.completed"
    timestamp: datetime = Field(default_factory=datetime.now)
    workspace_id: str = "default"
    data: dict[str, Any] = Field(default_factory=dict)

    @classmethod
    def create(
        cls,
        cycle_id: int,
        findings_created: int,
        findings_updated: int,
        total_cost_usd: float,
        duration_seconds: float,
        workspace_id: str = "default",
    ):
        """Create cycle completed event."""
        return cls(
            workspace_id=workspace_id,
            data={
                "cycle_id": cycle_id,
                "findings_created": findings_created,
                "findings_updated": findings_updated,
                "total_cost_usd": total_cost_usd,
                "duration_seconds": duration_seconds,
            },
        )


class CycleFailedEvent(BaseModel):
    """Cycle failed with error."""

    type: Literal["cycle.failed"] = "cycle.failed"
    timestamp: datetime = Field(default_factory=datetime.now)
    workspace_id: str = "default"
    data: dict[str, Any] = Field(default_factory=dict)

    @classmethod
    def create(
        cls,
        cycle_id: int,
        error_message: str,
        step: str,
        workspace_id: str = "default",
    ):
        """Create cycle failed event."""
        return cls(
            workspace_id=workspace_id,
            data={
                "cycle_id": cycle_id,
                "error_message": error_message,
                "step": step,
            },
        )


# Agent activity events


class AgentStartedEvent(BaseModel):
    """Agent started research."""

    type: Literal["agent.started"] = "agent.started"
    timestamp: datetime = Field(default_factory=datetime.now)
    workspace_id: str = "default"
    data: dict[str, Any] = Field(default_factory=dict)

    @classmethod
    def create(
        cls,
        cycle_id: int,
        agent_name: str,
        prompt_preview: str,
        workspace_id: str = "default",
    ):
        """Create agent started event."""
        return cls(
            workspace_id=workspace_id,
            data={
                "cycle_id": cycle_id,
                "agent_name": agent_name,
                "prompt_preview": prompt_preview[:200],  # Truncate for brevity
            },
        )


class AgentSearchEvent(BaseModel):
    """Agent performed a search."""

    type: Literal["agent.search"] = "agent.search"
    timestamp: datetime = Field(default_factory=datetime.now)
    workspace_id: str = "default"
    data: dict[str, Any] = Field(default_factory=dict)

    @classmethod
    def create(
        cls,
        cycle_id: int,
        agent_name: str,
        query: str,
        results_count: int,
        workspace_id: str = "default",
    ):
        """Create agent search event."""
        return cls(
            workspace_id=workspace_id,
            data={
                "cycle_id": cycle_id,
                "agent_name": agent_name,
                "query": query,
                "results_count": results_count,
            },
        )


class AgentCompletedEvent(BaseModel):
    """Agent completed research."""

    type: Literal["agent.completed"] = "agent.completed"
    timestamp: datetime = Field(default_factory=datetime.now)
    workspace_id: str = "default"
    data: dict[str, Any] = Field(default_factory=dict)

    @classmethod
    def create(
        cls,
        cycle_id: int,
        agent_name: str,
        findings_count: int,
        cost_usd: float,
        duration_seconds: float,
        workspace_id: str = "default",
    ):
        """Create agent completed event."""
        return cls(
            workspace_id=workspace_id,
            data={
                "cycle_id": cycle_id,
                "agent_name": agent_name,
                "findings_count": findings_count,
                "cost_usd": cost_usd,
                "duration_seconds": duration_seconds,
            },
        )


# Graph update events


class NodeCreatedEvent(BaseModel):
    """New node was created."""

    type: Literal["node.created"] = "node.created"
    timestamp: datetime = Field(default_factory=datetime.now)
    workspace_id: str = "default"
    data: dict[str, Any] = Field(default_factory=dict)

    @classmethod
    def create(
        cls,
        cycle_id: int,
        node_id: str,
        parent_id: str | None,
        claim: str,
        confidence: float,
        workspace_id: str = "default",
    ):
        """Create node created event."""
        return cls(
            workspace_id=workspace_id,
            data={
                "cycle_id": cycle_id,
                "node_id": node_id,
                "parent_id": parent_id,
                "claim": claim,
                "confidence": confidence,
            },
        )


class NodeUpdatedEvent(BaseModel):
    """Existing node was updated."""

    type: Literal["node.updated"] = "node.updated"
    timestamp: datetime = Field(default_factory=datetime.now)
    workspace_id: str = "default"
    data: dict[str, Any] = Field(default_factory=dict)

    @classmethod
    def create(
        cls,
        cycle_id: int,
        node_id: str,
        old_confidence: float,
        new_confidence: float,
        evidence_added: int,
        workspace_id: str = "default",
    ):
        """Create node updated event."""
        return cls(
            workspace_id=workspace_id,
            data={
                "cycle_id": cycle_id,
                "node_id": node_id,
                "old_confidence": old_confidence,
                "new_confidence": new_confidence,
                "evidence_added": evidence_added,
            },
        )


# Synthesis events


class SynthesisStartedEvent(BaseModel):
    """Multi-agent synthesis started."""

    type: Literal["synthesis.started"] = "synthesis.started"
    timestamp: datetime = Field(default_factory=datetime.now)
    workspace_id: str = "default"
    data: dict[str, Any] = Field(default_factory=dict)

    @classmethod
    def create(
        cls,
        cycle_id: int,
        agent_count: int,
        workspace_id: str = "default",
    ):
        """Create synthesis started event."""
        return cls(
            workspace_id=workspace_id,
            data={
                "cycle_id": cycle_id,
                "agent_count": agent_count,
            },
        )


class SynthesisCompletedEvent(BaseModel):
    """Multi-agent synthesis completed."""

    type: Literal["synthesis.completed"] = "synthesis.completed"
    timestamp: datetime = Field(default_factory=datetime.now)
    workspace_id: str = "default"
    data: dict[str, Any] = Field(default_factory=dict)

    @classmethod
    def create(
        cls,
        cycle_id: int,
        consensus_count: int,
        divergent_count: int,
        workspace_id: str = "default",
    ):
        """Create synthesis completed event."""
        return cls(
            workspace_id=workspace_id,
            data={
                "cycle_id": cycle_id,
                "consensus_count": consensus_count,
                "divergent_count": divergent_count,
            },
        )


# Type alias for all event types
EventType = (
    CycleStartedEvent
    | CycleStepEvent
    | CycleCompletedEvent
    | CycleFailedEvent
    | AgentStartedEvent
    | AgentSearchEvent
    | AgentCompletedEvent
    | NodeCreatedEvent
    | NodeUpdatedEvent
    | SynthesisStartedEvent
    | SynthesisCompletedEvent
)
