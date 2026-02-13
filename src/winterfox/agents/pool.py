"""
Agent pool for parallel dispatch and consensus analysis.

Supports:
- Parallel agent dispatch
- Consensus detection
- Confidence boosting when agents agree
- Finding deduplication
"""

import asyncio
import logging
from dataclasses import dataclass
from typing import Any

from .protocol import AgentAdapter, AgentOutput, Finding, ToolDefinition

logger = logging.getLogger(__name__)


@dataclass
class ConsensusResult:
    """Result of consensus analysis."""

    findings: list[Finding]
    consensus_count: int
    divergent_count: int
    individual_outputs: list[AgentOutput]
    total_cost_usd: float
    total_duration_seconds: float


class AgentPool:
    """Pool of agents for parallel research with consensus analysis."""

    def __init__(self, adapters: list[AgentAdapter]):
        """
        Initialize agent pool.

        Args:
            adapters: List of agent adapters
        """
        if not adapters:
            raise ValueError("At least one agent adapter required")

        self.adapters = adapters
        logger.info(f"Initialized pool with {len(adapters)} agents")

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

        # Handle exceptions
        results = []
        for i, output in enumerate(outputs):
            if isinstance(output, Exception):
                logger.error(
                    f"Agent {self.adapters[i].name} failed: {output}",
                    exc_info=output,
                )
                # Create empty output for failed agent
                results.append(
                    AgentOutput(
                        findings=[],
                        self_critique=f"Agent failed: {output}",
                        raw_text="",
                        searches_performed=[],
                        cost_usd=0.0,
                        duration_seconds=0.0,
                        agent_name=self.adapters[i].name,
                        model="unknown",
                        total_tokens=0,
                        input_tokens=0,
                        output_tokens=0,
                    )
                )
            else:
                results.append(output)

        return results

    async def dispatch_with_consensus(
        self,
        system_prompt: str,
        user_prompt: str,
        tools: list[ToolDefinition],
        max_iterations: int = 30,
        similarity_threshold: float = 0.75,
        consensus_boost: float = 0.15,
    ) -> ConsensusResult:
        """
        Dispatch to agents and analyze consensus.

        When multiple agents arrive at similar findings independently,
        boost the confidence.

        Args:
            system_prompt: System instructions
            user_prompt: User research request
            tools: Available tools
            max_iterations: Maximum tool-use iterations
            similarity_threshold: Minimum similarity for consensus
            consensus_boost: Confidence boost for consensus findings

        Returns:
            ConsensusResult with merged findings
        """
        # Dispatch to all agents
        outputs = await self.dispatch(system_prompt, user_prompt, tools, max_iterations)

        # Collect all findings
        all_findings = []
        for output in outputs:
            for finding in output.findings:
                # Tag with agent name
                if not finding.tags:
                    finding.tags = []
                finding.tags.append(f"agent:{output.agent_name}")
                all_findings.append(finding)

        # Group similar findings
        finding_groups = self._group_similar_findings(
            all_findings, similarity_threshold
        )

        # Merge and boost consensus findings
        merged_findings = []
        consensus_count = 0
        divergent_count = 0

        for group in finding_groups:
            if len(group) >= 2:
                # Consensus: multiple agents agree
                merged = self._merge_findings(group)
                merged.confidence = min(0.95, merged.confidence + consensus_boost)
                merged.tags.append("consensus")
                merged_findings.append(merged)
                consensus_count += 1

                logger.info(
                    f"Consensus finding ({len(group)} agents): "
                    f"{merged.claim[:60]}... (conf={merged.confidence:.2f})"
                )
            else:
                # Divergent: only one agent found this
                merged_findings.append(group[0])
                divergent_count += 1

        # Calculate totals
        total_cost = sum(o.cost_usd for o in outputs)
        total_duration = max(o.duration_seconds for o in outputs)  # Parallel, so max

        return ConsensusResult(
            findings=merged_findings,
            consensus_count=consensus_count,
            divergent_count=divergent_count,
            individual_outputs=outputs,
            total_cost_usd=total_cost,
            total_duration_seconds=total_duration,
        )

    def _group_similar_findings(
        self,
        findings: list[Finding],
        threshold: float = 0.75,
    ) -> list[list[Finding]]:
        """
        Group similar findings using claim similarity.

        Args:
            findings: List of findings
            threshold: Minimum similarity for grouping

        Returns:
            List of finding groups
        """
        from ..graph.operations import calculate_claim_similarity

        groups = []
        processed = set()

        for i, finding1 in enumerate(findings):
            if i in processed:
                continue

            group = [finding1]
            processed.add(i)

            for j, finding2 in enumerate(findings[i + 1 :], start=i + 1):
                if j in processed:
                    continue

                similarity = calculate_claim_similarity(finding1.claim, finding2.claim)

                if similarity >= threshold:
                    group.append(finding2)
                    processed.add(j)

            groups.append(group)

        return groups

    def _merge_findings(self, findings: list[Finding]) -> Finding:
        """
        Merge multiple similar findings into one.

        Args:
            findings: List of similar findings

        Returns:
            Merged finding
        """
        if not findings:
            raise ValueError("Cannot merge empty findings list")

        if len(findings) == 1:
            return findings[0]

        # Use the longest claim
        claims = [f.claim for f in findings]
        merged_claim = max(claims, key=len)

        # Combine all evidence
        all_evidence = []
        for f in findings:
            all_evidence.extend(f.evidence)

        # Average confidence (independent confirmation model would be better)
        merged_confidence = sum(f.confidence for f in findings) / len(findings)

        # Combine tags
        all_tags = []
        for f in findings:
            all_tags.extend(f.tags)
        merged_tags = list(set(all_tags))  # Deduplicate

        # Combine suggested children
        all_children = []
        for f in findings:
            all_children.extend(f.suggested_children)
        merged_children = list(set(all_children))

        return Finding(
            claim=merged_claim,
            confidence=merged_confidence,
            evidence=all_evidence,
            suggested_parent_id=findings[0].suggested_parent_id,
            suggested_children=merged_children,
            tags=merged_tags,
        )
