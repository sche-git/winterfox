"""
Agent pool for parallel dispatch and optional synthesis.

This module is retained for compatibility with legacy integrations.
It now operates on raw AgentOutput objects (no structured findings required).
"""

import asyncio
import logging
from dataclasses import dataclass
from typing import Any

from .protocol import AgentAdapter, AgentOutput, ToolDefinition

logger = logging.getLogger(__name__)


@dataclass
class SynthesisResult:
    """Result of optional synthesis over multiple agent outputs."""

    findings: list[Any]
    synthesis_reasoning: str
    consensus_findings: list[str]
    contradictions: list[dict[str, Any]]
    individual_outputs: list[AgentOutput]
    total_cost_usd: float
    total_duration_seconds: float


class AgentPool:
    """Pool of agents for parallel research with optional synthesis."""

    def __init__(self, adapters: list[AgentAdapter], primary_agent_index: int = 0):
        if not adapters:
            raise ValueError("At least one agent adapter required")

        if primary_agent_index < 0 or primary_agent_index >= len(adapters):
            raise ValueError(
                f"primary_agent_index {primary_agent_index} out of range [0, {len(adapters)-1}]"
            )

        self.adapters = adapters
        self.primary_agent_index = primary_agent_index
        logger.info(
            "Initialized pool with %s agents, primary: %s",
            len(adapters),
            adapters[primary_agent_index].name,
        )

    async def dispatch(
        self,
        system_prompt: str,
        user_prompt: str,
        tools: list[ToolDefinition],
        max_iterations: int = 30,
    ) -> list[AgentOutput]:
        """Dispatch to all agents in parallel."""
        tasks = [
            adapter.run(system_prompt, user_prompt, tools, max_iterations)
            for adapter in self.adapters
        ]
        outputs = await asyncio.gather(*tasks, return_exceptions=True)

        results: list[AgentOutput] = []
        for output in outputs:
            if isinstance(output, Exception):
                raise output
            results.append(output)

        return results

    async def dispatch_with_synthesis(
        self,
        system_prompt: str,
        user_prompt: str,
        tools: list[ToolDefinition],
        max_iterations: int = 30,
    ) -> SynthesisResult:
        """Dispatch to all agents, then run a lightweight synthesis pass."""
        outputs = await self.dispatch(system_prompt, user_prompt, tools, max_iterations)

        if len(outputs) == 1:
            return SynthesisResult(
                findings=getattr(outputs[0], "findings", []),
                synthesis_reasoning="Single agent, no synthesis performed",
                consensus_findings=[],
                contradictions=[],
                individual_outputs=outputs,
                total_cost_usd=outputs[0].cost_usd,
                total_duration_seconds=outputs[0].duration_seconds,
            )

        synthesis_output = await self._synthesize_with_llm(
            outputs, system_prompt, user_prompt
        )

        total_cost = sum(o.cost_usd for o in outputs) + synthesis_output.cost_usd
        total_duration = (
            max(o.duration_seconds for o in outputs) + synthesis_output.duration_seconds
        )

        consensus_findings, contradictions = self._parse_synthesis_metadata(
            synthesis_output
        )

        return SynthesisResult(
            findings=getattr(synthesis_output, "findings", []),
            synthesis_reasoning=synthesis_output.self_critique,
            consensus_findings=consensus_findings,
            contradictions=contradictions,
            individual_outputs=outputs,
            total_cost_usd=total_cost,
            total_duration_seconds=total_duration,
        )

    async def _synthesize_with_llm(
        self,
        outputs: list[AgentOutput],
        original_system_prompt: str,
        original_user_prompt: str,
    ) -> AgentOutput:
        """Use the primary agent to produce a synthesis narrative."""
        primary_agent = self.adapters[self.primary_agent_index]
        formatted_outputs = self._format_agent_outputs(outputs)

        synthesis_system_prompt = (
            "You are the primary research synthesizer. "
            "Synthesize multiple agent outputs into a concise summary.\n\n"
            f"{original_system_prompt}"
        )

        synthesis_user_prompt = (
            "# Original Research Request\n\n"
            f"{original_user_prompt}\n\n"
            "# Agent Outputs\n\n"
            f"{formatted_outputs}\n\n"
            "Provide:\n"
            "1) key consensus points\n"
            "2) contradictions\n"
            "3) highest-confidence takeaways"
        )

        return await primary_agent.run(
            system_prompt=synthesis_system_prompt,
            user_prompt=synthesis_user_prompt,
            tools=[],
            max_iterations=1,
        )

    def _format_agent_outputs(self, outputs: list[AgentOutput]) -> str:
        """Format raw agent outputs for synthesis prompt."""
        parts: list[str] = []

        for i, output in enumerate(outputs, 1):
            parts.append(f"## Agent {i}: {output.agent_name}\n")
            parts.append(f"Model: {output.model}\n")
            parts.append(f"Searches: {len(output.searches_performed)}\n")
            parts.append(f"Cost: ${output.cost_usd:.4f}\n")
            parts.append(f"Duration: {output.duration_seconds:.1f}s\n\n")

            if output.raw_text:
                preview = output.raw_text[:5000]
                parts.append(f"### Raw Output\n\n{preview}\n\n")

            if output.self_critique:
                parts.append(f"### Self-Critique\n\n{output.self_critique}\n\n")

            parts.append("---\n\n")

        return "".join(parts)

    def _parse_synthesis_metadata(
        self,
        synthesis_output: AgentOutput,
    ) -> tuple[list[str], list[dict[str, Any]]]:
        """Best-effort extraction of consensus/contradictions from synthesis text."""
        text = (synthesis_output.self_critique or "") + "\n" + (
            synthesis_output.raw_text or ""
        )
        lowered = text.lower()

        consensus_findings: list[str] = []
        contradictions: list[dict[str, Any]] = []

        if "consensus" in lowered:
            consensus_findings.append("Consensus noted in synthesis output")

        if "contradict" in lowered or "disagree" in lowered:
            contradictions.append(
                {"claim": "Synthesis indicates contradiction", "note": "Review raw output"}
            )

        return consensus_findings, contradictions
