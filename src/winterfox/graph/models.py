"""
Data models for the knowledge graph.

This module defines the core data structures used throughout the winterfox system:
- Evidence: Individual pieces of supporting evidence
- KnowledgeNode: Nodes in the knowledge graph representing claims/findings
"""

from datetime import datetime
from typing import Literal
from uuid import uuid4

from pydantic import BaseModel, Field


class Evidence(BaseModel):
    """A piece of evidence supporting a claim."""

    text: str = Field(..., description="The evidence text/quote")
    source: str = Field(..., description="URL or reference to the source")
    date: datetime = Field(default_factory=datetime.now, description="When evidence was found")
    verified_by: list[str] = Field(
        default_factory=list, description="List of agent names that verified this evidence"
    )

    model_config = {"frozen": False}  # Allow modifications for verified_by updates


class KnowledgeNode(BaseModel):
    """
    A node in the knowledge graph representing a research direction.

    All nodes are directions to pursue - no semantic types (question, hypothesis, etc.).
    The Lead LLM decides what directions matter and how to structure them.
    """

    # Core identification
    id: str = Field(default_factory=lambda: str(uuid4()), description="Unique node ID")
    workspace_id: str = Field(default="default", description="Workspace this node belongs to")
    parent_id: str | None = Field(default=None, description="Parent node ID (None for root)")

    # Content
    claim: str = Field(..., min_length=1, description="The direction/claim text")
    description: str | None = Field(
        default=None,
        description="Longer description of the direction for human-readable context",
    )

    # Metrics
    confidence: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="How well-supported this direction is"
    )
    importance: float = Field(
        default=0.5,
        ge=0.0,
        le=1.0,
        description="Strategic relevance to the north star"
    )
    depth: int = Field(default=0, ge=0, description="How many cycles have refined this node")

    # Node semantics - simplified to direction-only
    node_type: Literal["direction"] = Field(
        default="direction", description="All nodes are directions (unified model)"
    )

    # Status and relationships
    status: Literal["active", "completed", "closed", "killed", "merged", "speculative"] = Field(
        default="active", description="Current status of the node"
    )
    children_ids: list[str] = Field(
        default_factory=list, description="List of child node IDs"
    )
    tags: list[str] = Field(default_factory=list, description="Freeform tags for categorization")

    # Supporting data
    evidence: list[Evidence] = Field(
        default_factory=list, description="Evidence supporting this direction"
    )
    sources: list[str] = Field(
        default_factory=list, description="Paths to Layer 3 raw output files"
    )

    # Metadata
    created_at: datetime = Field(
        default_factory=datetime.now, description="When this node was created"
    )
    updated_at: datetime = Field(
        default_factory=datetime.now, description="When this node was last updated"
    )
    created_by_cycle: int = Field(..., description="Which research cycle created this")
    updated_by_cycle: int = Field(..., description="Which research cycle last updated this")

    # Computed properties (not stored directly)
    @property
    def staleness_hours(self) -> float:
        """Hours since last update."""
        delta = datetime.now() - self.updated_at
        return delta.total_seconds() / 3600

    def add_evidence(self, evidence: Evidence) -> None:
        """Add evidence to this node."""
        self.evidence.append(evidence)
        self.updated_at = datetime.now()

    def add_child(self, child_id: str) -> None:
        """Register a child node."""
        if child_id not in self.children_ids:
            self.children_ids.append(child_id)
            self.updated_at = datetime.now()

    def kill(self, reason: str) -> None:
        """Mark this node as killed (never delete, audit trail matters)."""
        self.status = "killed"
        self.tags.append(f"killed:{reason}")
        self.updated_at = datetime.now()

    model_config = {
        "frozen": False,  # Allow updates
        "json_schema_extra": {
            "example": {
                "id": "abc123",
                "workspace_id": "default",
                "parent_id": "parent123",
                "claim": "Explore B2B vs B2C market fit for legal tech startups in 2024",
                "description": "Compare ICPs, sales motion, pricing expectations, and adoption barriers for each segment.",
                "confidence": 0.75,
                "importance": 0.9,
                "depth": 3,
                "node_type": "direction",
                "status": "active",
                "children_ids": ["child1", "child2"],
                "tags": ["market-fit", "legal-tech", "segmentation"],
                "evidence": [],
                "sources": [".winterfox/raw/2024-01-15/cycle_003.md"],
                "created_by_cycle": 1,
                "updated_by_cycle": 3,
            }
        },
    }


class NodeSummary(BaseModel):
    """Lightweight node representation for summary views (token efficiency)."""

    id: str
    claim: str
    confidence: float
    depth: int
    children_count: int
    staleness_hours: float
    status: str
    node_type: str | None = None

    @classmethod
    def from_node(cls, node: KnowledgeNode) -> "NodeSummary":
        """Create summary from full node."""
        return cls(
            id=node.id,
            claim=node.claim[:100] + "..." if len(node.claim) > 100 else node.claim,
            confidence=node.confidence,
            depth=node.depth,
            children_count=len(node.children_ids),
            staleness_hours=node.staleness_hours,
            status=node.status,
            node_type=node.node_type,
        )
