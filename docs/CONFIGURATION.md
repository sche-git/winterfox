# Configuration Reference

Complete reference for `winterfox.toml` configuration file.

## Table of Contents

- [Project Settings](#project-settings)
- [Agent Configuration](#agent-configuration)
- [Search Configuration](#search-configuration)
- [Orchestrator Settings](#orchestrator-settings)
- [Storage Configuration](#storage-configuration)
- [Multi-Tenancy Settings](#multi-tenancy-settings)
- [Complete Example](#complete-example)

## Project Settings

```toml
[project]
name = "Your Research Project Name"
north_star = """
Your research mission/goal.
This guides all research decisions.
"""
```

### Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `name` | string | Yes | Project name (used in exports, logs) |
| `north_star` | string | Yes | Research mission statement. Can be multi-line. Guides agent decisions and node selection. |

### Examples

```toml
# Market research
[project]
name = "Legal Tech SaaS Market Analysis"
north_star = """
Build a legal tech SaaS product for mid-market general counsels.
Target: 100-1000 employee companies needing affordable legal ops automation.
Focus on: market size, competition, buyer personas, pricing strategies.
"""

# Technical investigation
[project]
name = "React Server Components Deep Dive"
north_star = """
Understand how React Server Components work under the hood.
Focus on: rendering lifecycle, hydration, data fetching, performance implications.
"""

# Competitive analysis
[project]
name = "AI Code Assistant Competition"
north_star = """
Analyze the competitive landscape for AI code assistants.
Track: feature sets, pricing, market positioning, user sentiment.
"""
```

## Agent Configuration

Agents are LLMs that perform research. Configure one or more agents.

```toml
[[agents]]
provider = "anthropic"  # or "moonshot", "openai", "google", "xai"
model = "claude-opus-4-20251120"
api_key_env = "ANTHROPIC_API_KEY"
timeout = 300  # Optional, default 300
max_retries = 3  # Optional, default 3
supports_native_search = true  # Optional, default false
use_subscription = false  # Optional, Anthropic only, default false
```

### Fields

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `provider` | string | Yes | - | Provider: "anthropic", "moonshot", "openai", "google", "xai" |
| `model` | string | Yes | - | Model identifier |
| `api_key_env` | string | Yes | - | Environment variable containing API key |
| `timeout` | int | No | 300 | Request timeout in seconds |
| `max_retries` | int | No | 3 | Max retry attempts on failure |
| `supports_native_search` | bool | No | false | Whether model has built-in web search |
| `use_subscription` | bool | No | false | Use Anthropic subscription auth (Claude only) |

### Supported Providers

#### Anthropic (Claude)

```toml
[[agents]]
provider = "anthropic"
model = "claude-opus-4-20251120"  # Opus 4.6 (best quality)
# model = "claude-sonnet-4-20250514"  # Sonnet 4.5 (balanced)
# model = "claude-haiku-4-20250108"  # Haiku 4 (fast)
api_key_env = "ANTHROPIC_API_KEY"
supports_native_search = true  # Opus 4.6 has extended thinking
```

**Cost**: $15 input / $75 output per 1M tokens (Opus 4.6)

#### Moonshot (Kimi)

```toml
[[agents]]
provider = "moonshot"
model = "kimi-2.5"  # 200k+ context, bilingual (CN/EN)
api_key_env = "MOONSHOT_API_KEY"
```

**Cost**: ~$0.20 per 1M tokens (100x cheaper than Claude)
**Best for**: Cost-effective research, Chinese+English content

#### OpenAI (GPT)

```toml
[[agents]]
provider = "openai"
model = "gpt-4o"  # GPT-4o (multimodal)
# model = "gpt-4o-mini"  # Mini (cheaper)
api_key_env = "OPENAI_API_KEY"
```

**Cost**: $5 input / $15 output per 1M tokens (GPT-4o)

#### Google (Gemini)

```toml
[[agents]]
provider = "google"
model = "gemini-2.0-flash-exp"  # Flash (fast)
# model = "gemini-1.5-pro"  # Pro (quality)
api_key_env = "GOOGLE_API_KEY"
supports_native_search = true  # Gemini has built-in search
```

**Cost**: Free tier available, then $0.25 input / $1 output per 1M tokens

#### xAI (Grok)

```toml
[[agents]]
provider = "xai"
model = "grok-beta"
api_key_env = "XAI_API_KEY"
```

### Multi-Agent Setup

Use multiple agents for consensus (increases cost but improves quality):

```toml
# Primary: Claude Opus 4.6 (high quality)
[[agents]]
provider = "anthropic"
model = "claude-opus-4-20251120"
api_key_env = "ANTHROPIC_API_KEY"

# Secondary: Kimi 2.5 (cost-effective, diverse perspective)
[[agents]]
provider = "moonshot"
model = "kimi-2.5"
api_key_env = "MOONSHOT_API_KEY"

# Tertiary: GPT-4o (another perspective)
[[agents]]
provider = "openai"
model = "gpt-4o"
api_key_env = "OPENAI_API_KEY"
```

**When agents agree**, confidence gets boosted by `consensus_boost` (default: 0.15).

## Search Configuration

Configure web search providers for agents.

```toml
[search]
use_llm_native_search = true  # Prefer LLM's built-in search
fallback_enabled = true  # Try next provider on failure

[[search.providers]]
name = "tavily"
api_key_env = "TAVILY_API_KEY"
priority = 1  # Lower = higher priority
max_results = 10
enabled = true
```

### Fields

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `use_llm_native_search` | bool | No | true | Use LLM's built-in search when available |
| `fallback_enabled` | bool | No | true | Try next provider on failure |

### Provider Fields

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `name` | string | Yes | - | Provider: "tavily", "brave", "serper", "serpapi", "duckduckgo" |
| `api_key_env` | string | No* | - | Environment variable with API key (*not needed for duckduckgo) |
| `priority` | int | No | 1 | Lower number = higher priority |
| `max_results` | int | No | 10 | Max search results to return |
| `enabled` | bool | No | true | Whether provider is enabled |

### Supported Search Providers

#### Tavily (Recommended)

```toml
[[search.providers]]
name = "tavily"
api_key_env = "TAVILY_API_KEY"
priority = 1
max_results = 10
```

**Cost**: ~$0.001 per search
**Best for**: Research-grade results, clean extraction
**Get key**: https://tavily.com/

#### Brave

```toml
[[search.providers]]
name = "brave"
api_key_env = "BRAVE_API_KEY"
priority = 2
max_results = 10
```

**Cost**: Free tier (2,000 searches/month), then $5/month
**Best for**: Privacy-focused, no tracking
**Get key**: https://brave.com/search/api/

#### Serper (Google Results)

```toml
[[search.providers]]
name = "serper"
api_key_env = "SERPER_API_KEY"
priority = 3
max_results = 10
```

**Cost**: $50 for 5,000 searches
**Best for**: Google search results via API
**Get key**: https://serper.dev/

#### SerpAPI

```toml
[[search.providers]]
name = "serpapi"
api_key_env = "SERPAPI_KEY"
priority = 4
```

**Cost**: $50/month (5,000 searches)
**Best for**: Multiple search engines (Google, Bing, etc.)
**Get key**: https://serpapi.com/

#### DuckDuckGo (Free Fallback)

```toml
[[search.providers]]
name = "duckduckgo"
# No API key needed!
priority = 99  # Lowest priority (fallback)
max_results = 10
```

**Cost**: Free
**Best for**: Free fallback when paid providers fail
**Note**: Rate-limited, less reliable

### Recommended Multi-Provider Setup

```toml
[search]
use_llm_native_search = true
fallback_enabled = true

# Primary: Tavily (best quality)
[[search.providers]]
name = "tavily"
api_key_env = "TAVILY_API_KEY"
priority = 1

# Fallback: Brave (good quality, free tier)
[[search.providers]]
name = "brave"
api_key_env = "BRAVE_API_KEY"
priority = 2

# Last resort: DuckDuckGo (free, always available)
[[search.providers]]
name = "duckduckgo"
priority = 99
```

## Orchestrator Settings

Control how research cycles execute.

```toml
[orchestrator]
max_searches_per_agent = 25
agent_timeout_seconds = 300
confidence_discount = 0.7
consensus_boost = 0.15
similarity_threshold = 0.75
```

### Fields

| Field | Type | Default | Range | Description |
|-------|------|---------|-------|-------------|
| `max_searches_per_agent` | int | 25 | 1-100 | Max web searches per cycle per agent |
| `agent_timeout_seconds` | int | 300 | 30-900 | Agent timeout (prevents infinite loops) |
| `confidence_discount` | float | 0.7 | 0.0-1.0 | Multiplier for new finding confidence |
| `consensus_boost` | float | 0.15 | 0.0-0.5 | Confidence boost when 2+ agents agree |
| `similarity_threshold` | float | 0.75 | 0.0-1.0 | Jaccard similarity for deduplication |

### Parameter Tuning Guide

#### `max_searches_per_agent`

- **Higher (30-50)**: More thorough research, higher cost
- **Lower (10-20)**: Faster, cheaper, less comprehensive
- **Default (25)**: Balanced

#### `confidence_discount`

- **Higher (0.8-0.9)**: Trust initial findings more
- **Lower (0.5-0.6)**: Require more evidence for high confidence
- **Default (0.7)**: Balanced skepticism

Formula: `stored_confidence = agent_confidence × confidence_discount`

#### `consensus_boost`

- **Higher (0.2-0.3)**: Reward agreement more
- **Lower (0.05-0.1)**: Minimal boost for consensus
- **Default (0.15)**: Balanced

Applied when 2+ agents report similar findings.

#### `similarity_threshold`

- **Higher (0.85-0.95)**: Require near-identical claims to merge
- **Lower (0.6-0.7)**: More aggressive deduplication
- **Default (0.75)**: Balanced

Uses Jaccard similarity: `|A ∩ B| / |A ∪ B|`

## Storage Configuration

```toml
[storage]
db_path = ".winterfox/graph.db"
raw_output_dir = ".winterfox/raw"
git_auto_commit = false
git_auto_push = false
```

### Fields

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `db_path` | string | ".winterfox/graph.db" | SQLite database file path |
| `raw_output_dir` | string | ".winterfox/raw" | Directory for raw agent outputs (for debugging) |
| `git_auto_commit` | bool | false | Auto-commit after each cycle |
| `git_auto_push` | bool | false | Auto-push to remote (requires git_auto_commit) |

### Git Integration

```toml
[storage]
db_path = ".winterfox/graph.db"
git_auto_commit = true  # Commit after each cycle
git_auto_push = false  # Don't push (manual control)
```

Commit messages include:
- Cycle number
- Findings created/updated
- Cost
- Duration

Example: `research: Cycle 5 - 7 created, 3 updated | $0.12 | 42s`

## Multi-Tenancy Settings

For SaaS deployments (CLI users can ignore this section).

```toml
[multi_tenancy]
enabled = false
workspace_id = "default"
enforce_isolation = false
```

### Fields

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `enabled` | bool | false | Enable multi-workspace mode |
| `workspace_id` | string | "default" | Workspace identifier |
| `enforce_isolation` | bool | false | Strict workspace boundaries |

**CLI users**: Leave defaults (single workspace mode).

## Complete Example

```toml
# ============================================================
# Market Research Project Configuration
# ============================================================

[project]
name = "Legal Tech SaaS Market Research"
north_star = """
Build a legal tech SaaS product for mid-market general counsels.

Target: Companies with 100-1000 employees
Focus areas:
- Market size and growth (TAM/SAM/SOM)
- Competition landscape (direct + indirect)
- Buyer personas (pain points, budget, decision process)
- Pricing strategies (freemium vs paid, tiers)
- Go-to-market channels

Success criteria:
- Validated market opportunity ($50M+ SAM)
- Identified 3+ differentiation opportunities
- Clear understanding of buyer journey
"""

# ============================================================
# Multi-Agent Setup (Quality + Cost-Effective)
# ============================================================

# Primary: Claude Opus 4.6 (highest quality)
[[agents]]
provider = "anthropic"
model = "claude-opus-4-20251120"
api_key_env = "ANTHROPIC_API_KEY"
timeout = 300
supports_native_search = true
use_subscription = false

# Secondary: Kimi 2.5 (cost-effective, diverse perspective)
[[agents]]
provider = "moonshot"
model = "kimi-2.5"
api_key_env = "MOONSHOT_API_KEY"
timeout = 300

# ============================================================
# Multi-Provider Search (Reliability)
# ============================================================

[search]
use_llm_native_search = true  # Prefer Claude's extended thinking
fallback_enabled = true  # Try next provider on failure

# Primary: Tavily (best for research)
[[search.providers]]
name = "tavily"
api_key_env = "TAVILY_API_KEY"
priority = 1
max_results = 10
enabled = true

# Fallback: Brave (free tier available)
[[search.providers]]
name = "brave"
api_key_env = "BRAVE_API_KEY"
priority = 2
max_results = 8
enabled = true

# Last resort: DuckDuckGo (free)
[[search.providers]]
name = "duckduckgo"
priority = 99
max_results = 10
enabled = true

# ============================================================
# Orchestrator Settings (Tuned for Quality)
# ============================================================

[orchestrator]
max_searches_per_agent = 30  # Thorough research
agent_timeout_seconds = 300
confidence_discount = 0.65  # Slightly skeptical (require more evidence)
consensus_boost = 0.18  # Good reward for agent agreement
similarity_threshold = 0.75  # Standard deduplication

# ============================================================
# Storage & Git Integration
# ============================================================

[storage]
db_path = ".winterfox/graph.db"
raw_output_dir = ".winterfox/raw"
git_auto_commit = true  # Auto-commit for history tracking
git_auto_push = false  # Manual push for review

# ============================================================
# Multi-Tenancy (CLI: keep disabled)
# ============================================================

[multi_tenancy]
enabled = false
workspace_id = "default"
enforce_isolation = false
```

## Validation

Winterfox validates your configuration on load. Common errors:

### "At least one agent required"

```toml
# ❌ Wrong: No agents
[project]
name = "Test"

# ✅ Correct: Add at least one agent
[[agents]]
provider = "anthropic"
model = "claude-opus-4-20251120"
api_key_env = "ANTHROPIC_API_KEY"
```

### "At least one search provider must be enabled"

```toml
# ❌ Wrong: All providers disabled
[[search.providers]]
name = "tavily"
enabled = false

# ✅ Correct: Enable at least one
[[search.providers]]
name = "tavily"
enabled = true
```

### "confidence_discount must be between 0 and 1"

```toml
# ❌ Wrong
[orchestrator]
confidence_discount = 1.5

# ✅ Correct
[orchestrator]
confidence_discount = 0.7
```

## Environment Variables

Required environment variables based on your config:

```bash
# Agents
export ANTHROPIC_API_KEY="sk-ant-..."
export MOONSHOT_API_KEY="sk-..."
export OPENAI_API_KEY="sk-..."
export GOOGLE_API_KEY="..."
export XAI_API_KEY="..."

# Search
export TAVILY_API_KEY="tvly-..."
export BRAVE_API_KEY="..."
export SERPER_API_KEY="..."
export SERPAPI_KEY="..."
```

**Pro Tip**: Add to `~/.zshrc` or `~/.bashrc` for persistence.

---

**See also**:
- [Getting Started Guide](./GETTING_STARTED.md)
- [Example Configurations](../examples/)
