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
from typing import Dict, Tuple, Optional, List
from enum import Enum

from .file_lock import file_lock


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

    def __init__(self, storage_path: Path, session_id: str):
        """
        Initialize workflow enforcer.

        Args:
            storage_path: Base storage path for memories
            session_id: Current session ID
        """
        self.storage_path = storage_path
        self.session_id = session_id

    def _get_active_tasks_in_session(self) -> List[str]:
        """
        Get list of active tasks in current session.

        Returns:
            List of task names that have files in current session
        """
        active_tasks = []

        # Look for task directories with files for this session
        if self.storage_path.exists():
            for task_dir in self.storage_path.iterdir():
                if task_dir.is_dir():
                    task_name = task_dir.name
                    # Check if this task has any files for current session
                    session_files = list(task_dir.glob(f"*{self.session_id}*"))
                    if session_files:
                        # Consider any task with session files as active
                        # (even SETUP phase counts as active)
                        active_tasks.append(task_name)

        return active_tasks

    def get_task_files(self, task_name: str) -> Dict[FileType, Optional[Path]]:
        """
        Get paths for all task files.

        Args:
            task_name: Name of the task

        Returns:
            Dictionary mapping file types to paths (None if doesn't exist)
        """
        task_dir = self.storage_path / task_name
        files = {}

        for file_type in FileType:
            file_path = task_dir / f"{task_name}-{self.session_id}-{file_type.value}.md"
            files[file_type] = file_path if file_path.exists() else None

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

    def validate_action(self, task_name: str, action: str) -> Tuple[bool, str]:
        """
        Validate if an action is allowed in current phase.

        Args:
            task_name: Name of the task
            action: Action to validate ("scratchpad", "ensure", "append")

        Returns:
            Tuple of (is_valid, message)
        """
        # SINGLE-TASK-PER-SESSION ENFORCEMENT
        # Check if creating a new task when one already exists in this session
        if action == "scratchpad":
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

        current_phase, _ = self.get_workflow_phase(task_name)

        action_to_phase = {
            "scratchpad": [WorkflowPhase.SETUP, WorkflowPhase.DISCOVERY],
            "ensure": [WorkflowPhase.DISCOVERY, WorkflowPhase.PLANNING],
            "append": [WorkflowPhase.PLANNING, WorkflowPhase.EXECUTION]
        }

        allowed_phases = action_to_phase.get(action, [])

        if current_phase in allowed_phases:
            return True, f"Action '{action}' is valid for phase {current_phase.value}"
        else:
            return False, f"Action '{action}' not allowed in phase {current_phase.value}"

    def create_scratchpad(self, task_name: str, content: str = "") -> Path:
        """
        Create or update scratchpad file.

        Args:
            task_name: Name of the task
            content: Initial content

        Returns:
            Path to scratchpad file
        """
        task_dir = self.storage_path / task_name
        task_dir.mkdir(parents=True, exist_ok=True)

        scratchpad_path = task_dir / f"{task_name}-{self.session_id}-scratchpad.md"

        with file_lock(scratchpad_path):
            if content:
                with open(scratchpad_path, 'w') as f:
                    f.write(content)
            elif not scratchpad_path.exists():
                # Create empty scratchpad with template
                template = self._get_scratchpad_template(task_name)
                with open(scratchpad_path, 'w') as f:
                    f.write(template)

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

        # Check if plan already exists
        plan_path = self.storage_path / task_name / f"{task_name}-{self.session_id}-plan.md"
        if plan_path.exists():
            raise FileExistsError("Plan already exists and is immutable")

        task_dir = self.storage_path / task_name
        task_dir.mkdir(parents=True, exist_ok=True)

        with file_lock(plan_path):
            if content:
                with open(plan_path, 'w') as f:
                    f.write(content)
            else:
                # Create plan template with scratchpad reference
                template = self._get_plan_template(task_name)
                with open(plan_path, 'w') as f:
                    f.write(template)

            # Make plan file read-only (immutable)
            self._make_readonly(plan_path)

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
            ValueError: If no plan exists
        """
        files = self.get_task_files(task_name)

        # Ensure plan exists
        if not files[FileType.PLAN]:
            raise ValueError("Cannot track progress without plan")

        task_dir = self.storage_path / task_name
        task_dir.mkdir(parents=True, exist_ok=True)

        progress_path = task_dir / f"{task_name}-{self.session_id}-progress.md"

        with file_lock(progress_path):
            # Create progress file if it doesn't exist
            if not progress_path.exists():
                template = self._get_progress_template(task_name)
                with open(progress_path, 'w') as f:
                    f.write(template)

            # Append new content
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            entry = f"\n## Progress Update - {timestamp}\n\n{content}\n"

            with open(progress_path, 'a') as f:
                f.write(entry)

        return progress_path

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

    def _make_readonly(self, file_path: Path) -> None:
        """Make file read-only."""
        current_permissions = file_path.stat().st_mode
        readonly_permissions = current_permissions & ~(stat.S_IWUSR | stat.S_IWGRP | stat.S_IWOTH)
        file_path.chmod(readonly_permissions)

    def _is_readonly(self, file_path: Path) -> bool:
        """Check if file is read-only."""
        return not os.access(file_path, os.W_OK)

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