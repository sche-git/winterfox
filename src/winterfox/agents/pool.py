"""
Agent pool for parallel dispatch and LLM-driven synthesis.

Supports:
- Parallel agent dispatch
- LLM-driven synthesis (primary agent reviews all outputs)
- Intelligent consensus detection
- Evidence quality evaluation
"""

import asyncio
import logging
from dataclasses import dataclass
from typing import Any

from .protocol import AgentAdapter, AgentOutput, Finding, ToolDefinition

logger = logging.getLogger(__name__)


@dataclass
class SynthesisResult:
    """Result of LLM-driven synthesis."""

    findings: list[Finding]
    synthesis_reasoning: str
    consensus_findings: list[str]  # Claims with multi-agent agreement
    contradictions: list[dict[str, Any]]  # Conflicting findings
    individual_outputs: list[AgentOutput]
    total_cost_usd: float
    total_duration_seconds: float


class AgentPool:
    """Pool of agents for parallel research with LLM-driven synthesis."""

    def __init__(self, adapters: list[AgentAdapter], primary_agent_index: int = 0):
        """
        Initialize agent pool.

        Args:
            adapters: List of agent adapters
            primary_agent_index: Index of primary agent for synthesis (default: 0)
        """
        if not adapters:
            raise ValueError("At least one agent adapter required")

        if primary_agent_index < 0 or primary_agent_index >= len(adapters):
            raise ValueError(
                f"primary_agent_index {primary_agent_index} out of range [0, {len(adapters)-1}]"
            )

        self.adapters = adapters
        self.primary_agent_index = primary_agent_index
        logger.info(
            f"Initialized pool with {len(adapters)} agents, "
            f"primary: {adapters[primary_agent_index].name}"
        )

    async def dispatch(
        self,
        system_prompt: str,
        user_prompt: str,
        tools: list[ToolDefinition],
        max_iterations: int = 30,
    ) -> list[AgentOutput]:
        """
        Dispatch to all agents in parallel.

        Args:
            system_prompt: System instructions
            user_prompt: User research request
            tools: Available tools
            max_iterations: Maximum tool-use iterations per agent

        Returns:
            List of agent outputs
        """
        logger.info(f"Dispatching to {len(self.adapters)} agents in parallel")

        tasks = [
            adapter.run(system_prompt, user_prompt, tools, max_iterations)
            for adapter in self.adapters
        ]

        outputs = await asyncio.gather(*tasks, return_exceptions=True)

        # Fail fast on any agent error
        results = []
        for i, output in enumerate(outputs):
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
        """
        Dispatch to all agents, then use primary agent to synthesize results.

        This is the recommended way to use multiple agents. The workflow:
        1. All agents research the topic independently in parallel
        2. Primary agent receives all outputs and synthesizes them
        3. Primary agent identifies consensus, contradictions, and evaluates evidence
        4. Returns unified findings with synthesis reasoning

        Args:
            system_prompt: System instructions
            user_prompt: User research request
            tools: Available tools (all agents use same tools)
            max_iterations: Maximum tool-use iterations per agent

        Returns:
            SynthesisResult with synthesized findings
        """
        # Step 1: Dispatch to all agents in parallel
        logger.info("Step 1: Dispatching to all agents for independent research")
        outputs = await self.dispatch(system_prompt, user_prompt, tools, max_iterations)

        # If only one agent, no synthesis needed
        if len(self.adapters) == 1:
            logger.info("Single agent mode, skipping synthesis")
            return SynthesisResult(
                findings=outputs[0].findings,
                synthesis_reasoning="Single agent, no synthesis performed",
                consensus_findings=[],
                contradictions=[],
                individual_outputs=outputs,
                total_cost_usd=outputs[0].cost_usd,
                total_duration_seconds=outputs[0].duration_seconds,
            )

        # Step 2: Primary agent synthesizes all outputs
        logger.info(
            f"Step 2: Primary agent ({self.adapters[self.primary_agent_index].name}) "
            "synthesizing results"
        )
        synthesis_output = await self._synthesize_with_llm(
            outputs, system_prompt, user_prompt
        )

        # Calculate totals
        total_cost = sum(o.cost_usd for o in outputs) + synthesis_output.cost_usd
        total_duration = (
            max(o.duration_seconds for o in outputs) + synthesis_output.duration_seconds
        )

        # Parse synthesis output to extract consensus and contradictions
        consensus_findings, contradictions = self._parse_synthesis_metadata(
            synthesis_output
        )

        return SynthesisResult(
            findings=synthesis_output.findings,
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
        """
        Use primary agent to synthesize all agent outputs.

        Args:
            outputs: All agent outputs from parallel dispatch
            original_system_prompt: Original research system prompt
            original_user_prompt: Original research user prompt

        Returns:
            AgentOutput from synthesis
        """
        primary_agent = self.adapters[self.primary_agent_index]

        # Format all agent outputs for synthesis
        formatted_outputs = self._format_agent_outputs(outputs)

        # Synthesis system prompt
        synthesis_system_prompt = f"""You are the primary research synthesizer.

{original_system_prompt}

Your task is to synthesize findings from multiple AI research agents who independently
researched the same topic. You will receive their outputs and must produce a unified
set of findings that intelligently combines their work."""

        # Synthesis user prompt
        synthesis_user_prompt = f"""# Original Research Request

{original_user_prompt}

---

# Agent Outputs

Multiple AI agents researched this topic independently. Here are their outputs:

{formatted_outputs}

---

# Your Synthesis Task

Analyze all agent outputs and produce synthesized findings. For each finding:

1. **Identify Consensus**: If multiple agents report the same or similar claims,
   this is strong evidence. Boost confidence accordingly.

2. **Evaluate Contradictions**: If agents disagree, note the contradiction explicitly.
   Present both sides with evidence and assess which is more credible.

3. **Assess Evidence Quality**: Some agents may have stronger evidence than others.
   Weight findings by evidence quality, not just count.

4. **Avoid Redundancy**: Don't repeat the same finding multiple times. Synthesize
   similar claims into one finding with combined evidence.

5. **Preserve Unique Insights**: If only one agent found something unique but it has
   strong evidence, include it.

In your self_critique, explain your synthesis reasoning:
- Which findings had consensus (list claims)
- What contradictions you found (describe each)
- How you weighted evidence quality
- What unique insights you preserved

Output structured findings using note_finding for each synthesized claim."""

        # Only provide note_finding tool (no search, synthesis only)
        from .tools.graph_tools import create_note_finding_tool

        synthesis_tools = [create_note_finding_tool()]

        # Run synthesis (limit iterations since no research needed)
        synthesis_output = await primary_agent.run(
            system_prompt=synthesis_system_prompt,
            user_prompt=synthesis_user_prompt,
            tools=synthesis_tools,
            max_iterations=10,  # Synthesis shouldn't need many iterations
        )

        logger.info(
            f"Synthesis complete: {len(synthesis_output.findings)} findings, "
            f"cost ${synthesis_output.cost_usd:.4f}"
        )

        return synthesis_output

    def _format_agent_outputs(self, outputs: list[AgentOutput]) -> str:
        """
        Format agent outputs for synthesis prompt.

        Args:
            outputs: List of agent outputs

        Returns:
            Formatted string for LLM consumption
        """
        formatted = []

        for i, output in enumerate(outputs, 1):
            formatted.append(f"## Agent {i}: {output.agent_name}\n")
            formatted.append(f"**Model**: {output.model}\n")
            formatted.append(
                f"**Searches**: {len(output.searches_performed)} performed\n"
            )
            formatted.append(f"**Findings**: {len(output.findings)} reported\n\n")

            if output.findings:
                formatted.append("### Findings:\n\n")
                for j, finding in enumerate(output.findings, 1):
                    formatted.append(f"{j}. **Claim**: {finding.claim}\n")
                    formatted.append(
                        f"   - **Confidence**: {finding.confidence:.2f}\n"
                    )
                    formatted.append(f"   - **Evidence**: {len(finding.evidence)} sources\n")

                    # Include key evidence snippets
                    if finding.evidence:
                        formatted.append("   - **Key Evidence**:\n")
                        for evidence in finding.evidence[:2]:  # First 2 sources
                            formatted.append(f"     - {evidence.source}: \"{evidence.text[:150]}...\"\n")
                    formatted.append("\n")
            else:
                formatted.append("*No findings reported*\n\n")

            # Include agent's self-critique
            if output.self_critique:
                formatted.append(f"### Agent's Self-Critique:\n{output.self_critique}\n\n")

            formatted.append("---\n\n")

        return "".join(formatted)

    def _parse_synthesis_metadata(
        self, synthesis_output: AgentOutput
    ) -> tuple[list[str], list[dict[str, Any]]]:
        """
        Parse synthesis metadata from self_critique.

        Extracts consensus findings and contradictions that the primary agent
        identified during synthesis.

        Args:
            synthesis_output: Output from synthesis

        Returns:
            (consensus_findings, contradictions)
        """
        consensus_findings = []
        contradictions = []

        # Try to parse from self_critique
        critique = synthesis_output.self_critique.lower()

        # Look for consensus markers
        if "consensus" in critique:
            # Extract claims with consensus
            for finding in synthesis_output.findings:
                if any(tag == "consensus" for tag in (finding.tags or [])):
                    consensus_findings.append(finding.claim)

        # Look for contradiction markers
        if "contradict" in critique or "disagree" in critique:
            # Extract contradictions (this is best-effort parsing)
            # LLM should tag findings with contradiction details
            for finding in synthesis_output.findings:
                if finding.tags and any("contradict" in tag for tag in finding.tags):
                    contradictions.append(
                        {
                            "claim": finding.claim,
                            "note": "Agents reported contradictory information",
                        }
                    )

        return consensus_findings, contradictions
