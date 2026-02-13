"""Agent adapter layer for multi-LLM support."""

from .protocol import (
    AgentAdapter,
    AgentOutput,
    Evidence,
    Finding,
    SearchRecord,
    ToolDefinition,
)

__all__ = [
    "AgentAdapter",
    "AgentOutput",
    "Evidence",
    "Finding",
    "SearchRecord",
    "ToolDefinition",
]
