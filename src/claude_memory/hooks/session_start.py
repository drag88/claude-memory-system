#!/usr/bin/env python3
"""
Session start hook for Claude Code integration.

Initializes memory system when Claude Code session starts.
"""

import json
import sys
from pathlib import Path
from datetime import datetime

try:
    from claude_memory import MemoryAPI
    from claude_memory.core.context_manager import ProjectContext
except ImportError:
    # If package not installed, try to import from parent directory
    sys.path.insert(0, str(Path(__file__).parent.parent.parent))
    from claude_memory import MemoryAPI
    from claude_memory.core.context_manager import ProjectContext


def initialize_memory_session() -> dict:
    """
    Initialize memory system and project context for new Claude Code session.

    Returns:
        Context to add to Claude's session
    """
    try:
        api = MemoryAPI()

        # Check if memory system is initialized
        if not api.is_initialized():
            # Auto-initialize if not present
            storage_path = Path(api.get_storage_path())
            storage_path.mkdir(parents=True, exist_ok=True)

        # Get or create session
        current_session = api.get_current_session()
        if not current_session:
            current_session = api.create_session({
                "created_by": "claude_code_session_hook",
                "project_path": str(Path.cwd()),
                "initialized_at": datetime.now().isoformat()
            })

        # Get context information
        context = api.get_context_for_subagent()
        tasks = api.list_tasks()

        # Initialize project context
        project_context = ProjectContext()
        project_context_text = project_context.get_session_context()

        # Create combined session context for Claude
        session_context = f"""## 🧠 Memory System Active

Sub-Agent Context:
Session ID: {current_session}
Storage Path: {context['storage_path']}
Active Tasks: {'None' if len(tasks) == 0 else f"{len(tasks)} tasks in progress"}
╭───────────────────────────── Sub-Agent Commands ─────────────────────────────╮
│ Use these commands in sub-agents:                                            │
│                                                                              │
│ • claude-memory scratchpad "task-name" - Explore and research                │
│ • claude-memory plan "task-name" - Create implementation plan                │
│ • claude-memory append "task-name" "update" - Track progress                 │
│ • claude-memory status "task-name" - Check task status                       │
╰──────────────────────────────────────────────────────────────────────────────╯

{project_context_text}

### Available Memory Commands:
```bash
claude-memory status                    # Show all tasks
claude-memory scratchpad "task-name"    # Start exploration
claude-memory plan "task-name"          # Create implementation plan
claude-memory append "task-name" "..."  # Track progress
claude-memory session info              # Session details
```

### Three-Phase Workflow:
1. **DISCOVERY** → Mutable scratchpad for exploration
2. **PLANNING** → Write-once plan creation
3. **EXECUTION** → Append-only progress tracking

Use these commands throughout your work to maintain persistent memory across sessions.
"""

        return {
            "success": True,
            "session_id": current_session,
            "context": session_context,
            "storage_path": context['storage_path'],
            "task_count": len(tasks),
            "project_context": project_context_text
        }

    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "context": f"# Memory System Error\n\nFailed to initialize: {e}"
        }


def main():
    """Main hook function."""
    try:
        # Read input from Claude (if any)
        try:
            input_data = json.loads(sys.stdin.read()) if sys.stdin.readable() else {}
        except:
            input_data = {}

        # Initialize memory session
        init_result = initialize_memory_session()

        if init_result["success"]:
            # Return context to add to Claude's session
            response = {
                "additionalContext": init_result["context"],
                "continue": True,
                "metadata": {
                    "memory_session_id": init_result["session_id"],
                    "memory_storage_path": init_result["storage_path"],
                    "memory_task_count": init_result["task_count"]
                }
            }
        else:
            # If initialization failed, still continue but with error context
            response = {
                "additionalContext": init_result["context"],
                "continue": True,
                "error": init_result["error"]
            }

        print(json.dumps(response))
        sys.exit(0)

    except Exception as e:
        # If anything goes wrong, still allow session to start
        response = {
            "additionalContext": f"# Memory System Unavailable\n\nError: {e}",
            "continue": True,
            "error": str(e)
        }
        print(json.dumps(response))
        sys.exit(0)


if __name__ == "__main__":
    main()