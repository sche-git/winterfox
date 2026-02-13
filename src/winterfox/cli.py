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
) -> None:
    """
    Initialize a new research project.

    Creates:
    - research.toml configuration file
    - research.db SQLite database
    - research/ directory for raw outputs

    Example:
        winterfox init "Legal Tech Market Research"
        winterfox init "AI Startups" --north-star "Research AI startup landscape"
    """
    try:
        # Ensure directory exists
        path.mkdir(parents=True, exist_ok=True)

        config_path = path / "research.toml"

        # Check if already initialized
        if config_path.exists():
            console.print(
                f"[yellow]Warning:[/yellow] {config_path} already exists. "
                "Use --force to overwrite (not implemented yet)."
            )
            raise typer.Exit(1)

        # Get north star if not provided
        if not north_star:
            console.print("\n[bold]Project Mission / North Star[/bold]")
            console.print(
                "Describe your research mission in 1-3 sentences. "
                "This guides the research agents.\n"
            )
            north_star = typer.prompt("Mission statement")

        # Create default config
        create_default_config(config_path, project_name, north_star)

        # Initialize database
        from .graph.store import KnowledgeGraph

        db_path = path / "research.db"
        asyncio.run(_init_database(db_path))

        # Create directories
        (path / "research" / "raw").mkdir(parents=True, exist_ok=True)

        # Success message
        console.print(Panel.fit(
            f"[green]✓[/green] Initialized research project: [bold]{project_name}[/bold]\n\n"
            f"Configuration: {config_path}\n"
            f"Database: {db_path}\n\n"
            "[dim]Next steps:[/dim]\n"
            "1. Set API keys in environment (ANTHROPIC_API_KEY, TAVILY_API_KEY, etc.)\n"
            "2. Edit research.toml to configure agents and search providers\n"
            "3. Run your first cycle: winterfox cycle",
            title="Project Initialized",
            border_style="green",
        ))

    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1)


async def _init_database(db_path: Path) -> None:
    """Initialize SQLite database."""
    from .graph.store import KnowledgeGraph

    graph = KnowledgeGraph(str(db_path))
    await graph.initialize()
    await graph.close()


@app.command()
def cycle(
    n: int = typer.Option(1, "--count", "-n", help="Number of cycles to run"),
    focus: Optional[str] = typer.Option(None, "--focus", "-f", help="Specific node ID to research"),
    config: Path = typer.Option(Path("research.toml"), "--config", "-c", help="Config file path"),
    log_level: str = typer.Option("INFO", "--log-level", "-l", help="Log level"),
    no_consensus: bool = typer.Option(False, "--no-consensus", help="Disable multi-agent consensus"),
) -> None:
    """
    Run research cycle(s).

    A cycle:
    1. Selects a target node (or uses --focus)
    2. Generates research prompts
    3. Dispatches agents to research
    4. Merges findings into knowledge graph
    5. Propagates confidence changes

    Example:
        winterfox cycle                    # Run 1 cycle
        winterfox cycle -n 10              # Run 10 cycles
        winterfox cycle --focus node-123   # Research specific node
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
    from .agents.adapters.kimi import KimiAdapter
    from .agents.pool import AgentPool

    api_keys = config.get_agent_api_keys()

    adapters = []
    for agent_config in config.agents:
        key = f"{agent_config.provider}:{agent_config.model}"
        api_key = api_keys.get(key, "")

        if agent_config.provider == "anthropic":
            adapter = AnthropicAdapter(
                model=agent_config.model,
                api_key=api_key if not agent_config.use_subscription else None,
                use_subscription=agent_config.use_subscription,
                timeout_seconds=agent_config.timeout_seconds,
            )
        elif agent_config.provider == "moonshot":
            adapter = KimiAdapter(
                model=agent_config.model,
                api_key=api_key,
                timeout_seconds=agent_config.timeout_seconds,
            )
        else:
            console.print(f"[yellow]Warning: Unsupported provider {agent_config.provider}, skipping[/yellow]")
            continue

        adapters.append(adapter)

    agent_pool = AgentPool(adapters)

    # Initialize tools
    from .agents.tools import get_research_tools

    tools = get_research_tools(graph)

    # Initialize orchestrator
    from .orchestrator import Orchestrator

    north_star = config.get_north_star(config_path.parent)

    orchestrator = Orchestrator(
        graph=graph,
        agent_pool=agent_pool,
        north_star=north_star,
        tools=tools,
        max_searches_per_cycle=config.orchestrator.max_searches_per_agent,
        confidence_discount=config.orchestrator.confidence_discount,
        consensus_boost=config.orchestrator.consensus_boost,
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
    config: Path = typer.Option(Path("research.toml"), "--config", "-c", help="Config file path"),
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
        console.print("[yellow]Graph is empty. Run 'winterfox cycle' to start research.[/yellow]")
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
    config: Path = typer.Option(Path("research.toml"), "--config", "-c", help="Config file path"),
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
    config: Path = typer.Option(Path("research.toml"), "--config", "-c", help="Config file path"),
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
    config: Path = typer.Option(Path("research.toml"), "--config", "-c", help="Config file path"),
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
