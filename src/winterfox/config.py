"""
Configuration loading and validation for winterfox.

Loads research.toml files and validates settings using Pydantic.
"""

import os
from pathlib import Path
from typing import Literal

try:
    import tomllib  # Python 3.11+
except ImportError:
    import tomli as tomllib  # type: ignore

from pydantic import BaseModel, Field, field_validator


class AgentConfig(BaseModel):
    """Configuration for a single agent."""

    provider: str  # "anthropic", "moonshot", "openai", "xai", "google"
    model: str
    api_key_env: str
    timeout_seconds: int = 300
    max_retries: int = 3
    supports_native_search: bool = False
    use_subscription: bool = False  # For Claude: use subscription auth


class SearchProviderConfig(BaseModel):
    """Configuration for a search provider."""

    name: Literal["tavily", "brave", "serper", "serpapi", "duckduckgo"]
    api_key_env: str | None = None  # DuckDuckGo doesn't need API key
    priority: int = 1  # Higher priority = tried first
    max_results: int = 10
    enabled: bool = True


class SearchConfig(BaseModel):
    """Multi-provider search configuration."""

    providers: list[SearchProviderConfig] = Field(
        default_factory=lambda: [
            SearchProviderConfig(name="tavily", api_key_env="TAVILY_API_KEY")
        ]
    )
    fallback_enabled: bool = True
    use_llm_native_search: bool = True

    @field_validator("providers")
    @classmethod
    def validate_at_least_one_provider(cls, v: list[SearchProviderConfig]) -> list[SearchProviderConfig]:
        """Ensure at least one provider is enabled."""
        if not v or all(not p.enabled for p in v):
            raise ValueError("At least one search provider must be enabled")
        return v


class OrchestratorConfig(BaseModel):
    """Orchestrator configuration."""

    max_searches_per_agent: int = 25
    agent_timeout_seconds: int = 300
    confidence_discount: float = Field(default=0.7, ge=0.0, le=1.0)
    consensus_boost: float = Field(default=0.15, ge=0.0, le=0.5)
    similarity_threshold: float = Field(default=0.75, ge=0.0, le=1.0)


class StorageConfig(BaseModel):
    """Storage configuration."""

    db_path: Path = Path("research.db")
    raw_output_dir: Path = Path("research/raw")
    git_auto_commit: bool = True
    git_auto_push: bool = False


class MultiTenancyConfig(BaseModel):
    """Multi-tenancy settings (for SaaS deployment)."""

    enabled: bool = False  # CLI mode: single workspace
    workspace_id: str = "default"
    enforce_isolation: bool = False


class ProjectConfig(BaseModel):
    """Project metadata."""

    name: str
    north_star: str | Path  # Can be inline string or path to .md file


class ResearchConfig(BaseModel):
    """Complete research project configuration."""

    project: ProjectConfig
    agents: list[AgentConfig]
    search: SearchConfig = Field(default_factory=SearchConfig)
    orchestrator: OrchestratorConfig = Field(default_factory=OrchestratorConfig)
    storage: StorageConfig = Field(default_factory=StorageConfig)
    multi_tenancy: MultiTenancyConfig = Field(default_factory=MultiTenancyConfig)

    @field_validator("agents")
    @classmethod
    def validate_at_least_one_agent(cls, v: list[AgentConfig]) -> list[AgentConfig]:
        """Ensure at least one agent is configured."""
        if len(v) == 0:
            raise ValueError("At least one agent must be configured")
        return v

    def get_north_star(self, base_path: Path | None = None) -> str:
        """
        Get north star content.

        Args:
            base_path: Base directory for resolving relative paths

        Returns:
            North star content as string
        """
        north_star = self.project.north_star

        # If it's already a string (inline), return it
        if isinstance(north_star, str) and not north_star.endswith(".md"):
            return north_star

        # Otherwise, treat as file path
        path = Path(north_star)
        if base_path and not path.is_absolute():
            path = base_path / path

        if not path.exists():
            raise FileNotFoundError(f"North star file not found: {path}")

        return path.read_text(encoding="utf-8")

    def get_agent_api_keys(self) -> dict[str, str]:
        """
        Get API keys from environment variables.

        Returns:
            Dict mapping agent provider to API key

        Raises:
            ValueError: If required API key is missing
        """
        api_keys = {}

        for agent in self.agents:
            if agent.use_subscription:
                # Subscription mode doesn't need API key
                api_keys[f"{agent.provider}:{agent.model}"] = "subscription"
                continue

            # Get API key from environment
            api_key = os.environ.get(agent.api_key_env)
            if not api_key:
                raise ValueError(
                    f"API key not found in environment: {agent.api_key_env} "
                    f"(required for {agent.provider}:{agent.model})"
                )

            api_keys[f"{agent.provider}:{agent.model}"] = api_key

        return api_keys

    def get_search_api_keys(self) -> dict[str, str | None]:
        """
        Get search provider API keys from environment.

        Returns:
            Dict mapping provider name to API key (None for providers that don't need keys)
        """
        api_keys = {}

        for provider in self.search.providers:
            if not provider.enabled:
                continue

            if provider.api_key_env is None:
                # Provider doesn't need API key (e.g., DuckDuckGo)
                api_keys[provider.name] = None
                continue

            # Get API key from environment (don't fail if missing, let SearchManager handle it)
            api_key = os.environ.get(provider.api_key_env)
            api_keys[provider.name] = api_key

        return api_keys


def load_config(config_path: Path) -> ResearchConfig:
    """
    Load research configuration from TOML file.

    Args:
        config_path: Path to research.toml

    Returns:
        Validated ResearchConfig

    Raises:
        FileNotFoundError: If config file doesn't exist
        ValueError: If config is invalid
    """
    if not config_path.exists():
        raise FileNotFoundError(f"Configuration file not found: {config_path}")

    # Load TOML
    with open(config_path, "rb") as f:
        config_data = tomllib.load(f)

    # Validate with Pydantic
    try:
        config = ResearchConfig(**config_data)
    except Exception as e:
        raise ValueError(f"Invalid configuration: {e}") from e

    return config


def create_default_config(output_path: Path, project_name: str, north_star: str) -> None:
    """
    Create a default research.toml configuration file.

    Args:
        output_path: Where to write research.toml
        project_name: Project name
        north_star: North star mission statement
    """
    template = f'''[project]
name = "{project_name}"
north_star = """
{north_star}
"""

# Primary research agent: Claude Opus 4.6
[[agents]]
provider = "anthropic"
model = "claude-opus-4-20251120"
api_key_env = "ANTHROPIC_API_KEY"
supports_native_search = true
use_subscription = false  # Set to true if using Anthropic Console subscription

# Secondary agent: Kimi 2.5 (uncomment to enable multi-agent consensus)
# [[agents]]
# provider = "moonshot"
# model = "kimi-2.5"
# api_key_env = "MOONSHOT_API_KEY"
# supports_native_search = false

[search]
use_llm_native_search = true
fallback_enabled = true

# Primary search provider: Tavily
[[search.providers]]
name = "tavily"
api_key_env = "TAVILY_API_KEY"
priority = 1
max_results = 10
enabled = true

# Fallback: Brave Search (uncomment to enable)
# [[search.providers]]
# name = "brave"
# api_key_env = "BRAVE_API_KEY"
# priority = 2
# max_results = 8
# enabled = false

[orchestrator]
max_searches_per_agent = 25
agent_timeout_seconds = 300
confidence_discount = 0.7
consensus_boost = 0.15
similarity_threshold = 0.75

[storage]
db_path = "research.db"
raw_output_dir = "research/raw"
git_auto_commit = true
git_auto_push = false

[multi_tenancy]
enabled = false
workspace_id = "default"
'''

    output_path.write_text(template, encoding="utf-8")
