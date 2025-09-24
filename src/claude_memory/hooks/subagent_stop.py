#!/usr/bin/env python3
"""
Sub-agent stop hook for Claude Code integration.

Synchronizes memory state when sub-agents complete.
"""

import json
import sys
import subprocess
from pathlib import Path
from datetime import datetime

# Try to import claude_memory - handle different installation methods
try:
    from claude_memory import MemoryAPI
except ImportError:
    # For global tool installations, try to find the package
    try:
        # Try to get the installation path from uv tool
        result = subprocess.run(['uv', 'tool', 'dir'], capture_output=True, text=True)
        if result.returncode == 0:
            tool_dir = Path(result.stdout.strip())
            # Look for claude-memory-system installation with any Python 3.x version
            claude_tool_dir = tool_dir / "claude-memory-system"
            if claude_tool_dir.exists():
                lib_dir = claude_tool_dir / "lib"
                if lib_dir.exists():
                    # Find any python3.x directory
                    for python_dir in lib_dir.glob("python3.*"):
                        site_packages = python_dir / "site-packages"
                        if site_packages.exists():
                            sys.path.insert(0, str(site_packages))
                            break
    except:
        pass

    try:
        from claude_memory import MemoryAPI
    except ImportError:
        # If still failing, try relative import from package directory
        try:
            sys.path.insert(0, str(Path(__file__).parent.parent.parent))
            from claude_memory import MemoryAPI
        except ImportError:
            # Final fallback
            MemoryAPI = None


def sync_subagent_memory(input_data: dict) -> dict:
    """
    Synchronize memory after sub-agent completion.

    Args:
        input_data: Sub-agent completion data

    Returns:
        Sync result information
    """
    try:
        api = MemoryAPI()

        # Extract sub-agent information
        subagent_type = input_data.get('subagent_type', 'unknown')
        prompt = input_data.get('prompt', '')
        response = input_data.get('response', '')

        # Try to extract task name from the interaction
        task_name = None

        # Look for memory commands in the response
        memory_commands = []
        if 'claude-memory' in response:
            lines = response.split('\n')
            for line in lines:
                if 'claude-memory' in line:
                    memory_commands.append(line.strip())

        # Look for task names in commands
        for cmd in memory_commands:
            if '"' in cmd:
                # Extract quoted task name
                parts = cmd.split('"')
                if len(parts) >= 2:
                    potential_task = parts[1]
                    if potential_task and not potential_task.startswith('-'):
                        task_name = potential_task
                        break

        # Log sub-agent completion
        timestamp = datetime.now().isoformat()
        sync_info = {
            "timestamp": timestamp,
            "subagent_type": subagent_type,
            "task_name": task_name,
            "memory_commands_used": len(memory_commands),
            "commands": memory_commands[:3]  # First 3 commands for brevity
        }

        # If we identified a task, add completion note
        if task_name:
            try:
                completion_note = f"""Sub-agent ({subagent_type}) completed at {timestamp}

**Memory commands used:** {len(memory_commands)}
**Commands:** {', '.join(memory_commands[:2])}

**Key activities:**
{response[:300]}{"..." if len(response) > 300 else ""}
"""
                api.append(task_name, completion_note)
                sync_info["logged_to_task"] = True

            except Exception as e:
                sync_info["log_error"] = str(e)
                sync_info["logged_to_task"] = False

        # Also log to special sub-agent tracking task
        try:
            api.append(
                "_subagent_activity",
                f"Sub-agent: {subagent_type} | Task: {task_name or 'unknown'} | Commands: {len(memory_commands)}"
            )
            sync_info["logged_to_tracking"] = True
        except:
            sync_info["logged_to_tracking"] = False

        return {
            "success": True,
            **sync_info
        }

    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }


def main():
    """Main hook function."""
    try:
        # Read input from Claude
        input_data = json.loads(sys.stdin.read())

        # Synchronize memory after sub-agent completion if available
        if MemoryAPI is not None:
            sync_result = sync_subagent_memory(input_data)
        else:
            sync_result = {"success": False, "error": "Memory system not available"}

        # SubagentStop hooks can control whether Claude continues
        # We'll always allow continuation but log any sync issues
        if sync_result["success"]:
            response = {
                "continue": True,
                "reason": f"Memory synchronized for {sync_result.get('subagent_type', 'unknown')} sub-agent"
            }
        else:
            response = {
                "continue": True,
                "reason": f"Memory sync failed but continuing: {sync_result['error']}"
            }

        print(json.dumps(response))
        sys.exit(0)

    except Exception as e:
        # If anything goes wrong, still allow continuation
        response = {
            "continue": True,
            "reason": f"Subagent stop hook error: {e}"
        }
        print(json.dumps(response))
        sys.exit(0)


if __name__ == "__main__":
    main()