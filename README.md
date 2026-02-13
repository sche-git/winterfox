# Winterfox 🦊

**Autonomous research system with multi-agent knowledge compounding**

Winterfox is an open-source Python package that runs autonomous research cycles, building knowledge graphs through multi-agent consensus. It's designed for CLI-first usage with multi-tenancy built in from day 1 for seamless SaaS scaling.

[![License](https://img.shields.io/badge/license-Apache%202.0-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/downloads/)
[![Tests](https://img.shields.io/badge/tests-passing-green.svg)](tests/)

## Features

- 🤖 **Multi-Agent Research**: Claude Opus 4.6 + Kimi 2.5 with consensus mechanisms
- 📊 **Knowledge Graphs**: SQLite-backed with confidence propagation and deduplication
- 🔍 **Multi-Provider Search**: Tavily, Brave, Serper with automatic fallback
- 🎯 **UCB1-Inspired Selection**: Balances exploration vs exploitation
- 💰 **Cost Tracking**: Track API costs across cycles and agents
- 📈 **Confidence Compounding**: Independent confirmation model for evidence
- 🏢 **Multi-Tenancy Ready**: Built for CLI now, SaaS later
- 🎨 **Rich CLI**: Beautiful terminal output with progress bars and panels

## Quick Start

### Installation

```bash
# Using UV (recommended)
uv pip install winterfox

# Or using pip
pip install -e .
```

### Initialize Your First Project

```bash
# Initialize research project
winterfox init "Legal Tech Market Research" \
  --north-star "Research the market opportunity for legal tech SaaS targeting mid-market general counsels"

# Set API keys
export ANTHROPIC_API_KEY="sk-ant-..."
export TAVILY_API_KEY="tvly-..."

# Run research cycles
winterfox cycle -n 10

# Check progress
winterfox status

# Export results
winterfox export report.md
```

### Output

```
✓ Cycle 1: 7 created, 3 updated | $0.1234 | 45.2s
✓ Cycle 2: 5 created, 8 updated | $0.0987 | 38.1s
...

┌─────────────────────────────────────┐
│ Legal Tech Market Research          │
│                                     │
│ Total nodes: 47                     │
│ Average confidence: 72%             │
│ Low confidence: 5                   │
└─────────────────────────────────────┘

[Market Opportunity] (conf: 0.82, depth: 5) ✓
├─ [Legal Tech TAM] (conf: 0.88, depth: 3) ✓
│  ├─ [Market Size $50B by 2025] (conf: 0.92, depth: 2) ✓
│  └─ [Growth Rate 15% CAGR] (conf: 0.85, depth: 2) ✓
└─ [Competition] (conf: 0.81, depth: 4) ✓
   ├─ [Harvey AI] (conf: 0.89, depth: 3) ✓
   └─ [Thomson Reuters] (conf: 0.86, depth: 3) ✓
```

## Architecture

Winterfox consists of 4 main components:

### 1. Knowledge Graph (Phase 1)
- SQLite-backed with multi-tenancy support
- Confidence propagation using independent confirmation
- Jaccard similarity for deduplication
- Full-text search with FTS5
- Token-efficient graph views

### 2. Agent Adapter Layer (Phase 2)
- **Claude Opus 4.6** (primary): Extended thinking with native search
- **Kimi 2.5** (secondary): 200k+ context window, bilingual (EN/CN)
- **Multi-provider search**: Tavily, Brave, Serper, SerpAPI, DuckDuckGo
- **Tool-use loops**: Web search, content fetch, graph interaction
- **Consensus analysis**: Groups similar findings, boosts confidence

### 3. Research Orchestrator (Phase 3)
- **UCB1-inspired node selection**: Balances uncertainty, importance, staleness
- **Cycle execution**: Select → Prompt → Dispatch → Merge → Propagate → Deduplicate
- **Finding merge**: Deduplicates with Jaccard similarity (threshold: 0.75)
- **Confidence compounding**: `1 - (1-p1)(1-p2)` for independent confirmation
- **Run modes**: Single cycle, N cycles, until confidence target

### 4. CLI & Configuration (Phase 4)
- **6 commands**: init, cycle, status, show, export, interactive
- **TOML configuration**: Type-safe with Pydantic validation
- **Rich output**: Panels, tables, progress bars, colored text
- **Export formats**: Markdown (human-readable), JSON (machine-readable)
- **Interactive mode**: User steering between cycles

## Configuration

Edit `winterfox.toml` to configure your research project:

```toml
[project]
name = "Legal Tech Market Research"
north_star = """
Build a legal tech SaaS product for mid-market general counsels.
Target: 100-1000 employee companies that need affordable legal ops automation.
"""

# Primary research agent: Claude Opus 4.6
[[agents]]
provider = "anthropic"
model = "claude-opus-4-20251120"
api_key_env = "ANTHROPIC_API_KEY"
supports_native_search = true

# Secondary agent: Kimi 2.5 (uncomment for multi-agent consensus)
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
db_path = ".winterfox/graph.db"
git_auto_commit = true
```

## CLI Commands

### `winterfox init`
Initialize a new research project.

```bash
winterfox init "Project Name"
winterfox init "AI Startups" --north-star "Research AI startup landscape"
```

Creates:
- `winterfox.toml` - Configuration file
- `.winterfox/graph.db` - SQLite database
- `.winterfox/raw/` - Raw agent outputs

### `winterfox cycle`
Run research cycles.

```bash
winterfox cycle                     # Run 1 cycle
winterfox cycle -n 10               # Run 10 cycles
winterfox cycle --focus node-123    # Research specific node
winterfox cycle --no-consensus      # Disable multi-agent consensus
```

### `winterfox status`
Show research progress.

```bash
winterfox status
winterfox status --depth 5
```

### `winterfox show`
Display specific node details.

```bash
winterfox show abc123
winterfox show abc123 --depth 3
```

### `winterfox export`
Export knowledge graph.

```bash
winterfox export report.md
winterfox export data.json --format json
winterfox export brief.md --no-evidence
```

### `winterfox interactive`
Interactive mode with user steering.

```bash
winterfox interactive
```

## Programmatic Usage

Use Winterfox as a Python library:

```python
import asyncio
from winterfox import KnowledgeGraph, Orchestrator, AgentPool
from winterfox.agents.adapters.anthropic import AnthropicAdapter
from winterfox.agents.tools import get_research_tools

async def main():
    # Initialize graph
    graph = KnowledgeGraph(".winterfox/graph.db")
    await graph.initialize()

    # Create initial research question
    await graph.add_node(
        claim="What is the market opportunity for legal tech SaaS?",
        confidence=0.0,
        importance=1.0,
        created_by_cycle=0,
    )

    # Initialize agents
    agent = AnthropicAdapter(
        model="claude-opus-4-20251120",
        api_key="sk-ant-...",
    )
    agent_pool = AgentPool([agent])

    # Get research tools
    tools = get_research_tools(graph)

    # Create orchestrator
    orchestrator = Orchestrator(
        graph=graph,
        agent_pool=agent_pool,
        north_star="Build a legal tech SaaS for mid-market GCs",
        tools=tools,
    )

    # Run research cycles
    results = await orchestrator.run_until_complete(
        min_confidence=0.8,
        max_cycles=50,
    )

    # Print summary
    print(orchestrator.get_summary())

    # Export
    from winterfox.export import export_to_markdown
    await export_to_markdown(graph, "report.md")

    await graph.close()

asyncio.run(main())
```

## How It Works

### Research Cycle

Each cycle follows 6 steps:

1. **Select Target Node**: UCB1 algorithm picks node balancing:
   - Uncertainty: `(1 - confidence) * 0.5`
   - Importance: `importance * 0.3`
   - Staleness: `log(1 + hours/24) * 0.2`

2. **Generate Prompts**: Combines north star + focused graph view:
   ```
   Focus on: Thomson Reuters competitive positioning
   Current confidence: 0.52
   Goal: Bring to >0.8 with strong evidence
   ```

3. **Dispatch Agents**: Run agents in parallel (with optional consensus):
   - Single agent: Simple dispatch
   - Multi-agent: Group similar findings, boost confidence by 0.15

4. **Merge Findings**: Integrate into graph with deduplication:
   - Jaccard similarity > 0.75 → Update existing node
   - Otherwise → Create new node
   - Apply confidence discount: `0.7 * initial_confidence`

5. **Propagate Confidence**: Update parent nodes recursively:
   ```python
   parent.confidence = (
       evidence_confidence * 0.3 +
       children_avg_confidence * 0.7
   )
   ```

6. **Deduplicate Subtree**: Merge redundant siblings (similarity > 0.85)

### Confidence Model

**Independent Confirmation**:
```python
# Two agents confirm same finding
conf_combined = 1 - (1 - conf1) * (1 - conf2)

# Example: 0.7 and 0.75
# = 1 - (1 - 0.7) * (1 - 0.75)
# = 1 - 0.3 * 0.25 = 1 - 0.075 = 0.925
```

**Evidence Accumulation**:
```python
# Multiple pieces of evidence
conf = 1.0
for evidence in evidences:
    conf *= (1 - evidence_conf)
final_conf = min(1 - conf, 0.95)  # Capped at 0.95
```

### Deduplication

**Jaccard Similarity**:
```python
tokens_A = set(claim_A.lower().split())
tokens_B = set(claim_B.lower().split())

similarity = len(tokens_A ∩ tokens_B) / len(tokens_A ∪ tokens_B)

if similarity >= 0.75:
    # Update existing node
else:
    # Create new node
```

## Project Status

**Current Version**: 0.1.0 (Alpha)

**Implementation Status**:
- ✅ Phase 1: Knowledge Graph (5 files, ~1,100 lines)
- ✅ Phase 2: Agent Adapters (14 files, ~1,200 lines)
- ✅ Phase 3: Orchestrator (5 files, ~1,056 lines)
- ✅ Phase 4: CLI & Configuration (9 files, ~1,345 lines)

**Total**: 33 files, ~4,700 lines of production code

**Testing**:
- ✅ Phase 1: 13/13 tests passing
- ⚠️ Phase 2-4: Partial test coverage (10/25 passing)
- 🔄 Integration tests: In progress

**What Works**:
- Complete CLI interface
- Knowledge graph with SQLite
- Configuration management
- Export to markdown/JSON
- Multi-tenant data model
- Cost tracking
- UCB1 node selection
- Finding deduplication
- Confidence propagation

**What's Next** (TODO):
- Complete Phase 2 agent adapter implementations
- Finish AgentPool consensus logic
- Add integration tests with real APIs
- Complete documentation (getting-started guide)
- Add example research projects
- CI/CD workflows

## Development

### Setup

```bash
# Clone repository
git clone https://github.com/yourusername/winterfox.git
cd winterfox

# Install dependencies with UV
uv sync

# Run tests
uv run pytest tests/ -v

# Type checking
uv run mypy src/winterfox

# Linting
uv run ruff check src/winterfox

# Formatting
uv run ruff format src/winterfox
```

### Running Tests

```bash
# All tests
uv run pytest tests/ -v

# Phase 1 (Knowledge Graph)
uv run pytest tests/unit/test_graph/ -v

# Integration tests (requires API keys)
uv run pytest tests/integration/ -v -m integration

# With coverage
uv run pytest tests/ --cov=winterfox --cov-report=html
```

## Contributing

Contributions welcome! Please:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

See [CONTRIBUTING.md](CONTRIBUTING.md) for detailed guidelines.

## License

Apache 2.0 - See [LICENSE](LICENSE) for details.

This provides patent protection while remaining permissive for commercial use.

## Roadmap

### v0.2.0 (Next Release)
- [ ] Complete Phase 2 agent implementations
- [ ] Full multi-agent consensus
- [ ] Integration tests with real APIs
- [ ] Getting started guide
- [ ] Example research projects

### v0.3.0 (Future)
- [ ] Semantic search with embeddings
- [ ] Graph visualization (D3.js)
- [ ] Research templates library
- [ ] Agent plugin system
- [ ] Real-time streaming updates

### v1.0.0 (Production)
- [ ] Web UI (Next.js)
- [ ] Multi-user collaboration
- [ ] REST API
- [ ] Stripe billing integration
- [ ] Documentation site

## SaaS Evolution

Winterfox is designed as **open-core**:

**Open Source (Free)**:
- CLI tool with all features
- Single-agent research
- Self-hosted unlimited usage
- All export formats

**SaaS (Paid)**:
- Multi-agent consensus (3+ agents)
- Web UI with graph visualization
- Team collaboration
- Real-time sync
- API access
- Priority support

Multi-tenancy is built into the database schema from day 1 for seamless scaling.

## Acknowledgments

Built with:
- [Claude](https://anthropic.com) - Primary research agent
- [Kimi 2.5](https://moonshot.ai) - Secondary agent
- [Tavily](https://tavily.com) - Search API
- [Typer](https://typer.tiangolo.com) - CLI framework
- [Rich](https://rich.readthedocs.io) - Terminal formatting
- [Pydantic](https://pydantic.dev) - Data validation

## Citation

If you use Winterfox in your research, please cite:

```bibtex
@software{winterfox2024,
  title = {Winterfox: Autonomous Research with Multi-Agent Knowledge Compounding},
  author = {Your Name},
  year = {2024},
  url = {https://github.com/yourusername/winterfox}
}
```

## Links

- **Documentation**: [winterfox.readthedocs.io](https://winterfox.readthedocs.io) (Coming soon)
- **Issues**: [github.com/yourusername/winterfox/issues](https://github.com/yourusername/winterfox/issues)
- **Discussions**: [github.com/yourusername/winterfox/discussions](https://github.com/yourusername/winterfox/discussions)
- **PyPI**: [pypi.org/project/winterfox](https://pypi.org/project/winterfox) (Coming soon)

---

Made with 🦊 and ❤️ for autonomous research
