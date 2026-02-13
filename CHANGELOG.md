# Changelog

All notable changes to winterfox will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.1.0] - 2026-02-13

### Added
- **Knowledge Graph System**: SQLite-backed graph with confidence propagation
  - Multi-tenancy support from day 1
  - Jaccard similarity for deduplication
  - Full-text search (FTS5)
  - Token-efficient graph views
  - Independent confirmation model for confidence

- **Agent Adapters**: Multi-LLM support with tool-use
  - Claude Opus 4.6 adapter with extended thinking
  - Kimi 2.5 adapter (Moonshot AI, 200k+ context)
  - Complete 30-iteration tool-use loops
  - Token tracking and cost calculation
  - Graceful error handling

- **Multi-Agent Consensus**: Parallel dispatch with agreement detection
  - Jaccard similarity grouping (threshold: 0.75)
  - Confidence boosting (+0.15) for consensus
  - Finding merging with evidence combination
  - Cost tracking across agents

- **Research Orchestrator**: UCB1-inspired node selection
  - 6-step research cycle (Select → Prompt → Dispatch → Merge → Propagate → Dedupe)
  - Finding merge with deduplication
  - Confidence propagation
  - Statistics tracking

- **Multi-Provider Search**: Automatic fallback support
  - Tavily (best for research)
  - Brave (privacy-focused)
  - Serper (Google results)
  - Web fetch with Jina Reader + readability fallback

- **CLI Interface**: 6 commands with rich output
  - `winterfox init` - Initialize projects
  - `winterfox cycle` - Run research cycles
  - `winterfox status` - View progress
  - `winterfox show` - View node details
  - `winterfox export` - Export to markdown/JSON
  - `winterfox interactive` - Interactive mode

- **Configuration Management**: TOML-based with validation
  - Pydantic models for type safety
  - Environment variable resolution
  - Default config generation

- **Export Functionality**: Human and machine-readable formats
  - Markdown with hierarchical structure
  - JSON with full graph structure
  - Import from JSON

### Testing
- 38 unit tests with 100% pass rate
- Phase 1: Knowledge graph (13 tests)
- Phase 2: Agent adapters and consensus (18 tests)
- Phase 3: Orchestrator (11 tests)

### Documentation
- Comprehensive README with quick start
- Architecture overview
- CLI command reference
- Programmatic API examples
- Algorithm explanations

## [0.0.1] - 2026-02-11

### Added
- Initial project structure
- Basic graph models and protocol definitions

[Unreleased]: https://github.com/siinnche/winterfox/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/siinnche/winterfox/releases/tag/v0.1.0
[0.0.1]: https://github.com/siinnche/winterfox/releases/tag/v0.0.1
