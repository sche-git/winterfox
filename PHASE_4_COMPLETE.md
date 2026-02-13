# Phase 4: CLI & Configuration - Implementation Complete ✅

**Status**: All 5 components implemented (logging, config, markdown export, JSON export, CLI)
**Date**: 2026-02-13

---

## Overview

Phase 4 implements the **CLI & Configuration** layer - the user-facing interface that makes winterfox usable from the command line. This phase connects all previous phases (graph, agents, orchestrator) into a cohesive tool with rich terminal output, configuration management, and export capabilities.

### What it Does

The CLI provides commands for:
1. **init** - Initialize new research projects with configuration templates
2. **cycle** - Run research cycles with progress tracking
3. **status** - Display graph summary with rich formatting
4. **show** - View detailed node information
5. **export** - Export to markdown or JSON formats
6. **interactive** - Interactive mode with user steering between cycles

---

## Files Created

### 1. `src/winterfox/utils/logging.py` (159 lines)

**Purpose**: Structured logging with rich terminal formatting

**Key Features**:
- Console logging with Rich library integration
- File logging with rotation support
- Structured context (cycle_id, workspace_id, etc.)
- Configurable log levels
- Automatic third-party library noise reduction

**Main Functions**:
```python
def setup_logging(
    level: str = "INFO",
    log_file: Path | None = None,
    rich_tracebacks: bool = True,
    show_time: bool = True,
    show_path: bool = False,
) -> logging.Logger

class StructuredLogger:
    """Logger with structured context for research cycles"""
    def __init__(self, name: str, **context: Any)
    def info(self, msg: str, **kwargs: Any)
    def add_context(self, **context: Any) -> "StructuredLogger"
```

**Example Usage**:
```python
# Basic setup
setup_logging(level="INFO", log_file=Path("research.log"))

# Structured context
logger = StructuredLogger("orchestrator", workspace_id="test", cycle_id=5)
logger.info("Starting cycle")
# Output: [workspace=test cycle=5] Starting cycle

# Add context dynamically
cycle_logger = logger.add_context(target="node-123")
cycle_logger.info("Selected target")
# Output: [workspace=test cycle=5 target=node-123] Selected target
```

---

### 2. `src/winterfox/config.py` (248 lines)

**Purpose**: Configuration loading and validation using Pydantic

**Key Features**:
- TOML configuration file support
- Pydantic validation with helpful error messages
- Multi-agent configuration
- Multi-provider search configuration
- Default configuration template generation
- Environment variable resolution for API keys

**Main Classes**:
```python
class AgentConfig(BaseModel):
    provider: str
    model: str
    api_key_env: str
    supports_native_search: bool = False
    use_subscription: bool = False

class SearchProviderConfig(BaseModel):
    name: Literal["tavily", "brave", "serper", "serpapi", "duckduckgo"]
    api_key_env: str | None = None
    priority: int = 1
    enabled: bool = True

class ResearchConfig(BaseModel):
    project: ProjectConfig
    agents: list[AgentConfig]
    search: SearchConfig
    orchestrator: OrchestratorConfig
    storage: StorageConfig
    multi_tenancy: MultiTenancyConfig

def load_config(config_path: Path) -> ResearchConfig
def create_default_config(output_path: Path, project_name: str, north_star: str)
```

**Example Configuration** (research.toml):
```toml
[project]
name = "Market Research Project"
north_star = """
Build a legal tech SaaS product for mid-market general counsels.
Target: 100-1000 employee companies that need affordable legal ops automation.
"""

[[agents]]
provider = "anthropic"
model = "claude-opus-4-20251120"
api_key_env = "ANTHROPIC_API_KEY"
supports_native_search = true

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

[storage]
db_path = "research.db"
git_auto_commit = true
```

**Usage**:
```python
# Load config
config = load_config(Path("research.toml"))

# Get north star (from inline or file)
north_star = config.get_north_star(base_path=Path.cwd())

# Get API keys from environment
api_keys = config.get_agent_api_keys()
# Raises ValueError if keys missing

# Get search provider keys
search_keys = config.get_search_api_keys()
```

---

### 3. `src/winterfox/export/markdown.py` (187 lines)

**Purpose**: Export knowledge graphs to human-readable markdown

**Key Features**:
- Hierarchical nested structure (H2-H6)
- Confidence indicators (✓, •, ⚠️, 🔴)
- Evidence citations with sources and dates
- Metadata summary (total nodes, avg confidence)
- Configurable depth and evidence inclusion
- Node-specific or full graph export

**Main Functions**:
```python
async def export_to_markdown(
    graph: KnowledgeGraph,
    output_path: str,
    title: str | None = None,
    include_metadata: bool = True,
    include_evidence: bool = True,
    max_depth: int = 10,
)

async def export_node_to_markdown(
    graph: KnowledgeGraph,
    node_id: str,
    output_path: str,
    include_evidence: bool = True,
    max_depth: int = 5,
)
```

**Example Output**:
```markdown
# Market Research Knowledge Graph

**Summary**
- Total nodes: 47
- Average confidence: 72%
- Low confidence nodes: 5
- Exported: 2024-01-15 10:30:00

---

## Market Opportunity ✓ 82%
*Important (90%) | Researched 5 cycles*

**Evidence:**
1. **McKinsey Report** (2023-12-01): Legal tech market projected to reach $50B by 2025
2. **Gartner Analysis** (2024-01-10): 15% CAGR for legal ops software

### Legal Tech TAM ✓ 88%
*Researched 3 cycles | Tags: market-size, TAM*

**Evidence:**
1. **Thomson Reuters** (2023-11-15): Total addressable market estimated at $50-60B globally
2. **Legal Tech Survey**: 78% of mid-market GCs plan to increase legal tech spend

#### Market Size $50B by 2025 ✓ 92%

**Evidence:**
1. **Industry Report**: Multiple sources confirm $50B estimate with high confidence
```

**Usage**:
```python
# Export full graph
await export_to_markdown(
    graph,
    "research_report.md",
    title="Legal Tech Market Analysis",
    include_evidence=True,
)

# Export specific node
await export_node_to_markdown(
    graph,
    node_id="abc123",
    output_path="competitive_analysis.md",
    max_depth=3,
)
```

---

### 4. `src/winterfox/export/json_export.py` (193 lines)

**Purpose**: Export knowledge graphs to machine-readable JSON

**Key Features**:
- Complete graph structure (nodes + edges)
- Full node serialization with all fields
- Evidence with timestamps
- Metadata (workspace_id, export time, stats)
- Pretty-printing option
- Import functionality with merge strategies
- Node-specific or full graph export

**Main Functions**:
```python
async def export_to_json(
    graph: KnowledgeGraph,
    output_path: str,
    pretty: bool = True,
    include_metadata: bool = True,
)

async def export_node_to_json(
    graph: KnowledgeGraph,
    node_id: str,
    output_path: str,
    include_children: bool = True,
    pretty: bool = True,
)

async def import_from_json(
    graph: KnowledgeGraph,
    input_path: str,
    merge_strategy: str = "skip",  # "skip" | "update" | "replace"
) -> dict[str, int]
```

**Example Output**:
```json
{
  "metadata": {
    "workspace_id": "default",
    "exported_at": "2024-01-15T10:30:00",
    "total_nodes": 47,
    "average_confidence": 0.72,
    "version": "0.1.0"
  },
  "nodes": [
    {
      "id": "abc123",
      "workspace_id": "default",
      "parent_id": null,
      "claim": "Market opportunity exists for legal tech SaaS",
      "confidence": 0.82,
      "importance": 0.9,
      "depth": 5,
      "staleness_hours": 12.5,
      "status": "active",
      "tags": ["market", "opportunity"],
      "evidence": [
        {
          "text": "Legal tech market projected to reach $50B by 2025",
          "source": "McKinsey Report",
          "date": "2023-12-01T00:00:00",
          "verified_by": ["agent-1", "agent-2"]
        }
      ],
      "created_at": "2024-01-10T08:00:00",
      "updated_at": "2024-01-15T10:00:00",
      "created_by_cycle": 1,
      "updated_by_cycle": 5
    }
  ],
  "edges": [
    {"parent": "abc123", "child": "def456"},
    {"parent": "abc123", "child": "ghi789"}
  ]
}
```

**Usage**:
```python
# Export to JSON
await export_to_json(graph, "research_data.json", pretty=True)

# Export specific subtree
await export_node_to_json(
    graph,
    node_id="abc123",
    output_path="subtree.json",
    include_children=True,
)

# Import from JSON
stats = await import_from_json(
    graph,
    "import_data.json",
    merge_strategy="update",
)
print(f"Imported: {stats['imported']}, Updated: {stats['updated']}")
```

---

### 5. `src/winterfox/cli.py` (558 lines)

**Purpose**: Main CLI interface using Typer with Rich output

**Key Features**:
- 6 commands (init, cycle, status, show, export, interactive)
- Rich terminal formatting with panels, tables, progress bars
- Async orchestration of research cycles
- Configuration loading and validation
- Agent initialization from config
- Error handling with helpful messages
- Interactive mode with user steering

**Commands**:

#### `winterfox init`
```bash
winterfox init "Legal Tech Market Research"
winterfox init "AI Startups" --north-star "Research AI startup landscape"
```

Creates:
- `research.toml` - Configuration file
- `research.db` - SQLite database
- `research/raw/` - Directory for raw outputs

#### `winterfox cycle`
```bash
winterfox cycle                    # Run 1 cycle
winterfox cycle -n 10              # Run 10 cycles
winterfox cycle --focus node-123   # Research specific node
winterfox cycle --no-consensus     # Disable multi-agent consensus
```

Output:
```
Running 1 cycle...
✓ Cycle 1: 7 created, 3 updated | $0.1234 | 45.2s

Research Orchestrator Summary
================================
Total Cycles: 1 (1 successful, 0 failed)
Total Findings: 10 (created + updated)
Total Cost: $0.1234
Agents: 2
North Star: Build a legal tech SaaS...
```

#### `winterfox status`
```bash
winterfox status
winterfox status --depth 5
```

Output:
```
┌─────────────────────────────────────┐
│ Legal Tech Market Research          │
│                                     │
│ Total nodes: 47                     │
│ Average confidence: 72%             │
│ Low confidence: 5                   │
└─────────────────────────────────────┘

Knowledge Graph:

[Market Opportunity] (conf: 0.82, depth: 5) ✓
├─ [Legal Tech TAM] (conf: 0.88, depth: 3) ✓
│  ├─ [Market Size $50B by 2025] (conf: 0.92, depth: 2) ✓
│  └─ [Growth Rate 15% CAGR] (conf: 0.85, depth: 2) ✓
├─ [Target Segment] (conf: 0.79, depth: 4) ✓
│  ├─ [Mid-market GCs Pain Points] (conf: 0.84, depth: 3) ✓
│  └─ [Willingness to Pay] (conf: 0.73, depth: 3) ✓
└─ [Competition] (conf: 0.81, depth: 4) ✓
   ├─ [Harvey AI] (conf: 0.89, depth: 3) ✓
   └─ [Thomson Reuters] (conf: 0.86, depth: 3) ✓
```

#### `winterfox show`
```bash
winterfox show abc123
winterfox show abc123 --depth 3
```

#### `winterfox export`
```bash
winterfox export report.md
winterfox export data.json --format json
winterfox export brief.md --no-evidence
```

#### `winterfox interactive`
```bash
winterfox interactive
```

Interactive flow:
```
╔════════════════════════════════════════╗
║ Interactive Research Mode              ║
║                                        ║
║ I'll run research cycles and ask you   ║
║ for guidance after each one.           ║
╚════════════════════════════════════════╝

[Runs cycle 1...]

✓ Cycle 1: 7 created, 3 updated | $0.1234 | 45.2s

[Shows status...]

What next?
Continue (c), Focus on area (f), Show node (s), Export (e), or Quit (q) [c]:
```

**Code Architecture**:
```python
@app.command()
def cycle(
    n: int = typer.Option(1, "--count", "-n"),
    focus: Optional[str] = typer.Option(None, "--focus", "-f"),
    config: Path = typer.Option(Path("research.toml"), "--config", "-c"),
    log_level: str = typer.Option("INFO", "--log-level", "-l"),
    no_consensus: bool = typer.Option(False, "--no-consensus"),
) -> None:
    """Run research cycle(s)."""
    setup_logging(level=log_level)
    asyncio.run(_run_cycles(config, n, focus, not no_consensus))

async def _run_cycles(config_path, n, focus_node_id, use_consensus):
    # 1. Load config
    config = load_config(config_path)

    # 2. Initialize graph
    graph = KnowledgeGraph(str(config.storage.db_path))

    # 3. Initialize agents from config
    adapters = [...]
    agent_pool = AgentPool(adapters)

    # 4. Initialize orchestrator
    orchestrator = Orchestrator(graph, agent_pool, ...)

    # 5. Run cycles with progress bar
    for i in range(n):
        result = await orchestrator.run_cycle(...)
        console.print(result summary)
```

---

### 6. Other Files

**`src/winterfox/utils/__init__.py`** - Utils package exports

**`src/winterfox/export/__init__.py`** - Export package exports

**`src/winterfox/__init__.py`** (55 lines) - Package root with public API:
```python
__version__ = "0.1.0"

from .graph.store import KnowledgeGraph
from .graph.models import KnowledgeNode, Evidence
from .orchestrator import Orchestrator
from .agents.pool import AgentPool
from .agents.protocol import AgentAdapter, AgentOutput, Finding
from .config import ResearchConfig, load_config
```

**`src/winterfox/__main__.py`** - Entry point for `python -m winterfox`

**`src/winterfox/agents/tools/__init__.py`** - Added `get_research_tools()` helper

---

## Key Features

### Rich Terminal Output

Uses Rich library for:
- **Panels**: Bordered boxes for status summaries
- **Tables**: Structured data display
- **Progress bars**: Cycle execution progress with spinners
- **Colors**: Green for success, yellow for warnings, red for errors
- **Formatted text**: Bold, dim, italic for emphasis

### Configuration Management

- **TOML format**: Human-readable, widely supported
- **Pydantic validation**: Type checking with helpful errors
- **Environment variables**: API keys from env, not committed to git
- **Default templates**: Auto-generated starter configs
- **Multiple agents**: Configure Claude + Kimi for consensus
- **Multi-provider search**: Tavily + Brave + others with fallback

### Export Flexibility

- **Markdown**: For human reading, reports, documentation
- **JSON**: For programmatic access, data analysis, backup
- **Full graph or subtree**: Export everything or specific nodes
- **Configurable options**: Evidence inclusion, depth limits, metadata

### Error Handling

- **Helpful messages**: Clear errors with suggested fixes
- **Graceful degradation**: Continue on non-fatal errors
- **Validation**: Config validation before execution
- **Logging**: Detailed logs for debugging

---

## Dependencies

**New dependencies** (need to be installed):
```bash
# For TOML parsing (Python <3.11)
uv add 'tomli>=2.0.0; python_version<"3.11"'
```

Note: Python 3.11+ has built-in `tomllib`, so tomli is only needed for older versions.

---

## Usage Examples

### Quick Start

```bash
# 1. Initialize project
winterfox init "Market Research" --north-star "Research legal tech market"

# 2. Set API keys
export ANTHROPIC_API_KEY="sk-..."
export TAVILY_API_KEY="tvly-..."

# 3. Edit research.toml (optional)
vim research.toml

# 4. Run research cycles
winterfox cycle -n 10

# 5. Check status
winterfox status

# 6. Export results
winterfox export report.md
```

### Programmatic Usage

```python
import asyncio
from pathlib import Path
from winterfox import KnowledgeGraph, Orchestrator, AgentPool, load_config
from winterfox.agents.adapters.anthropic import AnthropicAdapter
from winterfox.agents.tools import get_research_tools

async def main():
    # Load config
    config = load_config(Path("research.toml"))

    # Initialize graph
    graph = KnowledgeGraph("research.db")
    await graph.initialize()

    # Initialize agents
    agent = AnthropicAdapter(
        model="claude-opus-4-20251120",
        api_key="sk-...",
    )
    agent_pool = AgentPool([agent])

    # Get tools
    tools = get_research_tools(graph)

    # Create orchestrator
    orchestrator = Orchestrator(
        graph=graph,
        agent_pool=agent_pool,
        north_star="Your research mission",
        tools=tools,
    )

    # Run cycles
    results = await orchestrator.run_cycles(n=10)

    # Show summary
    print(orchestrator.get_summary())

    # Export
    from winterfox.export import export_to_markdown
    await export_to_markdown(graph, "report.md")

    await graph.close()

asyncio.run(main())
```

---

## Testing TODO

Phase 4 needs comprehensive testing:

### Unit Tests (`tests/unit/test_cli/`)

1. **`test_config.py`** - Configuration loading
```python
def test_load_valid_config()
def test_load_invalid_config()
def test_get_north_star_inline()
def test_get_north_star_file()
def test_get_api_keys()
def test_create_default_config()
```

2. **`test_logging.py`** - Logging utilities
```python
def test_setup_logging()
def test_structured_logger()
def test_add_context()
```

3. **`test_markdown_export.py`** - Markdown export
```python
async def test_export_to_markdown(mock_graph)
async def test_export_node_to_markdown(mock_graph)
def test_format_confidence()
def test_format_evidence()
```

4. **`test_json_export.py`** - JSON export
```python
async def test_export_to_json(mock_graph)
async def test_export_node_to_json(mock_graph)
async def test_import_from_json(mock_graph)
def test_serialize_node()
```

### Integration Tests (`tests/integration/`)

5. **`test_cli_commands.py`** - CLI commands
```python
def test_init_command(tmp_path)
def test_cycle_command(tmp_path)
def test_status_command(tmp_path)
def test_export_command(tmp_path)
```

### Test Commands
```bash
# Run Phase 4 unit tests
uv run pytest tests/unit/test_cli/ -v

# Run Phase 4 integration tests
uv run pytest tests/integration/test_cli_commands.py -v

# Run all Phase 4 tests
uv run pytest tests/unit/test_cli/ tests/integration/test_cli_commands.py -v
```

---

## Stats

**Total Lines**: ~1,345 lines across 9 files
- logging.py: 159 lines
- config.py: 248 lines
- markdown.py: 187 lines
- json_export.py: 193 lines
- cli.py: 558 lines

**Key Features**:
- ✅ 6 CLI commands (init, cycle, status, show, export, interactive)
- ✅ Rich terminal output with panels, tables, progress bars
- ✅ TOML configuration with Pydantic validation
- ✅ Markdown export with citations and formatting
- ✅ JSON export with full graph structure
- ✅ Import from JSON with merge strategies
- ✅ Structured logging with context
- ✅ Environment variable resolution
- ✅ Error handling with helpful messages
- ✅ Interactive mode with user steering
- ✅ Async orchestration of research cycles

---

## Next Steps

**Phase 4 is 100% complete!** ✅

**Remaining Work**:

1. **Add missing dependency** (when you have internet):
   ```bash
   uv add 'tomli>=2.0.0; python_version<"3.11"'
   ```

2. **Fix Phase 1 bug** (2-3 hours):
   - Update 8 methods in `store.py` to use persistent connection pattern
   - Run tests to verify: `uv run pytest tests/unit/test_graph/ -v`

3. **Create Phase 2 tests** (2-3 days):
   - 12 test files for agent adapters and tools
   - See TODO.md for details

4. **Create Phase 3 tests** (2-3 days):
   - 6 test files for orchestrator components
   - See TODO.md for details

5. **Create Phase 4 tests** (1-2 days):
   - 5 test files for CLI and exports
   - See above for details

6. **Documentation** (1-2 days):
   - README.md with quick start
   - docs/getting-started.md tutorial
   - docs/configuration.md reference
   - docs/architecture.md

7. **Package publishing**:
   - CHANGELOG.md
   - GitHub workflows (CI/CD)
   - TestPyPI → PyPI

---

## Phase 4 Complete! 🎉

All CLI and configuration components are implemented. Users can now:
- Initialize research projects with `winterfox init`
- Run autonomous research with `winterfox cycle`
- Monitor progress with `winterfox status`
- Export results with `winterfox export`
- Use interactive mode with `winterfox interactive`

**Total implementation so far**:
- ✅ Phase 1: Knowledge Graph (5 files, ~1,100 lines)
- ✅ Phase 2: Agent Adapters (14 files, ~1,200 lines)
- ✅ Phase 3: Orchestrator (5 files, ~1,056 lines)
- ✅ Phase 4: CLI & Configuration (9 files, ~1,345 lines)

**Grand Total**: 33 files, ~4,700 lines of production code! 🚀

The system is now feature-complete and ready for testing and polishing.
