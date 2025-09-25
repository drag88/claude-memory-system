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
    force: bool = typer.Option(False, "--force", "-f", help="Overwrite existing configuration"),
    skip_setup: bool = typer.Option(False, "--skip-setup", help="Skip automatic hooks and agents setup")
) -> None:
    """Initialize Claude Memory System for current project."""
    import shutil
    import subprocess

    project_root = Path.cwd()
    claude_dir = project_root / ".claude"
    memories_dir = claude_dir / "memories"

    try:
        # Create directories
        memories_dir.mkdir(parents=True, exist_ok=True)
        rprint(f"[green]✓[/green] Initialized memory storage at {memories_dir}")

        # Create or update CLAUDE.md with memory system instructions
        claude_md_path = project_root / "CLAUDE.md"
        try:
            # Load template from package templates
            import claude_memory
            package_path = Path(claude_memory.__file__).parent
            template_path = package_path / "templates" / "claude_template.md"

            if template_path.exists():
                template_content = template_path.read_text()

                if claude_md_path.exists():
                    # Check if memory system section already exists
                    existing_content = claude_md_path.read_text()
                    if "## 🧠 Claude Memory System" not in existing_content:
                        # Append memory system section
                        updated_content = existing_content.rstrip() + "\n\n" + template_content
                        claude_md_path.write_text(updated_content)
                        rprint(f"[green]✓[/green] Added memory system instructions to existing CLAUDE.md")
                    else:
                        rprint(f"[yellow]ℹ️[/yellow] CLAUDE.md already contains memory system instructions")
                else:
                    # Create new CLAUDE.md with template
                    claude_md_path.write_text(template_content)
                    rprint(f"[green]✓[/green] Created CLAUDE.md with memory system instructions")
            else:
                rprint(f"[yellow]⚠️[/yellow] Template file not found, skipping CLAUDE.md creation")

        except Exception as e:
            rprint(f"[yellow]⚠️[/yellow] CLAUDE.md creation failed: {e}")

        # Auto-setup hooks and agents unless skipped
        if not skip_setup:
            rprint("[blue]🔧 Setting up hooks and agents...[/blue]")

            # Create Claude Code directories
            hooks_dir = claude_dir / "hooks"
            agents_dir = claude_dir / "agents"
            hooks_dir.mkdir(parents=True, exist_ok=True)
            agents_dir.mkdir(parents=True, exist_ok=True)

            # Find package location and install hooks/agents
            try:
                import claude_memory
                package_path = Path(claude_memory.__file__).parent

                # Install hooks
                hooks_source = package_path / "hooks"
                if hooks_source.exists():
                    for hook_file in hooks_source.glob("*.py"):
                        dest_file = hooks_dir / hook_file.name
                        if not dest_file.exists() or force:
                            shutil.copy2(hook_file, dest_file)
                            dest_file.chmod(0o755)  # Make executable
                    rprint(f"[green]✓[/green] Installed hooks to {hooks_dir}")

                # Install agents from package data
                try:
                    agents_source = package_path / "data"
                    if agents_source.exists():
                        agent_count = 0
                        for agent_file in agents_source.glob("*.md"):
                            if not agent_file.name.startswith('.') and agent_file.name != "claude_template.md":  # Skip hidden files and template
                                dest_file = agents_dir / agent_file.name
                                if not dest_file.exists() or force:
                                    shutil.copy2(agent_file, dest_file)
                                    agent_count += 1
                        if agent_count > 0:
                            rprint(f"[green]✓[/green] Installed {agent_count} agents to {agents_dir}")
                        else:
                            rprint("[yellow]⚠️  No agent files found or all already exist[/yellow]")
                    else:
                        rprint("[yellow]⚠️  Agent data directory not found in package[/yellow]")

                except Exception as e:
                    rprint(f"[yellow]⚠️  Agent installation failed: {e}[/yellow]")

                # Update Claude settings
                settings_file = claude_dir / "settings.json"
                try:
                    if settings_file.exists():
                        with open(settings_file, 'r') as f:
                            settings = json.load(f)
                    else:
                        settings = {}

                    # Ensure hooks section exists
                    if "hooks" not in settings:
                        settings["hooks"] = {}

                    # Add memory system hooks
                    hook_configs = {
                        "PreToolUse": [{"matcher": "Task", "hooks": [{"type": "command", "command": "python3 .claude/hooks/pre_tool_use.py"}]}],
                        "PostToolUse": [{"matcher": ".*", "hooks": [{"type": "command", "command": "python3 .claude/hooks/post_tool_use.py"}]}],
                        "SessionStart": [{"hooks": [{"type": "command", "command": "python3 .claude/hooks/session_start.py"}]}],
                        "SubagentStop": [{"hooks": [{"type": "command", "command": "python3 .claude/hooks/subagent_stop.py"}]}]
                    }

                    for hook_type, hook_config in hook_configs.items():
                        settings["hooks"][hook_type] = hook_config

                    # Write updated settings
                    with open(settings_file, 'w') as f:
                        json.dump(settings, f, indent=2)

                    rprint(f"[green]✓[/green] Updated Claude Code settings")

                except Exception as e:
                    rprint(f"[yellow]⚠️  Settings update failed: {e}[/yellow]")

            except Exception as e:
                rprint(f"[yellow]⚠️  Auto-setup failed: {e}[/yellow]")
                rprint("[dim]You can run the setup manually with: python scripts/setup_hooks.py[/dim]")

        # Create initial session
        manager = MemoryManager()
        session_result = manager.session_manager_action("start")

        if session_result["success"]:
            rprint(f"[green]✓[/green] Created session: {session_result['session_id']}")

        # Generate project context
        try:
            context = ProjectContext()
            context.refresh_context()  # This returns the context data directly
            rprint(f"[green]✓[/green] Generated project context")
        except Exception as e:
            rprint(f"[yellow]⚠️  Project context generation failed: {e}[/yellow]")

        rprint("\n[bold]Claude Memory System initialized![/bold]")

        if not skip_setup:
            agent_count = len(list(agents_dir.glob("*.md"))) if (claude_dir / "agents").exists() else 0
            if agent_count > 0:
                rprint(f"[green]🤖 {agent_count} specialized agents available[/green]")
            rprint("[green]🔗 Memory system hooks configured[/green]")
            rprint("[yellow]⚠️  Restart Claude Code to activate hooks[/yellow]")

        rprint("\nAvailable commands:")
        rprint("  [cyan]claude-memory scratchpad[/cyan] 'task' --content 'exploration'")
        rprint("  [cyan]claude-memory plan[/cyan] 'task' --content 'implementation strategy'")
        rprint("  [cyan]claude-memory append[/cyan] 'task' 'progress update'")
        rprint("  [cyan]claude-memory status[/cyan] # Show all tasks")
        rprint("  [cyan]claude-memory uninstall[/cyan] # Remove from project")

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

    # Pre-validate phase transition with enhanced guidance
    validation = manager.validate_phase_transition(task_name, "scratchpad")
    if not validation["valid"]:
        rprint(f"[red]{validation['message']}[/red]")
        rprint(f"[dim]Current phase: {validation['current_phase']}[/dim]")
        raise typer.Exit(1)

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

    # Pre-validate phase transition with enhanced guidance
    validation = manager.validate_phase_transition(task_name, "ensure")
    if not validation["valid"]:
        rprint(f"[red]{validation['message']}[/red]")
        rprint(f"[dim]Current phase: {validation['current_phase']}[/dim]")
        raise typer.Exit(1)

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


@app.command("edit-plan")
def edit_plan(
    task_name: str = typer.Argument(..., help="Name of the task"),
    content: str = typer.Option("", "--content", "-c", help="Updated plan content"),
    edit: bool = typer.Option(False, "--edit", "-e", help="Open plan in editor"),
    show: bool = typer.Option(False, "--show", "-s", help="Show current plan")
) -> None:
    """Edit plan during PLANNING phase (before execution starts)."""
    manager = MemoryManager()

    # Check current phase
    status = manager.get_task_status(task_name)
    if not status["success"]:
        rprint(f"[red]Task '{task_name}' not found[/red]")
        raise typer.Exit(1)

    current_phase = status["current_phase"]

    if current_phase != "PLANNING":
        if current_phase == "EXECUTION":
            rprint("[red]❌ Cannot edit plan after execution has started![/red]")
            rprint("[yellow]Plan is locked during execution phase[/yellow]")
        elif current_phase == "DISCOVERY":
            rprint(f"[red]❌ Cannot edit plan in {current_phase} phase[/red]")
            rprint("[yellow]Create a plan first with: claude-memory plan 'task-name'[/yellow]")
        else:
            rprint(f"[red]❌ Cannot edit plan in {current_phase} phase[/red]")
            rprint("[yellow]Plan editing is only available during PLANNING phase[/yellow]")
        raise typer.Exit(1)

    # Handle edit modes
    if edit:
        # Open in editor
        file_path = Path(status["files"]["plan"])
        if not file_path or not file_path.exists():
            rprint("[red]Plan file not found[/red]")
            raise typer.Exit(1)

        import os
        editor = os.getenv("EDITOR", "vi")
        os.system(f"{editor} '{file_path}'")
        rprint("[green]✓ Plan updated via editor[/green]")
    elif content:
        # Update with provided content
        try:
            enforcer = manager._get_enforcer()
            enforcer.update_plan(task_name, content)
            rprint("[green]✓ Plan updated[/green]")
        except Exception as e:
            rprint(f"[red]✗ Error updating plan: {e}[/red]")
            raise typer.Exit(1)
    elif show:
        # Show current plan
        file_path = Path(status["files"]["plan"]) if status["files"]["plan"] else None
        if file_path and file_path.exists():
            console.print(Panel(file_path.read_text(), title=f"Plan: {task_name}"))
        else:
            rprint("[yellow]No plan content to show[/yellow]")
    else:
        # Default: show current plan if no other options provided
        file_path = Path(status["files"]["plan"]) if status["files"]["plan"] else None
        if file_path and file_path.exists():
            console.print(Panel(file_path.read_text(), title=f"Current Plan: {task_name}"))
            rprint("\n[dim]To edit:[/dim] claude-memory edit-plan 'task' --edit")
            rprint("[dim]To update:[/dim] claude-memory edit-plan 'task' --content 'new content'")
        else:
            rprint("[yellow]No plan found[/yellow]")


@app.command()
def append(
    task_name: str = typer.Argument(..., help="Name of the task"),
    content: str = typer.Argument(..., help="Progress update content")
) -> None:
    """Append progress update to task."""
    manager = MemoryManager()

    # Pre-validate phase transition with enhanced guidance
    validation = manager.validate_phase_transition(task_name, "append")
    if not validation["valid"]:
        rprint(f"[red]{validation['message']}[/red]")
        rprint(f"[dim]Current phase: {validation['current_phase']}[/dim]")
        raise typer.Exit(1)

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
def uninstall(
    force: bool = typer.Option(False, "--force", "-f", help="Force removal without confirmation"),
    keep_memories: bool = typer.Option(False, "--keep-memories", help="Keep .claude/memories directory"),
    keep_claude_md: bool = typer.Option(False, "--keep-claude-md", help="Keep CLAUDE.md file unchanged")
) -> None:
    """Uninstall Claude Memory System from current project."""
    import shutil

    if not force:
        confirm = typer.confirm("Are you sure you want to uninstall Claude Memory System from this project?")
        if not confirm:
            rprint("[yellow]Uninstall cancelled[/yellow]")
            return

    cwd = Path.cwd()
    removed_items = []

    # Remove .claude/hooks directory
    hooks_dir = cwd / ".claude" / "hooks"
    if hooks_dir.exists():
        # Only remove memory system hooks
        memory_hooks = ["pre_tool_use.py", "post_tool_use.py", "session_start.py", "subagent_stop.py"]
        for hook in memory_hooks:
            hook_file = hooks_dir / hook
            if hook_file.exists():
                hook_file.unlink()
                removed_items.append(f".claude/hooks/{hook}")

        # Remove hooks directory if empty
        if not any(hooks_dir.iterdir()):
            hooks_dir.rmdir()
            removed_items.append(".claude/hooks/")

    # Remove .claude/agents directory
    agents_dir = cwd / ".claude" / "agents"
    if agents_dir.exists():
        shutil.rmtree(agents_dir)
        removed_items.append(".claude/agents/")

    # Remove .claude/memories directory (if not keeping)
    if not keep_memories:
        memories_dir = cwd / ".claude" / "memories"
        if memories_dir.exists():
            shutil.rmtree(memories_dir)
            removed_items.append(".claude/memories/")

    # Clean up .claude/settings.json (remove memory hooks)
    settings_file = cwd / ".claude" / "settings.json"
    if settings_file.exists():
        try:
            with open(settings_file, 'r') as f:
                settings = json.load(f)

            # Remove memory system hooks from settings
            if "hooks" in settings:
                for hook_type in ["PreToolUse", "PostToolUse", "SessionStart", "SubagentStop"]:
                    if hook_type in settings["hooks"]:
                        # Filter out memory system hooks
                        filtered_hooks = []
                        for hook_entry in settings["hooks"][hook_type]:
                            if isinstance(hook_entry, dict) and "hooks" in hook_entry:
                                hooks_list = hook_entry["hooks"]
                                if isinstance(hooks_list, list):
                                    memory_hook = any(
                                        isinstance(h, dict) and
                                        h.get("command", "").endswith(("pre_tool_use.py", "post_tool_use.py", "session_start.py", "subagent_stop.py"))
                                        for h in hooks_list
                                    )
                                    if not memory_hook:
                                        filtered_hooks.append(hook_entry)
                                else:
                                    filtered_hooks.append(hook_entry)
                            else:
                                filtered_hooks.append(hook_entry)

                        if filtered_hooks:
                            settings["hooks"][hook_type] = filtered_hooks
                        else:
                            del settings["hooks"][hook_type]

                # Remove hooks section if empty
                if not settings["hooks"]:
                    del settings["hooks"]

            # Write updated settings
            with open(settings_file, 'w') as f:
                json.dump(settings, f, indent=2)

            removed_items.append("Memory hooks from .claude/settings.json")

        except Exception as e:
            rprint(f"[yellow]⚠️  Warning: Could not clean settings.json: {e}[/yellow]")

    # Handle CLAUDE.md cleanup (if not keeping)
    if not keep_claude_md:
        claude_md_path = cwd / "CLAUDE.md"
        if claude_md_path.exists():
            try:
                content = claude_md_path.read_text()
                # Check if it contains memory system section
                if "## 🧠 Claude Memory System" in content:
                    # Split content and remove memory system section
                    lines = content.split('\n')
                    filtered_lines = []
                    skip_section = False
                    found_memory_section = False

                    for i, line in enumerate(lines):
                        if line.strip() == "## 🧠 Claude Memory System":
                            found_memory_section = True
                            skip_section = True
                            # Also remove the preceding title if it's our template title
                            if (i > 0 and
                                lines[i-1].strip() == "# CLAUDE.md - Project Instructions" and
                                (i == 1 or lines[i-2].strip() == "")):
                                # Remove the template title and empty line before it
                                if filtered_lines and filtered_lines[-1].strip() == "":
                                    filtered_lines.pop()
                                if filtered_lines and filtered_lines[-1].strip() == "# CLAUDE.md - Project Instructions":
                                    filtered_lines.pop()
                            continue
                        elif line.startswith("## ") and skip_section and line.strip() != "## 🧠 Claude Memory System":
                            # Next section found, stop skipping
                            skip_section = False
                            filtered_lines.append(line)
                        elif not skip_section:
                            filtered_lines.append(line)

                    # Remove trailing empty lines and write back
                    filtered_content = '\n'.join(filtered_lines).rstrip() + '\n'

                    # If file would be empty or only has title, remove it
                    if len(filtered_content.strip()) <= len("# CLAUDE.md - Project Instructions"):
                        claude_md_path.unlink()
                        removed_items.append("CLAUDE.md (file was mostly empty)")
                    else:
                        claude_md_path.write_text(filtered_content)
                        removed_items.append("Memory system section from CLAUDE.md")

            except Exception as e:
                rprint(f"[yellow]⚠️  Warning: Could not clean CLAUDE.md: {e}[/yellow]")

    # Remove empty .claude directory
    claude_dir = cwd / ".claude"
    if claude_dir.exists() and not any(claude_dir.iterdir()):
        claude_dir.rmdir()
        removed_items.append(".claude/")

    if removed_items:
        rprint("[green]✓[/green] Uninstalled Claude Memory System")
        rprint("[dim]Removed:[/dim]")
        for item in removed_items:
            rprint(f"  [dim]• {item}[/dim]")

        if keep_memories:
            rprint(f"[yellow]ℹ️  Kept memories at: .claude/memories/[/yellow]")

        rprint("\n[dim]To reinstall: uv add git+https://github.com/drag88/claude-memory-system.git[/dim]")
    else:
        rprint("[yellow]No Claude Memory System files found to remove[/yellow]")


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