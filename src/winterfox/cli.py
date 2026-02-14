"""
Winterfox CLI - Command-line interface for autonomous research.

Commands:
- init: Initialize a new research project
- run: Run research cycle(s)
- report: Generate narrative research report from knowledge graph
- status: Show graph summary
- show: Display specific node
- export: Export knowledge graph
- cycle list: List and filter past cycles
- cycle view: View detailed cycle output
- cycle export: Export multiple cycles to report
- cycle remove: Delete a cycle by ID
- interactive: Run in interactive mode
- serve: Launch web dashboard
"""

import asyncio
from pathlib import Path
from typing import Any, Optional

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

cycle_app = typer.Typer(
    name="cycle",
    help="Manage research cycles (list, view, export, remove)",
    no_args_is_help=True,
)
app.add_typer(cycle_app)


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
            lead_agent_config, research_agents_config = _prompt_agent_setup()
            search_config = _prompt_search_setup()
        else:
            # Default: single Claude agent for both Lead and Research
            lead_agent_config = {
                "provider": "anthropic",
                "model": "claude-opus-4-20251120",
                "supports_native_search": True,
            }
            research_agents_config = [
                {
                    "provider": "anthropic",
                    "model": "claude-opus-4-20251120",
                    "supports_native_search": True,
                }
            ]
            search_config = [{"name": "tavily", "priority": 1}]

        # Create config with selected options
        create_default_config(
            config_path,
            project_name,
            north_star,
            lead_agent_config,
            research_agents_config,
            search_config
        )

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

        # Add Lead agent API key
        if lead_agent_config["provider"] == "anthropic":
            api_keys_needed.add("ANTHROPIC_API_KEY")
        elif lead_agent_config["provider"] == "moonshot":
            api_keys_needed.add("MOONSHOT_API_KEY")
        elif lead_agent_config["provider"] == "openai":
            api_keys_needed.add("OPENAI_API_KEY")
        elif lead_agent_config["provider"] == "google":
            api_keys_needed.add("GOOGLE_API_KEY")
        elif lead_agent_config["provider"] == "xai":
            api_keys_needed.add("XAI_API_KEY")
        elif lead_agent_config["provider"] == "openrouter":
            api_keys_needed.add("OPENROUTER_API_KEY")

        # Add Research agent API keys
        for agent in research_agents_config:
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


def _prompt_agent_setup() -> tuple[dict, list[dict]]:
    """
    Interactive prompt for agent selection.

    Returns:
        (lead_agent_config, research_agents_config)
    """
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

    # Display options table (shared for both Lead and Research)
    def show_llm_table():
        table = Table(title="Available LLMs", show_header=True, header_style="bold magenta")
        table.add_column("ID", style="cyan", width=4)
        table.add_column("LLM", style="white", width=35)
        table.add_column("Cost", style="yellow", width=40)

        for id, llm in llm_options.items():
            table.add_row(id, llm["name"], llm["cost"])

        console.print(table)

    # ═══ SECTION 1: Lead LLM Selection ═══
    console.print("\n[bold cyan]═══ Lead LLM Configuration ═══[/bold cyan]\n")
    console.print("The Lead LLM orchestrates the entire research cycle:")
    console.print("  • Selects which direction to pursue next")
    console.print("  • Dispatches research agents for parallel investigation")
    console.print("  • Synthesizes raw outputs into strategic directions")
    console.print("  • Recommended: Claude Opus (best strategic reasoning)\n")

    show_llm_table()

    console.print("\n[bold]Select Lead LLM (single selection)[/bold]")
    console.print("The Lead LLM should have strong reasoning capabilities.\n")

    lead_selection = typer.prompt("Lead LLM ID", default="1", show_default=True)

    # Validate and process Lead LLM selection
    if lead_selection not in llm_options:
        console.print("[yellow]Invalid selection, using default: Claude Opus 4.6[/yellow]")
        lead_selection = "1"

    lead_llm = llm_options[lead_selection].copy()

    # Handle OpenRouter for Lead LLM if selected
    if lead_llm["provider"] == "openrouter":
        lead_llm = _handle_openrouter_selection(lead_llm, console, "Lead LLM")
        if lead_llm is None:
            console.print("[yellow]Falling back to Claude Opus 4.6 for Lead LLM[/yellow]")
            lead_llm = llm_options["1"].copy()

    # Build Lead agent config (no role field)
    lead_agent_config = {
        "provider": lead_llm["provider"],
        "model": lead_llm["model"],
        "supports_native_search": lead_llm["supports_native_search"],
    }

    console.print(f"\n[green]✓[/green] Lead LLM configured: {lead_llm['name']}\n")

    # ═══ SECTION 2: Research Agent Selection ═══
    console.print("\n[bold cyan]═══ Research Agent Configuration ═══[/bold cyan]\n")
    console.print("Research agents perform parallel investigation:")
    console.print("  • Multiple agents = diverse perspectives + consensus")
    console.print("  • Single agent = faster and cheaper")
    console.print("  • Can use same LLM as Lead (overlap allowed)\n")

    show_llm_table()

    console.print("\n[bold]Select Research LLMs (comma-separated)[/bold]")
    console.print("Examples: '1' for Claude only, '1,2' for Claude + Kimi")
    console.print("You can include the same LLM as your Lead agent.\n")

    research_selection = typer.prompt("Research LLM IDs", default="1,2", show_default=True)

    # Parse research agent selections
    research_ids = [s.strip() for s in research_selection.split(",")]
    research_llms = []

    for id in research_ids:
        if id in llm_options:
            llm = llm_options[id].copy()

            # Handle OpenRouter if selected
            if llm["provider"] == "openrouter":
                llm = _handle_openrouter_selection(llm, console, f"Research Agent {len(research_llms) + 1}")
                if llm is None:
                    console.print(f"[yellow]Skipping OpenRouter agent[/yellow]")
                    continue

            research_llms.append(llm)
        else:
            console.print(f"[yellow]Warning: Invalid option '{id}', skipping[/yellow]")

    if not research_llms:
        console.print("[yellow]No valid Research LLMs selected, using default: Claude Opus 4.6[/yellow]")
        research_llms = [llm_options["1"].copy()]

    # Build research agent configs (no role field)
    research_agents_config = []
    for llm in research_llms:
        research_agents_config.append({
            "provider": llm["provider"],
            "model": llm["model"],
            "supports_native_search": llm["supports_native_search"],
        })

    # Summary
    console.print(f"\n[green]✓[/green] Configured {len(research_agents_config)} Research agent(s):")
    for agent in research_agents_config:
        console.print(f"  • {agent['model']}")

    return lead_agent_config, research_agents_config


def _handle_openrouter_selection(llm: dict, console: Console, label: str) -> dict | None:
    """
    Handle OpenRouter model selection with API fetching.

    Returns:
        Updated llm config dict, or None if selection failed
    """
    console.print(f"\n[bold cyan]OpenRouter selected for {label}![/bold cyan]")
    console.print("OpenRouter provides access to many models through one API.")
    console.print("Fetching available models (no API key needed for browsing)...\n")

    try:
        import asyncio
        from .agents.adapters.openrouter import fetch_openrouter_models

        with console.status("[bold green]Fetching models from OpenRouter..."):
            models = asyncio.run(fetch_openrouter_models())  # No API key needed

        if not models:
            console.print("[red]No models available from OpenRouter[/red]")
            return None

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
        console.print(f"\n[bold]Select a model for {label}[/bold]")
        console.print("[dim]You'll need to set OPENROUTER_API_KEY env var before running[/dim]\n")
        model_selection = typer.prompt("Model ID", default="1")

        if model_selection not in model_map:
            console.print(f"[yellow]Invalid selection[/yellow]")
            return None

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

        return llm

    except Exception as e:
        console.print(f"[red]Failed to fetch OpenRouter models: {e}[/red]")
        return None


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


def _derive_initial_direction_claim(north_star: str) -> str:
    """Derive an initial seed direction from North Star text."""
    lines = [line.strip() for line in north_star.splitlines() if line.strip()]
    seed = lines[0] if lines else north_star.strip()
    if not seed:
        return "Explore the project's highest-value direction."
    if len(seed) > 220:
        seed = seed[:220].rstrip() + "..."
    return f"Start with this mission direction: {seed}"


@app.command()
def run(
    n: int = typer.Option(1, "--count", "-n", help="Number of cycles to run"),
    focus: Optional[str] = typer.Option(None, "--focus", "-f", help="Specific node ID to research"),
    no_consensus: bool = typer.Option(
        False,
        "--no-consensus",
        help="Deprecated. Consensus mode is always enabled in Lead LLM flow.",
    ),
    config: Path = typer.Option(Path("winterfox.toml"), "--config", "-c", help="Config file path"),
    log_level: str = typer.Option("INFO", "--log-level", "-l", help="Log level"),
    report: bool = typer.Option(False, "--report", help="Generate a report after cycles complete"),
) -> None:
    """
    Run N research cycles with Lead LLM architecture.
    Run research cycles.

    A cycle:
    1. Selects a target node (or uses --focus)
    2. Generates research prompts
    3. Dispatches agents to research
    4. Synthesizes and merges new directions into knowledge graph
    5. Propagates confidence changes

    Example:
        winterfox run                    # Run 1 cycle
        winterfox run -n 10              # Run 10 cycles
        winterfox run --focus node-123   # Research specific node
        winterfox run -n 5 --report      # Run 5 cycles, then generate report
    """
    setup_logging(level=log_level)

    try:
        asyncio.run(_run_cycles(config, n, focus, not no_consensus, report))
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
    generate_report: bool = False,
) -> None:
    """Run research cycles."""
    if not use_consensus:
        console.print(
            "[yellow]Warning:[/yellow] --no-consensus is deprecated and ignored."
        )

    # Load configuration
    config = load_config(config_path)

    # Initialize graph
    from .graph.store import KnowledgeGraph

    graph = KnowledgeGraph(str(config.storage.db_path), workspace_id=config.multi_tenancy.workspace_id)
    await graph.initialize()

    # Check if graph is empty
    nodes = await graph.get_all_active_nodes()
    if not nodes:
        console.print(
            "[yellow]Graph is empty. Bootstrapping initial direction from North Star...[/yellow]\n"
        )
        north_star = config.get_north_star(config_path.parent)
        initial_claim = _derive_initial_direction_claim(north_star)

        await graph.add_node(
            claim=initial_claim,
            confidence=0.0,
            importance=1.0,
            depth=0,
            created_by_cycle=0,
            node_type="direction",
        )

    # Initialize agents
    from .agents.adapters.anthropic import AnthropicAdapter
    from .agents.adapters.base import AgentAuthenticationError
    from .agents.adapters.kimi import KimiAdapter
    from .agents.adapters.openrouter import OpenRouterAdapter

    api_keys = config.get_agent_api_keys()

    def create_adapter(agent_config, api_keys_dict):
        """Helper function to create an adapter from agent config."""
        key = f"{agent_config.provider}:{agent_config.model}"
        api_key = api_keys_dict.get(key, "")

        if agent_config.provider == "anthropic":
            return AnthropicAdapter(
                model=agent_config.model,
                api_key=api_key if not agent_config.use_subscription else None,
                use_subscription=agent_config.use_subscription,
                timeout=agent_config.timeout_seconds,
            )
        elif agent_config.provider == "moonshot":
            return KimiAdapter(
                model=agent_config.model,
                api_key=api_key,
                timeout=agent_config.timeout_seconds,
            )
        elif agent_config.provider == "openrouter":
            return OpenRouterAdapter(
                model=agent_config.model,
                api_key=api_key,
                timeout=agent_config.timeout_seconds,
                supports_native_search=agent_config.supports_native_search,
            )
        else:
            raise ValueError(f"Unsupported provider: {agent_config.provider}")

    # Create Lead agent adapter
    try:
        lead_adapter = create_adapter(config.lead_agent, api_keys)
    except ValueError as e:
        console.print(f"[red]Error creating Lead agent: {e}[/red]")
        await graph.close()
        raise typer.Exit(1)

    # Create Research agent adapters
    research_adapters = []
    for agent_config in config.agents:
        try:
            adapter = create_adapter(agent_config, api_keys)
            research_adapters.append(adapter)
        except ValueError as e:
            console.print(f"[yellow]Warning: {e}, skipping research agent[/yellow]")
            continue

    # Pre-flight: verify all agent API keys before starting research
    all_adapters = [lead_adapter] + research_adapters
    for adapter in all_adapters:
        try:
            await adapter.verify()
            console.print(f"[green]✓[/green] {adapter.name}: API key verified")
        except AgentAuthenticationError as e:
            console.print(f"[red]✗[/red] {adapter.name}: {e}")
            await graph.close()
            raise typer.Exit(1)
        except Exception as e:
            console.print(f"[red]✗[/red] {adapter.name}: verification failed ({e})")
            await graph.close()
            raise typer.Exit(1)

    # Create LeadLLM instance
    from .orchestrator.lead import LeadLLM

    lead_llm = LeadLLM(
        adapter=lead_adapter,
        graph=graph,
        north_star=config.get_north_star(config_path.parent),
        report_content=None,  # Will be generated on first report interval
    )

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

    raw_output_dir = config_path.parent / config.storage.raw_output_dir

    orchestrator = Orchestrator(
        graph=graph,
        lead_llm=lead_llm,
        research_agents=research_adapters,
        north_star=north_star,
        tools=tools,
        max_searches_per_cycle=config.orchestrator.max_searches_per_agent,
        report_interval=config.orchestrator.report_interval,
        search_instructions=search_instructions,
        context_files=context_files,
        raw_output_dir=raw_output_dir,
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
            )

            # Show cycle result
            if result.success:
                console.print(
                    f"\n[green]✓[/green] Cycle {result.cycle_id}: "
                    f"{result.directions_created} created, {result.directions_updated} updated | "
                    f"${result.total_cost_usd:.4f} | {result.duration_seconds:.1f}s"
                )

                # Show concise per-agent stats (raw-output architecture)
                for output in result.agent_outputs:
                    console.print(
                        f"  [bold cyan]{output.agent_name}[/bold cyan]: "
                        f"{len(output.searches_performed)} searches | "
                        f"${output.cost_usd:.4f} | {output.duration_seconds:.1f}s"
                    )
            else:
                console.print(
                    f"\n[red]✗[/red] Cycle {result.cycle_id} failed: {result.error_message}"
                )

            progress.advance(task)

    # Show graph state
    console.print(f"\n{orchestrator.get_summary()}")

    from .graph.views import render_summary_view

    console.print("[bold]Knowledge Graph:[/bold]\n")
    summary = await render_summary_view(graph, max_depth=3)
    console.print(summary)

    # Generate report if requested
    if generate_report:
        north_star = config.get_north_star(config_path.parent)
        await _generate_and_save_report(
            graph,
            lead_adapter,
            north_star,
            config_path,
        )

    await graph.close()


@app.command()
def report(
    output: Optional[Path] = typer.Option(None, "--output", "-o", help="Output file path (default: .winterfox/report.md)"),
    config: Path = typer.Option(Path("winterfox.toml"), "--config", "-c", help="Config file path"),
    no_save: bool = typer.Option(False, "--no-save", help="Print only, don't save to file"),
    no_print: bool = typer.Option(False, "--no-print", help="Save only, don't print to console"),
    log_level: str = typer.Option("INFO", "--log-level", "-l", help="Log level"),
) -> None:
    """
    Generate a narrative research report from the knowledge graph.

    Uses the primary LLM to synthesize all findings into a cohesive
    document organized by themes, with confidence labels and citations.

    Example:
        winterfox report                        # Save to .winterfox/report.md and print
        winterfox report --output report.md     # Custom output path
        winterfox report --no-save              # Print only
        winterfox report --no-print             # Save only
    """
    setup_logging(level=log_level)

    try:
        asyncio.run(_generate_report(config, output, no_save, no_print))
    except KeyboardInterrupt:
        console.print("\n[yellow]Interrupted by user[/yellow]")
        raise typer.Exit(0)
    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1)


async def _generate_report(
    config_path: Path,
    output_path: Path | None,
    no_save: bool,
    no_print: bool,
) -> None:
    """Generate a narrative research report."""
    from .agents.adapters.anthropic import AnthropicAdapter
    from .agents.adapters.base import AgentAuthenticationError
    from .agents.adapters.kimi import KimiAdapter
    from .agents.adapters.openrouter import OpenRouterAdapter
    from .graph.store import KnowledgeGraph
    from .orchestrator.report import ReportSynthesizer

    config = load_config(config_path)

    graph = KnowledgeGraph(
        str(config.storage.db_path),
        workspace_id=config.multi_tenancy.workspace_id,
    )
    await graph.initialize()

    try:
        # Find the primary agent config
        primary_config = None
        for agent_config in config.agents:
            if agent_config.role == "primary":
                primary_config = agent_config
                break
        if primary_config is None:
            primary_config = config.agents[0]

        # Initialize only the primary adapter
        api_keys = config.get_agent_api_keys()
        key = f"{primary_config.provider}:{primary_config.model}"
        api_key = api_keys.get(key, "")

        if primary_config.provider == "anthropic":
            adapter = AnthropicAdapter(
                model=primary_config.model,
                api_key=api_key if not primary_config.use_subscription else None,
                use_subscription=primary_config.use_subscription,
                timeout=primary_config.timeout_seconds,
            )
        elif primary_config.provider == "moonshot":
            adapter = KimiAdapter(
                model=primary_config.model,
                api_key=api_key,
                timeout=primary_config.timeout_seconds,
            )
        elif primary_config.provider == "openrouter":
            adapter = OpenRouterAdapter(
                model=primary_config.model,
                api_key=api_key,
                timeout=primary_config.timeout_seconds,
                supports_native_search=primary_config.supports_native_search,
            )
        else:
            console.print(f"[red]Error: Unsupported provider {primary_config.provider}[/red]")
            return

        # Verify API key
        try:
            await adapter.verify()
            console.print(f"[green]\u2713[/green] {adapter.name}: API key verified")
        except AgentAuthenticationError as e:
            console.print(f"[red]\u2717[/red] {adapter.name}: {e}")
            return

        north_star = config.get_north_star(config_path.parent)
        await _generate_and_save_report(
            graph, adapter, north_star, config_path, output_path, no_save, no_print,
        )
    finally:
        await graph.close()


async def _generate_and_save_report(
    graph: Any,
    adapter: Any,
    north_star: str,
    config_path: Path,
    output_path: Path | None = None,
    no_save: bool = False,
    no_print: bool = False,
) -> None:
    """Generate report and handle saving/printing.

    Shared between `winterfox report` and `winterfox run --report`.
    """
    from .orchestrator.report import ReportSynthesizer

    synthesizer = ReportSynthesizer(graph, adapter, north_star)

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        task = progress.add_task("Generating report...", total=None)

        try:
            result = synthesizer.generate()
            # Handle both sync and async
            if asyncio.iscoroutine(result):
                result = await result
        except ValueError as e:
            console.print(f"[red]Error:[/red] {e}")
            return

        progress.update(task, description="Report complete")

    # Determine output path
    if not no_save:
        if output_path is None:
            output_path = config_path.parent / ".winterfox" / "report.md"
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(result.markdown, encoding="utf-8")
        console.print(f"[green]\u2713[/green] Report saved to {output_path}")

    # Print to console
    if not no_print:
        console.print()
        console.print(result.markdown)

    # Cost summary
    console.print(
        f"\n[dim]Report: {result.node_count} nodes, {result.cycle_count} cycles | "
        f"${result.cost_usd:.4f} | {result.duration_seconds:.1f}s | "
        f"{result.total_tokens:,} tokens[/dim]"
    )


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


@cycle_app.command("view")
def cycle_view(
    cycle_id: int = typer.Argument(..., help="Cycle ID to view"),
    config: Path = typer.Option(Path("winterfox.toml"), "--config", "-c"),
    format: str = typer.Option("markdown", "--format", "-f", help="Format: markdown or summary"),
    save: Optional[Path] = typer.Option(None, "--save", "-s", help="Save to file instead of printing"),
) -> None:
    """
    View detailed output from a specific cycle.

    Examples:
        winterfox cycle view 15
        winterfox cycle view 15 --save cycle_015.md
        winterfox cycle view 15 --format summary
    """
    setup_logging()

    try:
        asyncio.run(_view_cycle_output(config, cycle_id, format, save))
    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1)


async def _view_cycle_output(
    config_path: Path,
    cycle_id: int,
    format: str,
    save_path: Path | None,
) -> None:
    """Load and display cycle output."""
    from .export.cycle_export import CycleExportService
    from .graph.store import KnowledgeGraph

    # Load config and graph
    config = load_config(config_path)
    graph = KnowledgeGraph(str(config.storage.db_path), workspace_id=config.multi_tenancy.workspace_id)
    await graph.initialize()

    try:
        if format == "markdown":
            # Generate markdown
            service = CycleExportService(graph)
            markdown = await service.export_cycle_markdown(cycle_id)

            if save_path:
                save_path.write_text(markdown, encoding="utf-8")
                console.print(f"[green]✓[/green] Saved to {save_path}")
            else:
                console.print(markdown)

        elif format == "summary":
            # Show summary table
            cycle = await graph.get_cycle_output(cycle_id)
            if not cycle:
                console.print(f"[red]Cycle {cycle_id} not found[/red]")
                return

            # Create summary table
            table = Table(title=f"Cycle {cycle_id} Summary")
            table.add_column("Field", style="cyan")
            table.add_column("Value", style="white")

            table.add_row("Target", cycle["target_claim"][:80] + ("..." if len(cycle["target_claim"]) > 80 else ""))
            table.add_row("Status", "✅ Success" if cycle["success"] else "❌ Failed")
            table.add_row("Created", f"{cycle['findings_created']} nodes")
            table.add_row("Updated", f"{cycle['findings_updated']} nodes")
            table.add_row("Agents", str(cycle["agent_count"]))
            table.add_row("Cost", f"${cycle['total_cost_usd']:.4f}")
            table.add_row("Duration", f"{cycle['duration_seconds']:.1f}s")
            table.add_row("Tokens", f"{cycle['total_tokens']:,}")

            console.print(table)

    finally:
        await graph.close()


@cycle_app.command("list")
def cycle_list(
    config: Path = typer.Option(Path("winterfox.toml"), "--config", "-c"),
    limit: int = typer.Option(20, "--limit", "-n", help="Number of cycles to show"),
    node: Optional[str] = typer.Option(None, "--node", help="Filter by target node ID"),
    min_cost: Optional[float] = typer.Option(None, "--min-cost", help="Minimum cost filter"),
    max_cost: Optional[float] = typer.Option(None, "--max-cost", help="Maximum cost filter"),
    search: Optional[str] = typer.Option(None, "--search", "-s", help="Search synthesis text"),
    success_only: bool = typer.Option(False, "--success-only", help="Show only successful cycles"),
) -> None:
    """
    List past research cycles with filtering.

    Examples:
        winterfox cycle list
        winterfox cycle list --limit 10
        winterfox cycle list --node abc123
        winterfox cycle list --min-cost 0.10 --max-cost 1.00
        winterfox cycle list --search "legal tech"
    """
    setup_logging()

    try:
        asyncio.run(_list_cycle_outputs(config, limit, node, min_cost, max_cost, search, success_only))
    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1)


async def _list_cycle_outputs(
    config_path: Path,
    limit: int,
    node_id: str | None,
    min_cost: float | None,
    max_cost: float | None,
    search_query: str | None,
    success_only: bool,
) -> None:
    """List and filter cycle outputs."""
    from .graph.store import KnowledgeGraph

    # Load config and graph
    config = load_config(config_path)
    graph = KnowledgeGraph(str(config.storage.db_path), workspace_id=config.multi_tenancy.workspace_id)
    await graph.initialize()

    try:
        # Search or list
        if search_query:
            cycles = await graph.search_cycle_outputs(
                query=search_query,
                workspace_id=config.multi_tenancy.workspace_id,
                limit=limit,
            )
        else:
            cycles = await graph.list_cycle_outputs(
                workspace_id=config.multi_tenancy.workspace_id,
                limit=limit,
                offset=0,
                min_cost=min_cost,
                max_cost=max_cost,
                target_node_id=node_id,
                success_only=success_only,
            )

        if not cycles:
            # Fall back: discover cycles from nodes table
            node_cycles = await graph.list_cycles_from_nodes(
                workspace_id=config.multi_tenancy.workspace_id,
                limit=limit,
            )
            if not node_cycles:
                console.print("[yellow]No cycles found[/yellow]")
                return

            table = Table(title=f"Research Cycles ({len(node_cycles)} from graph nodes)")
            table.add_column("Cycle", style="cyan", width=6)
            table.add_column("Nodes", style="green", width=8)
            table.add_column("Date", style="white", width=19)

            for nc in node_cycles:
                table.add_row(
                    str(nc["cycle_id"]),
                    str(nc["node_count"]),
                    nc["first_created"][:19],
                )

            console.print(table)
            console.print(f"\n[dim]These cycles have no stored output data (pre-dating cycle output tracking).[/dim]")
            return

        # Display table
        table = Table(title=f"Research Cycles ({len(cycles)} results)")
        table.add_column("Cycle", style="cyan", width=6)
        table.add_column("Date", style="white", width=19)
        table.add_column("Claim", style="white", width=50)
        table.add_column("Status", style="white", width=8)
        table.add_column("Findings", style="green", width=10)
        table.add_column("Cost", style="yellow", width=8)
        table.add_column("Duration", style="blue", width=8)

        for cycle in cycles:
            status = "✅" if cycle["success"] else "❌"
            claim_preview = cycle["target_claim"][:47] + "..." if len(cycle["target_claim"]) > 50 else cycle["target_claim"]
            findings = f"+{cycle['findings_created']} ~{cycle['findings_updated']}"

            table.add_row(
                str(cycle["cycle_id"]),
                cycle["created_at"][:19],  # Trim microseconds
                claim_preview,
                status,
                findings,
                f"${cycle['total_cost_usd']:.3f}",
                f"{cycle['duration_seconds']:.0f}s",
            )

        console.print(table)
        console.print(f"\n[dim]Use 'winterfox cycle view <id>' to see details[/dim]")

    finally:
        await graph.close()


@cycle_app.command("remove")
def cycle_remove(
    cycle_id: int = typer.Argument(..., help="Cycle ID to delete"),
    config: Path = typer.Option(Path("winterfox.toml"), "--config", "-c"),
    force: bool = typer.Option(False, "--force", "-f", help="Skip confirmation prompt"),
) -> None:
    """
    Delete a cycle and its associated data.

    Removes cycle output, agent outputs, and graph operations for the cycle.
    Does NOT remove knowledge graph nodes created by the cycle.

    Examples:
        winterfox cycle remove 15
        winterfox cycle remove 15 --force
    """
    setup_logging()

    try:
        asyncio.run(_remove_cycle(config, cycle_id, force))
    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1)


async def _remove_cycle(config_path: Path, cycle_id: int, force: bool) -> None:
    """Delete a cycle by ID (database records + raw output files)."""
    import glob as globmod

    from .graph.store import KnowledgeGraph

    config = load_config(config_path)
    workspace_id = config.multi_tenancy.workspace_id
    graph = KnowledgeGraph(str(config.storage.db_path), workspace_id=workspace_id)
    await graph.initialize()

    try:
        if not force:
            # Try cycle_outputs first for rich info
            cycle = await graph.get_cycle_output(cycle_id)
            if cycle:
                console.print(
                    f"Cycle [bold]{cycle_id}[/bold]: {cycle['target_claim'][:80]}\n"
                    f"  Cost: ${cycle['total_cost_usd']:.4f} | "
                    f"Findings: +{cycle['findings_created']} ~{cycle['findings_updated']} | "
                    f"Date: {cycle['created_at'][:19]}"
                )
            else:
                # Fall back to nodes table
                node_cycles = await graph.list_cycles_from_nodes(workspace_id, limit=1000)
                found = next((c for c in node_cycles if c["cycle_id"] == cycle_id), None)
                if not found:
                    console.print(f"[red]Cycle {cycle_id} not found[/red]")
                    return
                console.print(
                    f"Cycle [bold]{cycle_id}[/bold]: {found['node_count']} nodes | "
                    f"Date: {found['first_created'][:19]}"
                )

            if not typer.confirm("Delete this cycle?"):
                console.print("[yellow]Cancelled[/yellow]")
                return

        # Delete from database (cycle_outputs, graph_operations, nodes)
        deleted = await graph.delete_cycle(workspace_id=workspace_id, cycle_id=cycle_id)

        # Delete raw output files: raw/{YYYY-MM-DD}/cycle_{id}.md
        raw_dir = config_path.parent / config.storage.raw_output_dir
        raw_files = globmod.glob(str(raw_dir / "**" / f"cycle_{cycle_id}.md"), recursive=True)
        for f in raw_files:
            Path(f).unlink()
            console.print(f"[dim]Deleted {f}[/dim]")

        if deleted or raw_files:
            console.print(f"[green]✓[/green] Deleted cycle {cycle_id}")
        else:
            console.print(f"[red]Cycle {cycle_id} not found[/red]")
    finally:
        await graph.close()


@cycle_app.command("export")
def cycle_export(
    output: Path = typer.Argument(..., help="Output file path"),
    config: Path = typer.Option(Path("winterfox.toml"), "--config", "-c"),
    cycles: Optional[str] = typer.Option(None, "--cycles", help="Cycle range (e.g., '1-10' or '5,7,9')"),
    node: Optional[str] = typer.Option(None, "--node", help="Export cycles for specific node"),
    title: str = typer.Option("Research Cycles Report", "--title", "-t"),
    format: str = typer.Option("markdown", "--format", "-f", help="Format: markdown"),
) -> None:
    """
    Export multiple cycles to a combined report.

    Examples:
        winterfox cycle export report.md --cycles "1-10"
        winterfox cycle export report.md --cycles "5,7,9,12"
        winterfox cycle export report.md --node abc123
    """
    setup_logging()

    try:
        asyncio.run(_export_cycles_combined(config, output, cycles, node, title, format))
        console.print(f"[green]✓[/green] Exported to {output}")
    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1)


async def _export_cycles_combined(
    config_path: Path,
    output: Path,
    cycles: str | None,
    node_id: str | None,
    title: str,
    format: str,
) -> None:
    """Export multiple cycles to single file."""
    from .export.cycle_export import export_cycles_to_markdown
    from .graph.store import KnowledgeGraph

    # Load config and graph
    config = load_config(config_path)
    graph = KnowledgeGraph(str(config.storage.db_path), workspace_id=config.multi_tenancy.workspace_id)
    await graph.initialize()

    try:
        # Parse cycle IDs
        cycle_ids = []

        if cycles:
            # Parse range or list
            if "-" in cycles:
                # Range: "1-10"
                start, end = cycles.split("-")
                cycle_ids = list(range(int(start), int(end) + 1))
            else:
                # List: "5,7,9"
                cycle_ids = [int(c.strip()) for c in cycles.split(",")]

        elif node_id:
            # Get all cycles for node
            all_cycles = await graph.list_cycle_outputs(
                workspace_id=config.multi_tenancy.workspace_id,
                limit=1000,
                target_node_id=node_id,
            )
            cycle_ids = [c["cycle_id"] for c in all_cycles]

        else:
            # Export all recent cycles (default: last 20)
            all_cycles = await graph.list_cycle_outputs(
                workspace_id=config.multi_tenancy.workspace_id,
                limit=20,
            )
            cycle_ids = [c["cycle_id"] for c in all_cycles]

        if not cycle_ids:
            console.print("[yellow]No cycles to export[/yellow]")
            return

        # Export to markdown
        await export_cycles_to_markdown(graph, cycle_ids, str(output), title)

    finally:
        await graph.close()


@app.command()
def serve(
    port: int = typer.Option(8000, "--port", "-p", help="Port to serve on"),
    host: str = typer.Option("127.0.0.1", "--host", "-H", help="Host to bind to"),
    config: Path = typer.Option(Path("winterfox.toml"), "--config", "-c", help="Config file path"),
    reload: bool = typer.Option(False, "--reload", help="Auto-reload on code changes (dev mode)"),
    open_browser: bool = typer.Option(False, "--open/--no-open", help="Open browser automatically"),
    log_level: str = typer.Option("INFO", "--log-level", "-l", help="Log level"),
) -> None:
    """
    Launch web dashboard.

    Starts a local web server with:
    - REST API at http://localhost:8000/api
    - Interactive API docs at http://localhost:8000/api/docs
    - Web UI at http://localhost:8000 (when frontend is built)

    Example:
        winterfox serve
        winterfox serve --port 8080 --open  # Auto-open browser
        winterfox serve --reload  # Development mode
    """
    setup_logging(level=log_level)

    try:
        _serve_dashboard(config, host, port, reload, open_browser, log_level)
    except KeyboardInterrupt:
        console.print("\n[yellow]Server stopped[/yellow]")
        raise typer.Exit(0)
    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1)


def _serve_dashboard(
    config_path: Path,
    host: str,
    port: int,
    reload: bool,
    open_browser: bool,
    log_level: str,
) -> None:
    """Start the dashboard server."""
    try:
        import uvicorn
    except ImportError:
        console.print(
            "[red]Error:[/red] FastAPI dependencies not installed.\n"
            "Run: pip install fastapi uvicorn[standard] websockets"
        )
        raise typer.Exit(1)

    from .web.server import create_app

    # Load configuration
    try:
        cfg = load_config(config_path)
    except FileNotFoundError:
        console.print(
            f"[red]Error:[/red] Configuration file not found: {config_path}\n"
            "Run 'winterfox init' to create one."
        )
        raise typer.Exit(1)
    except Exception as e:
        console.print(f"[red]Error:[/red] Failed to load config: {e}")
        raise typer.Exit(1)

    db_path = str(cfg.storage.db_path)
    workspace_id = cfg.multi_tenancy.workspace_id

    # Check if database exists
    if not Path(db_path).exists():
        console.print(
            f"[yellow]Warning:[/yellow] Database not found: {db_path}\n"
            "Run 'winterfox run' to start research first."
        )

    # Show startup message
    console.print(Panel.fit(
        f"[green]Starting dashboard...[/green]\n\n"
        f"Project: [bold]{cfg.project.name}[/bold]\n"
        f"URL: http://{host}:{port}\n"
        f"API Docs: http://{host}:{port}/api/docs\n"
        f"Database: {db_path}\n"
        f"Workspace: {workspace_id}",
        title="Winterfox Dashboard",
        border_style="blue",
    ))

    # Open browser after short delay
    if open_browser:
        import threading
        import webbrowser

        def open_in_browser():
            import time
            time.sleep(1.5)  # Wait for server to start
            url = f"http://{host}:{port}"
            console.print(f"[dim]Opening browser: {url}[/dim]")
            webbrowser.open(url)

        threading.Thread(target=open_in_browser, daemon=True).start()

    # Create and run app
    app = create_app(config_path, db_path, workspace_id)

    # Run server
    uvicorn.run(
        app,
        host=host,
        port=port,
        log_level=log_level.lower(),
        access_log=True,
    )


def main() -> None:
    """CLI entry point."""
    app()


if __name__ == "__main__":
    main()
