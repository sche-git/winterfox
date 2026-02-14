# Winterfox - Remaining Implementation Tasks

## Phase 1: Knowledge Graph (95% Complete)

### Critical Bug Fix (HIGH PRIORITY)
**Issue**: Other graph methods need to use persistent connection pattern for in-memory databases.

**What's Working**:
- ✅ Schema creation with SCHEMA_STATEMENTS
- ✅ Persistent connection for `:memory:` databases
- ✅ `add_node()` method works correctly
- ✅ `_get_db()` async context manager implemented
- ✅ test_add_node passes

**What Needs Fixing**:
All methods that currently use `async with aiosqlite.connect(self.db_path) as db:` need to be updated to use `async with self._get_db() as db:`:

1. `update_node()` - Line ~328
2. `get_node()` - Line ~413
3. `get_all_active_nodes()` - Line ~441
4. `get_root_nodes()` - Line ~459
5. `get_children()` - Line ~478
6. `search()` - Line ~507
7. `count_nodes()` - Line ~527
8. `kill_node()` - Line ~376

**How to Fix**:
Replace this pattern:
```python
async with aiosqlite.connect(self.db_path) as db:
    # operations
```

With this:
```python
async with self._get_db() as db:
    # operations
```

**File**: `src/winterfox/graph/store.py`

### Tests Status
- ✅ 2/13 tests passing (test_add_node, test_claim_similarity)
- ❌ 11/13 tests failing due to connection pattern issue above
- Once fixed, all tests should pass

---

## Phase 2: Agent Adapter Layer (✅ COMPLETE - Testing Pending)

### ✅ Completed Implementation
- ✅ `agents/protocol.py` - Protocol definitions (AgentAdapter, AgentOutput, Finding, etc.)
- ✅ `agents/adapters/base.py` - Base utilities (retry, cost tracking, pricing)
- ✅ `agents/adapters/anthropic.py` - Claude Opus 4.6 adapter (PRIMARY)
- ✅ `agents/adapters/kimi.py` - Kimi 2.5 adapter (Moonshot AI)
- ✅ `agents/tools/search/` - Multi-provider search (Tavily, Brave, Serper)
- ✅ `agents/tools/web_fetch.py` - Web fetch with Jina Reader fallback
- ✅ `agents/tools/graph_tools.py` - Graph interaction tools
- ✅ `agents/pool.py` - AgentPool with consensus analysis

**See**: `PHASE_2_COMPLETE.md` for full documentation

### ❌ Testing TODO (BEFORE Phase 3)

#### Unit Tests (`tests/unit/test_agents/`)

**1. `test_protocol.py`** - Protocol compliance
```python
def test_agent_adapter_protocol():
    # Test that adapters implement protocol correctly

def test_finding_validation():
    # Test Finding dataclass validation

def test_agent_output_structure():
    # Test AgentOutput structure
```

**2. `test_base.py`** - BaseAdapter utilities
```python
async def test_retry_logic():
    # Test exponential backoff retry

def test_cost_calculation():
    # Test cost calculation for different models

def test_pricing_database():
    # Verify all model pricing is correct
```

**3. `test_anthropic.py`** - Claude adapter (mocked)
```python
async def test_anthropic_tool_loop(mock_anthropic):
    # Test tool execution loop with mocked API

async def test_anthropic_finding_extraction(mock_anthropic):
    # Test parsing findings from responses

async def test_anthropic_error_handling(mock_anthropic):
    # Test graceful error handling
```

**4. `test_kimi.py`** - Kimi adapter (mocked)
```python
async def test_kimi_tool_loop(mock_httpx):
    # Test OpenAI-compatible tool use

async def test_kimi_finding_extraction(mock_httpx):
    # Test finding extraction
```

**5. `test_pool.py`** - AgentPool logic
```python
async def test_parallel_dispatch():
    # Test parallel agent execution

async def test_consensus_detection():
    # Test finding grouping by similarity

async def test_confidence_boosting():
    # Test consensus confidence boost

async def test_finding_merge():
    # Test merging similar findings
```

**6. `test_search.py`** - Search tools
```python
async def test_search_manager_fallback(mock_providers):
    # Test provider fallback

async def test_tavily_search(mock_tavily):
    # Test Tavily provider

async def test_brave_search(mock_httpx):
    # Test Brave provider
```

**7. `test_web_fetch.py`** - Web fetch
```python
async def test_jina_reader(mock_httpx):
    # Test Jina Reader strategy

async def test_readability_fallback(mock_httpx):
    # Test readability fallback

async def test_batch_fetching():
    # Test concurrent batch fetching
```

**8. `test_graph_tools.py`** - Graph tools
```python
async def test_read_graph_node(mock_graph):
    # Test reading node details

async def test_search_graph(mock_graph):
    # Test graph search

async def test_note_finding():
    # Test finding recording
```

#### Integration Tests (`tests/integration/`)

**9. `test_real_anthropic.py`** - Real API (marked)
```python
@pytest.mark.integration
async def test_claude_real_api():
    # Real Anthropic API call with simple tool

@pytest.mark.integration
async def test_claude_extended_thinking():
    # Test extended thinking capability
```

**10. `test_real_kimi.py`** - Real API (marked)
```python
@pytest.mark.integration
async def test_kimi_real_api():
    # Real Moonshot API call
```

**11. `test_real_search.py`** - Real search (marked)
```python
@pytest.mark.integration
async def test_tavily_real_search():
    # Real Tavily search

@pytest.mark.integration
async def test_brave_real_search():
    # Real Brave search
```

**12. `test_pool_consensus_e2e.py`** - End-to-end
```python
@pytest.mark.integration
async def test_multi_agent_consensus():
    # Full consensus flow with real agents
```

### Test Commands
```bash
# Run Phase 2 unit tests (fast, no API calls)
uv run pytest tests/unit/test_agents/ -v

# Run Phase 2 integration tests (real APIs, slow, costs money)
uv run pytest tests/integration/ -v -m integration

# Run all Phase 2 tests
uv run pytest tests/unit/test_agents/ tests/integration/ -v
```

### Testing Priority
1. **High**: test_pool.py (consensus logic is critical)
2. **High**: test_base.py (shared by all adapters)
3. **Medium**: test_anthropic.py, test_kimi.py (adapters)
4. **Medium**: test_search.py (search manager)
5. **Low**: test_web_fetch.py, test_graph_tools.py
6. **Optional**: Integration tests (only if you have API keys)

---

## Phase 3: Research Orchestrator (✅ COMPLETE - Testing Pending)

### ✅ Completed Implementation
- ✅ `orchestrator/core.py` - Main Orchestrator class with run_cycle(), run_cycles(), run_until_complete()
- ✅ `orchestrator/cycle.py` - ResearchCycle execution (select → prompt → dispatch → merge → propagate → deduplicate)
- ✅ `orchestrator/selection.py` - UCB1-inspired node selection algorithm
- ✅ `orchestrator/prompts.py` - Research prompt generation with focused graph views
- ✅ `orchestrator/merge.py` - Finding merge with deduplication and confidence combination

**See**: `PHASE_3_COMPLETE.md` for full documentation (~1,056 lines across 5 files)

**Key Features**:
- UCB1-inspired selection balancing uncertainty, importance, staleness
- Token-efficient prompt generation (<500 tokens for 100 nodes)
- Jaccard similarity deduplication (threshold: 0.75)
- Independent confirmation model for confidence
- Multi-agent consensus support (via AgentPool)
- Comprehensive error handling
- Cost and duration tracking

### ❌ Testing TODO

#### Unit Tests (`tests/unit/test_orchestrator/`)

**1. `test_selection.py`** - Node selection
```python
async def test_select_target_node(mock_graph):
    # Test UCB1 scoring

async def test_selection_weights(mock_graph):
    # Test configurable weights

async def test_staleness_bonus(mock_graph):
    # Test exploration bonus

async def test_get_priority_nodes(mock_graph):
    # Test top N selection
```

**2. `test_prompts.py`** - Prompt generation
```python
async def test_generate_research_prompt(mock_graph):
    # Test prompt generation

async def test_initial_research_prompt():
    # Test prompts for empty graph

async def test_source_quality_hierarchy():
    # Test tier system in prompts
```

**3. `test_merge.py`** - Finding merge
```python
async def test_merge_findings_deduplication(mock_graph):
    # Test Jaccard similarity deduplication

async def test_confidence_combination(mock_graph):
    # Test independent confirmation model

async def test_evidence_merging(mock_graph):
    # Test evidence combination

async def test_subtree_deduplication(mock_graph):
    # Test sibling consolidation
```

**4. `test_cycle.py`** - Cycle execution
```python
async def test_cycle_execution(mock_graph, mock_agent_pool):
    # Test full cycle flow

async def test_cycle_error_handling(mock_graph, mock_agent_pool):
    # Test graceful failure

async def test_cycle_stats(mock_graph, mock_agent_pool):
    # Test CycleResult stats
```

**5. `test_core.py`** - Orchestrator
```python
async def test_run_single_cycle(mock_graph, mock_agent_pool):
    # Test single cycle

async def test_run_multiple_cycles(mock_graph, mock_agent_pool):
    # Test run_cycles(n)

async def test_run_until_complete(mock_graph, mock_agent_pool):
    # Test confidence-based stopping

async def test_orchestrator_stats(mock_graph, mock_agent_pool):
    # Test summary and statistics
```

#### Integration Tests (`tests/integration/`)

**6. `test_end_to_end.py`** - Full cycle
```python
@pytest.mark.integration
async def test_full_research_cycle():
    # Complete cycle with real components (mock agents)

@pytest.mark.integration
async def test_multi_cycle_knowledge_compounding():
    # Test knowledge building over multiple cycles
```

### Test Commands
```bash
# Run Phase 3 unit tests (fast, mocked)
uv run pytest tests/unit/test_orchestrator/ -v

# Run Phase 3 integration tests (end-to-end, slow)
uv run pytest tests/integration/test_end_to_end.py -v

# Run all Phase 3 tests
uv run pytest tests/unit/test_orchestrator/ tests/integration/test_end_to_end.py -v
```

---

## Phase 4: CLI & Configuration (Not Started - 0%)

### Files to Create

#### 1. `cli.py` - Typer CLI
**Commands**:
- `winterfox init` - Initialize project
- `winterfox run` - Run research cycles
- `winterfox status` - Show graph summary
- `winterfox show <node_id>` - Focused view
- `winterfox export` - Export markdown/JSON
- `winterfox interactive` - Interactive mode

#### 2. `config.py` - Configuration management
**Purpose**: Load and validate winterfox.toml

#### 3. `export/markdown.py` - Markdown export
**Purpose**: Human-readable nested markdown with citations

#### 4. `export/json_export.py` - JSON export
**Purpose**: Machine-readable full graph export

---

## Phase 5: Multi-Provider Search (Not Started - 0%)

See Phase 2 #4 above for search tool implementation details.

---

## Testing TODO

### Phase 1 Tests (Once bug is fixed)
- Run: `uv run pytest tests/unit/test_graph/ -v`
- All 13 tests should pass

### Phase 2 Tests (Need to create)
```bash
tests/unit/test_agents/
  test_protocol.py - Protocol compliance
  test_anthropic.py - Claude adapter (mock)
  test_kimi.py - Kimi adapter (mock)
  test_pool.py - AgentPool logic
  test_tools.py - Search tools

tests/integration/
  test_real_anthropic.py - Real API call (marked)
  test_real_kimi.py - Real API call (marked)
```

### Phase 3 Tests (Need to create)
```bash
tests/unit/test_orchestrator/
  test_cycle.py - Cycle execution
  test_selection.py - Node selection
  test_prompts.py - Prompt generation
  test_merge.py - Finding merge logic

tests/integration/
  test_end_to_end.py - Full cycle with mock agents
```

---

## Documentation TODO

1. **README.md** - Getting started, installation, quick example
2. **docs/getting-started.md** - Comprehensive tutorial
3. **docs/configuration.md** - winterfox.toml reference
4. **docs/architecture.md** - System design
5. **docs/api-reference.md** - Python API docs
6. **examples/** - Sample research projects

---

## Package Publishing TODO

1. Add missing metadata to pyproject.toml (GitHub URLs, etc.)
2. Create CHANGELOG.md
3. Set up GitHub workflows (CI/CD)
4. Publish to TestPyPI first
5. Publish to PyPI

---

## Priority Order

### Immediate (to get working end-to-end)
1. **Complete Phase 4: CLI** (1-2 days) **← START HERE**
   - Basic commands (init, cycle, status, export)
   - Config loading (winterfox.toml)
   - Rich terminal output

### Short Term (testing & polish)
2. **Fix Phase 1 connection pattern bug** (2-3 hours)
   - Update 8 methods in store.py
   - Run tests to verify all pass

3. **Create Phase 2 tests** (2-3 days)
   - Unit tests with mocked APIs
   - Integration tests with real APIs (optional)

4. **Create Phase 3 tests** (2-3 days)
   - Unit tests for orchestrator components
   - End-to-end integration test

### Medium Term (polish)
5. Kimi 2.5 adapter
6. Multi-provider search fallback
7. Interactive mode
8. Export formats

### Long Term (nice to have)
9. Web UI prototype
10. Documentation site
11. Example projects
12. Video demos

---

## Quick Reference: Key Files Status

✅ Complete | 🚧 In Progress | ❌ Not Started

### Phase 1: Knowledge Graph
- ✅ `graph/models.py`
- 🚧 `graph/store.py` (needs 8 method fixes)
- ✅ `graph/views.py`
- ✅ `graph/propagation.py`
- ✅ `graph/operations.py`
- 🚧 `tests/unit/test_graph/test_basic.py` (2/13 passing)

### Phase 2: Agents
- ✅ `agents/protocol.py`
- ✅ `agents/adapters/base.py`
- ✅ `agents/adapters/anthropic.py`
- ✅ `agents/adapters/kimi.py`
- ✅ `agents/tools/search/`
- ✅ `agents/tools/web_fetch.py`
- ✅ `agents/tools/graph_tools.py`
- ✅ `agents/pool.py`

### Phase 3: Orchestrator
- ✅ `orchestrator/core.py`
- ✅ `orchestrator/cycle.py`
- ✅ `orchestrator/selection.py`
- ✅ `orchestrator/prompts.py`
- ✅ `orchestrator/merge.py`

### Phase 4: CLI
- ❌ All files (see list above)

---

## Estimated Timeline

- ✅ **Phase 1 Implementation**: Complete (5 files)
- ✅ **Phase 2 Implementation**: Complete (14 files, ~1,200 lines)
- ✅ **Phase 3 Implementation**: Complete (5 files, ~1,056 lines)
- **Phase 1 Fix**: 2-3 hours (connection pattern bug)
- **Phase 4 Complete**: 1-2 days (CLI & config)
- **Testing & Polish**: 4-6 days (all phases)

**Total Remaining**: ~6-9 days for tested v0.1.0

---

## Commands Reference

```bash
# Install dependencies
uv sync

# Run Phase 1 tests
uv run pytest tests/unit/test_graph/ -v

# Run all tests
uv run pytest tests/ -v

# Run integration tests (real API calls)
uv run pytest tests/integration/ -v -m integration

# Type checking
uv run mypy src/winterfox

# Linting
uv run ruff check src/winterfox

# Format code
uv run ruff format src/winterfox
```

---

Last Updated: 2025-02-13 (Phase 3 Complete)
