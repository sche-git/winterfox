"""
Winterfox CLI - Command-line interface for autonomous research.

Commands:
- init: Initialize a new research project
- cycle: Run research cycle(s)
- status: Show graph summary
- show: Display specific node
- export: Export knowledge graph
- interactive: Run in interactive mode
"""

import asyncio
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table

from .config import ResearchConfig, create_default_config, load_config
from .utils.logging import setup_logging

app = typer.Typer(
    name="winterfox",
    help="Autonomous research system with multi-agent knowledge compounding",
    no_args_is_help=True,
    add_completion=False,
)

console = Console()


@app.command()
def init(
    project_name: str = typer.Argument(..., help="Project name"),
    path: Path = typer.Option(Path.cwd(), "--path", "-p", help="Project directory"),
    north_star: Optional[str] = typer.Option(
        None, "--north-star", "-n", help="Mission statement (or use interactive prompt)"
    ),
    interactive: bool = typer.Option(True, "--interactive/--no-interactive", help="Interactive setup"),
    skip_context: bool = typer.Option(False, "--skip-context", help="Skip additional context setup"),
) -> None:
    """
    Initialize a new research project.

    Creates:
    - winterfox.toml configuration file
    - .winterfox/graph.db SQLite database
    - .winterfox/raw/ directory for raw outputs

    Example:
        winterfox init "Legal Tech Market Research"
        winterfox init "AI Startups" --north-star "Research AI startup landscape"
    """
    try:
        # Ensure directory exists
        path.mkdir(parents=True, exist_ok=True)

        config_path = path / "winterfox.toml"

        # Check if already initialized
        if config_path.exists():
            console.print(
                f"[yellow]Warning:[/yellow] {config_path} already exists. "
                "Use --force to overwrite (not implemented yet)."
            )
            raise typer.Exit(1)

        # Get north star if not provided
        if not north_star:
            console.print("\n[bold cyan]Project Mission / North Star[/bold cyan]")
            console.print(
                "Describe your research mission in 1-3 sentences. "
                "This guides the research agents.\n"
            )
            north_star = typer.prompt("Mission statement")

        # Interactive setup
        if interactive:
            agents_config = _prompt_agent_setup()
            search_config = _prompt_search_setup()
        else:
            # Default: single Claude agent with Tavily search
            agents_config = [
                {
                    "provider": "anthropic",
                    "model": "claude-opus-4-20251120",
                    "role": "primary",
                }
            ]
            search_config = [{"name": "tavily", "priority": 1}]

        # Create config with selected options
        create_default_config(config_path, project_name, north_star, agents_config, search_config)

        # Create .winterfox/ directory structure
        (path / ".winterfox" / "raw").mkdir(parents=True, exist_ok=True)
        (path / ".winterfox" / "context").mkdir(parents=True, exist_ok=True)

        # Initialize database
        from .graph.store import KnowledgeGraph

        db_path = path / ".winterfox" / "graph.db"
        asyncio.run(_init_database(db_path))

        # Optional: Additional context setup
        search_instructions_path = None
        context_files = []

        if interactive and not skip_context:
            console.print("\n[bold cyan]═══ Additional Research Context (Optional) ═══[/bold cyan]\n")
            console.print("You can provide additional context to guide the research:\n")
            console.print("  • Search instructions: How agents should search and what to prioritize")
            console.print("  • Context documents: Prior research, PDFs, notes, etc.\n")

            add_context = typer.confirm("Would you like to add additional context?", default=False)

            if add_context:
                # Search instructions
                console.print("\n[bold]Search Instructions[/bold]")
                console.print("Provide guidance on how agents should perform research.")
                console.print("Examples: 'Focus on academic papers', 'Prioritize recent news', etc.\n")

                has_instructions = typer.confirm("Add search instructions?", default=False)
                if has_instructions:
                    instructions_source = typer.prompt(
                        "Enter instructions (or file path starting with @)",
                        default=""
                    )

                    if instructions_source:
                        if instructions_source.startswith("@"):
                            # Read from file
                            source_file = Path(instructions_source[1:])
                            if source_file.exists():
                                instructions_content = source_file.read_text(encoding="utf-8")
                            else:
                                console.print(f"[yellow]Warning: File not found: {source_file}[/yellow]")
                                instructions_content = ""
                        else:
                            # Inline instructions
                            instructions_content = instructions_source

                        if instructions_content:
                            search_instructions_path = path / ".winterfox" / "search_instructions.md"
                            search_instructions_path.write_text(instructions_content, encoding="utf-8")
                            console.print(f"[green]✓[/green] Saved to {search_instructions_path.relative_to(path)}")

                # Context documents
                console.print("\n[bold]Context Documents[/bold]")
                console.print("Add prior research, notes, or any relevant documents.")
                console.print("These will be available to agents during research.\n")

                has_docs = typer.confirm("Add context documents?", default=False)
                if has_docs:
                    console.print("\nEnter file paths, one per line (empty line to finish):")
                    while True:
                        doc_path = typer.prompt("Document path", default="", show_default=False)
                        if not doc_path:
                            break

                        source = Path(doc_path)
                        if source.exists():
                            # Copy to .winterfox/context/
                            import shutil
                            dest = path / ".winterfox" / "context" / source.name
                            shutil.copy2(source, dest)
                            context_files.append(f".winterfox/context/{source.name}")
                            console.print(f"[green]✓[/green] Copied {source.name}")
                        else:
                            console.print(f"[yellow]Warning: File not found: {source}[/yellow]")

                if search_instructions_path or context_files:
                    console.print(f"\n[green]✓[/green] Added {len(context_files)} context document(s)")

        # Update config with context paths
        if search_instructions_path or context_files:
            _update_config_with_context(
                config_path,
                search_instructions_path.relative_to(path) if search_instructions_path else None,
                context_files
            )

        # Success message with API key reminders
        api_keys_needed = set()
        for agent in agents_config:
            if agent["provider"] == "anthropic":
                api_keys_needed.add("ANTHROPIC_API_KEY")
            elif agent["provider"] == "moonshot":
                api_keys_needed.add("MOONSHOT_API_KEY")
            elif agent["provider"] == "openai":
                api_keys_needed.add("OPENAI_API_KEY")
            elif agent["provider"] == "google":
                api_keys_needed.add("GOOGLE_API_KEY")
            elif agent["provider"] == "xai":
                api_keys_needed.add("XAI_API_KEY")
            elif agent["provider"] == "openrouter":
                api_keys_needed.add("OPENROUTER_API_KEY")

        for search in search_config:
            if search["name"] == "tavily":
                api_keys_needed.add("TAVILY_API_KEY")
            elif search["name"] == "brave":
                api_keys_needed.add("BRAVE_API_KEY")
            elif search["name"] == "serper":
                api_keys_needed.add("SERPER_API_KEY")
            elif search["name"] == "serpapi":
                api_keys_needed.add("SERPAPI_KEY")

        api_keys_str = "\n".join(f"   - {key}" for key in sorted(api_keys_needed))

        console.print(Panel.fit(
            f"[green]✓[/green] Initialized research project: [bold]{project_name}[/bold]\n\n"
            f"Configuration: {config_path}\n"
            f"Database: {db_path}\n\n"
            "[dim]Next steps:[/dim]\n"
            f"1. Set API keys in environment:\n{api_keys_str}\n\n"
            "2. Run your first cycle: winterfox run",
            title="Project Initialized",
            border_style="green",
        ))

    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1)


def _update_config_with_context(
    config_path: Path,
    search_instructions: Path | None,
    context_files: list[str],
) -> None:
    """
    Update winterfox.toml with context paths.

    Args:
        config_path: Path to winterfox.toml
        search_instructions: Relative path to search instructions file
        context_files: List of relative paths to context files
    """
    # Read current config
    content = config_path.read_text(encoding="utf-8")

    # Find [project] section and add context fields
    lines = content.split("\n")
    project_end = -1

    for i, line in enumerate(lines):
        if line.startswith("[project]"):
            # Find end of [project] section (next section or empty line followed by section)
            for j in range(i + 1, len(lines)):
                if lines[j].startswith("[") and not lines[j].startswith("[project]"):
                    project_end = j
                    break
            break

    if project_end == -1:
        # [project] is last section, append at end
        project_end = len(lines)

    # Insert context fields before next section
    insert_lines = []

    if search_instructions:
        insert_lines.append(f'search_instructions = "{search_instructions}"')

    if context_files:
        files_str = ', '.join(f'"{f}"' for f in context_files)
        insert_lines.append(f'context_files = [{files_str}]')

    if insert_lines:
        # Insert before the next section
        for line in reversed(insert_lines):
            lines.insert(project_end, line)

        # Write back
        config_path.write_text("\n".join(lines), encoding="utf-8")


def _prompt_agent_setup() -> list[dict]:
    """Interactive prompt for agent selection."""
    console.print("\n[bold cyan]═══ LLM Configuration ═══[/bold cyan]\n")

    # Available LLMs with costs
    llm_options = {
        "1": {
            "name": "Claude Opus 4.6 (Anthropic)",
            "provider": "anthropic",
            "model": "claude-opus-4-20251120",
            "cost": "$15 input / $75 output per 1M tokens",
            "supports_native_search": True,
        },
        "2": {
            "name": "Kimi 2.5 (Moonshot AI)",
            "provider": "moonshot",
            "model": "kimi-2.5",
            "cost": "$0.20 per 1M tokens (100x cheaper)",
            "supports_native_search": False,
        },
        "3": {
            "name": "GPT-4o (OpenAI)",
            "provider": "openai",
            "model": "gpt-4o",
            "cost": "$5 input / $15 output per 1M tokens",
            "supports_native_search": False,
        },
        "4": {
            "name": "Gemini 2.0 (Google)",
            "provider": "google",
            "model": "gemini-2.0-flash-exp",
            "cost": "Free tier available, then paid",
            "supports_native_search": True,
        },
        "5": {
            "name": "Grok 2 (xAI)",
            "provider": "xai",
            "model": "grok-2",
            "cost": "Beta pricing varies",
            "supports_native_search": False,
        },
        "6": {
            "name": "OpenRouter (Multiple Models)",
            "provider": "openrouter",
            "model": None,  # Will be selected from API
            "cost": "Varies by model",
            "supports_native_search": False,  # Depends on model
        },
    }

    # Display options
    table = Table(title="Available LLMs", show_header=True, header_style="bold magenta")
    table.add_column("ID", style="cyan", width=4)
    table.add_column("LLM", style="white", width=35)
    table.add_column("Cost", style="yellow", width=40)

    for id, llm in llm_options.items():
        table.add_row(id, llm["name"], llm["cost"])

    console.print(table)

    # Select LLMs for parallel research
    console.print("\n[bold]Select LLMs for parallel research[/bold]")
    console.print("Enter numbers separated by commas (e.g., '1,2' for Claude + Kimi)")
    console.print("Or press Enter for default: Claude Opus 4.6 only\n")

    selection = typer.prompt("Your selection", default="1", show_default=True)

    # Parse selection
    selected_ids = [s.strip() for s in selection.split(",")]
    selected_llms = []

    for id in selected_ids:
        if id in llm_options:
            llm = llm_options[id].copy()

            # Handle OpenRouter - fetch models from API
            if llm["provider"] == "openrouter":
                console.print("\n[bold cyan]OpenRouter selected![/bold cyan]")
                console.print("OpenRouter provides access to many models through one API.")
                console.print("Fetching available models (no API key needed for browsing)...\n")

                try:
                    import asyncio
                    from .agents.adapters.openrouter import fetch_openrouter_models

                    with console.status("[bold green]Fetching models from OpenRouter..."):
                        models = asyncio.run(fetch_openrouter_models())  # No API key needed

                    if not models:
                        console.print("[red]No models available from OpenRouter[/red]")
                        continue

                    # Display models
                    console.print(f"\n[green]✓[/green] Found {len(models)} models\n")

                    # Filter to popular/recommended models for better UX
                    popular_models = [
                        m for m in models
                        if any(keyword in m["id"].lower() for keyword in [
                            "claude", "gpt-4", "gpt-3.5", "gemini", "llama-3",
                            "mixtral", "qwen", "deepseek"
                        ])
                    ]

                    if not popular_models:
                        popular_models = models[:20]  # Fallback to first 20

                    # Create model selection table
                    model_table = Table(title="OpenRouter Models", show_header=True)
                    model_table.add_column("ID", style="cyan", width=4)
                    model_table.add_column("Model", style="white", width=40)
                    model_table.add_column("Context", style="yellow", width=12)
                    model_table.add_column("Cost (1M tokens)", style="green", width=25)

                    model_map = {}
                    for i, model in enumerate(popular_models[:30], 1):  # Show max 30
                        model_id = model["id"]
                        model_name = model.get("name", model_id)
                        context_length = model.get("context_length", "N/A")

                        # Format pricing
                        pricing = model.get("pricing", {})
                        prompt_price = float(pricing.get("prompt", 0)) * 1_000_000
                        completion_price = float(pricing.get("completion", 0)) * 1_000_000
                        price_str = f"${prompt_price:.2f}in/${completion_price:.2f}out"

                        model_table.add_row(
                            str(i),
                            model_name[:38],
                            str(context_length),
                            price_str
                        )
                        model_map[str(i)] = model

                    console.print(model_table)

                    # Let user select model
                    console.print("\n[bold]Select a model[/bold]")
                    console.print("[dim]You'll need to set OPENROUTER_API_KEY env var before running[/dim]\n")
                    model_selection = typer.prompt("Model ID", default="1")

                    if model_selection not in model_map:
                        console.print(f"[yellow]Invalid selection, skipping OpenRouter[/yellow]")
                        continue

                    selected_model = model_map[model_selection]

                    # Update llm config with selected model
                    llm["model"] = selected_model["id"]
                    llm["name"] = f"OpenRouter: {selected_model.get('name', selected_model['id'])}"
                    llm["cost"] = f"${float(selected_model.get('pricing', {}).get('prompt', 0)) * 1_000_000:.2f} input / ${float(selected_model.get('pricing', {}).get('completion', 0)) * 1_000_000:.2f} output per 1M tokens"

                    # Check if model supports native search (Claude, Gemini)
                    model_id_lower = selected_model["id"].lower()
                    llm["supports_native_search"] = any(
                        keyword in model_id_lower for keyword in ["claude", "gemini"]
                    )

                except Exception as e:
                    console.print(f"[red]Failed to fetch OpenRouter models: {e}[/red]")
                    console.print("[yellow]Skipping OpenRouter[/yellow]")
                    continue

            selected_llms.append(llm)
        else:
            console.print(f"[yellow]Warning: Invalid option '{id}', skipping[/yellow]")

    if not selected_llms:
        console.print("[yellow]No valid LLMs selected, using default: Claude Opus 4.6[/yellow]")
        selected_llms = [llm_options["1"]]

    # Select primary LLM (if multiple selected)
    primary_idx = 0
    if len(selected_llms) > 1:
        console.print(f"\n[bold]Select primary LLM for synthesis[/bold]")
        console.print("The primary LLM will review and synthesize findings from all LLMs.\n")

        for i, llm in enumerate(selected_llms, 1):
            console.print(f"{i}. {llm['name']}")

        primary_selection = typer.prompt(
            "\nPrimary LLM",
            default="1",
            show_default=True,
            type=int,
        )

        if 1 <= primary_selection <= len(selected_llms):
            primary_idx = primary_selection - 1
        else:
            console.print(f"[yellow]Invalid selection, using first LLM as primary[/yellow]")
            primary_idx = 0

    # Build agent configs
    agents_config = []
    for i, llm in enumerate(selected_llms):
        role = "primary" if i == primary_idx else "secondary"
        agents_config.append({
            "provider": llm["provider"],
            "model": llm["model"],
            "role": role,
            "supports_native_search": llm["supports_native_search"],
        })

    # Summary
    console.print(f"\n[green]✓[/green] Configured {len(agents_config)} LLM(s):")
    for agent in agents_config:
        role_badge = "[cyan](primary)[/cyan]" if agent["role"] == "primary" else "[dim](secondary)[/dim]"
        console.print(f"  • {agent['model']} {role_badge}")

    return agents_config


def _prompt_search_setup() -> list[dict]:
    """Interactive prompt for search engine selection."""
    console.print("\n[bold cyan]═══ Search Engine Configuration ═══[/bold cyan]\n")

    # Available search engines
    search_options = {
        "1": {
            "name": "Tavily",
            "cost": "$1 per 1000 searches (best for research)",
            "api_key_env": "TAVILY_API_KEY",
        },
        "2": {
            "name": "Brave Search",
            "cost": "Free tier: 2000 queries/month",
            "api_key_env": "BRAVE_API_KEY",
        },
        "3": {
            "name": "Serper (Google)",
            "cost": "$5 per 1000 searches",
            "api_key_env": "SERPER_API_KEY",
        },
        "4": {
            "name": "SerpAPI (Multi-engine)",
            "cost": "$50/month for 5000 searches",
            "api_key_env": "SERPAPI_KEY",
        },
        "5": {
            "name": "DuckDuckGo",
            "cost": "Free (no API key needed)",
            "api_key_env": None,
        },
    }

    # Display options
    table = Table(title="Available Search Engines", show_header=True, header_style="bold magenta")
    table.add_column("ID", style="cyan", width=4)
    table.add_column("Search Engine", style="white", width=25)
    table.add_column("Cost", style="yellow", width=40)

    for id, engine in search_options.items():
        table.add_row(id, engine["name"], engine["cost"])

    console.print(table)

    # Select search engines
    console.print("\n[bold]Select search engines[/bold]")
    console.print("Enter numbers separated by commas (e.g., '1,2' for Tavily + Brave)")
    console.print("Multiple engines will be used with automatic fallback.")
    console.print("Or press Enter for default: Tavily only\n")

    selection = typer.prompt("Your selection", default="1", show_default=True)

    # Parse selection
    selected_ids = [s.strip() for s in selection.split(",")]
    selected_engines = []

    for i, id in enumerate(selected_ids, 1):
        if id in search_options:
            engine = search_options[id].copy()
            engine["priority"] = i  # Priority based on selection order
            selected_engines.append(engine)
        else:
            console.print(f"[yellow]Warning: Invalid option '{id}', skipping[/yellow]")

    if not selected_engines:
        console.print("[yellow]No valid engines selected, using default: Tavily[/yellow]")
        selected_engines = [{"name": "tavily", "priority": 1, "api_key_env": "TAVILY_API_KEY"}]

    # Summary
    console.print(f"\n[green]✓[/green] Configured {len(selected_engines)} search engine(s):")
    for engine in selected_engines:
        priority_badge = f"[cyan](priority {engine['priority']})[/cyan]"
        console.print(f"  • {engine['name']} {priority_badge}")

    # Build search config
    search_config = []
    for engine in selected_engines:
        # Normalize names to match config.SearchProviderConfig
        name_normalized = engine["name"].lower().replace(" ", "").replace("(", "").replace(")", "")
        if name_normalized == "bravesearch":
            name_normalized = "brave"
        elif name_normalized == "serpergoogle":
            name_normalized = "serper"
        elif name_normalized == "serpapimulti-engine":
            name_normalized = "serpapi"

        search_config.append({
            "name": name_normalized,
            "priority": engine["priority"],
        })

    return search_config


async def _init_database(db_path: Path) -> None:
    """Initialize SQLite database."""
    from .graph.store import KnowledgeGraph

    graph = KnowledgeGraph(str(db_path))
    await graph.initialize()
    await graph.close()


@app.command()
def run(
    n: int = typer.Option(1, "--count", "-n", help="Number of cycles to run"),
    focus: Optional[str] = typer.Option(None, "--focus", "-f", help="Specific node ID to research"),
    config: Path = typer.Option(Path("winterfox.toml"), "--config", "-c", help="Config file path"),
    log_level: str = typer.Option("INFO", "--log-level", "-l", help="Log level"),
    no_consensus: bool = typer.Option(False, "--no-consensus", help="Disable multi-agent consensus"),
) -> None:
    """
    Run research cycles.

    A cycle:
    1. Selects a target node (or uses --focus)
    2. Generates research prompts
    3. Dispatches agents to research
    4. Merges findings into knowledge graph
    5. Propagates confidence changes

    Example:
        winterfox run                    # Run 1 cycle
        winterfox run -n 10              # Run 10 cycles
        winterfox run --focus node-123   # Research specific node
    """
    setup_logging(level=log_level)

    try:
        asyncio.run(_run_cycles(config, n, focus, not no_consensus))
    except KeyboardInterrupt:
        console.print("\n[yellow]Interrupted by user[/yellow]")
        raise typer.Exit(0)
    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1)


async def _run_cycles(
    config_path: Path,
    n: int,
    focus_node_id: Optional[str],
    use_consensus: bool,
) -> None:
    """Run research cycles."""
    # Load configuration
    config = load_config(config_path)

    # Initialize graph
    from .graph.store import KnowledgeGraph

    graph = KnowledgeGraph(str(config.storage.db_path), workspace_id=config.multi_tenancy.workspace_id)
    await graph.initialize()

    # Check if graph is empty
    nodes = await graph.get_all_active_nodes()
    if not nodes:
        console.print("[yellow]Graph is empty. Creating initial research question...[/yellow]\n")

        north_star = config.get_north_star(config_path.parent)
        initial_claim = typer.prompt("What is your initial research question?")

        await graph.add_node(
            claim=initial_claim,
            confidence=0.0,
            importance=1.0,
            depth=0,
            created_by_cycle=0,
        )

    # Initialize agents
    from .agents.adapters.anthropic import AnthropicAdapter
    from .agents.adapters.base import AgentAuthenticationError
    from .agents.adapters.kimi import KimiAdapter
    from .agents.adapters.openrouter import OpenRouterAdapter
    from .agents.pool import AgentPool

    api_keys = config.get_agent_api_keys()

    adapters = []
    primary_provider = None
    for agent_config in config.agents:
        key = f"{agent_config.provider}:{agent_config.model}"
        api_key = api_keys.get(key, "")

        if agent_config.provider == "anthropic":
            adapter = AnthropicAdapter(
                model=agent_config.model,
                api_key=api_key if not agent_config.use_subscription else None,
                use_subscription=agent_config.use_subscription,
                timeout=agent_config.timeout_seconds,
            )
        elif agent_config.provider == "moonshot":
            adapter = KimiAdapter(
                model=agent_config.model,
                api_key=api_key,
                timeout=agent_config.timeout_seconds,
            )
        elif agent_config.provider == "openrouter":
            adapter = OpenRouterAdapter(
                model=agent_config.model,
                api_key=api_key,
                timeout=agent_config.timeout_seconds,
                supports_native_search=agent_config.supports_native_search,
            )
        else:
            console.print(f"[yellow]Warning: Unsupported provider {agent_config.provider}, skipping[/yellow]")
            continue

        if agent_config.role == "primary":
            primary_provider = agent_config.provider
        adapters.append(adapter)

    # Pre-flight: verify all agent API keys before starting research
    verified_adapters = []
    for adapter in adapters:
        try:
            await adapter.verify()
            verified_adapters.append(adapter)
            console.print(f"[green]✓[/green] {adapter.name}: API key verified")
        except AgentAuthenticationError as e:
            console.print(f"[red]✗[/red] {adapter.name}: {e}")
        except Exception as e:
            console.print(f"[yellow]![/yellow] {adapter.name}: verification failed ({e}), skipping")

    if not verified_adapters:
        console.print("\n[red]Error: No agents passed API key verification. Check your API keys.[/red]")
        await graph.close()
        raise typer.Exit(1)

    if len(verified_adapters) < len(adapters):
        console.print(
            f"\n[yellow]Continuing with {len(verified_adapters)}/{len(adapters)} agent(s)[/yellow]"
        )

    # Determine primary agent index among verified adapters
    primary_agent_index = 0
    if primary_provider:
        for i, adapter in enumerate(verified_adapters):
            if primary_provider in adapter.name.lower():
                primary_agent_index = i
                break

    agent_pool = AgentPool(verified_adapters, primary_agent_index=primary_agent_index)

    # Initialize search providers
    from .agents.tools.search import configure_search
    from .agents.tools.search.brave import BraveSearchProvider
    from .agents.tools.search.tavily import TavilySearchProvider
    from .agents.tools.search.serper import SerperSearchProvider

    search_api_keys = config.get_search_api_keys()
    search_providers = []

    provider_classes = {
        "tavily": TavilySearchProvider,
        "brave": BraveSearchProvider,
        "serper": SerperSearchProvider,
    }

    for provider_config in sorted(config.search.providers, key=lambda p: p.priority):
        if not provider_config.enabled:
            continue
        api_key = search_api_keys.get(provider_config.name)
        if api_key is None and provider_config.name != "duckduckgo":
            console.print(
                f"[yellow]Warning: No API key for {provider_config.name}, skipping[/yellow]"
            )
            continue
        cls = provider_classes.get(provider_config.name)
        if cls is None:
            console.print(
                f"[yellow]Warning: Unsupported search provider {provider_config.name}, skipping[/yellow]"
            )
            continue
        search_providers.append(cls(api_key=api_key))

    if not search_providers:
        console.print("[red]Error: No search providers configured. Check API keys.[/red]")
        raise typer.Exit(1)

    configure_search(search_providers, fallback_enabled=config.search.fallback_enabled)

    # Initialize tools
    from .agents.tools import get_research_tools

    tools = get_research_tools(graph)

    # Initialize orchestrator
    from .orchestrator import Orchestrator

    north_star = config.get_north_star(config_path.parent)
    search_instructions = config.get_search_instructions(config_path.parent)
    context_files = config.get_context_files_content(config_path.parent)

    orchestrator = Orchestrator(
        graph=graph,
        agent_pool=agent_pool,
        north_star=north_star,
        tools=tools,
        max_searches_per_cycle=config.orchestrator.max_searches_per_agent,
        confidence_discount=config.orchestrator.confidence_discount,
        consensus_boost=config.orchestrator.consensus_boost,
        search_instructions=search_instructions,
        context_files=context_files,
    )

    # Run cycles with progress
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        task = progress.add_task(f"Running {n} cycle{'s' if n != 1 else ''}...", total=n)

        for i in range(n):
            progress.update(task, description=f"Cycle {i + 1}/{n}")

            result = await orchestrator.run_cycle(
                target_node_id=focus_node_id,
                use_consensus=use_consensus,
            )

            # Show cycle result
            if result.success:
                console.print(
                    f"[green]✓[/green] Cycle {result.cycle_id}: "
                    f"{result.findings_created} created, {result.findings_updated} updated | "
                    f"${result.total_cost_usd:.4f} | {result.duration_seconds:.1f}s"
                )
            else:
                console.print(
                    f"[red]✗[/red] Cycle {result.cycle_id} failed: {result.error_message}"
                )

            progress.advance(task)

    # Show summary
    console.print(f"\n{orchestrator.get_summary()}")

    await graph.close()


@app.command()
def status(
    config: Path = typer.Option(Path("winterfox.toml"), "--config", "-c", help="Config file path"),
    max_depth: int = typer.Option(3, "--depth", "-d", help="Maximum tree depth"),
) -> None:
    """
    Show research progress and graph summary.

    Displays:
    - Total nodes and average confidence
    - Tree structure with confidence indicators
    - Low confidence nodes needing attention

    Example:
        winterfox status
        winterfox status --depth 5
    """
    try:
        asyncio.run(_show_status(config, max_depth))
    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1)


async def _show_status(config_path: Path, max_depth: int) -> None:
    """Show graph status."""
    # Load config
    config = load_config(config_path)

    # Load graph
    from .graph.store import KnowledgeGraph
    from .graph.views import render_summary_view

    graph = KnowledgeGraph(str(config.storage.db_path), workspace_id=config.multi_tenancy.workspace_id)
    await graph.initialize()

    # Get stats
    nodes = await graph.get_all_active_nodes()
    if not nodes:
        console.print("[yellow]Graph is empty. Run 'winterfox run' to start research.[/yellow]")
        await graph.close()
        return

    total = len(nodes)
    avg_confidence = sum(n.confidence for n in nodes) / total
    low_confidence = sum(1 for n in nodes if n.confidence < 0.5)

    # Header
    console.print(Panel.fit(
        f"[bold]{config.project.name}[/bold]\n\n"
        f"Total nodes: {total}\n"
        f"Average confidence: [{'green' if avg_confidence >= 0.7 else 'yellow'}]{avg_confidence:.0%}[/]\n"
        f"Low confidence: {low_confidence}",
        title="Research Status",
        border_style="blue",
    ))

    # Tree view
    console.print("\n[bold]Knowledge Graph:[/bold]\n")
    summary = await render_summary_view(graph, max_depth=max_depth)
    console.print(summary)

    await graph.close()


@app.command()
def show(
    node_id: str = typer.Argument(..., help="Node ID to display"),
    config: Path = typer.Option(Path("winterfox.toml"), "--config", "-c", help="Config file path"),
    depth: int = typer.Option(2, "--depth", "-d", help="Children depth to show"),
) -> None:
    """
    Show detailed view of a specific node.

    Displays:
    - Full claim text
    - Confidence and importance
    - All evidence with sources
    - Children nodes

    Example:
        winterfox show abc123
        winterfox show abc123 --depth 3
    """
    try:
        asyncio.run(_show_node(config, node_id, depth))
    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1)


async def _show_node(config_path: Path, node_id: str, depth: int) -> None:
    """Show node details."""
    # Load config
    config = load_config(config_path)

    # Load graph
    from .graph.store import KnowledgeGraph
    from .graph.views import render_focused_view

    graph = KnowledgeGraph(str(config.storage.db_path), workspace_id=config.multi_tenancy.workspace_id)
    await graph.initialize()

    # Get node
    node = await graph.get_node(node_id)
    if not node:
        console.print(f"[red]Node not found:[/red] {node_id}")
        await graph.close()
        return

    # Render focused view
    view = await render_focused_view(graph, node_id, max_depth=depth)
    console.print(view)

    await graph.close()


@app.command()
def export(
    output: Path = typer.Argument(..., help="Output file path"),
    format: str = typer.Option("markdown", "--format", "-f", help="Format: markdown or json"),
    config: Path = typer.Option(Path("winterfox.toml"), "--config", "-c", help="Config file path"),
    no_evidence: bool = typer.Option(False, "--no-evidence", help="Exclude evidence citations"),
) -> None:
    """
    Export knowledge graph.

    Formats:
    - markdown: Human-readable nested markdown with citations
    - json: Machine-readable JSON with full graph structure

    Example:
        winterfox export report.md
        winterfox export data.json --format json
        winterfox export brief.md --no-evidence
    """
    try:
        asyncio.run(_export_graph(config, output, format, not no_evidence))
        console.print(f"[green]✓[/green] Exported to {output}")
    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1)


async def _export_graph(
    config_path: Path,
    output: Path,
    format: str,
    include_evidence: bool,
) -> None:
    """Export knowledge graph."""
    # Load config
    config = load_config(config_path)

    # Load graph
    from .graph.store import KnowledgeGraph

    graph = KnowledgeGraph(str(config.storage.db_path), workspace_id=config.multi_tenancy.workspace_id)
    await graph.initialize()

    # Export
    if format == "markdown":
        from .export import export_to_markdown

        await export_to_markdown(
            graph,
            str(output),
            title=f"{config.project.name} - Knowledge Graph",
            include_evidence=include_evidence,
        )
    elif format == "json":
        from .export import export_to_json

        await export_to_json(graph, str(output))
    else:
        raise ValueError(f"Unsupported format: {format}")

    await graph.close()


@app.command()
def interactive(
    config: Path = typer.Option(Path("winterfox.toml"), "--config", "-c", help="Config file path"),
    log_level: str = typer.Option("INFO", "--log-level", "-l", help="Log level"),
) -> None:
    """
    Run in interactive mode with user steering between cycles.

    After each cycle:
    - Shows results and updated graph
    - Asks if you want to continue
    - Optionally lets you specify focus area

    Example:
        winterfox interactive
    """
    setup_logging(level=log_level)

    try:
        asyncio.run(_interactive_mode(config))
    except KeyboardInterrupt:
        console.print("\n[yellow]Exiting interactive mode[/yellow]")
        raise typer.Exit(0)
    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1)


async def _interactive_mode(config_path: Path) -> None:
    """Run interactive research mode."""
    console.print(Panel.fit(
        "[bold]Interactive Research Mode[/bold]\n\n"
        "I'll run research cycles and ask you for guidance after each one.\n"
        "You can continue, focus on specific areas, or stop anytime.",
        border_style="blue",
    ))

    while True:
        # Run single cycle
        await _run_cycles(config_path, n=1, focus_node_id=None, use_consensus=True)

        # Show current status
        await _show_status(config_path, max_depth=2)

        # Ask for next action
        console.print("\n[bold]What next?[/bold]")
        action = typer.prompt(
            "Continue (c), Focus on area (f), Show node (s), Export (e), or Quit (q)",
            default="c",
        )

        if action.lower() == "q":
            console.print("[green]Research session complete![/green]")
            break
        elif action.lower() == "f":
            focus_area = typer.prompt("Enter node ID to focus on")
            await _run_cycles(config_path, n=1, focus_node_id=focus_area, use_consensus=True)
        elif action.lower() == "s":
            node_id = typer.prompt("Enter node ID to show")
            await _show_node(config_path, node_id, depth=2)
        elif action.lower() == "e":
            output_path = Path(typer.prompt("Output file path", default="export.md"))
            await _export_graph(config_path, output_path, "markdown", True)
            console.print(f"[green]✓[/green] Exported to {output_path}")
        # else continue (default)


def main() -> None:
    """CLI entry point."""
    app()


if __name__ == "__main__":
    main()
