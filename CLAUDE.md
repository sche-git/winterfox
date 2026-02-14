# Winterfox Research Cycles: Comprehensive Architecture Guide

## Table of Contents
1. [Lead LLM Architecture (v0.2.0)](#lead-llm-architecture-v020) ⭐ **NEW**
2. [System Overview](#system-overview)
3. [Research Cycles Explained](#research-cycles-explained)
4. [Architecture & Components](#architecture--components)
5. [Complete Cycle Flow](#complete-cycle-flow)
6. [Data Processing & Storage](#data-processing--storage)
7. [Multi-Agent Synthesis](#multi-agent-synthesis)
8. [Integration Points](#integration-points)
9. [API Reference](#api-reference)
10. [Key Design Patterns](#key-design-patterns)
11. [CLI Commands](#cli-commands)

---

## Lead LLM Architecture (v0.2.0)

> **MAJOR UPDATE (February 2025)**: Winterfox has been redesigned to use **Lead LLM architecture** where a single elite LLM orchestrates the entire research cycle with maximum autonomy.

### What Changed?

#### 🎯 Lead LLM Ownership
A single strategic LLM (the "Lead") now owns the entire cycle:
- **Selection**: Lead LLM analyzes graph state and strategically selects which direction to pursue (replaces hardcoded UCB1 formulas)
- **Dispatch**: Lead LLM generates prompts and dispatches research agents in parallel
- **Synthesis**: Lead LLM extracts strategic directions from raw research outputs

#### 📊 Direction-Only Knowledge Graph
Simplified from 4 node types to 1:
- **OLD**: `question` → `hypothesis` → `supporting`/`opposing` evidence
- **NEW**: Everything is a `direction` - strategic paths to explore
- **Why**: Eliminates artificial structure, preserves full LLM reasoning

#### 📝 Raw Output Preservation
- **Removed**: `note_finding` tool and structured `Finding` objects
- **Now**: Research agents produce raw text output (primary data)
- **Lead LLM**: Extracts directions during synthesis phase
- **Why**: Preserves full LLM context and reasoning, no forced structure

#### 💰 Separate Cost Tracking
- **Lead LLM costs**: Selection + synthesis (strategic intelligence)
- **Research costs**: Parallel agent investigation
- **Database**: New columns `lead_llm_cost_usd` and `research_agents_cost_usd`

#### ⚙️ Configuration Changes
New TOML structure with separate Lead configuration:

```toml
[lead_agent]  # NEW: Strategic orchestrator
provider = "anthropic"
model = "claude-opus-4-20251120"

[[agents]]  # Research agents (can overlap with Lead)
provider = "anthropic"
model = "claude-opus-4-20251120"

[[agents]]
provider = "moonshot"
model = "kimi-2.5"
```

### Migration

Existing databases are automatically migrated:
- All node types → `direction`
- Cost columns added with 50/50 backfill
- Report metadata table created
- **Idempotent**: Safe to run multiple times

### Key Benefits

1. **Maximum LLM Autonomy**: No hardcoded formulas, pure strategic reasoning
2. **Simplified Model**: One node type, easier to understand
3. **Better Context**: Raw outputs preserve full reasoning
4. **Cost Visibility**: Separate tracking for strategic vs research work
5. **Flexible Configuration**: Lead can be same or different model as research agents

---

## System Overview

**Winterfox** is an autonomous research system that builds knowledge graphs through iterative research cycles. It's important to note: **This system uses "research cycles," not "research sessions"**.

### Core Concept

```
Research Cycle = One complete iteration of autonomous research on a specific node
```

Each cycle:
- Selects a target node intelligently
- Researches using one or more LLM agents
- Synthesizes findings with multi-agent consensus
- Merges results with confidence compounding
- Persists everything for tracking and replay

### Key Features

- **Autonomous Research**: LLM agents independently research topics with web search
- **Multi-Agent Consensus**: Multiple agents verify findings, with synthesis by primary agent
- **Knowledge Compounding**: Confidence increases when independent agents agree
- **Type-Aware Graph**: Questions → Hypotheses → Supporting/Opposing Evidence
- **Cost Tracking**: Comprehensive token and USD cost tracking per cycle
- **Multi-Tenancy**: Workspace isolation for future SaaS scaling
- **Full Observability**: WebSocket events, audit logs, cycle exports

---

## Research Cycles Explained

### What is a Research Cycle?

A **Research Cycle** is the fundamental unit of work in Winterfox. Each cycle:

1. **Targets** a specific knowledge node (question, hypothesis, or claim)
2. **Researches** using one or more LLM agents with web search
3. **Synthesizes** findings (if multi-agent)
4. **Merges** new knowledge into the graph with deduplication
5. **Compounds** confidence when multiple agents agree
6. **Persists** all outputs for reproducibility

### Cycle Characteristics

- **Unique ID**: Auto-incrementing integer per workspace
- **Autonomous**: Runs without human intervention
- **Context-Aware**: Builds on all previous cycles' knowledge
- **Strategic**: EXPLORE (breadth) / DEEPEN (depth) / CHALLENGE (stress-test)
- **Traceable**: Full audit trail and markdown exports

### Cycle Lifecycle

```
┌────────────────────────────────────────────────────────────────┐
│                    RESEARCH CYCLE LIFECYCLE                    │
└────────────────────────────────────────────────────────────────┘

    START
      │
      ↓
  ┌────────────────────┐
  │ Node Selection     │  ← LLM-driven or UCB1 scoring
  │ + Strategy Choice  │    (EXPLORE/DEEPEN/CHALLENGE)
  └────────────────────┘
      │
      ↓
  ┌────────────────────┐
  │ Build Context      │  ← Prior cycles, searches, contradictions
  └────────────────────┘
      │
      ↓
  ┌────────────────────┐
  │ Generate Prompts   │  ← Strategy-specific + accumulated context
  └────────────────────┘
      │
      ↓
  ┌────────────────────────────────────────────────────────────┐
  │              AGENT DISPATCH                                 │
  │                                                              │
  │  Single Agent:          Multi-Agent with Consensus:         │
  │  ┌──────────────┐       ┌──────────┬──────────┬─────────┐  │
  │  │ Agent        │       │ Agent 1  │ Agent 2  │ Agent N │  │
  │  │ Research     │       │ Research │ Research │ Research│  │
  │  └──────────────┘       └──────────┴──────────┴─────────┘  │
  │         │                      │          │          │      │
  │         │                      └──────────┴──────────┘      │
  │         │                               ↓                   │
  │         │                      ┌─────────────────────┐      │
  │         │                      │ Primary Agent       │      │
  │         │                      │ Synthesizes         │      │
  │         │                      │ - Consensus         │      │
  │         │                      │ - Contradictions    │      │
  │         │                      │ - Evidence Quality  │      │
  │         │                      └─────────────────────┘      │
  │         │                               │                   │
  │         └───────────────────────────────┘                   │
  │                               ↓                             │
  └──────────────────────────────────────────────────────────────┘
      │
      ↓
  ┌────────────────────┐
  │ Merge Findings     │  ← Deduplication + Confidence compounding
  │ into Graph         │    Type-aware merging
  └────────────────────┘
      │
      ↓
  ┌────────────────────┐
  │ Deduplicate        │  ← Consolidate redundant siblings
  │ Subtree            │    (Jaccard > 0.85)
  └────────────────────┘
      │
      ↓
  ┌────────────────────┐
  │ Save Cycle Output  │  ← Persist to DB + Export markdown
  │ + Agent Outputs    │
  └────────────────────┘
      │
      ↓
    COMPLETE
```

### Cycle Strategies

1. **EXPLORE** (Breadth)
   - Propose new hypotheses
   - Discover related areas
   - Expand the knowledge graph
   - Use case: Early research, topic mapping

2. **DEEPEN** (Depth)
   - Find more evidence for existing claims
   - Strengthen confidence through independent verification
   - Add detailed supporting information
   - Use case: Validate important hypotheses

3. **CHALLENGE** (Stress-Test)
   - Actively seek counter-evidence
   - Find opposing viewpoints
   - Identify weaknesses in current understanding
   - Use case: Test high-confidence claims

---

## Architecture & Components

### System Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────┐
│                         WINTERFOX ARCHITECTURE                       │
└─────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────┐
│                          USER INTERFACES                             │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────────┐  │
│  │   CLI        │  │  Web Dashboard│  │  WebSocket Events       │  │
│  │   Commands   │  │  (React SPA)  │  │  (Real-time updates)    │  │
│  └──────┬───────┘  └──────┬───────┘  └──────────┬───────────────┘  │
│         │                  │                      │                  │
└─────────┼──────────────────┼──────────────────────┼──────────────────┘
          │                  │                      │
          ↓                  ↓                      ↓
┌─────────────────────────────────────────────────────────────────────┐
│                        ORCHESTRATION LAYER                           │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │              Orchestrator (core.py)                         │   │
│  │  - run_cycle() / run_cycles() / run_until_complete()       │   │
│  │  - Cost tracking, cycle history, progress monitoring        │   │
│  └───────────────────────────┬─────────────────────────────────┘   │
│                              │                                      │
│  ┌───────────────────────────┴─────────────────────────────────┐   │
│  │            ResearchCycle (cycle.py)                         │   │
│  │  - execute(): Main cycle execution logic                    │   │
│  │  - Coordinates all cycle steps                              │   │
│  └───────────┬───────────────────────────────┬─────────────────┘   │
│              │                               │                      │
│  ┌───────────┴──────────┐       ┌───────────┴──────────┐           │
│  │ NodeSelector         │       │ ResearchContext      │           │
│  │ (selection.py)       │       │ Builder              │           │
│  │ - LLM-driven         │       │ (research_context.py)│           │
│  │ - UCB1 fallback      │       │ - Prior cycles       │           │
│  └──────────────────────┘       │ - Search history     │           │
│                                 │ - Contradictions     │           │
│                                 └──────────────────────┘           │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
          │
          ↓
┌─────────────────────────────────────────────────────────────────────┐
│                          AGENT LAYER                                 │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │              AgentPool (pool.py)                            │   │
│  │  - dispatch(): Single agent execution                       │   │
│  │  - dispatch_with_synthesis(): Multi-agent + synthesis       │   │
│  └───────────────────────────┬─────────────────────────────────┘   │
│                              │                                      │
│              ┌───────────────┼───────────────┐                      │
│              ↓               ↓               ↓                      │
│  ┌────────────────┐ ┌────────────────┐ ┌────────────────┐          │
│  │ Claude Opus    │ │   Kimi 2.5     │ │  OpenRouter    │          │
│  │ (anthropic.py) │ │   (kimi.py)    │ │  (openrouter.py│          │
│  │ - Primary      │ │ - Cost-effective│ │  - Gateway     │          │
│  │ - Synthesizer  │ │ - Secondary    │ │                │          │
│  └────────┬───────┘ └────────┬───────┘ └────────┬───────┘          │
│           │                  │                  │                   │
│           └──────────────────┴──────────────────┘                   │
│                              │                                      │
│                   ┌──────────┴──────────┐                           │
│                   ↓                     ↓                           │
│       ┌────────────────────┐  ┌──────────────────┐                 │
│       │  Search Tools      │  │  Graph Tools     │                 │
│       │  - web_search      │  │  - read_node     │                 │
│       │  - web_fetch       │  │  - search_graph  │                 │
│       │  - note_finding    │  │  - context       │                 │
│       └────────────────────┘  └──────────────────┘                 │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
          │
          ↓
┌─────────────────────────────────────────────────────────────────────┐
│                       KNOWLEDGE GRAPH LAYER                          │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │          KnowledgeGraph (graph/store.py)                    │   │
│  │  - Node CRUD operations                                     │   │
│  │  - Full-text search (FTS5)                                  │   │
│  │  - Cycle output persistence                                 │   │
│  │  - Tree traversal & views                                   │   │
│  └───────────────────────────┬─────────────────────────────────┘   │
│                              │                                      │
│  ┌───────────────────────────┴─────────────────────────────────┐   │
│  │              SQLite Database                                │   │
│  │                                                              │   │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────────┐  │   │
│  │  │   nodes      │  │ cycle_outputs│  │ agent_outputs    │  │   │
│  │  │ - Full data  │  │ - Synthesis  │  │ - Per-agent data │  │   │
│  │  │ - JSON       │  │ - Consensus  │  │ - Findings       │  │   │
│  │  └──────────────┘  └──────────────┘  └──────────────────┘  │   │
│  │                                                              │   │
│  │  ┌──────────────┐  ┌──────────────────────────────────────┐│   │
│  │  │  nodes_fts   │  │     graph_operations                 ││   │
│  │  │  (FTS5)      │  │     (audit trail)                    ││   │
│  │  └──────────────┘  └──────────────────────────────────────┘│   │
│  └──────────────────────────────────────────────────────────────┘   │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
          │
          ↓
┌─────────────────────────────────────────────────────────────────────┐
│                      EXTERNAL SERVICES                               │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────────┐  │
│  │ LLM APIs     │  │ Search APIs  │  │  Export Storage          │  │
│  │ - Anthropic  │  │ - Tavily     │  │  - .winterfox/raw/       │  │
│  │ - Moonshot   │  │ - Brave      │  │    {date}/cycle_{id}.md  │  │
│  │ - OpenRouter │  │ - Serper     │  │                          │  │
│  │ - OpenAI     │  │ - DuckDuckGo │  │                          │  │
│  └──────────────┘  └──────────────┘  └──────────────────────────┘  │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
```

### Core Components

#### 1. Knowledge Graph Layer (`/src/winterfox/graph/`)

**Purpose**: Persistent storage and retrieval of knowledge nodes

**Key Files**:
- `models.py`: Data structures (KnowledgeNode, Evidence)
- `store.py`: SQLite persistence (1,318 lines)
- `views.py`: Token-efficient graph views

**Node Types**:
```
? question      - Research question needing investigation
H hypothesis    - Proposed answer/explanation (importance: 0.8)
+ supporting    - Evidence supporting parent claim
- opposing      - Evidence contradicting parent claim
```

**Database Schema**:
```sql
-- Core node storage
nodes (
  id TEXT PRIMARY KEY,
  workspace_id TEXT NOT NULL,
  parent_id TEXT,
  claim TEXT NOT NULL,
  confidence REAL,
  importance REAL,
  depth INTEGER,
  status TEXT,
  node_type TEXT,
  data TEXT,  -- Full JSON of KnowledgeNode
  created_by_cycle INTEGER,
  updated_at TIMESTAMP
)

-- Full-text search
nodes_fts (claim) -- FTS5 virtual table

-- Cycle metadata
cycle_outputs (
  cycle_id INTEGER PRIMARY KEY,
  workspace_id TEXT NOT NULL,
  target_node_id TEXT,
  synthesis_reasoning TEXT,
  consensus_findings TEXT,  -- JSON array
  contradictions TEXT,      -- JSON array
  selection_strategy TEXT,
  selection_reasoning TEXT,
  agent_count INTEGER,
  total_cost_usd REAL,
  duration_seconds REAL,
  created_at TIMESTAMP
)

-- Per-agent normalized data
agent_outputs (
  id INTEGER PRIMARY KEY,
  cycle_output_id INTEGER,
  agent_name TEXT,
  findings TEXT,           -- JSON array
  self_critique TEXT,
  searches_performed TEXT, -- JSON array
  cost_usd REAL,
  tokens_used INTEGER,
  raw_output TEXT
)

-- Audit trail
graph_operations (
  id INTEGER PRIMARY KEY,
  workspace_id TEXT,
  cycle_id INTEGER,
  operation TEXT,  -- create_node, update_node, merge_nodes
  node_id TEXT,
  details TEXT,    -- JSON
  timestamp TIMESTAMP
)
```

**Graph Views**:
- `summary_view`: Token-efficient tree (~500 tokens for 100 nodes)
- `focused_view`: Detailed subtree + path to root for agent context
- `weakest_nodes`: Priority nodes for next research (low confidence, high importance)

#### 2. Agent Adapter Layer (`/src/winterfox/agents/`)

**Purpose**: Unified interface for multiple LLM providers

**Agent Protocol** (`protocol.py`):
```python
class AgentAdapter(Protocol):
    async def research(
        self,
        system_prompt: str,
        user_prompt: str,
        tools: List[ToolDefinition],
        max_iterations: int = 10
    ) -> AgentOutput

class AgentOutput:
    findings: List[Finding]
    self_critique: str
    searches_performed: List[SearchRecord]
    cost_usd: float
    tokens_used: int
    raw_output: str
```

**Implemented Adapters**:
- **Claude Opus 4.6** (`anthropic.py`): Primary agent, synthesis, native search
- **Kimi 2.5** (`kimi.py`): Cost-effective secondary agent
- **OpenRouter** (`openrouter.py`): Gateway to multiple models

**Agent Pool** (`pool.py`):
```python
class AgentPool:
    async def dispatch(
        agent: AgentAdapter,
        prompt: str,
        tools: List[ToolDefinition]
    ) -> AgentOutput

    async def dispatch_with_synthesis(
        agents: List[AgentAdapter],
        prompt: str,
        tools: List[ToolDefinition],
        synthesizer: AgentAdapter
    ) -> SynthesisResult
        # 1. Run all agents in parallel
        # 2. Synthesizer reviews all outputs
        # 3. Returns unified findings + reasoning
```

**Why LLM-Based Synthesis?**
- Semantic understanding beyond keyword matching
- Handles nuance, context, evidence quality
- Explains reasoning in natural language
- Domain-agnostic, no tuning required
- Adapts to any research topic

#### 3. Research Orchestrator (`/src/winterfox/orchestrator/`)

**Purpose**: High-level coordination of research cycles

**Orchestrator** (`core.py`):
```python
class Orchestrator:
    def __init__(self, graph, agent_pool, config)

    async def run_cycle(
        focus_node_id: Optional[str] = None,
        strategy: Optional[str] = None
    ) -> CycleResult

    async def run_cycles(n: int) -> List[CycleResult]

    async def run_until_complete(
        max_cycles: int = 100,
        confidence_threshold: float = 0.8
    ) -> List[CycleResult]
```

**Research Cycle** (`cycle.py`):
```python
class ResearchCycle:
    async def execute(
        target_node_id: Optional[str],
        max_searches: int,
        use_consensus: bool,
        strategy: Optional[str]
    ) -> CycleResult
        # Full cycle execution logic
```

**Node Selection** (`selection.py`):

Two strategies:

1. **LLM-Driven Selection** (intelligent):
   ```python
   # Analyzes graph state, chooses:
   # - EXPLORE: New hypotheses (breadth)
   # - DEEPEN: More evidence (depth)
   # - CHALLENGE: Counter-evidence (stress-test)
   ```

2. **UCB1-Inspired Scoring** (fallback):
   ```python
   score = (
       (1 - confidence) * 0.5 +           # Uncertainty
       importance * 0.3 +                  # Strategic value
       log(1 + staleness_hours/24) * 0.2  # Exploration bonus
   )
   ```

**Research Context Builder** (`research_context.py`):

Accumulates knowledge from all prior cycles:
```python
sections = {
    "graph_summary": 3200 chars,      # Tree structure
    "prior_cycles": 4800 chars,       # Recent cycle summaries
    "search_history": 2400 chars,     # Avoid redundant searches
    "contradictions": 1600 chars,     # Known disagreements
    "weakest_nodes": 1600 chars,      # Low-confidence areas
    "open_questions": 2400 chars      # Unanswered questions
}
# Total: ~16,000 chars (~4,000 tokens)
```

**Prompt Generation** (`prompts.py`):

Combines:
- System prompt: Role, guidelines, tool usage
- User prompt:
  - Current knowledge state (focused view)
  - Research context (accumulated)
  - Research objective (target node)
  - Strategy section (EXPLORE/DEEPEN/CHALLENGE)
  - Success criteria

**Finding Merge** (`merge.py`):

Critical knowledge compounding logic:
```python
def merge_findings_into_graph(findings, target_node_id):
    for finding in findings:
        # 1. Search for similar nodes (Jaccard > 0.75)
        similar = find_similar_nodes(finding, target_node_id)

        if similar:
            # 2. Update existing node
            node.evidence.append(finding.evidence)

            # 3. Independent confirmation boost
            old_conf = node.confidence
            new_conf = finding.confidence * 0.7  # Discount
            node.confidence = 1 - (1 - old_conf) * (1 - new_conf)

            # 4. Merge tags, update claim if more detailed
            node.tags.update(finding.tags)
            if len(finding.claim) > len(node.claim):
                node.claim = finding.claim
        else:
            # 5. Create new node with discounted confidence
            create_node(
                claim=finding.claim,
                confidence=finding.confidence * 0.7,
                importance=importance_by_type[finding.type]
            )

        # 6. Propagate confidence upward
        propagate_confidence(node)
```

**Type-Aware Merging**:
- `opposing` and `supporting` don't merge (different stances)
- Only merges within same type
- Preserves semantic structure

#### 4. Web API & Dashboard (`/src/winterfox/web/`)

**FastAPI Server** (`server.py`):
```python
app = FastAPI()
app.add_middleware(CORSMiddleware)
app.mount("/", StaticFiles(directory="frontend/build"))

# Lifecycle management
@app.on_event("startup")
async def startup():
    await graph_service.initialize()

@app.on_event("shutdown")
async def shutdown():
    await graph_service.close()
```

**WebSocket Manager** (`websocket.py`):
```python
class ConnectionManager:
    async def connect(websocket, workspace_id)
    async def disconnect(websocket)
    async def broadcast(event: Dict, workspace_id)
```

**Event Types**:
```javascript
// Cycle lifecycle
{ type: "cycle.started", cycle_id, target_node_id }
{ type: "cycle.step", step: "prompt_generation" }
{ type: "cycle.completed", cycle_id, result }
{ type: "cycle.failed", cycle_id, error }

// Agent activity
{ type: "agent.started", agent_name }
{ type: "agent.search", agent_name, query }
{ type: "agent.completed", agent_name, findings_count }

// Synthesis
{ type: "synthesis.started", agent_count }
{ type: "synthesis.completed", consensus_count }

// Graph updates
{ type: "node.created", node_id }
{ type: "node.updated", node_id }
```

---

## Complete Cycle Flow

### Detailed Step-by-Step Flow

```
╔══════════════════════════════════════════════════════════════════╗
║                    CYCLE EXECUTION: DETAILED FLOW                ║
╚══════════════════════════════════════════════════════════════════╝

┌────────────────────────────────────────────────────────────────┐
│ STEP 0: Initialization                                         │
│ - Load graph state from SQLite                                 │
│ - Load configuration (agents, strategies, budgets)             │
│ - Initialize event emitter (WebSocket broadcast)               │
│ - Increment cycle_id                                           │
└────────────────────────────────────────────────────────────────┘
                          ↓
┌────────────────────────────────────────────────────────────────┐
│ STEP 1: Node Selection                                         │
│                                                                 │
│ IF LLM selector enabled:                                       │
│   1. Get graph summary view (~500 tokens)                      │
│   2. Get weakest nodes list                                    │
│   3. Prompt LLM to select:                                     │
│      - Which node to research                                  │
│      - Strategy: EXPLORE / DEEPEN / CHALLENGE                  │
│      - Reasoning for choice                                    │
│   4. Parse selection response                                  │
│                                                                 │
│ IF LLM fails or disabled:                                      │
│   1. Calculate UCB1 scores for all nodes:                      │
│      score = uncertainty * 0.5 +                               │
│              importance * 0.3 +                                │
│              staleness_bonus * 0.2                             │
│   2. Select highest scoring node                               │
│   3. Default strategy: DEEPEN                                  │
│                                                                 │
│ IF focus_node_id provided:                                     │
│   - Use specified node directly                                │
│   - Strategy from user or default to DEEPEN                    │
│                                                                 │
│ Output: (target_node_id, strategy, reasoning)                  │
│ Event: cycle.started                                           │
└────────────────────────────────────────────────────────────────┘
                          ↓
┌────────────────────────────────────────────────────────────────┐
│ STEP 2: Build Research Context                                 │
│                                                                 │
│ ResearchContextBuilder accumulates prior knowledge:            │
│                                                                 │
│ 1. Graph Summary (3200 chars):                                 │
│    - Tree structure with ├─└ characters                        │
│    - Truncated claims for overview                             │
│    - Confidence and importance indicators                      │
│                                                                 │
│ 2. Prior Cycle Summaries (4800 chars):                         │
│    - Last 5-10 cycles                                          │
│    - What was researched                                       │
│    - Key findings from each cycle                              │
│    - Costs and duration                                        │
│                                                                 │
│ 3. Search History (2400 chars):                                │
│    - Previous search queries                                   │
│    - Timestamps                                                │
│    - Prevents redundant searches                               │
│                                                                 │
│ 4. Known Contradictions (1600 chars):                          │
│    - Conflicting evidence from prior cycles                    │
│    - Disagreements between agents                              │
│    - Areas needing resolution                                  │
│                                                                 │
│ 5. Weakest Nodes (1600 chars):                                 │
│    - Low-confidence, high-importance nodes                     │
│    - Candidates for future research                            │
│                                                                 │
│ 6. Open Questions (2400 chars):                                │
│    - Unanswered questions from graph                           │
│    - Gaps in knowledge                                         │
│                                                                 │
│ Total budget: ~16,000 chars (~4,000 tokens)                    │
│ Event: cycle.step (context_building)                           │
└────────────────────────────────────────────────────────────────┘
                          ↓
┌────────────────────────────────────────────────────────────────┐
│ STEP 3: Generate Prompts                                       │
│                                                                 │
│ System Prompt:                                                 │
│ ┌────────────────────────────────────────────────────────────┐ │
│ │ You are an expert research agent for Winterfox.           │ │
│ │                                                            │ │
│ │ Your mission: {north_star_mission}                        │ │
│ │                                                            │ │
│ │ Guidelines:                                                │ │
│ │ - Use web_search to find information                      │ │
│ │ - Use web_fetch to read sources                           │ │
│ │ - Use note_finding to record findings                     │ │
│ │ - Cite sources with URLs and dates                        │ │
│ │ - Be skeptical, verify claims                             │ │
│ │ - Note contradictions and uncertainty                     │ │
│ │ - Perform {max_searches} searches                         │ │
│ └────────────────────────────────────────────────────────────┘ │
│                                                                 │
│ User Prompt:                                                    │
│ ┌────────────────────────────────────────────────────────────┐ │
│ │ # Current Knowledge State                                 │ │
│ │ {focused_view_of_target_node}                             │ │
│ │                                                            │ │
│ │ # Research Context                                        │ │
│ │ {accumulated_context_from_prior_cycles}                   │ │
│ │                                                            │ │
│ │ # Research Objective                                      │ │
│ │ Target: {target_node.claim}                               │ │
│ │                                                            │ │
│ │ # Strategy: {EXPLORE/DEEPEN/CHALLENGE}                    │ │
│ │ {strategy_specific_instructions}                          │ │
│ │                                                            │ │
│ │ IF EXPLORE:                                               │ │
│ │   - Propose new hypotheses and sub-questions              │ │
│ │   - Explore related areas                                 │ │
│ │   - Think broadly and creatively                          │ │
│ │                                                            │ │
│ │ IF DEEPEN:                                                │ │
│ │   - Find more evidence supporting/opposing current claim  │ │
│ │   - Get specific details, statistics, examples            │ │
│ │   - Verify with multiple independent sources              │ │
│ │                                                            │ │
│ │ IF CHALLENGE:                                             │ │
│ │   - Actively seek counter-evidence                        │ │
│ │   - Find opposing viewpoints                              │ │
│ │   - Look for weaknesses in current understanding          │ │
│ │   - Be a skeptical critic                                 │ │
│ │                                                            │ │
│ │ # Success Criteria                                        │ │
│ │ - Find {max_searches} distinct pieces of evidence         │ │
│ │ - Cite all sources with URLs                              │ │
│ │ - Note confidence level for each finding                  │ │
│ │ - Identify any contradictions or uncertainties            │ │
│ │                                                            │ │
│ │ {optional_custom_search_instructions}                     │ │
│ │ {optional_context_files}                                  │ │
│ └────────────────────────────────────────────────────────────┘ │
│                                                                 │
│ Event: cycle.step (prompt_generation)                          │
└────────────────────────────────────────────────────────────────┘
                          ↓
┌────────────────────────────────────────────────────────────────┐
│ STEP 4: Dispatch Agents                                        │
│                                                                 │
│ ┌──────────────────────────────────────────────────────────┐   │
│ │                    SINGLE AGENT MODE                     │   │
│ │                                                          │   │
│ │  agent_pool.dispatch(agent, prompts, tools)             │   │
│ │         ↓                                                │   │
│ │  ┌─────────────────────────────────────────────────┐    │   │
│ │  │ Agent Loop (up to max_iterations=10)            │    │   │
│ │  │                                                  │    │   │
│ │  │ 1. Call LLM with tools                          │    │   │
│ │  │    Event: agent.started                         │    │   │
│ │  │                                                  │    │   │
│ │  │ 2. Process tool calls:                          │    │   │
│ │  │    - web_search(query)                          │    │   │
│ │  │      * Try providers: Tavily → Brave → Serper   │    │   │
│ │  │      * Record cost ($0.001 per search)          │    │   │
│ │  │      * Event: agent.search                      │    │   │
│ │  │                                                  │    │   │
│ │  │    - web_fetch(url)                             │    │   │
│ │  │      * Extract content                          │    │   │
│ │  │      * Convert to markdown                      │    │   │
│ │  │                                                  │    │   │
│ │  │    - note_finding(claim, confidence, evidence)  │    │   │
│ │  │      * Queue finding for merge                  │    │   │
│ │  │                                                  │    │   │
│ │  │    - read_graph_node(id)                        │    │   │
│ │  │    - search_graph(query)                        │    │   │
│ │  │                                                  │    │   │
│ │  │ 3. Continue until:                              │    │   │
│ │  │    - Agent says "done"                          │    │   │
│ │  │    - Max iterations reached                     │    │   │
│ │  │    - Budget exhausted                           │    │   │
│ │  │                                                  │    │   │
│ │  │ 4. Extract findings from tool calls             │    │   │
│ │  │    Event: agent.completed                       │    │   │
│ │  └─────────────────────────────────────────────────┘    │   │
│ │         ↓                                                │   │
│ │  Returns: AgentOutput {                                 │   │
│ │    findings: [Finding],                                 │   │
│ │    self_critique: str,                                  │   │
│ │    searches_performed: [SearchRecord],                  │   │
│ │    cost_usd: float,                                     │   │
│ │    tokens_used: int                                     │   │
│ │  }                                                      │   │
│ └──────────────────────────────────────────────────────────┘   │
│                                                                 │
│ ┌──────────────────────────────────────────────────────────┐   │
│ │             MULTI-AGENT MODE WITH CONSENSUS              │   │
│ │                                                          │   │
│ │  agent_pool.dispatch_with_synthesis(                    │   │
│ │      agents=[claude, kimi, ...],                        │   │
│ │      synthesizer=claude                                 │   │
│ │  )                                                      │   │
│ │                                                          │   │
│ │  ┌────────────────────────────────────────────────┐     │   │
│ │  │ Phase 1: Parallel Agent Dispatch               │     │   │
│ │  │                                                 │     │   │
│ │  │  await asyncio.gather(                         │     │   │
│ │  │      agent1.research(prompts, tools),          │     │   │
│ │  │      agent2.research(prompts, tools),          │     │   │
│ │  │      agent3.research(prompts, tools)           │     │   │
│ │  │  )                                              │     │   │
│ │  │                                                 │     │   │
│ │  │  Each agent independently:                     │     │   │
│ │  │  - Searches web                                │     │   │
│ │  │  - Fetches sources                             │     │   │
│ │  │  - Records findings                            │     │   │
│ │  │  - No communication between agents             │     │   │
│ │  │                                                 │     │   │
│ │  │  Events: agent.started, agent.completed × N    │     │   │
│ │  └────────────────────────────────────────────────┘     │   │
│ │         ↓                                                │   │
│ │  ┌────────────────────────────────────────────────┐     │   │
│ │  │ Phase 2: LLM-Based Synthesis                   │     │   │
│ │  │                                                 │     │   │
│ │  │  Event: synthesis.started                      │     │   │
│ │  │                                                 │     │   │
│ │  │  Synthesizer (primary agent) receives:         │     │   │
│ │  │  - All agent outputs                           │     │   │
│ │  │  - All findings from all agents                │     │   │
│ │  │  - All sources and evidence                    │     │   │
│ │  │                                                 │     │   │
│ │  │  Synthesis Prompt:                             │     │   │
│ │  │  ┌──────────────────────────────────────────┐  │     │   │
│ │  │  │ Review all agent findings and:           │  │     │   │
│ │  │  │                                           │  │     │   │
│ │  │  │ 1. Identify consensus findings            │  │     │   │
│ │  │  │    - Multiple agents agree                │  │     │   │
│ │  │  │    - Similar claims from different sources│ │     │   │
│ │  │  │    - High confidence when corroborated    │  │     │   │
│ │  │  │                                           │  │     │   │
│ │  │  │ 2. Identify contradictions                │  │     │   │
│ │  │  │    - Agents disagree                      │  │     │   │
│ │  │  │    - Conflicting evidence                 │  │     │   │
│ │  │  │    - Requires further investigation       │  │     │   │
│ │  │  │                                           │  │     │   │
│ │  │  │ 3. Evaluate evidence quality              │  │     │   │
│ │  │  │    - Source credibility                   │  │     │   │
│ │  │  │    - Recency of information               │  │     │   │
│ │  │  │    - Consistency across sources           │  │     │   │
│ │  │  │                                           │  │     │   │
│ │  │  │ 4. Preserve unique insights               │  │     │   │
│ │  │  │    - Novel findings from single agent     │  │     │   │
│ │  │  │    - If well-supported, include           │  │     │   │
│ │  │  │                                           │  │     │   │
│ │  │  │ 5. Provide reasoning                      │  │     │   │
│ │  │  │    - Explain synthesis decisions          │  │     │   │
│ │  │  │    - Note confidence adjustments          │  │     │   │
│ │  │  └──────────────────────────────────────────┘  │     │   │
│ │  │                                                 │     │   │
│ │  │  Synthesizer LLM call:                         │     │   │
│ │  │  - Single call (not loop)                      │     │   │
│ │  │  - Returns structured synthesis                │     │   │
│ │  │                                                 │     │   │
│ │  │  Event: synthesis.completed                    │     │   │
│ │  └────────────────────────────────────────────────┘     │   │
│ │         ↓                                                │   │
│ │  Returns: SynthesisResult {                             │   │
│ │    unified_findings: [Finding],                         │   │
│ │    synthesis_reasoning: str,                            │   │
│ │    consensus_findings: [str],                           │   │
│ │    contradictions: [str],                               │   │
│ │    agent_outputs: [AgentOutput],                        │   │
│ │    total_cost_usd: float                                │   │
│ │  }                                                      │   │
│ └──────────────────────────────────────────────────────────┘   │
│                                                                 │
│ Event: cycle.step (agent_dispatch)                             │
└────────────────────────────────────────────────────────────────┘
                          ↓
┌────────────────────────────────────────────────────────────────┐
│ STEP 5: Merge Findings into Graph                              │
│                                                                 │
│ merge_findings_into_graph(findings, target_node_id)            │
│                                                                 │
│ For each finding:                                              │
│                                                                 │
│   ┌──────────────────────────────────────────────────────┐    │
│   │ 1. Find Similar Nodes (Type-Aware)                  │    │
│   │                                                       │    │
│   │    Query: All children of target_node_id             │    │
│   │           with same node_type as finding             │    │
│   │                                                       │    │
│   │    For each candidate:                               │    │
│   │      tokens_A = set(finding.claim.lower().split())   │    │
│   │      tokens_B = set(node.claim.lower().split())      │    │
│   │                                                       │    │
│   │      jaccard = |A ∩ B| / |A ∪ B|                     │    │
│   │                                                       │    │
│   │      if jaccard > 0.75:                              │    │
│   │        MATCH FOUND                                   │    │
│   └──────────────────────────────────────────────────────┘    │
│                  ↓                    ↓                        │
│            MATCH FOUND          NO MATCH                       │
│                  ↓                    ↓                        │
│   ┌──────────────────────────────────────────────────────┐    │
│   │ 2a. Update Existing Node                            │    │
│   │                                                       │    │
│   │    old_confidence = node.confidence                  │    │
│   │    new_confidence = finding.confidence * 0.7         │    │
│   │                                                       │    │
│   │    # Independent confirmation formula:               │    │
│   │    # P(A or B) = 1 - P(not A) * P(not B)            │    │
│   │    node.confidence = 1 - (1 - old_confidence) *      │    │
│   │                          (1 - new_confidence)        │    │
│   │                                                       │    │
│   │    # Example:                                         │    │
│   │    # old = 0.7, new = 0.6                            │    │
│   │    # = 1 - (0.3) * (0.4) = 1 - 0.12 = 0.88          │    │
│   │                                                       │    │
│   │    # Add evidence                                     │    │
│   │    node.evidence.extend(finding.evidence)            │    │
│   │                                                       │    │
│   │    # Update claim if new one is more detailed        │    │
│   │    if len(finding.claim) > len(node.claim):         │    │
│   │      node.claim = finding.claim                      │    │
│   │                                                       │    │
│   │    # Merge tags                                       │    │
│   │    node.tags.update(finding.tags)                    │    │
│   │                                                       │    │
│   │    # Update metadata                                  │    │
│   │    node.updated_at = now()                           │    │
│   │    node.updated_by_cycles.append(cycle_id)           │    │
│   │                                                       │    │
│   │    # Save to database                                 │    │
│   │    graph.update_node(node)                           │    │
│   │                                                       │    │
│   │    Event: node.updated                               │    │
│   │    Count: findings_updated++                         │    │
│   └──────────────────────────────────────────────────────┘    │
│                                                                 │
│   ┌──────────────────────────────────────────────────────┐    │
│   │ 2b. Create New Node                                 │    │
│   │                                                       │    │
│   │    # Discount confidence for new findings            │    │
│   │    confidence = finding.confidence * 0.7             │    │
│   │                                                       │    │
│   │    # Set importance by type                          │    │
│   │    importance_map = {                                │    │
│   │      "question": 0.7,                                │    │
│   │      "hypothesis": 0.8,                              │    │
│   │      "supporting": 0.5,                              │    │
│   │      "opposing": 0.6                                 │    │
│   │    }                                                 │    │
│   │    importance = importance_map[finding.type]         │    │
│   │                                                       │    │
│   │    # Create node                                     │    │
│   │    node = KnowledgeNode(                             │    │
│   │      id=generate_id(),                               │    │
│   │      parent_id=target_node_id,                       │    │
│   │      claim=finding.claim,                            │    │
│   │      confidence=confidence,                          │    │
│   │      importance=importance,                          │    │
│   │      node_type=finding.type,                         │    │
│   │      evidence=finding.evidence,                      │    │
│   │      tags=finding.tags,                              │    │
│   │      created_by_cycle=cycle_id,                      │    │
│   │      depth=parent.depth + 1                          │    │
│   │    )                                                 │    │
│   │                                                       │    │
│   │    # Save to database                                 │    │
│   │    graph.create_node(node)                           │    │
│   │                                                       │    │
│   │    Event: node.created                               │    │
│   │    Count: findings_created++                         │    │
│   └──────────────────────────────────────────────────────┘    │
│                                                                 │
│   ┌──────────────────────────────────────────────────────┐    │
│   │ 3. Propagate Confidence Upward                      │    │
│   │                                                       │    │
│   │    current = node                                     │    │
│   │    while current.parent_id:                          │    │
│   │      parent = graph.get_node(current.parent_id)      │    │
│   │                                                       │    │
│   │      # Aggregate children's confidence                │    │
│   │      children = graph.get_children(parent.id)        │    │
│   │      supporting = [c for c in children               │    │
│   │                    if c.type == "supporting"]         │    │
│   │      opposing = [c for c in children                 │    │
│   │                  if c.type == "opposing"]             │    │
│   │                                                       │    │
│   │      # Calculate net confidence                       │    │
│   │      if supporting:                                   │    │
│   │        support_conf = max(c.confidence               │    │
│   │                           for c in supporting)        │    │
│   │      else:                                            │    │
│   │        support_conf = 0.0                            │    │
│   │                                                       │    │
│   │      if opposing:                                     │    │
│   │        oppose_conf = max(c.confidence                │    │
│   │                          for c in opposing)           │    │
│   │      else:                                            │    │
│   │        oppose_conf = 0.0                             │    │
│   │                                                       │    │
│   │      # Net confidence                                 │    │
│   │      parent.confidence = (                           │    │
│   │        support_conf * (1 - oppose_conf)              │    │
│   │      )                                                │    │
│   │                                                       │    │
│   │      graph.update_node(parent)                       │    │
│   │      current = parent                                 │    │
│   └──────────────────────────────────────────────────────┘    │
│                                                                 │
│ Returns: {                                                      │
│   findings_created: int,                                       │
│   findings_updated: int,                                       │
│   findings_skipped: int                                        │
│ }                                                              │
│                                                                 │
│ Event: cycle.step (merge_findings)                             │
└────────────────────────────────────────────────────────────────┘
                          ↓
┌────────────────────────────────────────────────────────────────┐
│ STEP 6: Deduplicate Subtree                                    │
│                                                                 │
│ merge_and_deduplicate_subtree(target_node_id)                  │
│                                                                 │
│ Purpose: Consolidate redundant sibling nodes                   │
│                                                                 │
│ 1. Get all children of target node                             │
│                                                                 │
│ 2. Group by node_type (only merge within same type)            │
│                                                                 │
│ 3. For each pair of siblings:                                  │
│                                                                 │
│    tokens_A = set(node_a.claim.lower().split())                │
│    tokens_B = set(node_b.claim.lower().split())                │
│    jaccard = |A ∩ B| / |A ∪ B|                                 │
│                                                                 │
│    if jaccard > 0.85:  # Higher threshold than merge           │
│      # Consolidate into one node                               │
│      merged.claim = longer of (A, B)                           │
│      merged.confidence = 1 - (1 - A.conf) * (1 - B.conf)       │
│      merged.evidence = A.evidence + B.evidence                 │
│      merged.children = A.children + B.children (reparent)      │
│                                                                 │
│      graph.update_node(merged)                                 │
│      graph.delete_node(duplicate)                              │
│                                                                 │
│ Event: cycle.step (deduplication)                              │
└────────────────────────────────────────────────────────────────┘
                          ↓
┌────────────────────────────────────────────────────────────────┐
│ STEP 7: Save Cycle Output                                      │
│                                                                 │
│ 1. Insert into cycle_outputs table:                            │
│    ┌────────────────────────────────────────────────────┐     │
│    │ cycle_id: {cycle_id}                               │     │
│    │ workspace_id: {workspace_id}                       │     │
│    │ target_node_id: {target_node_id}                   │     │
│    │ selection_strategy: {EXPLORE/DEEPEN/CHALLENGE}     │     │
│    │ selection_reasoning: {why_this_node}               │     │
│    │                                                     │     │
│    │ # Multi-agent synthesis data                       │     │
│    │ synthesis_reasoning: {llm_synthesis_explanation}   │     │
│    │ consensus_findings: [{claims_agents_agree_on}]     │     │
│    │ contradictions: [{claims_agents_disagree_on}]      │     │
│    │                                                     │     │
│    │ # Merge statistics                                 │     │
│    │ findings_created: {count}                          │     │
│    │ findings_updated: {count}                          │     │
│    │ findings_skipped: {count}                          │     │
│    │                                                     │     │
│    │ # Resource tracking                                │     │
│    │ agent_count: {n_agents}                            │     │
│    │ total_cost_usd: {sum_of_agent_costs}               │     │
│    │ total_tokens: {sum_of_agent_tokens}                │     │
│    │ duration_seconds: {elapsed_time}                   │     │
│    │                                                     │     │
│    │ created_at: {timestamp}                            │     │
│    └────────────────────────────────────────────────────┘     │
│                                                                 │
│ 2. Insert into agent_outputs table (one per agent):            │
│    ┌────────────────────────────────────────────────────┐     │
│    │ cycle_output_id: {cycle_id}                        │     │
│    │ agent_name: "claude-opus-4-6"                      │     │
│    │ findings: [{claim, confidence, evidence}]          │     │
│    │ self_critique: {agent_reflection}                  │     │
│    │ searches_performed: [{query, provider, cost}]      │     │
│    │ cost_usd: {agent_cost}                             │     │
│    │ tokens_used: {agent_tokens}                        │     │
│    │ raw_output: {full_agent_text}                      │     │
│    └────────────────────────────────────────────────────┘     │
│                                                                 │
│ 3. Export to markdown:                                         │
│    Path: .winterfox/raw/{YYYY-MM-DD}/cycle_{id}.md            │
│                                                                 │
│    Format:                                                     │
│    ┌────────────────────────────────────────────────────┐     │
│    │ # Cycle {id}: {target_claim}                       │     │
│    │                                                     │     │
│    │ **Strategy**: {EXPLORE/DEEPEN/CHALLENGE}           │     │
│    │ **Cost**: ${total_cost_usd}                        │     │
│    │ **Duration**: {duration}s                          │     │
│    │ **Agents**: {agent_names}                          │     │
│    │                                                     │     │
│    │ ## Selection Reasoning                             │     │
│    │ {why_this_node}                                    │     │
│    │                                                     │     │
│    │ ## Agent Outputs                                   │     │
│    │ ### Agent: claude-opus-4-6                         │     │
│    │ {raw_output}                                       │     │
│    │                                                     │     │
│    │ ## Synthesis (Multi-Agent)                         │     │
│    │ {synthesis_reasoning}                              │     │
│    │                                                     │     │
│    │ ### Consensus Findings                             │     │
│    │ - {claim 1}                                        │     │
│    │ - {claim 2}                                        │     │
│    │                                                     │     │
│    │ ### Contradictions                                 │     │
│    │ - {disagreement 1}                                 │     │
│    │                                                     │     │
│    │ ## Merge Results                                   │     │
│    │ - Created: {n} nodes                               │     │
│    │ - Updated: {n} nodes                               │     │
│    │ - Skipped: {n} duplicates                          │     │
│    └────────────────────────────────────────────────────┘     │
│                                                                 │
│ Event: cycle.completed                                         │
└────────────────────────────────────────────────────────────────┘
                          ↓
┌────────────────────────────────────────────────────────────────┐
│ STEP 8: Update Orchestrator State                              │
│                                                                 │
│ orchestrator.cycle_history.append(cycle_result)                │
│ orchestrator.total_cost_usd += cycle_result.cost_usd           │
│ orchestrator.total_cycles_run += 1                             │
│                                                                 │
│ Returns: CycleResult {                                         │
│   cycle_id: int,                                               │
│   target_node_id: str,                                         │
│   target_claim: str,                                           │
│   strategy: str,                                               │
│   findings_created: int,                                       │
│   findings_updated: int,                                       │
│   consensus_findings: List[str],                               │
│   divergent_findings: List[str],                               │
│   agent_outputs: List[AgentOutput],                            │
│   total_cost_usd: float,                                       │
│   duration_seconds: float,                                     │
│   success: bool,                                               │
│   error_message: Optional[str]                                 │
│ }                                                              │
└────────────────────────────────────────────────────────────────┘
```

---

## Data Processing & Storage

### Data Flow Architecture

```
┌──────────────────────────────────────────────────────────────┐
│                      DATA FLOW DIAGRAM                        │
└──────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│ AGENT RESEARCH PHASE                                        │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  LLM Agent + Tools                                          │
│       │                                                      │
│       ├──► web_search("legal tech market size")            │
│       │         │                                            │
│       │         ↓                                            │
│       │    Search Providers (Tavily/Brave/Serper)           │
│       │         │                                            │
│       │         ↓                                            │
│       │    SearchResult[]                                    │
│       │                                                      │
│       ├──► web_fetch("https://source.com/article")          │
│       │         │                                            │
│       │         ↓                                            │
│       │    HTML → Markdown Content                           │
│       │                                                      │
│       ├──► note_finding(                                     │
│       │       claim="Legal tech TAM is $50B by 2025",        │
│       │       confidence=0.85,                               │
│       │       evidence=[Evidence(...)]                       │
│       │     )                                                │
│       │         │                                            │
│       │         ↓                                            │
│       │    Queue: [Finding, Finding, ...]                   │
│       │                                                      │
│       └──► Agent completes                                   │
│                 │                                            │
│                 ↓                                            │
│         AgentOutput {                                        │
│           findings: [Finding],                               │
│           searches: [SearchRecord],                          │
│           cost_usd: 0.15                                     │
│         }                                                    │
│                                                              │
└──────────────────────────────────────────────────────────────┘
                          ↓
┌──────────────────────────────────────────────────────────────┐
│ SYNTHESIS PHASE (Multi-Agent)                                │
├──────────────────────────────────────────────────────────────┤
│                                                              │
│  Primary Agent (Synthesizer)                                │
│       │                                                      │
│       ├──► Receives: [AgentOutput1, AgentOutput2, ...]      │
│       │                                                      │
│       ├──► Analyzes:                                        │
│       │     - Common findings (consensus)                   │
│       │     - Conflicting findings (contradictions)         │
│       │     - Evidence quality                              │
│       │     - Confidence levels                             │
│       │                                                      │
│       └──► Returns: SynthesisResult {                       │
│                 unified_findings: [Finding],                │
│                 synthesis_reasoning: str,                   │
│                 consensus_findings: [claim],                │
│                 contradictions: [claim]                     │
│             }                                               │
│                                                              │
└──────────────────────────────────────────────────────────────┘
                          ↓
┌──────────────────────────────────────────────────────────────┐
│ MERGE PHASE: Findings → Knowledge Nodes                      │
├──────────────────────────────────────────────────────────────┤
│                                                              │
│  For each Finding:                                          │
│                                                              │
│    Finding {                                                │
│      claim: "Legal tech TAM is $50B by 2025"                │
│      confidence: 0.85                                       │
│      type: "supporting"                                     │
│      evidence: [                                            │
│        Evidence(                                            │
│          source: "https://...",                             │
│          text: "Market research shows...",                  │
│          date: "2024-01-15",                                │
│          verified_by: ["claude-opus-4-6"]                   │
│        )                                                    │
│      ]                                                      │
│    }                                                        │
│          │                                                  │
│          ↓                                                  │
│    ┌─────────────────────────────────────────┐             │
│    │ Deduplication Check                     │             │
│    │ - Jaccard similarity > 0.75?            │             │
│    │ - Same node_type?                       │             │
│    └─────────────────────────────────────────┘             │
│          │                │                                 │
│     MATCH FOUND     NO MATCH                                │
│          │                │                                 │
│          ↓                ↓                                 │
│    UPDATE NODE      CREATE NODE                             │
│          │                │                                 │
│          ↓                ↓                                 │
│    KnowledgeNode {                                          │
│      id: "abc123..."                                        │
│      claim: "Legal tech TAM is $50B by 2025"                │
│      confidence: 0.88  ← COMPOUNDED if updated              │
│      node_type: "supporting"                                │
│      evidence: [...all evidence...]                         │
│      parent_id: "parent..."                                 │
│      created_by_cycle: 5                                    │
│      updated_by_cycles: [3, 5]                              │
│    }                                                        │
│          │                                                  │
│          ↓                                                  │
│    Propagate confidence to parent → grandparent → ...       │
│                                                              │
└──────────────────────────────────────────────────────────────┘
                          ↓
┌──────────────────────────────────────────────────────────────┐
│ PERSISTENCE PHASE: Nodes → SQLite                            │
├──────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌────────────────────────────────────────────────────────┐ │
│  │ Table: nodes                                           │ │
│  ├────────────────────────────────────────────────────────┤ │
│  │ id               │ "abc123..."                         │ │
│  │ workspace_id     │ "default"                           │ │
│  │ parent_id        │ "parent..."                         │ │
│  │ claim            │ "Legal tech TAM is $50B by 2025"    │ │
│  │ confidence       │ 0.88                                │ │
│  │ importance       │ 0.5                                 │ │
│  │ depth            │ 2                                   │ │
│  │ node_type        │ "supporting"                        │ │
│  │ data             │ {full KnowledgeNode JSON}           │ │
│  │ created_by_cycle │ 5                                   │ │
│  │ updated_at       │ 2025-02-14T10:30:00                 │ │
│  └────────────────────────────────────────────────────────┘ │
│                                                              │
│  ┌────────────────────────────────────────────────────────┐ │
│  │ Table: nodes_fts (FTS5 virtual table)                  │ │
│  ├────────────────────────────────────────────────────────┤ │
│  │ Auto-synced via trigger on INSERT/UPDATE to nodes      │ │
│  │ Enables: SELECT * FROM nodes_fts WHERE claim MATCH ?   │ │
│  └────────────────────────────────────────────────────────┘ │
│                                                              │
│  ┌────────────────────────────────────────────────────────┐ │
│  │ Table: cycle_outputs                                   │ │
│  ├────────────────────────────────────────────────────────┤ │
│  │ cycle_id              │ 5                              │ │
│  │ target_node_id        │ "node..."                      │ │
│  │ synthesis_reasoning   │ "Agents agree that..."         │ │
│  │ consensus_findings    │ ["claim1", "claim2"]           │ │
│  │ contradictions        │ ["disagreement1"]              │ │
│  │ findings_created      │ 3                              │ │
│  │ findings_updated      │ 2                              │ │
│  │ total_cost_usd        │ 0.35                           │ │
│  │ duration_seconds      │ 45.2                           │ │
│  └────────────────────────────────────────────────────────┘ │
│                                                              │
│  ┌────────────────────────────────────────────────────────┐ │
│  │ Table: agent_outputs (per-agent)                       │ │
│  ├────────────────────────────────────────────────────────┤ │
│  │ cycle_output_id  │ 5                                   │ │
│  │ agent_name       │ "claude-opus-4-6"                   │ │
│  │ findings         │ [{claim, conf, evidence}]           │ │
│  │ self_critique    │ "Evidence quality is high..."       │ │
│  │ searches_performed│ [{query, provider, cost}]          │ │
│  │ cost_usd         │ 0.15                                │ │
│  │ tokens_used      │ 12500                               │ │
│  │ raw_output       │ "Let me search for..."              │ │
│  └────────────────────────────────────────────────────────┘ │
│                                                              │
│  ┌────────────────────────────────────────────────────────┐ │
│  │ Table: graph_operations (audit log)                    │ │
│  ├────────────────────────────────────────────────────────┤ │
│  │ cycle_id    │ 5                                        │ │
│  │ operation   │ "update_node"                            │ │
│  │ node_id     │ "abc123..."                              │ │
│  │ details     │ {"old_conf": 0.7, "new_conf": 0.88}     │ │
│  │ timestamp   │ 2025-02-14T10:30:00                      │ │
│  └────────────────────────────────────────────────────────┘ │
│                                                              │
└──────────────────────────────────────────────────────────────┘
                          ↓
┌──────────────────────────────────────────────────────────────┐
│ EXPORT PHASE: Markdown Files                                 │
├──────────────────────────────────────────────────────────────┤
│                                                              │
│  File: .winterfox/raw/2025-02-14/cycle_5.md                 │
│                                                              │
│  Human-readable markdown format                              │
│  - Cycle metadata                                           │
│  - Selection reasoning                                       │
│  - Full agent outputs                                       │
│  - Synthesis results                                        │
│  - Merge statistics                                         │
│                                                              │
└──────────────────────────────────────────────────────────────┘
```

### Confidence Compounding Formula

When multiple independent sources confirm the same finding:

```
P(claim is true) = 1 - P(all sources wrong)
                 = 1 - ∏(1 - confidence_i)

Example:
- Agent 1 finds evidence: 70% confidence
- Agent 2 independently confirms: 75% confidence

Combined confidence:
= 1 - (1 - 0.70) × (1 - 0.75)
= 1 - (0.30) × (0.25)
= 1 - 0.075
= 0.925 (92.5%)
```

This models independent verification: the probability both are wrong is low.

### Discount Factor

New findings are discounted by 0.7 (70%) before merging:
- Accounts for potential bias in single-source findings
- Encourages multi-agent verification
- Prevents overconfidence from single agent

---

## Multi-Agent Synthesis

### Why LLM-Based Synthesis?

**Traditional approaches** (keyword matching, statistical aggregation):
- ❌ Miss semantic similarities
- ❌ Can't handle nuance and context
- ❌ Require domain-specific tuning
- ❌ No explanatory reasoning

**LLM-based synthesis**:
- ✅ Semantic understanding
- ✅ Handles nuance and weighted evidence
- ✅ Explains reasoning
- ✅ Domain-agnostic
- ✅ Evaluates evidence quality

### Synthesis Process Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                   MULTI-AGENT SYNTHESIS                      │
└─────────────────────────────────────────────────────────────┘

PHASE 1: Independent Research (Parallel)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

┌──────────────────┐  ┌──────────────────┐  ┌──────────────────┐
│ Agent 1          │  │ Agent 2          │  │ Agent 3          │
│ (Claude Opus)    │  │ (Kimi 2.5)       │  │ (GPT-4)          │
├──────────────────┤  ├──────────────────┤  ├──────────────────┤
│                  │  │                  │  │                  │
│ web_search(...)  │  │ web_search(...)  │  │ web_search(...)  │
│ web_fetch(...)   │  │ web_fetch(...)   │  │ web_fetch(...)   │
│ note_finding()   │  │ note_finding()   │  │ note_finding()   │
│                  │  │                  │  │                  │
│ Findings:        │  │ Findings:        │  │ Findings:        │
│ • Market $50B    │  │ • Market $48B    │  │ • Market $45-55B │
│   (conf: 0.85)   │  │   (conf: 0.70)   │  │   (conf: 0.80)   │
│ • Growth 15%     │  │ • Growth 12%     │  │ • Growth 18%     │
│   (conf: 0.75)   │  │   (conf: 0.80)   │  │   (conf: 0.65)   │
│ • Top vendor X   │  │ • Challenges Y   │  │ • Top vendor X   │
│   (conf: 0.90)   │  │   (conf: 0.75)   │  │   (conf: 0.85)   │
│                  │  │                  │  │                  │
└────────┬─────────┘  └────────┬─────────┘  └────────┬─────────┘
         │                     │                     │
         │                     │                     │
         └─────────────────────┴─────────────────────┘
                              ↓

PHASE 2: LLM-Based Synthesis
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

┌──────────────────────────────────────────────────────────────┐
│ Synthesizer Agent (Primary Agent - Claude Opus)              │
├──────────────────────────────────────────────────────────────┤
│                                                               │
│ INPUT:                                                        │
│ ┌─────────────────────────────────────────────────────────┐  │
│ │ Agent 1 Output: {findings, evidence, searches}          │  │
│ │ Agent 2 Output: {findings, evidence, searches}          │  │
│ │ Agent 3 Output: {findings, evidence, searches}          │  │
│ └─────────────────────────────────────────────────────────┘  │
│                                                               │
│ ANALYSIS:                                                     │
│ ┌─────────────────────────────────────────────────────────┐  │
│ │ 1. GROUP SIMILAR CLAIMS:                                │  │
│ │    "Market $50B" ≈ "Market $48B" ≈ "Market $45-55B"    │  │
│ │    → Consensus cluster                                  │  │
│ │                                                          │  │
│ │ 2. IDENTIFY CONSENSUS:                                  │  │
│ │    All 3 agents agree: Market ~$50B                     │  │
│ │    Evidence quality: High (multiple sources)            │  │
│ │    Boost confidence: 0.85 → 0.92                        │  │
│ │                                                          │  │
│ │ 3. IDENTIFY CONTRADICTIONS:                             │  │
│ │    Agent 1: Growth 15%                                  │  │
│ │    Agent 2: Growth 12%                                  │  │
│ │    Agent 3: Growth 18%                                  │  │
│ │    → Requires more research                             │  │
│ │                                                          │  │
│ │ 4. PRESERVE UNIQUE INSIGHTS:                            │  │
│ │    Agent 2 found unique: "Challenges Y"                 │  │
│ │    Well-sourced → Include with note: single-agent      │  │
│ │                                                          │  │
│ │ 5. EVALUATE EVIDENCE QUALITY:                           │  │
│ │    Agent 1 & 3: Same vendor X (independent sources)     │  │
│ │    → Corroboration increases confidence                 │  │
│ └─────────────────────────────────────────────────────────┘  │
│                                                               │
│ OUTPUT:                                                       │
│ ┌─────────────────────────────────────────────────────────┐  │
│ │ unified_findings: [                                     │  │
│ │   {                                                      │  │
│ │     claim: "Legal tech market size ~$50B by 2025",      │  │
│ │     confidence: 0.92,  ← Boosted by consensus           │  │
│ │     evidence: [all evidence from all agents],           │  │
│ │     verified_by: ["claude", "kimi", "gpt4"]             │  │
│ │   },                                                     │  │
│ │   {                                                      │  │
│ │     claim: "Leading vendor is X",                       │  │
│ │     confidence: 0.88,  ← Corroborated by 2 agents       │  │
│ │     evidence: [...],                                    │  │
│ │     verified_by: ["claude", "gpt4"]                     │  │
│ │   },                                                     │  │
│ │   {                                                      │  │
│ │     claim: "Key challenge is Y",                        │  │
│ │     confidence: 0.75,  ← Single agent                   │  │
│ │     evidence: [...],                                    │  │
│ │     verified_by: ["kimi"]                               │  │
│ │   }                                                      │  │
│ │ ]                                                        │  │
│ │                                                          │  │
│ │ synthesis_reasoning:                                    │  │
│ │   "All three agents found consistent evidence for       │  │
│ │    $50B market size from independent sources. This      │  │
│ │    consensus significantly increases confidence.        │  │
│ │    Agent 1 and 3 both identified vendor X as leader,    │  │
│ │    corroborating each other. Growth rate estimates      │  │
│ │    vary (12-18%), suggesting need for further research."│  │
│ │                                                          │  │
│ │ consensus_findings: [                                   │  │
│ │   "Legal tech market size ~$50B by 2025",               │  │
│ │   "Leading vendor is X"                                 │  │
│ │ ]                                                        │  │
│ │                                                          │  │
│ │ contradictions: [                                       │  │
│ │   "Growth rate: 12% vs 15% vs 18% - conflicting data"  │  │
│ │ ]                                                        │  │
│ └─────────────────────────────────────────────────────────┘  │
│                                                               │
└───────────────────────────────────────────────────────────────┘
```

### Synthesis Benefits

1. **Semantic Understanding**: Groups "Market is $50B" and "Market size $48-52B"
2. **Nuanced Confidence**: Different boost levels based on agreement strength
3. **Contradiction Detection**: Identifies genuine disagreements vs. semantic variations
4. **Evidence Quality**: Evaluates source credibility, recency, consistency
5. **Explanatory Reasoning**: Natural language explanation of synthesis decisions
6. **Domain Agnostic**: Works for legal tech, biology, history, etc.

---

## Integration Points

### Search Integration

```
┌─────────────────────────────────────────────────────────────┐
│                  SEARCH PROVIDER ARCHITECTURE                │
└─────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────┐
│ SearchManager                                                │
│ - Manages multiple search providers                          │
│ - Fallback on failure                                        │
│ - Cost tracking per provider                                 │
└──────────────────────────────────────────────────────────────┘
                          ↓
    ┌───────────────────────────────────────────────┐
    │                                               │
    ↓                  ↓              ↓            ↓
┌─────────┐    ┌──────────┐   ┌─────────┐   ┌────────────┐
│ Tavily  │    │  Brave   │   │ Serper  │   │ DuckDuckGo │
│         │    │          │   │         │   │            │
│ Best    │    │ Privacy  │   │ Google  │   │ Free       │
│ Research│    │ Focus    │   │ Results │   │ Fallback   │
│ $0.001  │    │ Free tier│   │ API     │   │ No API key │
└─────────┘    └──────────┘   └─────────┘   └────────────┘

Priority Order: Tavily → Brave → Serper → DuckDuckGo

Algorithm:
for provider in priority_order:
    try:
        results = await provider.search(query, max_results)
        if results:
            record_cost(provider.cost_per_search)
            return results
    except Exception:
        if not fallback_enabled:
            raise
        # Try next provider

return []  # All failed
```

### Graph Indexing

**Full-Text Search (FTS5)**:
```sql
-- Virtual table for fast text search
CREATE VIRTUAL TABLE nodes_fts USING fts5(claim);

-- Auto-sync trigger
CREATE TRIGGER nodes_fts_insert AFTER INSERT ON nodes
BEGIN
  INSERT INTO nodes_fts(rowid, claim) VALUES (new.rowid, new.claim);
END;

-- Query
SELECT * FROM nodes_fts WHERE claim MATCH 'legal tech market';
```

**Deduplication Index (Jaccard Similarity)**:
```python
def jaccard_similarity(claim_a: str, claim_b: str) -> float:
    tokens_a = set(claim_a.lower().split())
    tokens_b = set(claim_b.lower().split())

    intersection = tokens_a & tokens_b
    union = tokens_a | tokens_b

    if not union:
        return 0.0

    return len(intersection) / len(union)

# Thresholds
MERGE_THRESHOLD = 0.75    # Update existing node
DEDUPE_THRESHOLD = 0.85   # Consolidate siblings
```

**Type-Aware Indexing**:
- Only compare nodes with same `node_type`
- `opposing` ≠ `supporting` (different semantic stance)
- Prevents incorrect merges

### Multi-Tenancy

**Workspace Isolation**:
```sql
-- Every table scoped by workspace_id
workspaces (
  id TEXT PRIMARY KEY,
  name TEXT,
  owner_id TEXT,
  tier TEXT,  -- free, pro, enterprise
  settings TEXT  -- JSON
)

nodes (
  id TEXT,
  workspace_id TEXT,  ← Isolates data
  ...
  FOREIGN KEY (workspace_id) REFERENCES workspaces(id)
)

-- All queries filtered
SELECT * FROM nodes WHERE workspace_id = ? AND ...
```

**Current Mode**: Single workspace ("default") for CLI
**Future**: Multi-tenant SaaS with per-user workspaces

---

## API Reference

### REST API Endpoints

#### Graph Endpoints

```http
GET /api/graph/tree
  Query: ?workspace_id=default&root_id=node123
  Response: { nodes: [...], edges: [...] }

GET /api/graph/nodes/{node_id}
  Response: { id, claim, confidence, children, evidence, ... }

POST /api/graph/nodes
  Body: { claim, parent_id, node_type, confidence, ... }
  Response: { id, created: true }

GET /api/graph/search?q=legal+tech
  Response: { results: [...] }

GET /api/graph/stats
  Response: {
    total_nodes,
    avg_confidence,
    depth,
    node_type_distribution
  }
```

#### Cycle Endpoints

```http
GET /api/cycles
  Query: ?limit=10&offset=0&workspace_id=default
  Response: {
    cycles: [
      { cycle_id, target_node_id, cost_usd, duration_seconds, ... }
    ],
    total: 42
  }

GET /api/cycles/{cycle_id}
  Response: {
    cycle_id,
    target_node_id,
    target_claim,
    strategy,
    synthesis_reasoning,
    consensus_findings,
    contradictions,
    agent_outputs: [
      { agent_name, findings, searches_performed, cost_usd }
    ],
    findings_created,
    findings_updated,
    duration_seconds,
    created_at
  }

GET /api/cycles/active
  Response: {
    active: true,
    cycle_id: 15,
    target_node_id,
    elapsed_seconds: 25.3
  }
```

#### Stats Endpoints

```http
GET /api/stats
  Response: {
    total_cycles,
    total_nodes,
    total_cost_usd,
    avg_cost_per_cycle,
    total_searches,
    avg_confidence
  }

GET /api/stats/costs
  Response: {
    by_agent: { "claude-opus-4-6": 12.50, "kimi-2-5": 3.20 },
    by_cycle: [ { cycle_id, cost_usd }, ... ],
    total: 15.70
  }
```

#### Config Endpoints

```http
GET /api/config
  Response: {
    north_star_mission,
    workspace_id,
    agents: [
      { name: "claude-opus-4-6", enabled: true, role: "primary" }
    ],
    max_searches_per_cycle,
    use_consensus
  }
```

#### Report Endpoints

```http
POST /api/report
  Body: { format: "markdown", include_evidence: true }
  Response: { report: "# Knowledge Graph Report\n\n..." }
```

### WebSocket Events

**Connection**:
```javascript
const ws = new WebSocket('ws://localhost:8000/ws/events?workspace_id=default');

ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  handleEvent(data);
};
```

**Event Types**:
```javascript
// Cycle events
{ type: "cycle.started", cycle_id: 15, target_node_id: "node123" }
{ type: "cycle.step", step: "prompt_generation", details: {...} }
{ type: "cycle.completed", cycle_id: 15, result: {...} }
{ type: "cycle.failed", cycle_id: 15, error: "..." }

// Agent events
{ type: "agent.started", agent_name: "claude-opus-4-6" }
{ type: "agent.search", agent_name: "claude-opus-4-6", query: "legal tech TAM" }
{ type: "agent.completed", agent_name: "claude-opus-4-6", findings_count: 5 }

// Synthesis events
{ type: "synthesis.started", agent_count: 3 }
{ type: "synthesis.completed", consensus_count: 2, contradiction_count: 1 }

// Graph events
{ type: "node.created", node_id: "abc123", claim: "..." }
{ type: "node.updated", node_id: "abc123", old_confidence: 0.7, new_confidence: 0.88 }
```

---

## Key Design Patterns

### 1. Confidence Compounding

**Independent Confirmation**:
```python
# When multiple agents agree on same finding
conf_combined = 1 - (1 - conf1) * (1 - conf2) * ... * (1 - confN)

# Example: Two agents at 70% and 75%
conf_combined = 1 - (1 - 0.70) * (1 - 0.75)
              = 1 - (0.30) * (0.25)
              = 1 - 0.075
              = 0.925 (92.5%)
```

**Why it works**:
- Models probability that claim is true
- Assumes independent verification
- The more agents agree, the higher the confidence
- Diminishing returns (can't exceed 100%)

### 2. Type-Aware Merging

**Hypothesis Tree Structure**:
```
? Question: "What is the legal tech TAM?"
  H Hypothesis: "TAM is $50B by 2025"
    + Supporting: "Report shows $48-52B estimate"
    + Supporting: "Multiple analysts agree ~$50B"
    - Opposing: "Conservative estimate is $35B"
  H Hypothesis: "TAM growth rate is 15% annually"
    + Supporting: "Historical CAGR is 14-16%"
```

**Merge Rules**:
- Only merge within same `node_type`
- `opposing` and `supporting` are distinct stances
- Prevents semantic confusion

### 3. Token Efficiency

**Challenge**: Graph can grow to thousands of nodes
**Solution**: Multiple views with token budgets

```python
# Summary view (~500 tokens for 100 nodes)
def summary_view(graph):
    return tree_format(
        graph.root,
        max_depth=3,
        truncate_claims=50,  # chars
        show_only=["confidence", "type"]
    )

# Focused view (~2000 tokens for 20 nodes)
def focused_view(target_node_id):
    subtree = graph.get_subtree(target_node_id, max_depth=2)
    path_to_root = graph.get_path_to_root(target_node_id)
    return tree_format(subtree) + tree_format(path_to_root)
```

### 4. Research Context Accumulation

**Problem**: Each cycle should build on prior knowledge
**Solution**: Token-budgeted context sections

```python
context = ResearchContextBuilder.build(
    graph=graph,
    cycle_history=last_10_cycles,
    target_node_id=target_node_id
)

# Sections with character budgets
context = {
    "graph_summary": 3200,        # Tree structure
    "prior_cycles": 4800,         # Recent cycle summaries
    "search_history": 2400,       # Avoid redundancy
    "contradictions": 1600,       # Known disagreements
    "weakest_nodes": 1600,        # Low-confidence areas
    "open_questions": 2400        # Unanswered questions
}
# Total: ~16,000 chars (~4,000 tokens)
```

### 5. Strategy-Based Research

**Three strategies for different goals**:

```python
if strategy == "EXPLORE":
    # Breadth: Discover new areas
    instructions = """
    - Propose new hypotheses
    - Discover related topics
    - Think creatively and broadly
    - Expand the knowledge graph
    """

elif strategy == "DEEPEN":
    # Depth: More evidence for existing claims
    instructions = """
    - Find more evidence for current claim
    - Get specific details and statistics
    - Verify with multiple sources
    - Strengthen existing hypotheses
    """

elif strategy == "CHALLENGE":
    # Stress-test: Find counter-evidence
    instructions = """
    - Actively seek opposing viewpoints
    - Look for weaknesses in current understanding
    - Find contradictory evidence
    - Be a skeptical critic
    """
```

### 6. Propagation of Confidence

**Bottom-up confidence flow**:
```python
def propagate_confidence(node):
    """Update parent confidence based on children."""
    while node.parent_id:
        parent = graph.get_node(node.parent_id)
        children = graph.get_children(parent.id)

        supporting = [c for c in children if c.type == "supporting"]
        opposing = [c for c in children if c.type == "opposing"]

        support_conf = max(c.confidence for c in supporting) if supporting else 0.0
        oppose_conf = max(c.confidence for c in opposing) if opposing else 0.0

        # Net confidence considering opposition
        parent.confidence = support_conf * (1 - oppose_conf)

        graph.update_node(parent)
        node = parent
```

---

## CLI Commands

### Initialization

```bash
# Initialize new workspace
winterfox init "Legal Tech Research" \
  --north-star "Understand the legal tech market landscape"

# Initialize with context files
winterfox init "Project Name" \
  --north-star "Mission..." \
  --context-files research.pdf,notes.md
```

### Running Cycles

```bash
# Run N cycles
winterfox run -n 10

# Run with specific focus
winterfox run --focus node-abc123 -n 5

# Run with strategy
winterfox run --strategy EXPLORE -n 3

# Run without multi-agent consensus
winterfox run --no-consensus -n 10

# Run until graph is complete (confidence threshold)
winterfox run --until-complete --confidence-threshold 0.8
```

### Viewing

```bash
# Graph status and statistics
winterfox status

# Show specific node
winterfox show node-abc123

# List all cycles
winterfox cycle list --limit 20

# View specific cycle
winterfox cycle view 15

# View cycle and save to file
winterfox cycle view 15 --save cycle_015.md

# Search graph
winterfox search "legal tech market"
```

### Exporting

```bash
# Export full graph to markdown
winterfox export report.md

# Export to JSON
winterfox export data.json --format json

# Export specific cycles
winterfox cycle export report.md --cycles "1-10,15,20"

# Generate narrative report
winterfox report --output narrative.md
```

### Cycle Management

```bash
# List cycles with filtering
winterfox cycle list --limit 10 --sort cost

# Remove specific cycle (and its data)
winterfox cycle remove 15

# Replay cycle (re-run with same parameters)
winterfox cycle replay 15
```

### Interactive Mode

```bash
# Launch interactive session
winterfox interactive

# Interactive prompts:
# - Choose research strategy
# - Select target node
# - Review findings before merge
# - Approve or reject agent outputs
```

### Web Dashboard

```bash
# Launch web interface
winterfox serve --port 8000

# Open browser to http://localhost:8000
# Real-time WebSocket updates
# Visual graph exploration
```

### Configuration

```bash
# Show current config
winterfox config show

# Set configuration
winterfox config set max_searches_per_cycle 15
winterfox config set use_consensus true

# Configure agents
winterfox agents list
winterfox agents enable kimi-2-5
winterfox agents disable gpt-4
```

---

## Conclusion

Winterfox is a sophisticated autonomous research system built on **research cycles** (not sessions). Each cycle:

1. **Selects** a target intelligently (LLM-driven or UCB1)
2. **Researches** using multi-agent collaboration
3. **Synthesizes** with LLM-based semantic understanding
4. **Compounds** knowledge through confidence boosting
5. **Persists** everything for full observability

The architecture supports:
- Multi-agent consensus with intelligent synthesis
- Knowledge compounding over time
- Type-aware graph structure
- Full-text search and deduplication
- Cost tracking and budget management
- Multi-tenancy for future SaaS
- Real-time WebSocket events
- Comprehensive audit trail

This enables systematic, autonomous knowledge graph construction with increasing confidence through independent verification and evidence accumulation.
