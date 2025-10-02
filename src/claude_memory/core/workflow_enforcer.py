"""
Workflow enforcer for the three-phase memory system.

Validates phase transitions and enforces file immutability rules:
- Scratchpad: Mutable exploration
- Plan: Write-once, then immutable
- Progress: Append-only tracking
"""

import os
import stat
from datetime import datetime
from pathlib import Path
from typing import Dict, Tuple, Optional, List, TYPE_CHECKING
from enum import Enum

from .file_lock import file_lock

# Import backend abstraction
if TYPE_CHECKING:
    from claude_memory.backends import MemoryBackend


# Import context-aware components (will be available after they're created)
try:
    from .session_workflow_manager import SessionWorkflowManager
    from .context_loader import WorkflowContextLoader
    CONTEXT_AWARE_ENABLED = True
except ImportError:
    # Graceful fallback if context components not available yet
    SessionWorkflowManager = None
    WorkflowContextLoader = None
    CONTEXT_AWARE_ENABLED = False


class WorkflowPhase(Enum):
    """Workflow phases."""
    SETUP = "SETUP"
    DISCOVERY = "DISCOVERY"
    PLANNING = "PLANNING"
    EXECUTION = "EXECUTION"
    INVALID = "INVALID"


class FileType(Enum):
    """Memory file types."""
    SCRATCHPAD = "scratchpad"
    PLAN = "plan"
    PROGRESS = "progress"


class WorkflowEnforcer:
    """Enforces three-phase workflow rules and file immutability."""

    def __init__(self, storage_path: Path, session_id: str, backend: Optional["MemoryBackend"] = None, session_folder: Optional[Path] = None):
        """
        Initialize workflow enforcer.

        Args:
            storage_path: Base storage path for memories
            session_id: Current session ID
            backend: Optional memory backend (defaults to FileBackend)
            session_folder: Optional session folder path (for named sessions)
        """
        self.base_storage_path = storage_path
        self.session_id = session_id
        self.session_folder = session_folder

        # Use session folder if provided, otherwise use base storage path
        self.storage_path = session_folder if session_folder else storage_path

        # Initialize backend
        if backend is None:
            # Default to FileBackend for backward compatibility
            from claude_memory.backends import create_backend, BackendType
            self.backend = create_backend(BackendType.FILE, self.base_storage_path)
        else:
            self.backend = backend

        # Initialize context-aware components if available
        if CONTEXT_AWARE_ENABLED:
            self.session_manager = SessionWorkflowManager(self.storage_path, session_id)
            self.context_loader = WorkflowContextLoader(self.storage_path, session_id)
        else:
            self.session_manager = None
            self.context_loader = None

    def _get_active_tasks_in_session(self) -> List[str]:
        """
        Get list of active tasks in current session.

        Returns:
            List of task names that have files in current session
        """
        active_tasks = []

        # System directories that should not be considered as tasks
        system_dirs = {'.context', 'sessions', '.git', '.DS_Store'}

        # Look for task directories with files for this session using backend
        if self.backend.exists(self.storage_path):
            task_dirs = self.backend.list_directory(self.storage_path)
            for task_dir in task_dirs:
                if task_dir.is_dir() and task_dir.name not in system_dirs:
                    task_name = task_dir.name
                    # Check if this task has any files for current session
                    task_files = self.backend.list_directory(task_dir)
                    session_files = [f for f in task_files if self.session_id in f.name]
                    if session_files:
                        # Consider any task with session files as active
                        active_tasks.append(task_name)

        return active_tasks

    def _get_agent_info(self) -> str:
        """
        Get agent identification information.

        Returns:
            String identifying the current agent
        """
        import os
        import sys

        # First, check environment variables that might be set by Claude Code
        env_vars = [
            'CLAUDE_SUBAGENT_TYPE',
            'CLAUDE_AGENT_TYPE',
            'CLAUDE_AGENT_NAME',
            'ANTHROPIC_AGENT_TYPE',
            'TASK_AGENT_TYPE'
        ]

        for var in env_vars:
            value = os.getenv(var)
            if value:
                return value

        # Check if we can detect from process info or command line
        try:
            import psutil
            current_process = psutil.Process()
            cmdline = ' '.join(current_process.cmdline())

            # Look for agent names in command line
            if 'system-architect' in cmdline:
                return 'system-architect'
            elif 'python-expert' in cmdline:
                return 'python-expert'
            elif 'refactoring-expert' in cmdline:
                return 'refactoring-expert'
        except:
            pass

        # If in a subagent context but no specific type identified
        if os.getenv('CLAUDE_IS_SUBAGENT'):
            return "Sub-agent"

        # Default fallback
        return "Main Agent"

    def get_task_files(self, task_name: str) -> Dict[FileType, Optional[Path]]:
        """
        Get paths for all task files.

        Args:
            task_name: Name of the task

        Returns:
            Dictionary mapping file types to paths (None if doesn't exist)
        """
        # If we have a session folder, files go directly there (no task subfolder)
        if self.session_folder:
            task_dir = self.storage_path
            # Simplified naming when using session folders
            files = {}
            for file_type in FileType:
                file_path = task_dir / f"{file_type.value}.md"
                files[file_type] = file_path if self.backend.exists(file_path) else None
        else:
            # Legacy behavior: task subfolder with full names
            task_dir = self.storage_path / task_name
            files = {}
            for file_type in FileType:
                file_path = task_dir / f"{task_name}-{self.session_id}-{file_type.value}.md"
                files[file_type] = file_path if self.backend.exists(file_path) else None

        return files

    def get_workflow_phase(self, task_name: str) -> Tuple[WorkflowPhase, str]:
        """
        Determine current workflow phase for task.

        Args:
            task_name: Name of the task

        Returns:
            Tuple of (phase, description)
        """
        files = self.get_task_files(task_name)

        scratchpad = files[FileType.SCRATCHPAD]
        plan = files[FileType.PLAN]
        progress = files[FileType.PROGRESS]

        # Phase determination logic
        if not any(files.values()):
            return WorkflowPhase.SETUP, "No files created - start with scratchpad"

        elif scratchpad and not plan and not progress:
            return WorkflowPhase.DISCOVERY, "Scratchpad exists - continue exploration or create plan"

        elif scratchpad and plan and not progress:
            return WorkflowPhase.PLANNING, "Plan created - ready to begin execution"

        elif plan and progress:
            return WorkflowPhase.EXECUTION, "Implementation in progress"

        elif not scratchpad and plan:
            return WorkflowPhase.INVALID, "Plan exists without scratchpad - invalid state"

        else:
            return WorkflowPhase.INVALID, "Inconsistent file state"

    def validate_action(self, task_name: str, action: str, content: str = "") -> Tuple[bool, str]:
        """
        Enhanced validation with context-aware workflow enforcement.

        Args:
            task_name: Name of the task
            action: Action to validate ("scratchpad", "ensure", "append")
            content: Content to be contributed (for duplication checking)

        Returns:
            Tuple of (is_valid, message)
        """
        # CONTEXT-AWARE VALIDATION (if available)
        if CONTEXT_AWARE_ENABLED and self.session_manager:
            # Check workflow continuity and validate contribution
            is_valid, message = self.session_manager.validate_contribution(task_name, content, action)
            if not is_valid:
                return False, message

            # For new task creation, enforce workflow claim
            current_phase, _ = self.get_workflow_phase(task_name)
            if current_phase == WorkflowPhase.SETUP and action == "scratchpad":
                claim_success, claim_message = self.session_manager.claim_workflow(task_name)
                if not claim_success:
                    return False, claim_message

        # LEGACY SINGLE-TASK-PER-SESSION ENFORCEMENT (fallback)
        elif action == "scratchpad":
            # Get phase before any files are created
            current_phase, _ = self.get_workflow_phase(task_name)
            print(f"DEBUG: Task '{task_name}' current phase: {current_phase}")
            if current_phase == WorkflowPhase.SETUP:  # New task being created
                # Check for existing active tasks in session
                existing_tasks = self._get_active_tasks_in_session()
                print(f"DEBUG: Existing tasks: {existing_tasks}")
                # Filter out the current task we're trying to create
                other_tasks = [t for t in existing_tasks if t != task_name]
                print(f"DEBUG: Other tasks: {other_tasks}")
                if other_tasks:
                    active_task_names = ", ".join(other_tasks)
                    return False, f"Single-task-per-session rule: Active task(s) '{active_task_names}' exist. Complete current task before starting '{task_name}'"

        current_phase, phase_desc = self.get_workflow_phase(task_name)

        # Define strict phase-to-action mapping with actionable guidance
        phase_rules = {
            WorkflowPhase.SETUP: {
                "allowed": ["scratchpad"],
                "blocked": ["ensure", "append"],
                "guidance": {
                    "ensure": f"❌ Cannot create plan yet! Start with exploration: claude-memory scratchpad '{task_name}' --content 'exploration notes'",
                    "append": f"❌ Cannot track progress yet! Start with exploration: claude-memory scratchpad '{task_name}' --content 'exploration notes'"
                },
                "success": "✓ Starting discovery phase with scratchpad"
            },
            WorkflowPhase.DISCOVERY: {
                "allowed": ["scratchpad", "ensure"],
                "blocked": ["append"],
                "guidance": {
                    "append": f"❌ Cannot track progress yet! Complete discovery, then create plan: claude-memory plan '{task_name}' --content 'implementation plan'"
                },
                "success": "✓ Continue exploration or create implementation plan"
            },
            WorkflowPhase.PLANNING: {
                "allowed": ["append", "ensure"],
                "blocked": ["scratchpad"],
                "guidance": {
                    "scratchpad": f"❌ Discovery phase is complete! Review/edit plan or begin execution: claude-memory edit-plan '{task_name}' or claude-memory append '{task_name}' 'progress update'"
                },
                "success": "✓ Plan is ready for review. You can edit it or begin execution"
            },
            WorkflowPhase.EXECUTION: {
                "allowed": ["append"],
                "blocked": ["scratchpad", "ensure"],
                "guidance": {
                    "scratchpad": f"❌ Discovery phase is complete! Continue implementation: claude-memory append '{task_name}' 'progress update'",
                    "ensure": f"❌ Plan is locked and execution has started! Continue implementation: claude-memory append '{task_name}' 'progress update'"
                },
                "success": "✓ Continue tracking progress with append"
            },
            WorkflowPhase.INVALID: {
                "allowed": [],
                "blocked": ["scratchpad", "ensure", "append"],
                "guidance": {
                    "scratchpad": f"❌ Invalid state detected! Check task status: claude-memory status '{task_name}'",
                    "ensure": f"❌ Invalid state detected! Check task status: claude-memory status '{task_name}'",
                    "append": f"❌ Invalid state detected! Check task status: claude-memory status '{task_name}'"
                },
                "success": "Manual review required"
            }
        }

        rules = phase_rules.get(current_phase, phase_rules[WorkflowPhase.INVALID])

        # Check if action is blocked in current phase
        if action in rules["blocked"]:
            return False, rules["guidance"].get(action, f"Action '{action}' not allowed in {current_phase.value} phase")

        # Check if action is allowed
        if action not in rules["allowed"]:
            return False, f"❌ Invalid action '{action}' for {current_phase.value} phase. Current state: {phase_desc}"

        # Action is valid
        return True, rules["success"]

    def create_scratchpad(self, task_name: str, content: str = "") -> Path:
        """
        Create or update scratchpad file.

        Args:
            task_name: Name of the task
            content: Initial content

        Returns:
            Path to scratchpad file
        """
        # Use session folder if available, otherwise create task folder
        if self.session_folder:
            task_dir = self.storage_path
            scratchpad_path = task_dir / "scratchpad.md"
        else:
            task_dir = self.storage_path / task_name
            task_dir.mkdir(parents=True, exist_ok=True)
            scratchpad_path = task_dir / f"{task_name}-{self.session_id}-scratchpad.md"

        with file_lock(scratchpad_path):
            if not self.backend.exists(scratchpad_path):
                # Create new scratchpad with template and initial content
                template = self._get_scratchpad_template(task_name)
                initial_content = template
                if content:
                    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    agent_info = self._get_agent_info()
                    initial_content += f"\n## Initial Content - {agent_info} - {timestamp}\n\n{content}\n"
                self.backend.write(scratchpad_path, initial_content)
            elif content:
                # Append to existing scratchpad (collaborative/mutable)
                timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                agent_info = self._get_agent_info()
                entry = f"\n## Update - {agent_info} - {timestamp}\n\n{content}\n"
                self.backend.append(scratchpad_path, entry)

        return scratchpad_path

    def create_plan(self, task_name: str, content: str = "") -> Path:
        """
        Create plan file (write-once).

        Args:
            task_name: Name of the task
            content: Plan content

        Returns:
            Path to plan file

        Raises:
            FileExistsError: If plan already exists
            ValueError: If no scratchpad exists
        """
        files = self.get_task_files(task_name)

        # Ensure scratchpad exists
        if not files[FileType.SCRATCHPAD]:
            raise ValueError("Cannot create plan without scratchpad")

        # Determine plan path based on session folder
        if self.session_folder:
            plan_path = self.storage_path / "plan.md"
            task_dir = self.storage_path
        else:
            plan_path = self.storage_path / task_name / f"{task_name}-{self.session_id}-plan.md"
            task_dir = self.storage_path / task_name
            task_dir.mkdir(parents=True, exist_ok=True)

        # Check if plan already exists
        if self.backend.exists(plan_path):
            raise FileExistsError("Plan already exists and is immutable")

        with file_lock(plan_path):
            if content:
                self.backend.write(plan_path, content)
            else:
                # Create plan template with scratchpad reference
                template = self._get_plan_template(task_name)
                self.backend.write(plan_path, template)

            # Create phase transition lock to PLANNING phase
            # Note: Plan remains editable until execution starts
            self.lock_phase_transition(task_name, WorkflowPhase.DISCOVERY, WorkflowPhase.PLANNING)

        return plan_path

    def append_progress(self, task_name: str, content: str) -> Path:
        """
        Append to progress file.

        Args:
            task_name: Name of the task
            content: Content to append

        Returns:
            Path to progress file

        Raises:
            ValueError: If no plan exists or agent hasn't acknowledged existing plan
        """
        files = self.get_task_files(task_name)

        # Ensure plan exists
        if not files[FileType.PLAN]:
            raise ValueError("Cannot track progress without plan")

        # Read existing plan for validation using backend
        plan_path = files[FileType.PLAN]
        plan_content = ""
        if plan_path and self.backend.exists(plan_path):
            plan_content = self.backend.read(plan_path) or ""

        # Check if this is a subsequent agent (not the plan creator)
        agent_info = self._get_agent_info()

        # Determine progress path based on session folder
        if self.session_folder:
            progress_path = self.storage_path / "progress.md"
            task_dir = self.storage_path
        else:
            progress_path = self.storage_path / task_name / f"{task_name}-{self.session_id}-progress.md"
            task_dir = self.storage_path / task_name
            task_dir.mkdir(parents=True, exist_ok=True)

        # If progress file exists and this agent hasn't contributed yet, require plan acknowledgment
        if self.backend.exists(progress_path):
            existing_progress = self.backend.read(progress_path) or ""
            if agent_info not in existing_progress:
                # This is a new agent joining - require plan acknowledgment
                plan_keywords = ["plan", "strategy", "approach", "based on", "following", "according to"]
                if not any(keyword in content.lower() for keyword in plan_keywords):
                    plan_summary = plan_content[:300] + "..." if len(plan_content) > 300 else plan_content
                    raise ValueError(
                        f"Multi-agent workflow violation: New agent '{agent_info}' must acknowledge existing plan before contributing.\n"
                        f"Current plan summary:\n{plan_summary}\n\n"
                        f"Include plan references like: 'Following the established plan...', 'Based on the plan strategy...', etc."
                    )

        with file_lock(progress_path):
            # Create progress file if it doesn't exist
            if not self.backend.exists(progress_path):
                # This is the first progress entry - lock the plan now for execution phase
                plan_path = files[FileType.PLAN]
                if plan_path and not self.backend.is_readonly(plan_path):
                    self.backend.make_readonly(plan_path)
                    print(f"✓ Plan locked for execution phase")

                template = self._get_progress_template(task_name)
                self.backend.write(progress_path, template)

                # Create phase transition lock to EXECUTION phase (first progress entry)
                self.lock_phase_transition(task_name, WorkflowPhase.PLANNING, WorkflowPhase.EXECUTION)

            # Append new content
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            entry = f"\n## Progress Update - {agent_info} - {timestamp}\n\n{content}\n"

            self.backend.append(progress_path, entry)

        return progress_path

    def update_plan(self, task_name: str, content: str) -> Path:
        """
        Update plan content during PLANNING phase only.

        Args:
            task_name: Name of the task
            content: Updated plan content

        Returns:
            Path to updated plan file

        Raises:
            ValueError: If not in PLANNING phase or plan is locked
        """
        current_phase, _ = self.get_workflow_phase(task_name)

        if current_phase != WorkflowPhase.PLANNING:
            raise ValueError(
                f"❌ Cannot edit plan in {current_phase.value} phase. "
                f"Plan editing is only allowed during PLANNING phase."
            )

        files = self.get_task_files(task_name)
        plan_path = files[FileType.PLAN]

        if not plan_path:
            raise ValueError("No plan exists to update")

        # Check if plan is already locked (shouldn't be in PLANNING phase)
        if self.backend.is_readonly(plan_path):
            raise ValueError("Plan is locked and cannot be edited")

        # Update plan content
        with file_lock(plan_path):
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            agent_info = self._get_agent_info()

            # Add revision marker if this is an update (not initial creation)
            if content and not content.startswith("# "):  # Simple heuristic for updates vs full content
                original_content = self.backend.read(plan_path) or ""
                if "## Revision History" not in original_content:
                    content += f"\n\n## Revision History\n"
                content += f"\n### Revised - {agent_info} - {timestamp}\n"

            self.backend.write(plan_path, content)

        return plan_path

    def get_next_steps(self, task_name: str) -> Dict[str, str]:
        """
        Get recommended next steps for current phase.

        Args:
            task_name: Name of the task

        Returns:
            Dictionary with next step information
        """
        current_phase, phase_message = self.get_workflow_phase(task_name)

        next_steps = {
            WorkflowPhase.SETUP: {
                "action": "Create scratchpad",
                "command": f'claude-memory scratchpad "{task_name}"',
                "description": "Start with exploration and research"
            },
            WorkflowPhase.DISCOVERY: {
                "action": "Create plan or continue exploration",
                "command": f'claude-memory plan "{task_name}"',
                "description": "Convert scratchpad insights into implementation plan"
            },
            WorkflowPhase.PLANNING: {
                "action": "Begin execution",
                "command": f'claude-memory append "{task_name}" "Starting implementation"',
                "description": "Start implementing according to plan"
            },
            WorkflowPhase.EXECUTION: {
                "action": "Continue implementation",
                "command": f'claude-memory append "{task_name}" "Progress update"',
                "description": "Track implementation progress"
            },
            WorkflowPhase.INVALID: {
                "action": "Manual review required",
                "command": f'claude-memory status "{task_name}"',
                "description": "Fix inconsistent file state"
            }
        }

        return next_steps.get(current_phase, next_steps[WorkflowPhase.INVALID])

    def validate_file_integrity(self, task_name: str) -> List[str]:
        """
        Validate file integrity and workflow compliance.

        Args:
            task_name: Name of the task

        Returns:
            List of validation issues (empty if valid)
        """
        issues = []
        files = self.get_task_files(task_name)

        # Check for orphaned files
        if files[FileType.PLAN] and not files[FileType.SCRATCHPAD]:
            issues.append("Plan exists without scratchpad")

        if files[FileType.PROGRESS] and not files[FileType.PLAN]:
            issues.append("Progress exists without plan")

        # Check file permissions
        if files[FileType.PLAN] and not self._is_readonly(files[FileType.PLAN]):
            issues.append("Plan file is not read-only (should be immutable)")

        # Check file content requirements
        for file_type, file_path in files.items():
            if file_path and file_path.stat().st_size == 0:
                issues.append(f"{file_type.value} file is empty")

        return issues

    def lock_phase_transition(self, task_name: str, from_phase: WorkflowPhase, to_phase: WorkflowPhase) -> None:
        """
        Create a phase transition lock to make transitions intentional.

        Args:
            task_name: Name of the task
            from_phase: Phase transitioning from
            to_phase: Phase transitioning to
        """
        # Use session folder if available, otherwise create task folder
        if self.session_folder:
            task_dir = self.storage_path
        else:
            task_dir = self.storage_path / task_name
            task_dir.mkdir(parents=True, exist_ok=True)

        lock_file = task_dir / f".phase_{to_phase.value.lower()}_lock"
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        agent_info = self._get_agent_info()

        lock_content = f"""Phase transition lock
Transitioned: {from_phase.value} → {to_phase.value}
Agent: {agent_info}
Timestamp: {timestamp}
Session: {self.session_id}
"""

        self.backend.write(lock_file, lock_content)

    def check_phase_locks(self, task_name: str) -> Dict[WorkflowPhase, Optional[str]]:
        """
        Check existing phase transition locks.

        Args:
            task_name: Name of the task

        Returns:
            Dictionary mapping phases to lock timestamps (None if no lock)
        """
        locks = {}

        # Use session folder if available, otherwise use task folder
        if self.session_folder:
            task_dir = self.storage_path
        else:
            task_dir = self.storage_path / task_name

        if not self.backend.exists(task_dir):
            return {phase: None for phase in WorkflowPhase}

        for phase in WorkflowPhase:
            lock_file = task_dir / f".phase_{phase.value.lower()}_lock"
            if self.backend.exists(lock_file):
                try:
                    content = self.backend.read(lock_file) or ""
                    # Extract timestamp from lock content
                    for line in content.split('\n'):
                        if line.startswith('Timestamp:'):
                            locks[phase] = line.replace('Timestamp:', '').strip()
                            break
                    else:
                        locks[phase] = "Lock exists (no timestamp)"
                except:
                    locks[phase] = "Lock file corrupted"
            else:
                locks[phase] = None

        return locks

    def _make_readonly(self, file_path: Path) -> None:
        """Make file read-only using backend."""
        self.backend.make_readonly(file_path)

    def _is_readonly(self, file_path: Path) -> bool:
        """Check if file is read-only using backend."""
        return self.backend.is_readonly(file_path)

    def _get_scratchpad_template(self, task_name: str) -> str:
        """Get scratchpad template."""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        return f"""# {task_name} - Discovery Scratchpad

**Created:** {timestamp}
**Session:** {self.session_id}

## Exploration Notes

<!-- Use this space for messy exploration, questions, dead ends, and discoveries -->

## Questions

## Findings

## Next Steps

"""

    def _get_plan_template(self, task_name: str) -> str:
        """Get plan template."""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        return f"""# {task_name} - Implementation Plan

**Created:** {timestamp}
**Session:** {self.session_id}
**Based on:** scratchpad discoveries

## Problem Statement

## Solution Approach

## Implementation Steps

1.
2.
3.

## Success Criteria

"""

    def _get_progress_template(self, task_name: str) -> str:
        """Get progress template."""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        return f"""# {task_name} - Progress Tracking

**Started:** {timestamp}
**Session:** {self.session_id}

## Implementation Progress

<!-- Progress updates will be appended below -->
"""