# Claude Developer Guide

**Last Updated**: 2026-02-13
**Version**: 0.1.0
**Status**: Production-ready, 38/38 tests passing

---

## Purpose of This Document

This file helps AI assistants (Claude, GPT, etc.) quickly understand the winterfox codebase architecture, patterns, and development practices. It's a "README for AI developers" that provides context beyond what's in the code.

---

## Project Overview

**Winterfox** is an autonomous research system that uses multi-agent consensus to build knowledge graphs. Think of it as "autonomous literature review as code."

**Core Loop** (6 steps):
1. Select node with highest uncertainty/importance (UCB1-inspired)
2. Generate research prompt from graph context
3. Dispatch to multiple agents in parallel (Claude + Kimi)
4. Agents use tools (web_search, web_fetch, note_finding)
5. Merge findings into graph with deduplication
6. Propagate confidence scores upward

**Key Innovation**: Independent confirmation model - when multiple agents agree on a claim, confidence compounds: `conf_combined = 1 - (1-p1)(1-p2)`

---

## Architecture: 4 Core Components

### 1. Knowledge Graph (`src/winterfox/graph/`)

**Purpose**: Store research findings in a tree structure with confidence scores.

**Key Files**:
- `models.py` - Pydantic models for KnowledgeNode, Evidence
- `store.py` - SQLite storage with async operations
- `views.py` - Token-efficient graph rendering (summary_view, focused_view)
- `propagation.py` - Confidence propagation from children to parents

**Critical Pattern**: **Persistent Connection for In-Memory DBs**
```python
# WRONG (loses schema between calls):
async with aiosqlite.connect(":memory:") as db:
    await db.execute(...)

# RIGHT (persistent connection):
async with self._get_db() as db:
    await db.execute(...)
```

**Multi-Tenancy**: Every table has `workspace_id` column. All queries must filter by workspace.

**Node Selection Algorithm** (UCB1-inspired):
```python
score = (
    (1 - node.confidence) * 0.5 +  # Uncertainty (exploration)
    node.importance * 0.3 +         # Strategic value
    staleness_factor * 0.2          # Time since update
)
```

### 2. Agent Adapters (`src/winterfox/agents/`)

**Purpose**: Normalize different LLM APIs into a common protocol.

**Key Files**:
- `protocol.py` - AgentAdapter Protocol, AgentOutput dataclass
- `adapters/anthropic.py` - Claude Opus 4.6 (primary, 390 lines)
- `adapters/kimi.py` - Kimi 2.5 (cost-effective, 371 lines)
- `pool.py` - Multi-agent dispatch with consensus (272 lines)

**Tool-Use Loop Pattern**:
```python
async def run(self, system_prompt, user_prompt, tools, max_iterations=30):
    messages = [{"role": "user", "content": user_prompt}]

    for iteration in range(max_iterations):
        response = await self.client.messages.create(...)

        if response.stop_reason == "end_turn":
            break

        if response.stop_reason == "tool_use":
            tool_results = await self._execute_tools(response.content)
            messages.append({"role": "assistant", "content": response.content})
            messages.append({"role": "user", "content": tool_results})

    return self._parse_output(messages, response)
```

**LLM Synthesis Mechanism** (in `pool.py`):
1. Dispatch to all agents in parallel with `asyncio.gather`
2. Primary agent receives all outputs and synthesizes them intelligently
3. Primary agent identifies consensus, contradictions, and evaluates evidence quality
4. Returns unified findings with synthesis reasoning

**Why LLM Synthesis over Algorithmic?**
- Intelligence: LLMs can understand semantic similarity beyond keyword matching
- Nuance: Can handle contradictions and weighted evidence quality
- Context: Can explain synthesis reasoning in self_critique
- Adaptable: Works for any domain without tuning similarity thresholds

**Cost Tracking**: Every AgentOutput tracks:
- `total_tokens`, `input_tokens`, `output_tokens`
- `cost_usd` (calculated using model-specific pricing)
- `duration_seconds`

### 3. Orchestrator (`src/winterfox/orchestrator/`)

**Purpose**: Run research cycles that compound knowledge.

**Key Files**:
- `core.py` - Orchestrator class, main entry point
- `cycle.py` - Single cycle execution logic
- `selection.py` - Node selection (UCB1)
- `prompts.py` - Prompt generation from graph views
- `merge.py` - Finding deduplication and integration

**Cycle Flow**:
```python
async def run_cycle(self, focus: str | None = None):
    # 1. Select target node
    target = self._select_target(focus)

    # 2. Generate prompts
    system_prompt, user_prompt = self._generate_prompts(target)

    # 3. Dispatch to agent pool (with LLM synthesis if multi-agent)
    if len(agents) > 1:
        result = await self.agent_pool.dispatch_with_synthesis(...)
        findings = result.findings  # Already synthesized by primary agent
    else:
        outputs = await self.agent_pool.dispatch(...)
        findings = outputs[0].findings

    # 4. Merge findings into graph
    await self._merge_findings(target, findings)

    # 5. Propagate confidence
    self.graph.propagate_confidence(target.id)

    # 6. Record cycle metadata
    await self._record_cycle(target, outputs)
```

**Finding Merge Logic** (graph deduplication):
```python
# Check for duplicates in existing graph nodes
similar = self.graph.search_similar(finding.claim, threshold=0.75)

if similar:
    # Update existing node (independent confirmation)
    existing = similar[0]
    existing.evidence.extend(finding.evidence)
    existing.confidence = 1 - (1 - existing.confidence) * (1 - finding.confidence * 0.7)
else:
    # Create new node
    new_node = self.graph.add_node(...)
```

**Note**: Synthesis happens at the agent level (multi-agent → single synthesized output). Graph merge handles deduplication across cycles.

### 4. Multi-Provider Search (`src/winterfox/agents/tools/search/`)

**Purpose**: Never depend on a single search API. Support automatic fallback.

**Supported Providers**:
1. **Tavily** - Best for research (cost: $0.001/search)
2. **Brave** - Privacy-focused (free tier available)
3. **Serper** - Google results via API
4. **SerpAPI** - Multi-engine (Google, Bing, etc.)
5. **DuckDuckGo** - Free fallback (no API key needed)

**SearchManager Pattern**:
```python
async def search(self, query: str, max_results: int = 10):
    for provider in self.providers:  # Sorted by priority
        try:
            results = await provider.search(query, max_results)
            if results:
                await self._record_cost(provider.cost_per_search)
                return results
        except Exception as e:
            logger.warning(f"{provider.name} failed: {e}")
            if not self.fallback_enabled:
                raise

    return []  # All providers failed
```

**LLM Native Search**: Claude Opus 4.6 and Gemini can search natively (extended thinking). The `supports_native_search` flag enables this.

---

## Development Patterns

### Testing Strategy

**Unit Tests** (`tests/unit/`):
- Use in-memory SQLite (`:memory:`)
- Mock all external APIs
- Fast, no network I/O
- **Target: >90% coverage**
- **Current: 38/38 passing**

**Integration Tests** (`tests/integration/`):
- Real API calls (marked with `@pytest.mark.integration`)
- Run in CI only on main branch
- Test end-to-end workflows

**Test Fixtures** (`tests/fixtures/`):
- `sample_graphs.py` - Pre-built knowledge graphs
- `mock_agents.py` - MockAgent implementations
- `sample_outputs.py` - Sample AgentOutput data

### Common Pitfalls

**1. In-Memory Database Schema Loss**
```python
# WRONG - Each connect() creates new empty database:
async with aiosqlite.connect(":memory:") as db:
    await db.execute("SELECT * FROM nodes")  # Error: no such table

# RIGHT - Use persistent connection:
async with self._get_db() as db:
    await db.execute("SELECT * FROM nodes")  # Works
```

**2. Missing AgentOutput Fields**
```python
# WRONG - Will fail validation:
AgentOutput(
    findings=[],
    self_critique="...",
    raw_text="...",
    # Missing: model, total_tokens, input_tokens, output_tokens
)

# RIGHT - All required fields:
AgentOutput(
    findings=[],
    self_critique="...",
    raw_text="...",
    searches_performed=[],
    cost_usd=0.0,
    duration_seconds=0.0,
    agent_name="claude-opus-4",
    model="claude-opus-4-20251120",
    total_tokens=1000,
    input_tokens=800,
    output_tokens=200,
)
```

**3. Workspace Isolation**
```python
# WRONG - Queries entire database:
await db.execute("SELECT * FROM nodes WHERE status = 'active'")

# RIGHT - Scoped to workspace:
await db.execute(
    "SELECT * FROM nodes WHERE workspace_id = ? AND status = 'active'",
    (self.workspace_id,)
)
```

**4. Exception Types in Retry Logic**
```python
# WRONG - Generic Exception is NOT retried:
raise Exception("Temporary failure")

# RIGHT - ConnectionError and TimeoutError are retried:
raise ConnectionError("Temporary failure")
```

### Code Style

**Type Hints**: Strict typing with mypy (`mypy --strict`)
```python
# Good:
async def add_node(
    self,
    claim: str,
    parent_id: str | None = None,
    confidence: float = 0.0,
) -> KnowledgeNode:
    ...

# Bad (no types):
async def add_node(self, claim, parent_id=None, confidence=0.0):
    ...
```

**Async Patterns**: Use `asyncio.gather` for parallelism
```python
# Good (parallel):
results = await asyncio.gather(
    agent1.run(prompt, tools),
    agent2.run(prompt, tools),
    agent3.run(prompt, tools),
)

# Bad (sequential):
results = []
for agent in agents:
    result = await agent.run(prompt, tools)
    results.append(result)
```

**Error Handling**: Return valid results on error, don't crash
```python
# Good (graceful degradation):
try:
    result = await agent.run(prompt, tools)
except Exception as e:
    logger.error(f"Agent failed: {e}")
    result = AgentOutput(
        findings=[],
        self_critique=f"Agent failed: {e}",
        # ... other fields ...
    )

# Bad (crash):
result = await agent.run(prompt, tools)  # Unhandled exception
```

---

## Configuration System

**Format**: TOML with Pydantic validation

**Key Sections**:
```toml
[project]
name = "Research Project Name"
north_star = "north-star.md"  # Or inline string

[[agents]]
provider = "anthropic"  # anthropic | moonshot | openai | google | xai
model = "claude-opus-4-20251120"
api_key_env = "ANTHROPIC_API_KEY"
supports_native_search = true

[search]
use_llm_native_search = true  # Prefer LLM's native search
fallback_enabled = true

[[search.providers]]
name = "tavily"  # tavily | brave | serper | serpapi | duckduckgo
api_key_env = "TAVILY_API_KEY"
priority = 1  # Lower = higher priority
max_results = 10
enabled = true

[orchestrator]
max_searches_per_agent = 25
confidence_discount = 0.7  # Initial skepticism (0.0 = trust, 1.0 = skeptical)
consensus_boost = 0.15  # Confidence boost for agreement

[storage]
db_path = ".winterfox/graph.db"
raw_output_dir = ".winterfox/raw"
git_auto_commit = true

[multi_tenancy]
enabled = false  # CLI mode (single workspace)
workspace_id = "default"
```

**Loading Config**:
```python
from winterfox.config import ResearchConfig

config = ResearchConfig.from_toml("winterfox.toml")
# Pydantic validates all fields, API keys, etc.
```

---

## CLI Commands

```bash
# Initialize project
winterfox init "Project Name" --north-star north-star.md

# Run research cycles
winterfox run -n 10  # Run 10 cycles
winterfox run --focus "specific topic"  # Focus on specific area
winterfox run --until-confidence 0.8  # Run until target confidence

# View progress
winterfox status  # Summary view
winterfox show <node-id>  # Detailed node view

# Export results
winterfox export report.md  # Markdown format
winterfox export data.json --format json  # JSON format

# Interactive mode
winterfox interactive  # Run cycle, show results, prompt for next action
```

---

## Database Schema

**Multi-Tenant Design**: Every table has `workspace_id` for isolation.

**Key Tables**:

```sql
-- Workspaces (SaaS multi-tenancy)
CREATE TABLE workspaces (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    tier TEXT DEFAULT 'free',  -- free | pro | enterprise
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Knowledge graph nodes
CREATE TABLE nodes (
    id TEXT PRIMARY KEY,
    workspace_id TEXT NOT NULL DEFAULT 'default',
    parent_id TEXT,
    claim TEXT NOT NULL,
    confidence REAL NOT NULL DEFAULT 0.0,
    importance REAL NOT NULL DEFAULT 0.5,
    depth INTEGER NOT NULL DEFAULT 0,
    status TEXT NOT NULL DEFAULT 'active',
    data JSON NOT NULL,  -- Full KnowledgeNode serialized
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (workspace_id) REFERENCES workspaces(id),
    FOREIGN KEY (parent_id) REFERENCES nodes(id)
);

-- Full-text search
CREATE VIRTUAL TABLE nodes_fts USING fts5(
    id UNINDEXED,
    workspace_id UNINDEXED,
    claim
);

-- Research cycles
CREATE TABLE cycles (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    workspace_id TEXT NOT NULL DEFAULT 'default',
    started_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP,
    focus_node_id TEXT,
    total_cost_usd REAL DEFAULT 0.0,
    findings_count INTEGER DEFAULT 0
);

-- Usage tracking (for SaaS billing)
CREATE TABLE usage_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    workspace_id TEXT NOT NULL,
    event_type TEXT NOT NULL,  -- cycle | search | agent_call
    timestamp TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    cost_usd REAL DEFAULT 0.0
);
```

**Indexes for Performance**:
```sql
CREATE INDEX idx_workspace ON nodes(workspace_id);
CREATE INDEX idx_selection_score ON nodes(workspace_id, confidence, importance, updated_at);
CREATE INDEX idx_parent ON nodes(parent_id);
```

---

## Common Tasks

### Adding a New Agent Provider

1. Create adapter in `src/winterfox/agents/adapters/your_provider.py`:
```python
from winterfox.agents.protocol import AgentAdapter, AgentOutput

class YourProviderAdapter:
    def __init__(self, model: str, api_key: str):
        self.model = model
        self.client = YourProviderClient(api_key=api_key)

    @property
    def name(self) -> str:
        return self.model

    @property
    def supports_native_search(self) -> bool:
        return False  # Set True if model can search natively

    async def run(
        self,
        system_prompt: str,
        user_prompt: str,
        tools: list[ToolDefinition],
        max_iterations: int = 30,
    ) -> AgentOutput:
        # Implement tool-use loop
        # Return AgentOutput with all required fields
        ...
```

2. Add to `config.py` AgentConfig validation:
```python
class AgentConfig(BaseModel):
    provider: Literal["anthropic", "moonshot", "openai", "google", "xai", "your_provider"]
    # ...
```

3. Add factory method in `orchestrator/core.py`:
```python
def _create_adapter(self, config: AgentConfig) -> AgentAdapter:
    if config.provider == "your_provider":
        return YourProviderAdapter(config.model, api_key)
    # ...
```

4. Add tests in `tests/unit/test_agents/test_adapters.py`

### Adding a New Search Provider

1. Create provider in `src/winterfox/agents/tools/search/your_provider.py`:
```python
from winterfox.agents.tools.search.base import SearchProvider, SearchResult

class YourSearchProvider:
    def __init__(self, api_key: str):
        self.api_key = api_key

    @property
    def name(self) -> str:
        return "your_provider"

    @property
    def cost_per_search(self) -> float:
        return 0.001  # USD per search

    async def search(
        self,
        query: str,
        max_results: int = 10,
        **kwargs
    ) -> list[SearchResult]:
        # Implement search
        # Return list of SearchResult
        ...
```

2. Update SearchConfig in `config.py`:
```python
class SearchProviderConfig(BaseModel):
    name: Literal["tavily", "brave", "serper", "serpapi", "duckduckgo", "your_provider"]
    # ...
```

3. Add to SearchManager factory in `agents/tools/search/base.py`

### Debugging a Failed Cycle

1. **Check cycle metadata**:
```bash
sqlite3 .winterfox/graph.db "SELECT * FROM cycles ORDER BY started_at DESC LIMIT 1"
```

2. **Check raw agent outputs**:
```bash
ls -lt .winterfox/raw/  # Find latest cycle
cat .winterfox/raw/cycle_123_agent_claude-opus-4.json
```

3. **Check graph operations**:
```bash
sqlite3 .winterfox/graph.db "SELECT * FROM graph_operations WHERE cycle_id = 123"
```

4. **Run with verbose logging**:
```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

---

## Performance Considerations

### Token Efficiency

**summary_view** must be token-efficient for LLM context:
- Target: <500 tokens for 100 nodes
- Use tree characters (├─└) not full JSON
- Show only: claim, confidence, depth, children count
- Truncate at max_depth (default: 6)

**focused_view** can be more detailed:
- Target: <2000 tokens for 20 nodes
- Include evidence snippets
- Show parent and children context

### Query Optimization

**Bad** (N+1 queries):
```python
for node in nodes:
    parent = await self.get_node(node.parent_id)  # N queries
```

**Good** (single query with JOIN):
```python
query = """
    SELECT n.*, p.claim as parent_claim
    FROM nodes n
    LEFT JOIN nodes p ON n.parent_id = p.id
    WHERE n.workspace_id = ?
"""
```

### Concurrent Operations

**Use asyncio.gather for I/O-bound operations**:
```python
# Good (parallel):
results = await asyncio.gather(
    self.graph.get_node(id1),
    self.graph.get_node(id2),
    self.graph.get_node(id3),
)

# Bad (sequential):
results = [
    await self.graph.get_node(id1),
    await self.graph.get_node(id2),
    await self.graph.get_node(id3),
]
```

---

## Future Roadmap

### Short-term (v0.2.0)
- [ ] Real-time WebSocket updates
- [ ] Graph visualization (D3.js)
- [ ] Semantic search with embeddings
- [ ] Research templates

### Medium-term (v0.3.0)
- [ ] FastAPI wrapper for SaaS
- [ ] Web UI (Next.js)
- [ ] Team collaboration
- [ ] Stripe billing integration

### Long-term (v1.0.0)
- [ ] Custom tool plugins
- [ ] Data source connectors (Notion, Confluence)
- [ ] Fine-tuned agents
- [ ] Export to presentations (Reveal.js, PowerPoint)

---

## Getting Help

**Documentation**:
- `README.md` - Quick start
- `docs/GETTING_STARTED.md` - 15-minute tutorial
- `docs/CONFIGURATION.md` - Complete config reference
- `docs/ARCHITECTURE.md` - System design (TODO)

**Examples**:
- `examples/market-research/` - Complete market research example

**Tests**:
- `tests/unit/` - Unit tests show usage patterns
- `tests/integration/` - Integration tests show end-to-end flows

**Community**:
- GitHub Issues: https://github.com/naomi-kynes/winterfox/issues
- Discussions: https://github.com/naomi-kynes/winterfox/discussions

---

## Quick Reference

**Most Important Files**:
1. `src/winterfox/graph/store.py` - Knowledge graph storage
2. `src/winterfox/agents/adapters/anthropic.py` - Primary agent
3. `src/winterfox/orchestrator/cycle.py` - Research loop
4. `src/winterfox/orchestrator/merge.py` - Finding integration

**Most Complex Logic**:
1. Confidence propagation (`graph/propagation.py`)
2. Finding deduplication (`orchestrator/merge.py`)
3. Multi-agent consensus (`agents/pool.py`)
4. Node selection algorithm (`orchestrator/selection.py`)

**Most Common Bugs**:
1. In-memory database schema loss → Use `_get_db()`
2. Missing AgentOutput fields → Include all required fields
3. Workspace not scoped → Add `WHERE workspace_id = ?`
4. Wrong exception type → Use ConnectionError for retries

---

**Version**: 0.1.0
**Tests**: 38/38 passing
**Coverage**: >90%
**Status**: Production-ready, ready for PyPI publication

**Next Steps**: Integration testing with real APIs → GitHub Actions CI/CD → PyPI publication
