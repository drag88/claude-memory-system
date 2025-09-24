"""
CLI interface for Claude Memory System.

Provides command-line access to all memory operations using typer.
"""

import json
import sys
from pathlib import Path
from typing import Optional, Dict, Any

import typer
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.text import Text
from rich import print as rprint

from .core.memory_manager import MemoryManager
from .core.context_manager import ProjectContext

app = typer.Typer(
    name="claude-memory",
    help="Portable file-based memory system for Claude Code",
    add_completion=False
)

console = Console()


def print_result(result: Dict[str, Any], show_details: bool = False) -> None:
    """Print operation result with rich formatting."""
    if result.get("success"):
        if show_details:
            rprint(f"[green]✓[/green] {result.get('message', 'Operation successful')}")
            if "file_path" in result:
                rprint(f"[dim]File: {result['file_path']}[/dim]")
        else:
            rprint("[green]✓[/green]", end=" ")
    else:
        error = result.get("error", "Unknown error")
        rprint(f"[red]✗ Error:[/red] {error}")
        if show_details and "task_name" in result:
            rprint(f"[dim]Task: {result['task_name']}[/dim]")


@app.command()
def init(
    force: bool = typer.Option(False, "--force", "-f", help="Overwrite existing configuration")
) -> None:
    """Initialize Claude Memory System for current project."""
    project_root = Path.cwd()
    claude_dir = project_root / ".claude"
    memories_dir = claude_dir / "memories"

    try:
        # Create directories
        memories_dir.mkdir(parents=True, exist_ok=True)
        rprint(f"[green]✓[/green] Initialized memory storage at {memories_dir}")

        # Create initial session
        manager = MemoryManager()
        session_result = manager.session_manager_action("start")

        if session_result["success"]:
            rprint(f"[green]✓[/green] Created session: {session_result['session_id']}")

        rprint("\n[bold]Claude Memory System initialized![/bold]")
        rprint("Use [cyan]claude-memory --help[/cyan] to see available commands.")

    except Exception as e:
        rprint(f"[red]✗ Initialization failed:[/red] {e}")
        raise typer.Exit(1)


@app.command()
def scratchpad(
    task_name: str = typer.Argument(..., help="Name of the task"),
    content: str = typer.Option("", "--content", "-c", help="Initial content for scratchpad"),
    edit: bool = typer.Option(False, "--edit", "-e", help="Open scratchpad in editor"),
    show: bool = typer.Option(False, "--show", "-s", help="Show scratchpad content")
) -> None:
    """Create or update task scratchpad for exploration."""
    manager = MemoryManager()

    result = manager.task_memory_enforcer(task_name, "scratchpad", content)
    print_result(result, show_details=True)

    if result["success"]:
        file_path = Path(result["file_path"])

        if edit:
            import os
            editor = os.getenv("EDITOR", "vi")
            os.system(f"{editor} '{file_path}'")

        if show:
            if file_path.exists():
                console.print(Panel(file_path.read_text(), title=f"Scratchpad: {task_name}"))


@app.command()
def plan(
    task_name: str = typer.Argument(..., help="Name of the task"),
    content: str = typer.Option("", "--content", "-c", help="Plan content"),
    from_scratchpad: bool = typer.Option(False, "--from-scratchpad", help="Generate plan from scratchpad"),
    show: bool = typer.Option(False, "--show", "-s", help="Show plan content")
) -> None:
    """Create implementation plan (write-once, then immutable)."""
    manager = MemoryManager()

    # Auto-generate content from scratchpad if requested
    if from_scratchpad and not content:
        # This is a simplified version - in practice, you might want AI assistance here
        content = f"# Implementation plan based on scratchpad discoveries\n\n(Convert your scratchpad insights into concrete steps)\n"

    result = manager.task_memory_enforcer(task_name, "ensure", content)
    print_result(result, show_details=True)

    if result["success"] and show:
        file_path = Path(result["file_path"])
        if file_path.exists():
            console.print(Panel(file_path.read_text(), title=f"Plan: {task_name}"))


@app.command()
def append(
    task_name: str = typer.Argument(..., help="Name of the task"),
    content: str = typer.Argument(..., help="Progress update content")
) -> None:
    """Append progress update to task."""
    manager = MemoryManager()

    result = manager.task_memory_enforcer(task_name, "append", content)
    print_result(result, show_details=True)


@app.command()
def status(
    task_name: Optional[str] = typer.Argument(None, help="Specific task name (optional)")
) -> None:
    """Show status of tasks or specific task."""
    manager = MemoryManager()

    if task_name:
        # Show specific task status
        result = manager.get_task_status(task_name)

        if result["success"]:
            table = Table(title=f"Task Status: {task_name}")
            table.add_column("Property", style="cyan")
            table.add_column("Value", style="white")

            table.add_row("Phase", result["current_phase"])
            table.add_row("Session", result["session_id"])
            table.add_row("Message", result["phase_message"])

            # Show files
            for file_type, file_path in result["files"].items():
                status_icon = "✓" if file_path else "✗"
                table.add_row(f"{file_type.title()} File", f"{status_icon} {file_path or 'Not created'}")

            console.print(table)

            # Show next steps
            next_steps = result["next_steps"]
            console.print(Panel(
                f"[bold]Action:[/bold] {next_steps['action']}\n"
                f"[bold]Command:[/bold] {next_steps['command']}\n"
                f"[bold]Description:[/bold] {next_steps['description']}",
                title="Next Steps"
            ))

            # Show validation issues if any
            if result["validation_issues"]:
                issues_text = "\n".join(f"• {issue}" for issue in result["validation_issues"])
                console.print(Panel(issues_text, title="[red]Validation Issues[/red]"))
        else:
            print_result(result)

    else:
        # Show all tasks
        result = manager.list_tasks()

        if result["success"]:
            if result["tasks"]:
                table = Table(title="All Tasks")
                table.add_column("Task Name", style="cyan")
                table.add_column("Phase", style="green")
                table.add_column("Files", style="white")
                table.add_column("Issues", style="red")

                for task in result["tasks"]:
                    files_status = []
                    for file_type, file_path in task["files"].items():
                        if file_path:
                            files_status.append(f"✓ {file_type}")
                        else:
                            files_status.append(f"✗ {file_type}")

                    issues_icon = "⚠️" if task["has_issues"] else ""

                    table.add_row(
                        task["task_name"],
                        task["phase"],
                        " ".join(files_status),
                        issues_icon
                    )

                console.print(table)
                rprint(f"\n[dim]Session: {result['session_id']} | Total tasks: {result['count']}[/dim]")
            else:
                rprint("[yellow]No tasks found in current session[/yellow]")
        else:
            print_result(result)


@app.command()
def session(
    action: str = typer.Argument(..., help="Action: start, info, list, switch"),
    session_id: Optional[str] = typer.Option(None, "--id", help="Session ID for switch action"),
    limit: int = typer.Option(10, "--limit", "-l", help="Limit for list action")
) -> None:
    """Manage sessions."""
    manager = MemoryManager()

    if action == "start":
        result = manager.session_manager_action("start")
        print_result(result, show_details=True)

    elif action == "info":
        result = manager.session_manager_action("info")
        if result["success"]:
            table = Table(title="Session Information")
            table.add_column("Property", style="cyan")
            table.add_column("Value", style="white")

            table.add_row("Session ID", result["session_id"])
            table.add_row("Storage Path", result["storage_path"])

            if result["session_info"]:
                info = result["session_info"]
                table.add_row("Project Path", info["project_path"])
                table.add_row("Created", info["created_at"])
                table.add_row("Updated", info["updated_at"])
                table.add_row("Active Tasks", str(len(info["active_tasks"])))

            console.print(table)
        else:
            print_result(result)

    elif action == "list":
        result = manager.session_manager_action("list", limit=limit)
        if result["success"]:
            table = Table(title="Recent Sessions")
            table.add_column("Session ID", style="cyan")
            table.add_column("Project", style="white")
            table.add_column("Tasks", style="green")
            table.add_column("Updated", style="dim")

            for session in result["sessions"]:
                table.add_row(
                    session["session_id"],
                    Path(session["project_path"]).name,
                    str(len(session["active_tasks"])),
                    session["updated_at"][:19]  # Trim timestamp
                )

            console.print(table)
        else:
            print_result(result)

    elif action == "switch":
        if not session_id:
            rprint("[red]✗ Session ID required for switch action[/red]")
            raise typer.Exit(1)

        result = manager.session_manager_action("switch", session_id=session_id)
        print_result(result, show_details=True)

    else:
        rprint(f"[red]✗ Unknown session action: {action}[/red]")
        rprint("Available actions: start, info, list, switch")
        raise typer.Exit(1)


@app.command()
def cleanup(
    max_age_days: int = typer.Option(30, "--max-age", help="Maximum age for cleanup in days"),
    confirm: bool = typer.Option(False, "--confirm", "-y", help="Skip confirmation prompt")
) -> None:
    """Clean up old sessions and stale locks."""
    if not confirm:
        response = typer.confirm(f"Clean up sessions older than {max_age_days} days?")
        if not response:
            rprint("Cleanup cancelled")
            return

    manager = MemoryManager()
    result = manager.cleanup(max_age_days)

    if result["success"]:
        rprint(f"[green]✓[/green] {result['message']}")
    else:
        print_result(result)


@app.command()
def context() -> None:
    """Show context information for sub-agent coordination."""
    manager = MemoryManager()
    context = manager.get_task_context()

    rprint("[bold]Sub-Agent Context:[/bold]")
    rprint(f"Session ID: {context['session_id']}")
    rprint(f"Storage Path: {context['storage_path']}")
    rprint(f"Active Tasks: {', '.join(context['active_tasks']) if context['active_tasks'] else 'None'}")

    # Print usage instructions for sub-agents
    console.print(Panel(
        "Use these commands in sub-agents:\n\n"
        "• [cyan]claude-memory scratchpad \"task-name\"[/cyan] - Explore and research\n"
        "• [cyan]claude-memory plan \"task-name\"[/cyan] - Create implementation plan\n"
        "• [cyan]claude-memory append \"task-name\" \"update\"[/cyan] - Track progress\n"
        "• [cyan]claude-memory status \"task-name\"[/cyan] - Check task status",
        title="Sub-Agent Commands"
    ))


@app.command(name="project-context")
def project_context(
    action: str = typer.Argument("show", help="Action: show, refresh, clear"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Show detailed information")
) -> None:
    """Manage project context for session initialization."""
    project_ctx = ProjectContext()

    if action == "show":
        # Show current project context
        try:
            context_text = project_ctx.get_session_context()
            if verbose:
                console.print(Panel(context_text, title="Project Context", border_style="blue"))
            else:
                # Show condensed version
                console.print(context_text)
        except Exception as e:
            rprint(f"[red]✗ Failed to load project context:[/red] {e}")

    elif action == "refresh":
        # Force refresh of project context
        try:
            rprint("[cyan]Refreshing project context...[/cyan]")
            context_data = project_ctx.refresh_context()

            # Show summary of what was discovered
            rprint(f"[green]✓[/green] Project context refreshed")
            rprint(f"Project: {context_data.get('project_name')}")
            rprint(f"Type: {context_data.get('project_type')}")
            rprint(f"Language: {context_data.get('primary_language')}")
            rprint(f"Tech Stack: {', '.join(context_data.get('tech_stack', []))}")

            if verbose:
                context_text = project_ctx.get_session_context()
                console.print(Panel(context_text, title="Refreshed Project Context", border_style="green"))

        except Exception as e:
            rprint(f"[red]✗ Failed to refresh project context:[/red] {e}")

    elif action == "clear":
        # Clear cached context
        try:
            success = project_ctx.clear_context()
            if success:
                rprint("[green]✓[/green] Project context cache cleared")
            else:
                rprint("[yellow]No context cache found to clear[/yellow]")
        except Exception as e:
            rprint(f"[red]✗ Failed to clear context cache:[/red] {e}")

    else:
        rprint(f"[red]✗ Unknown action: {action}[/red]")
        rprint("Available actions: show, refresh, clear")
        raise typer.Exit(1)


@app.command(name="project-info")
def project_info() -> None:
    """Show detailed project information and metrics."""
    project_ctx = ProjectContext()

    try:
        # Force a fresh gather to get latest info
        context_data = project_ctx._gather_context(force_refresh=True)

        # Create detailed information table
        table = Table(title=f"Project Information: {context_data.get('project_name')}")
        table.add_column("Property", style="cyan")
        table.add_column("Value", style="white")

        # Basic info
        table.add_row("Name", context_data.get("project_name", "Unknown"))
        table.add_row("Type", context_data.get("project_type", "Unknown"))
        table.add_row("Primary Language", context_data.get("primary_language", "Unknown"))
        table.add_row("Path", context_data.get("project_path", "Unknown"))

        # Metrics
        metrics = context_data.get("project_metrics", {})
        table.add_row("Total Files", str(metrics.get("total_files", 0)))
        table.add_row("Code Files", str(metrics.get("code_files", 0)))
        table.add_row("Estimated Size", metrics.get("estimated_size", "Unknown"))

        # Tech stack
        tech_stack = context_data.get("tech_stack", [])
        table.add_row("Tech Stack", ", ".join(tech_stack) if tech_stack else "None detected")

        # Key files
        key_files = context_data.get("key_files", [])
        table.add_row("Key Files", ", ".join(key_files) if key_files else "None found")

        console.print(table)

        # Show available commands
        commands = context_data.get("available_commands", {})
        if commands:
            cmd_table = Table(title="Available Commands")
            cmd_table.add_column("Command Type", style="green")
            cmd_table.add_column("Command", style="cyan")

            for cmd_type, cmd in commands.items():
                cmd_table.add_row(cmd_type.title(), cmd)

            console.print(cmd_table)

        # Show recent commits
        commits = context_data.get("recent_commits", [])
        if commits:
            console.print("\n[bold]Recent Commits:[/bold]")
            for commit in commits:
                rprint(f"• [dim]{commit['hash']}[/dim] {commit['message']} [dim]({commit['time']})[/dim]")

        # Show directory structure if verbose
        structure = context_data.get("directory_structure", "")
        if structure:
            console.print(Panel(structure, title="Project Structure", border_style="dim"))

    except Exception as e:
        rprint(f"[red]✗ Failed to gather project information:[/red] {e}")


@app.command()
def export(
    task_name: str = typer.Argument(..., help="Name of the task"),
    format: str = typer.Option("json", "--format", "-f", help="Export format: json, text"),
    output: Optional[str] = typer.Option(None, "--output", "-o", help="Output file path")
) -> None:
    """Export task data."""
    manager = MemoryManager()
    result = manager.get_task_status(task_name)

    if not result["success"]:
        print_result(result)
        return

    # Read file contents
    files_content = {}
    for file_type, file_path in result["files"].items():
        if file_path and Path(file_path).exists():
            files_content[file_type] = Path(file_path).read_text()

    export_data = {
        "task_name": task_name,
        "session_id": result["session_id"],
        "phase": result["current_phase"],
        "files": files_content,
        "exported_at": result["timestamp"]
    }

    if format == "json":
        output_text = json.dumps(export_data, indent=2)
    else:  # text format
        output_text = f"# Task Export: {task_name}\n\n"
        output_text += f"Session: {result['session_id']}\n"
        output_text += f"Phase: {result['current_phase']}\n\n"

        for file_type, content in files_content.items():
            output_text += f"## {file_type.title()}\n\n{content}\n\n"

    if output:
        Path(output).write_text(output_text)
        rprint(f"[green]✓[/green] Exported to {output}")
    else:
        console.print(output_text)


@app.command()
def version() -> None:
    """Show version information."""
    from . import __version__
    rprint(f"Claude Memory System v{__version__}")


def main() -> None:
    """Main entry point for CLI."""
    try:
        app()
    except KeyboardInterrupt:
        rprint("\n[yellow]Operation cancelled[/yellow]")
        sys.exit(130)
    except Exception as e:
        rprint(f"[red]✗ Unexpected error:[/red] {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()