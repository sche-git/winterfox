"""
Protocol definitions for agent adapters.

This module defines the interfaces that all LLM adapters must implement,
enabling multi-provider support with a unified interface.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Callable, Literal, Protocol, runtime_checkable


@dataclass
class ToolDefinition:
    """Definition of a tool that agents can use."""

    name: str
    description: str
    parameters: dict[str, Any]  # JSON Schema
    execute: Callable[..., Any]


@dataclass
class Evidence:
    """Evidence supporting a finding."""

    text: str
    source: str
    date: datetime = field(default_factory=datetime.now)
    verified_by: list[str] = field(default_factory=list)


@dataclass
class SearchRecord:
    """Record of a search performed by an agent."""

    query: str
    engine: str
    timestamp: datetime
    results_summary: str
    urls_visited: list[str]


@dataclass
class AgentOutput:
    """
    Raw output from an agent's research cycle.

    NO structured findings - raw_text is the primary data source.
    Lead LLM extracts directions during synthesis.
    """

    raw_text: str  # PRIMARY DATA - full LLM reasoning and discoveries
    self_critique: str
    searches_performed: list[SearchRecord]
    cost_usd: float
    duration_seconds: float
    agent_name: str
    model: str
    total_tokens: int = 0
    input_tokens: int = 0
    output_tokens: int = 0


@runtime_checkable
class AgentAdapter(Protocol):
    """
    Protocol for LLM agent adapters.

    Any LLM that supports tool use can be an agent by implementing this protocol.
    """

    @property
    def name(self) -> str:
        """Human-readable agent name (e.g., 'claude-opus-4-20251120')."""
        ...

    @property
    def supports_native_search(self) -> bool:
        """Whether this model can search natively (extended thinking, etc.)."""
        ...

    async def verify(self) -> None:
        """
        Verify that the agent's API key is valid.

        Makes a minimal API call to check authentication.

        Raises:
            AgentAuthenticationError: If credentials are invalid
            Exception: If verification fails for other reasons
        """
        ...

    async def run(
        self,
        system_prompt: str,
        user_prompt: str,
        tools: list[ToolDefinition],
        max_iterations: int = 30,
    ) -> AgentOutput:
        """
        Run agent with tools and return structured output.

        Args:
            system_prompt: System-level instructions
            user_prompt: User's research request
            tools: Available tools for the agent
            max_iterations: Maximum tool-use iterations

        Returns:
            Structured AgentOutput with findings and metadata
        """
        ...
