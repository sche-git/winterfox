"""Agent adapter layer for multi-LLM support."""

from .protocol import (
    AgentAdapter,
    AgentOutput,
    Evidence,
    SearchRecord,
    ToolDefinition,
)

__all__ = [
    "AgentAdapter",
    "AgentOutput",
    "Evidence",
    "SearchRecord",
    "ToolDefinition",
]
