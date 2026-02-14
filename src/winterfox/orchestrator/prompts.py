"""
Prompt generation for research agents.

Creates effective research prompts by combining:
- Project north star / mission
- Current graph context (focused view)
- Research goals for target node
"""

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..graph.models import KnowledgeNode
    from ..graph.store import KnowledgeGraph

logger = logging.getLogger(__name__)


def _build_strategy_section(
    strategy: str | None,
    selection_reasoning: str | None,
) -> str:
    """Build the strategy-specific 'What We Need' section."""
    if strategy == "EXPLORE":
        reasoning_line = f"\n**Strategist reasoning**: {selection_reasoning}\n" if selection_reasoning else ""
        return f"""## What We Need — EXPLORE (New Hypotheses)
{reasoning_line}
1. **Propose new hypotheses**: What are the possible answers or strategies? Use `finding_type="hypothesis"` for each
2. **Identify blind spots**: What hasn't been considered yet?
3. **Breadth over depth**: Survey the landscape of possibilities
4. **Support initial hypotheses**: For each hypothesis, find at least one piece of evidence"""

    if strategy == "CHALLENGE":
        reasoning_line = f"\n**Strategist reasoning**: {selection_reasoning}\n" if selection_reasoning else ""
        return f"""## What We Need — CHALLENGE (Counter-Evidence)
{reasoning_line}
1. **Find counter-evidence**: Look for data that contradicts the current claim. Use `finding_type="opposing"`
2. **Devil's advocate**: What are the strongest arguments against this?
3. **Stress-test assumptions**: Which assumptions are weakest?
4. **Alternative explanations**: Could the same data support a different conclusion?"""

    if strategy == "DEEPEN":
        reasoning_line = f"\n**Strategist reasoning**: {selection_reasoning}\n" if selection_reasoning else ""
        return f"""## What We Need — DEEPEN (More Evidence)
{reasoning_line}
1. **Verify the claim**: Is the current statement accurate? Find specific evidence. Use `finding_type="supporting"` or `"opposing"`
2. **Add specificity**: Find concrete numbers, dates, examples, quotes
3. **Strengthen or weaken**: Does the evidence support or contradict? Be honest
4. **Find primary sources**: Prefer official reports, filings, peer-reviewed research"""

    # Default (no strategy or unknown) — existing behavior
    return """## What We Need

1. **Verify the claim**: Is the current statement accurate? Find specific evidence
2. **Add specificity**: Find concrete numbers, dates, examples, quotes
3. **Identify sub-topics**: What aspects of this claim need deeper investigation?
4. **Find contradictions**: Look for alternative viewpoints or conflicting data"""


async def generate_research_prompt(
    graph: "KnowledgeGraph",
    target_node: "KnowledgeNode",
    north_star: str,
    max_searches: int = 25,
    search_instructions: str | None = None,
    context_files: list[dict[str, str]] | None = None,
    research_context: str | None = None,
    strategy: str | None = None,
    selection_reasoning: str | None = None,
) -> tuple[str, str]:
    """
    Generate system and user prompts for researching a target node.

    Args:
        graph: Knowledge graph
        target_node: Node to research
        north_star: Project mission/north star
        max_searches: Maximum web searches allowed
        search_instructions: Optional custom search guidance
        context_files: Optional prior research documents
        research_context: Pre-rendered accumulated knowledge from prior cycles
        strategy: Research strategy (EXPLORE, DEEPEN, CHALLENGE) from LLM selection
        selection_reasoning: Why this strategy was chosen

    Returns:
        (system_prompt, user_prompt) tuple
    """
    from ..graph.views import render_focused_view

    # Generate focused view of target and context
    focused_view = await render_focused_view(graph, target_node.id, max_depth=3)

    # Build search instructions section
    search_guidance = ""
    if search_instructions:
        search_guidance = f"""
## Custom Search Instructions

{search_instructions}

"""

    # System prompt (role and capabilities)
    system_prompt = f"""You are an expert research agent working on the following mission:

{north_star}

Your role is to conduct thorough, evidence-based research to build a knowledge graph.
You have access to web search and content fetching tools. Use them extensively to gather
high-quality, verifiable information.
{search_guidance}
## Guidelines

1. **Evidence-Based**: Every claim needs strong evidence from credible sources
2. **Specific**: Prefer concrete numbers, quotes, and examples over vague statements
3. **Skeptical**: Challenge assumptions, look for contradicting views
4. **Structured**: Use note_finding tool to record each discrete finding
5. **Efficient**: You have a budget of {max_searches} web searches - use them wisely
6. **Build on prior work**: Review the accumulated research context. Do NOT repeat searches already performed. Focus on gaps, contradictions, and new angles

## Finding Format

When you discover information, use the note_finding tool with:
- **claim**: 2-3 sentence factual statement
- **confidence**: 0.0-1.0 based on evidence quality
  - 0.9-1.0: Multiple authoritative sources, recent data
  - 0.7-0.8: Single authoritative source or multiple secondary sources
  - 0.5-0.6: Secondary sources, older data
  - 0.3-0.4: Weak sources, speculation
  - 0.0-0.2: Hearsay, unverified claims
- **evidence**: List of sources with specific quotes/data points
- **finding_type** (optional): Categorize your finding:
  - `"hypothesis"`: A proposed answer, strategy, or approach
  - `"supporting"`: Evidence that supports the parent claim/hypothesis
  - `"opposing"`: Evidence that contradicts or challenges the parent claim

## Source Quality Hierarchy

1. **Tier 1** (0.9+ confidence): Official reports, peer-reviewed research, regulatory filings
2. **Tier 2** (0.7-0.8): Reputable news outlets, industry analysis, verified data
3. **Tier 3** (0.5-0.6): Blog posts, secondary analysis, older sources
4. **Tier 4** (<0.5): Social media, forums, unverified claims

Your research will be merged with findings from other agents, so focus on verifiable facts."""

    # Build context section
    context_section = ""
    if context_files:
        context_section = "\n## Prior Research & Context Documents\n\n"
        context_section += "You have access to prior research. Use this to avoid redundant work and build on existing knowledge:\n\n"

        for doc in context_files:
            # Truncate very long documents
            content = doc["content"]
            if len(content) > 2000:
                content = content[:2000] + "\n\n[Document truncated for brevity...]"

            context_section += f"### {doc['filename']}\n\n{content}\n\n"

    # Build accumulated research context section
    accumulated_context = ""
    if research_context:
        accumulated_context = f"\n{research_context}\n\n"

    # User prompt (specific research task)
    user_prompt = f"""## Current Knowledge State

{focused_view}
{context_section}{accumulated_context}## Research Objective

Focus on: **{target_node.claim}**

Current confidence: {target_node.confidence:.2f}
Current depth: {target_node.depth} research cycles

{_build_strategy_section(strategy, selection_reasoning)}

## Success Criteria

- Bring confidence above 0.8 with multiple high-quality sources
- Identify 2-5 sub-topics for further research
- Find specific, verifiable data points
- Challenge assumptions with evidence

Begin your research. Use web_search to find sources, then web_fetch to read full content.
Record each discrete finding using note_finding as you discover it."""

    logger.debug(
        f"Generated prompts for node {target_node.id[:8]}... "
        f"(system: {len(system_prompt)} chars, user: {len(user_prompt)} chars)"
    )

    return system_prompt, user_prompt


async def generate_initial_research_prompt(
    north_star: str,
    initial_question: str,
    max_searches: int = 25,
) -> tuple[str, str]:
    """
    Generate prompts for initial research (when graph is empty).

    Args:
        north_star: Project mission
        initial_question: Starting research question
        max_searches: Maximum searches allowed

    Returns:
        (system_prompt, user_prompt) tuple
    """
    system_prompt = f"""You are an expert research agent starting a new research project:

{north_star}

Your goal is to build a knowledge graph by conducting systematic research. Start by
exploring the initial question, then identify key sub-topics for deeper investigation.

## Guidelines

1. **Breadth First**: Identify major topic areas before going deep
2. **Structure**: Organize findings hierarchically (main topics → sub-topics → details)
3. **Evidence**: Always cite credible sources
4. **Actionable**: Each finding should suggest follow-up research areas

You have {max_searches} web searches available. Use them to get a comprehensive overview."""

    user_prompt = f"""## Initial Research Question

{initial_question}

## Your Task

1. Research this question comprehensively
2. Identify 5-10 major sub-topics that need investigation
3. For each finding, note:
   - The main claim
   - Supporting evidence
   - Suggested areas for deeper research
4. Prioritize findings by importance (0.0-1.0)

Begin your research using web_search and web_fetch. Record each finding using note_finding."""

    return system_prompt, user_prompt


def generate_critique_prompt(findings_summary: str) -> str:
    """
    Generate prompt for self-critique of research results.

    Args:
        findings_summary: Summary of findings

    Returns:
        Critique prompt
    """
    return f"""Review your research findings:

{findings_summary}

Provide a brief self-critique:
1. What did you do well?
2. What could be improved?
3. What are the key gaps in your research?
4. What follow-up questions emerged?

Keep your critique to 2-3 sentences."""
