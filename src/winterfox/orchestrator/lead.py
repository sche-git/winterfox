"""
Lead LLM orchestrator for autonomous research cycle management.

The LeadLLM class owns the entire research cycle lifecycle:
- Selects which direction to pursue (no hardcoded formulas)
- Dispatches research agents for parallel investigation
- Synthesizes raw outputs into strategic directions

This replaces the old multi-agent consensus system with a unified Lead LLM
that makes all strategic decisions autonomously.
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..agents.protocol import AgentAdapter, AgentOutput
    from ..graph.models import Evidence, KnowledgeNode
    from ..graph.store import KnowledgeGraph

logger = logging.getLogger(__name__)


@dataclass
class Direction:
    """
    A research direction extracted by Lead LLM from raw outputs.

    Directions are strategic paths to explore, not individual facts.
    """
    claim: str
    confidence: float  # 0.0 to 1.0
    importance: float  # 0.0 to 1.0
    reasoning: str  # Why this direction matters
    evidence_summary: str  # Brief summary of supporting evidence
    tags: list[str] | None = None


@dataclass
class DirectionSynthesis:
    """Result of Lead LLM synthesizing research into directions."""
    directions: list[Direction]
    synthesis_reasoning: str
    consensus_directions: list[str]  # Directions all agents agreed on
    contradictions: list[str]  # Where agents disagreed


class LeadLLM:
    """
    Orchestrates research cycles with maximum autonomy.

    The Lead LLM is the strategic intelligence that:
    - Analyzes graph state and decides which direction to pursue
    - Dispatches research agents for parallel investigation
    - Synthesizes raw outputs into meaningful directions

    This replaces hardcoded selection formulas (UCB1) and structured
    findings with pure LLM strategic reasoning.
    """

    def __init__(
        self,
        adapter: AgentAdapter,
        graph: KnowledgeGraph,
        north_star: str,
        report_content: str | None = None,
    ):
        """
        Initialize Lead LLM.

        Args:
            adapter: LLM adapter for Lead agent
            graph: Knowledge graph
            north_star: Project mission/research objective
            report_content: Optional report for context (auto-updated)
        """
        self.adapter = adapter
        self.graph = graph
        self.north_star = north_star
        self.report_content = report_content
        logger.info(f"Initialized Lead LLM: {adapter.name}")

    async def select_direction(
        self,
        last_selected_id: str | None = None,
    ) -> tuple[KnowledgeNode, str]:
        """
        Lead LLM strategically selects which direction to pursue next.

        Replaces hardcoded UCB1 formula with LLM strategic thinking.
        The Lead analyzes:
        - Graph structure and confidence gaps
        - Research history and prior cycles
        - Report context if available
        - Exploration/exploitation balance

        Args:
            last_selected_id: ID of previously selected node (optional)

        Returns:
            (target_node, selection_reasoning) tuple
        """
        from ..graph.views import render_summary_view, render_weakest_nodes

        logger.info("Lead LLM selecting direction...")

        # Build context for selection decision
        graph_summary = await render_summary_view(self.graph, max_depth=2, max_nodes=50)
        weakest_nodes = await render_weakest_nodes(self.graph, n=10)

        # Get all nodes for Lead to choose from
        all_nodes = await self.graph.get_all_active_nodes()

        if not all_nodes:
            raise ValueError("No active nodes in graph - cannot select direction")

        # Format node options for Lead LLM
        node_options = []
        for node in all_nodes[:30]:  # Limit to 30 most relevant
            claim_preview = node.claim[:100] + "..." if len(node.claim) > 100 else node.claim
            node_options.append(
                f"- **{node.id[:8]}**: {claim_preview}\n"
                f"  Conf: {node.confidence:.2f} | Imp: {node.importance:.2f} | "
                f"Depth: {node.depth} | Stale: {node.staleness_hours:.1f}h | "
                f"Children: {len(node.children_ids)}"
            )

        node_list = "\n".join(node_options)

        # Build selection prompt
        system_prompt = f"""You are the Lead LLM orchestrating an autonomous research project:

{self.north_star}

Your role is to strategically select which direction to pursue next in the knowledge graph.
You have maximum autonomy - analyze the current state and make the best strategic decision.

## Strategic Considerations

1. **Exploration vs Exploitation Balance**
   - Explore: Pursue directions with low depth and few children (breadth)
   - Exploit: Deepen directions with low confidence but high importance (depth)

2. **Confidence Gaps**
   - Prioritize directions with low confidence (<0.6) if they're important
   - Don't neglect high-confidence directions that might need challenging

3. **Staleness**
   - Consider refreshing stale directions (>72 hours)
   - Balance with pursuing new directions

4. **Research Momentum**
   - Build on recent progress where appropriate
   - Don't get stuck in local minima

5. **Strategic Value**
   - Importance score reflects strategic relevance to mission
   - High importance, low confidence = high priority

## Output Format

Respond with ONLY this JSON structure:
{{
  "selected_node_id": "abc123...",
  "reasoning": "2-3 sentences explaining why this direction is the best strategic choice right now"
}}
"""

        # Add report context if available
        report_section = ""
        if self.report_content:
            report_preview = self.report_content[:2000] + "\n\n[Report truncated...]" if len(self.report_content) > 2000 else self.report_content
            report_section = f"\n## Current Research Report\n\n{report_preview}\n"

        # Add last selected context if available
        last_selected_section = ""
        if last_selected_id:
            last_node = await self.graph.get_node(last_selected_id)
            if last_node:
                last_selected_section = f"\n## Last Selected Direction\n\n**{last_node.claim[:100]}**\n(ID: {last_selected_id})\n\nConsider whether to continue building on this or pivot to a different direction.\n"

        user_prompt = f"""## Graph State

{graph_summary}

## Priority Directions

{weakest_nodes}

## All Available Directions

{node_list}
{report_section}{last_selected_section}
---

Analyze the graph state and select the best direction to pursue next.
Consider exploration/exploitation balance, confidence gaps, staleness, and strategic value.

Respond with ONLY the JSON structure specified (no markdown, no explanation outside JSON).
"""

        # Call Lead LLM for selection
        output = await self.adapter.run(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            tools=[],  # No tools, pure strategic reasoning
            max_iterations=1,
        )

        # Parse JSON response
        import json
        import re

        # Extract JSON from response (handle markdown code blocks)
        raw_text = output.raw_text.strip()
        json_match = re.search(r'\{[^{}]*"selected_node_id"[^{}]*\}', raw_text, re.DOTALL)

        if not json_match:
            logger.warning(f"Lead LLM response not in JSON format: {raw_text[:200]}")
            # Fallback to first node
            logger.warning("Falling back to first available node")
            return all_nodes[0], "Fallback selection (Lead LLM response parse failed)"

        try:
            selection_data = json.loads(json_match.group())
            selected_id = selection_data["selected_node_id"]
            reasoning = selection_data["reasoning"]

            # Find the node
            target = await self.graph.get_node(selected_id)

            if not target:
                # Try partial match (Lead might have shortened the ID)
                for node in all_nodes:
                    if node.id.startswith(selected_id):
                        target = node
                        break

            if not target:
                logger.warning(f"Lead LLM selected invalid node ID: {selected_id}")
                logger.warning("Falling back to first available node")
                return all_nodes[0], f"Fallback selection (invalid ID: {selected_id})"

            logger.info(f"Lead LLM selected: {target.claim[:50]}... (Reason: {reasoning[:100]}...)")
            return target, reasoning

        except (json.JSONDecodeError, KeyError) as e:
            logger.warning(f"Failed to parse Lead LLM selection: {e}")
            logger.warning(f"Raw response: {raw_text[:200]}")
            return all_nodes[0], f"Fallback selection (parse error: {e})"

    async def dispatch_research(
        self,
        target_node: KnowledgeNode,
        research_agents: list[AgentAdapter],
        tools: list,
        max_searches: int,
    ) -> list[AgentOutput]:
        """
        Lead LLM dispatches research agents in parallel.

        Generates research prompts and coordinates parallel investigation.
        Research agents return raw outputs (no structured findings).

        Args:
            target_node: Direction to research
            research_agents: List of research agent adapters
            tools: Available research tools
            max_searches: Maximum searches per agent

        Returns:
            List of raw agent outputs
        """
        from ..graph.views import render_focused_view

        logger.info(f"Lead LLM dispatching {len(research_agents)} research agents...")

        # Generate focused view of target direction
        focused_view = await render_focused_view(self.graph, target_node.id, max_depth=3)

        # Build research system prompt (no note_finding tool)
        system_prompt = f"""You are an expert research agent working on:

{self.north_star}

Your task is to research a specific direction thoroughly using web search and content fetching.

## Research Guidelines

1. **Evidence-Based**: Find concrete facts, numbers, quotes, examples
2. **Multiple Sources**: Verify claims with independent sources
3. **Skeptical**: Look for contradicting viewpoints
4. **Comprehensive**: Cover all aspects of the research direction
5. **Budget**: You have {max_searches} web searches - use them effectively

## Important Changes

- **No structured findings**: Just do thorough research
- **Raw output is primary**: Your full reasoning and discoveries will be analyzed by the Lead LLM
- **Focus on quality**: Better to deeply investigate fewer aspects than superficially cover many

## Tools Available

- `web_search`: Search the web for information
- `web_fetch`: Read full content from URLs
- `read_graph_node`: Read other nodes in the knowledge graph
- `search_graph`: Search the knowledge graph

After your research, you'll be asked for a brief self-critique."""

        # Build research user prompt
        user_prompt = f"""## Research Direction

{focused_view}

## Your Research Task

Thoroughly investigate this direction. Find evidence, verify claims, explore sub-topics.

- Use web_search to find relevant sources
- Use web_fetch to read full content
- Look for specific data, quotes, examples, and statistics
- Consider multiple perspectives
- Note any contradictions or uncertainties you find

Begin your research. Remember: your raw output will be analyzed by the Lead LLM to extract strategic directions."""

        # Dispatch all research agents in parallel
        tasks = [
            agent.run(system_prompt, user_prompt, tools, max_iterations=30)
            for agent in research_agents
        ]

        outputs = await asyncio.gather(*tasks, return_exceptions=True)

        # Handle errors
        results = []
        for i, output in enumerate(outputs):
            if isinstance(output, Exception):
                logger.error(f"Research agent {research_agents[i].name} failed: {output}")
                # Continue with other agents
            else:
                results.append(output)

        if not results:
            raise ValueError("All research agents failed")

        logger.info(f"Research complete: {len(results)} agents returned outputs")
        return results

    async def synthesize_directions(
        self,
        agent_outputs: list[AgentOutput],
        target_node: KnowledgeNode,
    ) -> DirectionSynthesis:
        """
        Lead LLM extracts strategic directions from raw research outputs.

        Replaces note_finding tool - LLM decides what matters.
        Synthesizes multiple raw outputs into 3-7+ directions (no fixed limit).

        Args:
            agent_outputs: Raw outputs from research agents
            target_node: Direction that was researched

        Returns:
            DirectionSynthesis with extracted directions
        """
        logger.info(f"Lead LLM synthesizing {len(agent_outputs)} raw outputs...")

        # Format agent outputs for synthesis
        formatted_outputs = []
        for i, output in enumerate(agent_outputs, 1):
            searches_summary = f"{len(output.searches_performed)} searches performed"
            formatted_outputs.append(
                f"## Research Agent {i}: {output.agent_name}\n\n"
                f"**Searches**: {searches_summary}\n"
                f"**Duration**: {output.duration_seconds:.1f}s\n"
                f"**Cost**: ${output.cost_usd:.4f}\n\n"
                f"### Research Output:\n\n{output.raw_text}\n\n"
                f"### Self-Critique:\n\n{output.self_critique}\n\n"
                "---\n\n"
            )

        combined_outputs = "".join(formatted_outputs)

        # Build synthesis system prompt
        system_prompt = f"""You are the Lead LLM synthesizing research for:

{self.north_star}

Multiple research agents investigated a direction independently. You will receive their
raw outputs and must extract strategic DIRECTIONS to pursue next.

## What Are Directions?

Directions are meaningful paths to explore - NOT individual facts. Examples:
- "Investigate B2B vs B2C market fit for legal tech startups"
- "Explore funding strategies: VC vs bootstrapping vs strategic partnerships"
- "Analyze competitive advantages in the AI-powered contract review space"

NOT directions (too granular):
- "Legal tech market is $50B" (this is just a fact)
- "YC funded 10 legal tech companies" (just a data point)

## Synthesis Guidelines

1. **Extract Directions** (3-7+, no hard limit):
   - Look for strategic questions, approaches, or hypotheses
   - Group related findings into coherent directions
   - Each direction should suggest a path of inquiry

2. **Assess Confidence**:
   - High (0.8-1.0): Multiple agents agree, strong evidence
   - Medium (0.5-0.7): Some agreement, decent evidence
   - Low (0.0-0.4): Single source, weak evidence, speculative

3. **Determine Importance**:
   - High (0.8-1.0): Critical to mission, high impact
   - Medium (0.5-0.7): Relevant, moderate impact
   - Low (0.0-0.4): Tangential, low impact

4. **Identify Consensus**:
   - What did multiple agents agree on?
   - Where is there strong corroboration?

5. **Spot Contradictions**:
   - What disagreements exist?
   - Which claims conflict?

## Output Format

Respond with ONLY this JSON structure:
{{
  "directions": [
    {{
      "claim": "Direction statement (strategic path to explore)",
      "confidence": 0.85,
      "importance": 0.9,
      "reasoning": "Why this direction matters and what it builds on",
      "evidence_summary": "Brief summary of supporting evidence",
      "tags": ["tag1", "tag2"]
    }}
  ],
  "synthesis_reasoning": "2-3 sentences on your synthesis approach",
  "consensus_directions": ["Direction 1", "Direction 2"],
  "contradictions": ["Contradiction 1", "Contradiction 2"]
}}

Be strategic - extract directions that move research forward, not just facts."""

        user_prompt = f"""## Target Direction Researched

**{target_node.claim}**

## Raw Research Outputs

{combined_outputs}

---

Analyze all outputs and extract strategic DIRECTIONS (not facts).
Identify consensus and contradictions.
Respond with ONLY the JSON structure (no markdown, no extra text).
"""

        # Call Lead LLM for synthesis
        output = await self.adapter.run(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            tools=[],  # No tools, pure synthesis
            max_iterations=1,
        )

        # Parse JSON response
        import json
        import re

        raw_text = output.raw_text.strip()
        json_match = re.search(r'\{.*"directions".*\}', raw_text, re.DOTALL)

        if not json_match:
            logger.error(f"Lead LLM synthesis not in JSON format: {raw_text[:500]}")
            # Fallback: create default direction
            return DirectionSynthesis(
                directions=[
                    Direction(
                        claim=f"Continue investigating: {target_node.claim}",
                        confidence=0.5,
                        importance=0.7,
                        reasoning="Fallback direction (synthesis parse failed)",
                        evidence_summary="Research agents completed investigation but synthesis failed to parse",
                    )
                ],
                synthesis_reasoning="Synthesis parse failed - using fallback direction",
                consensus_directions=[],
                contradictions=[],
            )

        try:
            synthesis_data = json.loads(json_match.group())

            # Parse directions
            directions = []
            for dir_data in synthesis_data.get("directions", []):
                directions.append(Direction(
                    claim=dir_data["claim"],
                    confidence=float(dir_data["confidence"]),
                    importance=float(dir_data["importance"]),
                    reasoning=dir_data["reasoning"],
                    evidence_summary=dir_data["evidence_summary"],
                    tags=dir_data.get("tags", []),
                ))

            result = DirectionSynthesis(
                directions=directions,
                synthesis_reasoning=synthesis_data.get("synthesis_reasoning", ""),
                consensus_directions=synthesis_data.get("consensus_directions", []),
                contradictions=synthesis_data.get("contradictions", []),
            )

            logger.info(
                f"Lead LLM extracted {len(directions)} directions, "
                f"{len(result.consensus_directions)} consensus, "
                f"{len(result.contradictions)} contradictions"
            )

            return result

        except (json.JSONDecodeError, KeyError, ValueError) as e:
            logger.error(f"Failed to parse Lead LLM synthesis: {e}")
            logger.error(f"Raw response: {raw_text[:500]}")

            # Fallback
            return DirectionSynthesis(
                directions=[
                    Direction(
                        claim=f"Continue investigating: {target_node.claim}",
                        confidence=0.5,
                        importance=0.7,
                        reasoning=f"Fallback direction (synthesis parse error: {e})",
                        evidence_summary="Research agents completed investigation but synthesis failed to parse",
                    )
                ],
                synthesis_reasoning=f"Synthesis parse error: {e}",
                consensus_directions=[],
                contradictions=[],
            )
