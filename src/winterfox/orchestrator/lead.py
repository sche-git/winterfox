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


def _render_cycle_instruction(cycle_instruction: str | None) -> str:
    """Render optional cycle-specific steering guidance."""
    if not cycle_instruction:
        return ""

    text = cycle_instruction.strip()
    if not text:
        return ""

    return (
        "\n## Cycle Override Instruction (Highest Priority This Cycle)\n\n"
        f"{text}\n\n"
        "This comes from user-provided steering for this cycle. "
        "Honor it as the primary directive unless it conflicts with safety or factual integrity.\n"
    )


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
    description: str  # Detailed one-page narrative for users/UI
    stance: str = "mixed"  # support|mixed|disconfirm evidence alignment for this direction claim
    direction_outcome: str = "pursue"  # pursue|complete lifecycle recommendation for this direction
    tags: list[str] | None = None


@dataclass
class DirectionSynthesis:
    """Result of Lead LLM synthesizing research into directions."""
    directions: list[Direction]
    synthesis_reasoning: str
    consensus_directions: list[str]  # Directions all agents agreed on
    contradictions: list[str]  # Where agents disagreed


@dataclass
class ResearchDispatchResult:
    """Result of dispatching research agents plus prompt context snapshot."""

    outputs: list[AgentOutput]
    focused_view: str
    system_prompt: str
    user_prompt: str


@dataclass
class TargetReassessment:
    """Lead LLM reassessment of a target direction after a research cycle."""

    confidence: float
    importance: float
    status: str
    reasoning: str
    cost_usd: float = 0.0


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
        cycle_instruction: str | None = None,
        excluded_node_ids: set[str] | None = None,
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
            cycle_instruction: Optional cycle-specific steering guidance
            excluded_node_ids: Optional node IDs that must not be selected

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
        excluded = excluded_node_ids or set()
        candidate_nodes = [node for node in all_nodes if node.id not in excluded]

        if not all_nodes:
            raise ValueError("No active nodes in graph - cannot select direction")
        if not candidate_nodes:
            raise ValueError("No eligible active nodes remain after exclusions")

        # Format node options for Lead LLM
        node_options = []
        for node in candidate_nodes[:30]:  # Limit to 30 most relevant
            claim_preview = node.claim[:100] + "..." if len(node.claim) > 100 else node.claim
            node_options.append(
                f"- **{node.id[:8]}**: {claim_preview}\n"
                f"  Conf: {node.confidence:.2f} | Imp: {node.importance:.2f} | "
                f"Depth: {node.depth} | Stale: {node.staleness_hours:.1f}h | "
                f"Children: {len(node.children_ids)}"
            )

        node_list = "\n".join(node_options)
        cycle_instruction_section = _render_cycle_instruction(cycle_instruction)

        # Build selection prompt
        system_prompt = f"""You are the Lead LLM orchestrating an autonomous research project:

{self.north_star}

Your role is to strategically select which direction to pursue next in the knowledge graph.
You have maximum autonomy - analyze the current state and make the best strategic decision.

## Priority Order

1. **Honor user steering first**:
   - If a cycle override instruction is present, align selection to that intent.
2. **Maintain balanced progress**:
   - Avoid tunnel vision on a single branch when credible alternatives remain unexplored.
3. **Maximize useful learning**:
   - Prefer choices that reduce key uncertainty and improve decision quality.

## Strategic Considerations

1. **Exploration vs Exploitation Balance**
   - Explore: Pursue directions with low depth and few children (breadth)
   - Exploit: Deepen directions with low confidence but high importance (depth)
   - Keep a healthy portfolio across cycles instead of repeatedly selecting the same local area

2. **Confidence Gaps**
   - Prioritize directions with low confidence (<0.6) if they're important
   - Don't neglect high-confidence directions that might need challenging

3. **Staleness**
   - Consider refreshing stale directions (>72 hours)
   - Balance with pursuing new directions

4. **Research Momentum**
   - Build on recent progress where appropriate
   - Don't get stuck in local minima or repetitive deep dives

5. **Strategic Value**
   - Importance score reflects strategic relevance to mission
   - High importance, low confidence = high priority

6. **Concreteness Progression (Depth-Aware)**
   - Treat graph depth as a concreteness ladder:
     - Depth 0: strategic thesis
     - Depth 1: wedge + segment
     - Depth 2: buyer/workflow + measurable pain
     - Depth 3+: concrete targets (named companies/accounts), procurement path, integration/feasibility specifics
   - If the graph already has many sibling branches, prefer selecting leaf/near-leaf nodes to refine concreteness
   - Avoid repeatedly selecting high-level nodes when deeper unresolved nodes exist in that branch
{cycle_instruction_section}

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

        excluded_section = ""
        if excluded:
            excluded_list = "\n".join(f"- {node_id}" for node_id in sorted(excluded)[:30])
            excluded_section = (
                "\n## Excluded Directions (Do Not Select)\n\n"
                f"{excluded_list}\n"
            )

        user_prompt = f"""## Graph State

{graph_summary}

## Priority Directions

{weakest_nodes}

## All Available Directions

{node_list}
{report_section}{last_selected_section}{excluded_section}
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
            return candidate_nodes[0], "Fallback selection (Lead LLM response parse failed)"

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
                return candidate_nodes[0], f"Fallback selection (invalid ID: {selected_id})"
            if target.id in excluded:
                logger.warning(f"Lead LLM selected excluded node ID: {selected_id}")
                logger.warning("Falling back to first non-excluded node")
                return candidate_nodes[0], f"Fallback selection (excluded ID: {selected_id})"

            logger.info(f"Lead LLM selected: {target.claim[:50]}... (Reason: {reasoning[:100]}...)")
            return target, reasoning

        except (json.JSONDecodeError, KeyError) as e:
            logger.warning(f"Failed to parse Lead LLM selection: {e}")
            logger.warning(f"Raw response: {raw_text[:200]}")
            return candidate_nodes[0], f"Fallback selection (parse error: {e})"

    async def dispatch_research(
        self,
        target_node: KnowledgeNode,
        research_agents: list[AgentAdapter],
        tools: list,
        max_searches: int,
        cycle_instruction: str | None = None,
    ) -> ResearchDispatchResult:
        """
        Lead LLM dispatches research agents in parallel.

        Generates research prompts and coordinates parallel investigation.
        Research agents return raw outputs (no structured findings).

        Args:
            target_node: Direction to research
            research_agents: List of research agent adapters
            tools: Available research tools
            max_searches: Maximum searches per agent
            cycle_instruction: Optional cycle-specific steering guidance

        Returns:
            ResearchDispatchResult containing agent outputs and prompt context
        """
        from ..graph.views import render_focused_view

        logger.info(f"Lead LLM dispatching {len(research_agents)} research agents...")

        # Generate focused view of target direction
        focused_view = await render_focused_view(self.graph, target_node.id, max_depth=3)
        cycle_instruction_section = _render_cycle_instruction(cycle_instruction)

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
6. **Stay broad enough**: Test adjacent hypotheses and alternatives, not just the first promising thread
7. **Align with user steering**: If a cycle override instruction is present, treat it as the primary objective for this cycle

## Important Changes

- **No structured findings**: Just do thorough research
- **Raw output is primary**: Your full reasoning and discoveries will be analyzed by the Lead LLM
- **Focus on quality**: Better to deeply investigate fewer aspects than superficially cover many

## Tools Available

- `web_search`: Search the web for information
- `web_fetch`: Read full content from URLs
- `read_graph_node`: Read other nodes in the knowledge graph
- `search_graph`: Search the knowledge graph
{cycle_instruction_section}

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
        return ResearchDispatchResult(
            outputs=results,
            focused_view=focused_view,
            system_prompt=system_prompt,
            user_prompt=user_prompt,
        )

    async def synthesize_directions(
        self,
        agent_outputs: list[AgentOutput],
        target_node: KnowledgeNode,
        cycle_instruction: str | None = None,
    ) -> DirectionSynthesis:
        """
        Lead LLM extracts strategic directions from raw research outputs.

        Replaces note_finding tool - LLM decides what matters.
        Synthesizes multiple raw outputs into strategic next-step directions.

        Args:
            agent_outputs: Raw outputs from research agents
            target_node: Direction that was researched
            cycle_instruction: Optional cycle-specific steering guidance

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
        cycle_instruction_section = _render_cycle_instruction(cycle_instruction)

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

1. **Extract Directions**:
   - Look for strategic questions, approaches, or hypotheses
   - Group related findings into coherent directions
   - Each direction should suggest a path of inquiry
   - For each direction, provide:
     - `claim`: concise one-line summary
     - `description`: long-form Markdown narrative (at least 220 words; target 350-700 words)
       - Use Markdown structure with short sections and bullets where helpful
       - Preserve meaningful line breaks between sections/points
       - Include concrete items: context, key evidence, assumptions/risks, and Winterfox-executable next actions
     - `stance`: one of:
       - `support`: evidence supports this direction claim
       - `mixed`: evidence is mixed/uncertain
       - `disconfirm`: evidence undermines this direction claim
     - `direction_outcome`: one of:
       - `pursue`: keep active for future investigation
       - `complete`: treat as sufficiently concluded/dead-end for now
   - Prefer deepening or revising existing strategic paths when evidence supports that
   - Propose genuinely new branches only when current evidence indicates clear unexplored opportunity
   - Do not branch for its own sake; avoid direction inflation
   - Preserve depth-wise progression: child directions should usually be more concrete than the target direction

2. **Concreteness Ladder (By Target Depth)**:
   - If target depth is 0, output should trend toward wedge/segment specificity
   - If target depth is 1, output should trend toward buyer/workflow and measurable pains
   - If target depth is 2, output should trend toward concrete accounts/companies and deployment constraints
   - If target depth is 3+, output should trend toward execution-ready specificity (named targets, integration path, feasibility evidence)
   - Avoid lateral rewording at the same abstraction level unless evidence is explicitly contradictory
3. **Assess Confidence**:
   - Interpret confidence as confidence in THIS direction claim.
   - High (0.8-1.0): Strong corroboration for the claim
   - Medium (0.5-0.7): Mixed but direction still plausible
   - Low (0.0-0.4): Weak or contradictory support for this claim
   - If stance is `disconfirm`, confidence should usually be low unless disconfirmation itself is strongly evidenced.

4. **Determine Importance**:
   - High (0.8-1.0): Critical to mission, high impact
   - Medium (0.5-0.7): Relevant, moderate impact
   - Low (0.0-0.4): Tangential, low impact

5. **Identify Consensus**:
   - What did multiple agents agree on?
   - Where is there strong corroboration?

6. **Spot Contradictions**:
   - What disagreements exist?
   - Which claims conflict?
   - If most evidence is negative against a direction claim, label stance=`disconfirm` and prefer direction_outcome=`complete`

7. **Respect User Steering**:
   - If a cycle override instruction is present, bias synthesis priorities to that instruction
   - Keep conclusions evidence-grounded and avoid overfitting to a single narrative
{cycle_instruction_section}

8. **Branching Discipline**:
   - You are not required to create multiple new directions every cycle
   - It is valid to return a small set of focused directions if that best reflects the evidence
   - Prioritize clarity and strategic utility over quantity

9. **Next Actions Must Be Winterfox-Executable**:
   - In each direction description, the `## Next Actions` section must include ONLY actions
     that can be executed in a future Winterfox cycle via web-based research.
   - Allowed action types:
     - Investigate a sub-direction with targeted web searches
     - Assess feasibility by reviewing academic papers, benchmarks, standards, docs, filings, or technical reports
     - Resolve contradictions across independent sources
     - Gather specific missing evidence needed to raise/lower confidence
   - Disallowed action types:
     - Talk to customers, interviews, surveys, or sales calls
     - Run product experiments, build prototypes, or engineering implementation
     - Hiring, partnerships, procurement, or other offline operational tasks
   - For each next action include:
     - Objective: what the research action should prove/disprove
     - Query seeds: 2-5 concrete web search query ideas
     - Source targets: what source types to prioritize
     - Completion signal: explicit evidence threshold for considering the action done

## Output Format

Respond with ONLY this JSON structure:
{{
  "directions": [
    {{
      "claim": "Short summary (one line, <=120 chars)",
      "description": "Markdown one-page narrative (target 350-700 words) with sections like ## Context, ## Evidence, ## Risks/Assumptions, ## Next Actions, where Next Actions are Winterfox-executable research tasks only",
      "stance": "support|mixed|disconfirm",
      "direction_outcome": "pursue|complete",
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

**Target Depth**: {target_node.depth}

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
                        description=(
                            "This fallback direction is intentionally comprehensive because synthesis output "
                            "could not be parsed. The next cycle should restate the target direction and "
                            "establish the precise decision objective it informs, then enumerate the key "
                            "unknowns that currently block confident judgment. Research should map the "
                            "assumptions behind the current direction, identify which assumptions are most "
                            "fragile, and prioritize evidence collection that can falsify or confirm those "
                            "assumptions quickly. Include both supporting and contradicting signals from "
                            "independent sources, with explicit source quality assessment and recency checks. "
                            "Quantify where possible: market sizes, rates of change, comparative benchmarks, "
                            "and confidence intervals or uncertainty bounds when data quality is limited. "
                            "If contradictory claims appear, isolate the disagreement drivers such as scope "
                            "differences, stale data, or methodological inconsistencies, and propose targeted "
                            "queries to resolve each contradiction. The output should also define practical next "
                            "steps: what to test in the next cycle, what can be deprioritized, and which "
                            "conditions would justify re-scoring confidence or importance for this direction."
                        ),
                        confidence=0.5,
                        importance=0.7,
                        reasoning="Fallback direction (synthesis parse failed)",
                        evidence_summary="Research agents completed investigation but synthesis failed to parse",
                        stance="mixed",
                        direction_outcome="pursue",
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
                description = str(dir_data["description"]).strip()
                if not description:
                    raise ValueError("Direction description must be non-empty")
                stance = str(dir_data.get("stance", "mixed")).strip().lower()
                if stance not in {"support", "mixed", "disconfirm"}:
                    stance = "mixed"
                outcome = str(dir_data.get("direction_outcome", "pursue")).strip().lower()
                if outcome not in {"pursue", "complete"}:
                    outcome = "pursue"
                if "direction_outcome" not in dir_data and stance == "disconfirm":
                    # Bias toward faithful closure when model explicitly disconfirms a claim.
                    outcome = "complete"
                directions.append(Direction(
                    claim=dir_data["claim"],
                    description=description,
                    stance=stance,
                    direction_outcome=outcome,
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
                        description=(
                            "This fallback direction is intentionally comprehensive because synthesis output "
                            "failed schema validation. The next cycle should restate the target direction and "
                            "define the operational question to be answered, including how the answer will alter "
                            "decisions in the project roadmap. Build a structured evidence plan with independent "
                            "sources across primary data, reputable secondary analysis, and recent market signals. "
                            "Explicitly track assumptions, then test the highest-impact assumptions first using "
                            "queries designed to disconfirm weak narratives rather than reinforce prior beliefs. "
                            "Require quantitative support where possible, including ranges and source dates, and "
                            "separate descriptive facts from strategic implications so downstream synthesis can "
                            "evaluate confidence correctly. When evidence conflicts, categorize each conflict by "
                            "scope, geography, cohort, or timeframe, and specify follow-up checks needed to close "
                            "those gaps. The cycle output should finish with concrete next actions: what branch "
                            "to deepen, what branch to challenge, and what threshold of corroboration is required "
                            "before upgrading confidence or importance for this direction."
                        ),
                        confidence=0.5,
                        importance=0.7,
                        reasoning=f"Fallback direction (synthesis parse error: {e})",
                        evidence_summary="Research agents completed investigation but synthesis failed to parse",
                        stance="mixed",
                        direction_outcome="pursue",
                    )
                ],
                synthesis_reasoning=f"Synthesis parse error: {e}",
                consensus_directions=[],
                contradictions=[],
            )

    async def reassess_target_direction(
        self,
        target_node: KnowledgeNode,
        agent_outputs: list[AgentOutput],
        synthesis: DirectionSynthesis,
    ) -> TargetReassessment:
        """
        Reassess target direction confidence/importance after new research.

        This is a pure LLM judgment step. No heuristic blending is applied.
        """
        logger.info(f"Lead LLM reassessing target direction {target_node.id[:8]}...")

        # Keep prompt compact but informative.
        agent_summaries: list[str] = []
        for i, output in enumerate(agent_outputs, 1):
            raw_excerpt = output.raw_text[:1400]
            critique_excerpt = output.self_critique[:400] if output.self_critique else ""
            agent_summaries.append(
                f"## Agent {i}: {output.agent_name}\n"
                f"- Searches: {len(output.searches_performed)}\n"
                f"- Cost: ${output.cost_usd:.4f}\n"
                f"- Raw excerpt:\n{raw_excerpt}\n\n"
                f"- Self-critique:\n{critique_excerpt}\n"
            )

        directions_preview = "\n".join(
            [
                f"- {d.claim} (conf={d.confidence:.2f}, imp={d.importance:.2f})"
                for d in synthesis.directions[:12]
            ]
        )
        consensus_preview = "\n".join(f"- {c}" for c in synthesis.consensus_directions[:10]) or "- none"
        contradiction_preview = "\n".join(f"- {c}" for c in synthesis.contradictions[:10]) or "- none"

        system_prompt = f"""You are the Lead LLM for this research mission:

{self.north_star}

You must reassess ONE target direction after a completed research cycle.

Rules:
- Use only the provided cycle evidence and synthesis.
- Provide direct judgment (no averaging formula, no blending instructions).
- Keep scores in [0.0, 1.0].
- Confidence reflects how strongly the direction is now validated.
- Importance reflects strategic relevance to the mission now.
- Choose exactly ONE strategic action for this target:
  - diverge: keep this direction active and branch into additional related directions
  - deepen: keep this direction active and continue focused investigation on this same path
  - close: this path is a dead end or sufficiently concluded for now; mark as completed
- Decide lifecycle status:
  - active: continue investing (for `diverge` or `deepen`)
  - completed: sufficiently answered / dead end for now (for `close`)
  - closed: not viable / low strategic value now

Return ONLY JSON:
{{
  "action": "diverge|deepen|close",
  "confidence": 0.0,
  "importance": 0.0,
  "status": "active|completed|closed",
  "reasoning": "2-4 sentences justifying the chosen action and updated scores."
}}"""

        agent_evidence_summary = "\n\n".join(agent_summaries)

        user_prompt = f"""## Target Direction
- ID: {target_node.id}
- Claim: {target_node.claim}
- Previous confidence: {target_node.confidence:.2f}
- Previous importance: {target_node.importance:.2f}

## Synthesized Directions From This Cycle
{directions_preview if directions_preview else "- none"}

## Consensus
{consensus_preview}

## Contradictions
{contradiction_preview}

## Agent Evidence Summary
{agent_evidence_summary}

Reassess the target direction and return ONLY the JSON schema.
You must choose one action: diverge, deepen, or close."""

        output = await self.adapter.run(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            tools=[],
            max_iterations=1,
        )

        import json
        import re

        raw_text = output.raw_text.strip()
        json_match = re.search(r"\{.*\"confidence\".*\"importance\".*\}", raw_text, re.DOTALL)

        if not json_match:
            logger.warning("Target reassessment response not valid JSON; keeping existing scores")
            return TargetReassessment(
                confidence=target_node.confidence,
                importance=target_node.importance,
                status=target_node.status,
                reasoning="Reassessment parse failed; retained previous scores.",
                cost_usd=output.cost_usd,
            )

        try:
            data = json.loads(json_match.group())
            action = str(data.get("action", "")).strip().lower()
            confidence = float(data["confidence"])
            importance = float(data["importance"])
            status = str(data.get("status", target_node.status)).strip().lower()
            reasoning = str(data.get("reasoning", "")).strip()

            # Hard bounds for data integrity only (not heuristic scoring logic).
            confidence = max(0.0, min(1.0, confidence))
            importance = max(0.0, min(1.0, importance))
            if action == "close":
                # Explicit policy: dead-end/closed action maps to completed lifecycle state.
                status = "completed"
            if status not in {"active", "completed", "closed"}:
                status = target_node.status

            return TargetReassessment(
                confidence=confidence,
                importance=importance,
                status=status,
                reasoning=reasoning,
                cost_usd=output.cost_usd,
            )
        except (json.JSONDecodeError, KeyError, ValueError) as e:
            logger.warning(f"Failed to parse target reassessment JSON: {e}")
            return TargetReassessment(
                confidence=target_node.confidence,
                importance=target_node.importance,
                status=target_node.status,
                reasoning=f"Reassessment parse error: {e}; retained previous scores.",
                cost_usd=output.cost_usd,
            )
