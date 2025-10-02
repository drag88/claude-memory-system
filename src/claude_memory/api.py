"""
Python API for Claude Memory System.

Provides a convenient Python interface for direct integration.
"""

from pathlib import Path
from typing import Dict, Any, Optional, List, TYPE_CHECKING

from .core.memory_manager import MemoryManager
from .core.context_manager import ProjectContext

if TYPE_CHECKING:
    from claude_memory.backends import BackendType, MemoryBackend


class MemoryAPI:
    """
    High-level Python API for Claude Memory System.

    This class provides a convenient interface for Python applications
    that want to integrate with the memory system directly.
    """

    def __init__(
        self,
        storage_path: Optional[Path] = None,
        backend_type: Optional["BackendType"] = None,
        backend: Optional["MemoryBackend"] = None
    ):
        """
        Initialize Memory API.

        Args:
            storage_path: Custom storage path (defaults to auto-resolved)
            backend_type: Type of backend to use (defaults to AUTO detection)
            backend: Pre-configured backend instance (overrides backend_type)
        """
        self.manager = MemoryManager(storage_path, backend_type=backend_type, backend=backend)
        self.project_context = ProjectContext()
        self.backend = self.manager.backend

    # Task Memory Operations
    def scratchpad(self, task_name: str, content: str = "") -> Dict[str, Any]:
        """
        Create or update task scratchpad.

        Args:
            task_name: Name of the task
            content: Initial or additional content

        Returns:
            Operation result dictionary
        """
        return self.manager.task_memory_enforcer(task_name, "scratchpad", content)

    def plan(self, task_name: str, content: str = "") -> Dict[str, Any]:
        """
        Create implementation plan (write-once).

        Args:
            task_name: Name of the task
            content: Plan content

        Returns:
            Operation result dictionary
        """
        return self.manager.task_memory_enforcer(task_name, "ensure", content)

    def append(self, task_name: str, content: str) -> Dict[str, Any]:
        """
        Append progress update.

        Args:
            task_name: Name of the task
            content: Progress update content

        Returns:
            Operation result dictionary
        """
        return self.manager.task_memory_enforcer(task_name, "append", content)

    # Session Management
    def get_current_session(self) -> Optional[str]:
        """Get current session ID."""
        return self.manager.session_manager.get_current_session()

    def create_session(self, metadata: Optional[Dict[str, Any]] = None) -> str:
        """
        Create new session.

        Args:
            metadata: Optional session metadata

        Returns:
            New session ID
        """
        return self.manager.session_manager.create_session(metadata)

    def get_session_info(self, session_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Get session information.

        Args:
            session_id: Session ID (defaults to current)

        Returns:
            Session information dictionary
        """
        return self.manager.session_manager_action("info")

    def list_sessions(self, limit: int = 10) -> List[Dict[str, Any]]:
        """
        List recent sessions.

        Args:
            limit: Maximum number of sessions

        Returns:
            List of session dictionaries
        """
        result = self.manager.session_manager_action("list", limit=limit)
        return result.get("sessions", []) if result["success"] else []

    # Task Management
    def get_task_status(self, task_name: str) -> Dict[str, Any]:
        """
        Get task status.

        Args:
            task_name: Name of the task

        Returns:
            Task status dictionary
        """
        return self.manager.get_task_status(task_name)

    def list_tasks(self) -> List[Dict[str, Any]]:
        """
        List all tasks in current session.

        Returns:
            List of task dictionaries
        """
        result = self.manager.list_tasks()
        return result.get("tasks", []) if result["success"] else []

    def get_task_files(self, task_name: str) -> Dict[str, Optional[str]]:
        """
        Get file paths for a task.

        Args:
            task_name: Name of the task

        Returns:
            Dictionary mapping file types to paths
        """
        status = self.get_task_status(task_name)
        return status.get("files", {}) if status["success"] else {}

    def get_session_context_injection(self) -> str:
        """
        Get context injection text for current session.

        Returns:
            Context injection text for agent prompts
        """
        try:
            # Get workflow enforcer to access context-aware components
            enforcer = self.manager._get_enforcer()

            if hasattr(enforcer, 'session_manager') and enforcer.session_manager:
                # Try to get active task
                active_task = enforcer.session_manager.context_loader.get_active_task()
                if active_task:
                    return enforcer.session_manager.get_context_injection_text(active_task)

            return ""  # No context to inject
        except Exception:
            return ""  # Fail silently

    def read_task_file(self, task_name: str, file_type: str) -> Optional[str]:
        """
        Read content of a task file.

        Args:
            task_name: Name of the task
            file_type: File type ("scratchpad", "plan", "progress")

        Returns:
            File content or None if not found
        """
        files = self.get_task_files(task_name)
        file_path = files.get(file_type)

        if file_path and Path(file_path).exists():
            return Path(file_path).read_text()

        return None

    # Workflow Operations
    def get_current_phase(self, task_name: str) -> str:
        """
        Get current workflow phase for task.

        Args:
            task_name: Name of the task

        Returns:
            Current phase name
        """
        status = self.get_task_status(task_name)
        return status.get("current_phase", "UNKNOWN") if status["success"] else "ERROR"

    def get_next_steps(self, task_name: str) -> Dict[str, str]:
        """
        Get recommended next steps for task.

        Args:
            task_name: Name of the task

        Returns:
            Next steps dictionary
        """
        status = self.get_task_status(task_name)
        return status.get("next_steps", {}) if status["success"] else {}

    def validate_task(self, task_name: str) -> List[str]:
        """
        Validate task integrity.

        Args:
            task_name: Name of the task

        Returns:
            List of validation issues (empty if valid)
        """
        status = self.get_task_status(task_name)
        return status.get("validation_issues", []) if status["success"] else ["Task not found"]

    # Context for Sub-Agents
    def get_context_for_subagent(self) -> Dict[str, Any]:
        """
        Get context information for sub-agent coordination.

        Returns:
            Context dictionary for sub-agents
        """
        return self.manager.get_task_context()

    def inject_memory_instructions(self, task_name: str) -> str:
        """
        Generate memory instructions for sub-agents.

        Args:
            task_name: Name of the task

        Returns:
            Memory instruction template
        """
        context = self.get_context_for_subagent()
        status = self.get_task_status(task_name)
        current_phase = status.get("current_phase", "UNKNOWN") if status["success"] else "UNKNOWN"

        return f"""
## Memory Coordination
Task: {task_name}
Session: {context['session_id']}
Current Phase: {current_phase}

Use these commands for memory operations:
1. Discovery: `claude-memory scratchpad "{task_name}" --content "your exploration"`
2. Planning: `claude-memory plan "{task_name}"`
3. Progress: `claude-memory append "{task_name}" "progress update"`

IMPORTANT: All memory operations use the globally installed claude-memory CLI.
Storage Path: {context['storage_path']}
"""

    # Project Context Operations
    def get_project_context(self) -> str:
        """
        Get formatted project context for session initialization.

        Returns:
            Formatted project context string
        """
        return self.project_context.get_session_context()

    def refresh_project_context(self) -> Dict[str, Any]:
        """
        Force refresh of project context.

        Returns:
            Updated project context data
        """
        return self.project_context.refresh_context()

    def clear_project_context(self) -> bool:
        """
        Clear cached project context.

        Returns:
            True if cleared successfully
        """
        return self.project_context.clear_context()

    def get_project_info(self) -> Dict[str, Any]:
        """
        Get detailed project information and metrics.

        Returns:
            Comprehensive project information dictionary
        """
        return self.project_context._gather_context(force_refresh=False)

    def get_project_commands(self) -> Dict[str, str]:
        """
        Get available project commands.

        Returns:
            Dictionary of command types to commands
        """
        context_data = self.project_context._load_or_gather_context()
        return context_data.get("available_commands", {})

    def get_project_structure(self) -> str:
        """
        Get project directory structure.

        Returns:
            Formatted directory structure string
        """
        context_data = self.project_context._load_or_gather_context()
        return context_data.get("directory_structure", "")

    def get_project_tech_stack(self) -> List[str]:
        """
        Get detected technology stack.

        Returns:
            List of detected technologies
        """
        context_data = self.project_context._load_or_gather_context()
        return context_data.get("tech_stack", [])

    def get_enhanced_session_context(self) -> str:
        """
        Get enhanced session context combining memory and project information.

        Returns:
            Complete session context string for Claude initialization
        """
        # Get memory context
        memory_context = self.get_context_for_subagent()
        tasks = self.list_tasks()
        current_session = self.get_current_session()

        # Get project context
        project_context_text = self.project_context.get_session_context()

        # Combine into enhanced context
        enhanced_context = f"""## 🧠 Memory System Active

Sub-Agent Context:
Session ID: {current_session}
Storage Path: {memory_context['storage_path']}
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

        return enhanced_context

    # Utility Operations
    def cleanup(self, max_age_days: int = 30) -> Dict[str, Any]:
        """
        Clean up old sessions and stale locks.

        Args:
            max_age_days: Maximum age for cleanup

        Returns:
            Cleanup results dictionary
        """
        return self.manager.cleanup(max_age_days)

    def get_storage_path(self) -> str:
        """Get current storage path."""
        return str(self.manager.storage_path)

    def is_initialized(self) -> bool:
        """Check if memory system is initialized for current project."""
        return self.manager.storage_path.exists()

    # Context Managers
    def task_context(self, task_name: str):
        """
        Context manager for task operations.

        Args:
            task_name: Name of the task

        Returns:
            Task context manager
        """
        return TaskContext(self, task_name)


class TaskContext:
    """Context manager for task-specific operations."""

    def __init__(self, api: MemoryAPI, task_name: str):
        self.api = api
        self.task_name = task_name
        self._initial_phase = None

    def __enter__(self):
        """Enter task context."""
        status = self.api.get_task_status(self.task_name)
        self._initial_phase = status.get("current_phase") if status["success"] else None
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Exit task context."""
        # Could add cleanup or validation here
        pass

    def scratchpad(self, content: str = "") -> Dict[str, Any]:
        """Add to scratchpad."""
        return self.api.scratchpad(self.task_name, content)

    def plan(self, content: str = "") -> Dict[str, Any]:
        """Create plan."""
        return self.api.plan(self.task_name, content)

    def append(self, content: str) -> Dict[str, Any]:
        """Append progress."""
        return self.api.append(self.task_name, content)

    def status(self) -> Dict[str, Any]:
        """Get status."""
        return self.api.get_task_status(self.task_name)

    def phase(self) -> str:
        """Get current phase."""
        return self.api.get_current_phase(self.task_name)

    def files(self) -> Dict[str, Optional[str]]:
        """Get file paths."""
        return self.api.get_task_files(self.task_name)

    def read(self, file_type: str) -> Optional[str]:
        """Read file content."""
        return self.api.read_task_file(self.task_name, file_type)


# Convenience functions for direct import
def scratchpad(task_name: str, content: str = "") -> Dict[str, Any]:
    """Quick scratchpad operation."""
    api = MemoryAPI()
    return api.scratchpad(task_name, content)


def plan(task_name: str, content: str = "") -> Dict[str, Any]:
    """Quick plan operation."""
    api = MemoryAPI()
    return api.plan(task_name, content)


def append(task_name: str, content: str) -> Dict[str, Any]:
    """Quick append operation."""
    api = MemoryAPI()
    return api.append(task_name, content)


def status(task_name: str) -> Dict[str, Any]:
    """Quick status check."""
    api = MemoryAPI()
    return api.get_task_status(task_name)