# Getting Started with Winterfox

This guide will walk you through your first autonomous research project with winterfox in **15 minutes**.

## Prerequisites

- **Python 3.12+** installed
- **API Keys** (at least one):
  - [Anthropic API key](https://console.anthropic.com/) for Claude Opus 4.6
  - [Moonshot API key](https://platform.moonshot.cn/) for Kimi 2.5 (optional)
  - [Tavily API key](https://tavily.com/) for web search

## Installation

### Using UV (Recommended)

```bash
# Install winterfox
uv pip install winterfox

# Verify installation
winterfox --version
```

### Using pip

```bash
# Install winterfox
pip install winterfox

# Verify installation
winterfox --version
```

## Your First Research Project

Let's research the **legal tech SaaS market** as an example.

### Step 1: Set Up API Keys

Export your API keys as environment variables:

```bash
# Required: Anthropic API key for Claude
export ANTHROPIC_API_KEY="sk-ant-..."

# Optional: Additional agents for consensus
export MOONSHOT_API_KEY="sk-..."

# Required: Search API
export TAVILY_API_KEY="tvly-..."
```

**Pro Tip**: Add these to your `~/.bashrc` or `~/.zshrc` to persist across sessions:

```bash
# Add to ~/.zshrc
echo 'export ANTHROPIC_API_KEY="sk-ant-..."' >> ~/.zshrc
echo 'export TAVILY_API_KEY="tvly-..."' >> ~/.zshrc
source ~/.zshrc
```

### Step 2: Initialize Your Project

```bash
# Create project directory
mkdir legal-tech-research
cd legal-tech-research

# Initialize winterfox project
winterfox init "Legal Tech SaaS Market Research" \
  --north-star "Research the market opportunity for legal tech SaaS targeting mid-market general counsels (100-1000 employee companies)"
```

This creates:
- `research.toml` - Configuration file
- `research.db` - SQLite knowledge graph
- `research/raw/` - Raw agent outputs

### Step 3: Review Configuration

Open `research.toml` in your editor:

```toml
[project]
name = "Legal Tech SaaS Market Research"
north_star = """
Research the market opportunity for legal tech SaaS targeting mid-market
general counsels (100-1000 employee companies)
"""

# Primary research agent: Claude Opus 4.6
[[agents]]
provider = "anthropic"
model = "claude-opus-4-20251120"
api_key_env = "ANTHROPIC_API_KEY"
supports_native_search = true

# Optional: Add Kimi 2.5 for multi-agent consensus
# [[agents]]
# provider = "moonshot"
# model = "kimi-2.5"
# api_key_env = "MOONSHOT_API_KEY"

[search]
use_llm_native_search = true
fallback_enabled = true

[[search.providers]]
name = "tavily"
api_key_env = "TAVILY_API_KEY"
priority = 1
enabled = true

[orchestrator]
max_searches_per_agent = 25
confidence_discount = 0.7
consensus_boost = 0.15
similarity_threshold = 0.75

[storage]
db_path = "research.db"
git_auto_commit = false  # Set to true if using git
```

**Configuration Tips**:
- Leave defaults for your first project
- Enable `git_auto_commit` if your directory is a git repo
- Add more agents for multi-agent consensus (increases cost but improves quality)

### Step 4: Run Your First Research Cycle

```bash
# Run 1 research cycle
winterfox cycle

# Watch the output:
# ✓ Selecting target node...
# ✓ Generating research prompt...
# ✓ Dispatching to 1 agent(s)...
# ✓ Merging findings...
# ✓ Cycle 1: 7 created, 0 updated | $0.1234 | 45.2s
```

**What happened**:
1. Winterfox selected a research target (initially the main question)
2. Generated a focused research prompt
3. Sent it to Claude with search tools
4. Claude searched the web, analyzed results
5. Findings were merged into knowledge graph
6. Confidence scores were calculated

### Step 5: Check Progress

```bash
winterfox status
```

You'll see output like:

```
┌─────────────────────────────────────────────────────┐
│ Legal Tech SaaS Market Research                     │
│                                                     │
│ Total nodes: 8                                      │
│ Average confidence: 0.62                            │
│ Low confidence: 3                                   │
└─────────────────────────────────────────────────────┘

[Market Opportunity] (conf: 0.58, depth: 2) ⚠️
├─ [Legal Tech TAM] (conf: 0.75, depth: 1) ✓
│  └─ [Market Size $50B by 2025] (conf: 0.82, depth: 0) ✓
├─ [Mid-Market Segment] (conf: 0.45, depth: 1) 🔴
└─ [Competition Landscape] (conf: 0.63, depth: 1) •
   ├─ [Harvey AI] (conf: 0.71, depth: 0) ✓
   └─ [Thomson Reuters] (conf: 0.68, depth: 0) ✓
```

**Indicators**:
- ✓ High confidence (>0.7)
- • Medium confidence (0.5-0.7)
- ⚠️ Low confidence (0.3-0.5)
- 🔴 Very low confidence (<0.3)

### Step 6: Run More Cycles

Let's run 10 more cycles to deepen the research:

```bash
# Run 10 cycles
winterfox cycle -n 10

# This will take ~5-10 minutes depending on:
# - How many searches Claude performs per cycle
# - API response times
# - Complexity of findings
```

**Understanding Cost**:
- Claude Opus 4.6: ~$0.05-0.15 per cycle
- Tavily search: ~$0.001 per search (~25 searches/cycle = $0.025)
- **Total**: ~$0.10 per cycle → **~$1.00 for 10 cycles**

**Cost-Saving Tips**:
- Use Kimi 2.5 (100x cheaper than Claude, but bilingual CN/EN)
- Reduce `max_searches_per_agent` in config
- Run fewer cycles initially

### Step 7: View Detailed Node Information

```bash
# List all nodes to find ID
winterfox status --depth 10

# View specific node (copy ID from status output)
winterfox show abc123
```

Output:

```
Node: abc123
Claim: Market Size $50B by 2025
Confidence: 0.82
Depth: 0
Importance: 0.9
Created: Cycle 1
Updated: Cycle 3

Evidence (3 sources):
────────────────────────────────────────
1. Legal tech market expected to reach $50.4B by 2025
   Source: Grand View Research, 2024
   Date: 2024-11-15

2. CAGR of 15.2% from 2023-2025
   Source: MarketWatch Legal Tech Report
   Date: 2024-10-22

3. Mid-market segment growing fastest at 18% CAGR
   Source: Gartner Legal Technology Survey
   Date: 2024-09-30

Children: 0
Parent: Legal Tech TAM (def456)
```

### Step 8: Export Your Research

Export to markdown for humans:

```bash
winterfox export report.md
```

Creates a beautifully formatted markdown file:

```markdown
# Legal Tech SaaS Market Research

**Generated**: 2026-02-13 13:45:23
**Total Nodes**: 23
**Average Confidence**: 0.74

## Research Findings

### Market Opportunity (conf: 0.78, depth: 5) ✓

The legal tech SaaS market presents a significant opportunity...

#### Evidence
- Legal tech market expected to reach $50.4B by 2025
  *Source: Grand View Research, 2024-11-15*

#### Legal Tech TAM (conf: 0.88, depth: 3) ✓
...
```

Export to JSON for programmatic access:

```bash
winterfox export data.json --format json
```

### Step 9: Interactive Mode (User Steering)

For more control, use interactive mode:

```bash
winterfox interactive
```

This runs one cycle at a time and asks:

```
✓ Cycle 1: 7 created, 3 updated | $0.0987 | 38.1s

Continue researching? [Y/n/focus/stop]
>
```

Options:
- **Y** or Enter: Run another cycle
- **n**: Stop after this cycle
- **focus <topic>**: Research a specific area (e.g., "focus competition")
- **stop**: Stop immediately

## Understanding the Research Process

### How Winterfox Works

```
┌─────────────────────────────────────────────┐
│             Research Cycle                   │
└─────────────────────────────────────────────┘

1. Select Target Node
   ↓ (UCB1: uncertainty + importance + staleness)

2. Generate Research Prompt
   ↓ (North star + focused graph view)

3. Dispatch to Agent(s)
   ↓ (Parallel execution with tools)

4. Merge Findings
   ↓ (Deduplication via Jaccard similarity)

5. Propagate Confidence
   ↓ (Independent confirmation model)

6. Deduplicate Subtree
   ↓ (Merge redundant siblings)

→ Repeat
```

### Node Selection Algorithm (UCB1-Inspired)

Winterfox picks the next node to research by balancing:

1. **Uncertainty** (50%): Low confidence = high priority
2. **Importance** (30%): Strategic value to the research
3. **Staleness** (20%): How long since last update

Formula:
```
score = (1 - confidence) * 0.5
      + importance * 0.3
      + log(1 + hours/24) * 0.2
```

### Confidence Model

**Independent Confirmation**:
When multiple agents agree (or multiple pieces of evidence support):

```
conf_combined = 1 - (1 - conf1) * (1 - conf2)
```

Example: Agent 1 says 0.7, Agent 2 says 0.75:
```
= 1 - (1 - 0.7) * (1 - 0.75)
= 1 - 0.3 * 0.25
= 1 - 0.075
= 0.925 ✓
```

**Confidence Discount**:
New findings start with discounted confidence (default: 0.7x):
- Agent reports 0.8 → Stored as 0.8 * 0.7 = 0.56
- Requires more evidence to reach high confidence
- Prevents over-confidence from single sources

## Advanced Usage

### Multi-Agent Consensus

Add multiple agents to your `research.toml`:

```toml
# Primary agent: Claude Opus 4.6
[[agents]]
provider = "anthropic"
model = "claude-opus-4-20251120"
api_key_env = "ANTHROPIC_API_KEY"

# Secondary agent: Kimi 2.5 (cost-effective)
[[agents]]
provider = "moonshot"
model = "kimi-2.5"
api_key_env = "MOONSHOT_API_KEY"
```

Run with consensus:

```bash
winterfox cycle -n 5

# Winterfox will:
# 1. Dispatch to both agents in parallel
# 2. Compare their findings
# 3. Boost confidence by +0.15 when they agree
# 4. Report consensus vs divergent findings
```

### Focused Research

Research a specific area:

```bash
# Research competition specifically
winterfox cycle --focus "competition landscape"

# This finds nodes matching "competition" and prioritizes them
```

### Running Until Confidence Target

```bash
# Run until average confidence reaches 0.8 (max 50 cycles)
winterfox cycle --until 0.8 --max 50
```

### Programmatic Usage

Use winterfox as a Python library:

```python
import asyncio
from winterfox import KnowledgeGraph, Orchestrator, AgentPool
from winterfox.agents.adapters import AnthropicAdapter
from winterfox.agents.tools import get_research_tools

async def main():
    # Initialize graph
    graph = KnowledgeGraph("research.db")
    await graph.initialize()

    # Add starting question
    await graph.add_node(
        claim="What is the legal tech SaaS opportunity?",
        confidence=0.0,
        importance=1.0,
        created_by_cycle=0,
    )

    # Create agent
    agent = AnthropicAdapter(
        model="claude-opus-4-20251120",
        api_key="sk-ant-...",
    )

    pool = AgentPool([agent])
    tools = get_research_tools(graph)

    # Create orchestrator
    orch = Orchestrator(
        graph=graph,
        agent_pool=pool,
        north_star="Build legal tech SaaS for mid-market",
        tools=tools,
    )

    # Run 10 cycles
    results = await orch.run_cycles(n=10)

    print(f"Completed {len(results)} cycles")
    print(f"Total cost: ${orch.total_cost_usd:.2f}")

    await graph.close()

asyncio.run(main())
```

## Troubleshooting

### "No API key found"

**Error**: `ValueError: ANTHROPIC_API_KEY not found`

**Solution**:
```bash
# Check if set
echo $ANTHROPIC_API_KEY

# Set temporarily
export ANTHROPIC_API_KEY="sk-ant-..."

# Set permanently
echo 'export ANTHROPIC_API_KEY="sk-ant-..."' >> ~/.zshrc
source ~/.zshrc
```

### "Rate limit exceeded"

**Error**: `RateLimitError: 429 Too Many Requests`

**Solution**:
- Wait a few minutes
- Reduce cycles: `winterfox cycle -n 1` instead of `-n 10`
- Use multiple search providers for redundancy

### "Search failed"

**Error**: `SearchError: All search providers failed`

**Solution**:
1. Check Tavily API key: `echo $TAVILY_API_KEY`
2. Add fallback provider in `research.toml`:
   ```toml
   [[search.providers]]
   name = "brave"
   api_key_env = "BRAVE_API_KEY"
   priority = 2
   ```

### High costs

**Problem**: Spending too much on API calls

**Solution**:
1. Use Kimi 2.5 instead of Claude (100x cheaper)
2. Reduce searches: `max_searches_per_agent = 10`
3. Run fewer cycles initially
4. Check cost tracking: `winterfox status` shows total spend

## Next Steps

### Learn More

- Read the [Architecture Overview](../README.md#architecture)
- Explore [Configuration Reference](./CONFIGURATION.md)
- See [Example Projects](../examples/)

### Try Different Research Topics

- **Market Research**: "Analyze the SaaS market for X industry"
- **Technical Investigation**: "How does Y technology work under the hood?"
- **Competitive Analysis**: "Who are the competitors in Z space?"
- **Literature Review**: "What does recent research say about ABC?"

### Share Your Results

Built something cool with winterfox? Share it!

- GitHub Discussions: https://github.com/siinnche/winterfox/discussions
- Twitter/X: Tag @winterfox_ai
- Blog post with exported markdown

## Resources

- **Documentation**: https://github.com/siinnche/winterfox
- **Issues**: https://github.com/siinnche/winterfox/issues
- **Examples**: https://github.com/siinnche/winterfox/tree/main/examples

---

**Happy researching!** 🦊🔍
