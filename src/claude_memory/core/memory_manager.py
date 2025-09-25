"""
Core memory manager for Claude Memory System.

Provides the main interface for all memory operations, coordinating
session management, workflow enforcement, and file operations.
"""

import os
from pathlib import Path
from typing import Dict, Optional, Any, List, Tuple
from datetime import datetime

from .session_manager import SessionManager
from .workflow_enforcer import WorkflowEnforcer, WorkflowPhase, FileType
from .file_lock import file_lock, cleanup_stale_locks


class MemoryManager:
    """Main interface for Claude Memory System operations."""

    def __init__(self, storage_path: Optional[Path] = None):
        """
        Initialize memory manager.

        Args:
            storage_path: Custom storage path (defaults to auto-resolved)
        """
        self.session_manager = SessionManager(storage_path)
        self.storage_path = self.session_manager.storage_path

    def _get_enforcer(self) -> WorkflowEnforcer:
        """Get workflow enforcer for current session."""
        session_id = self.session_manager.get_current_session()
        if not session_id:
            # Auto-create session if none exists
            session_id = self.session_manager.create_session()

        return WorkflowEnforcer(self.storage_path, session_id)

    def validate_phase_transition(self, task_name: str, intended_action: str) -> Dict[str, Any]:
        """
        Pre-validate action with enhanced guidance for CLI.

        Args:
            task_name: Name of the task
            intended_action: Action to validate before execution

        Returns:
            Dictionary with validation result and guidance
        """
        enforcer = self._get_enforcer()

        try:
            current_phase, phase_desc = enforcer.get_workflow_phase(task_name)
            is_valid, message = enforcer.validate_action(task_name, intended_action)

            return {
                "valid": is_valid,
                "current_phase": current_phase.value,
                "phase_description": phase_desc,
                "message": message,
                "task_name": task_name
            }
        except Exception as e:
            return {
                "valid": False,
                "current_phase": "UNKNOWN",
                "phase_description": "Error detecting phase",
                "message": f"Phase validation failed: {str(e)}",
                "task_name": task_name
            }

    def task_memory_enforcer(
        self,
        task_name: str,
        action: str,
        content: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Main memory enforcement function - equivalent to mcp__serena__task_memory_enforcer.

        Args:
            task_name: Name of the task
            action: Action to perform ("scratchpad", "ensure", "append")
            content: Content for the action

        Returns:
            Dictionary with operation results
        """
        enforcer = self._get_enforcer()

        try:
            # Validate action
            is_valid, message = enforcer.validate_action(task_name, action)
            if not is_valid:
                return {
                    "success": False,
                    "error": message,
                    "task_name": task_name,
                    "action": action,
                    "current_phase": enforcer.get_workflow_phase(task_name)[0].value
                }

            # Update session with active task
            self.session_manager.update_session_tasks(task_name, "add")

            # Perform action
            if action == "scratchpad":
                file_path = enforcer.create_scratchpad(task_name, content or "")
                result = {
                    "success": True,
                    "action": "scratchpad",
                    "file_path": str(file_path),
                    "message": "Scratchpad ready for exploration"
                }

            elif action == "ensure":
                try:
                    # Check if we're updating an existing plan during PLANNING phase
                    current_phase, _ = enforcer.get_workflow_phase(task_name)
                    files = enforcer.get_task_files(task_name)

                    if current_phase == WorkflowPhase.PLANNING and files[FileType.PLAN]:
                        # Update existing plan during PLANNING phase
                        file_path = enforcer.update_plan(task_name, content or "")
                        result = {
                            "success": True,
                            "action": "ensure",
                            "file_path": str(file_path),
                            "message": "Plan updated (editable until execution starts)"
                        }
                    else:
                        # Create new plan
                        file_path = enforcer.create_plan(task_name, content or "")
                        result = {
                            "success": True,
                            "action": "ensure",
                            "file_path": str(file_path),
                            "message": "Plan created (editable until execution starts)"
                        }
                except FileExistsError:
                    # Plan already exists and we're not in PLANNING phase
                    files = enforcer.get_task_files(task_name)
                    result = {
                        "success": True,
                        "action": "ensure",
                        "file_path": str(files[FileType.PLAN]),
                        "message": "Plan already exists"
                    }

            elif action == "append":
                if not content:
                    return {
                        "success": False,
                        "error": "Content required for append action",
                        "task_name": task_name,
                        "action": action
                    }

                file_path = enforcer.append_progress(task_name, content)
                result = {
                    "success": True,
                    "action": "append",
                    "file_path": str(file_path),
                    "message": "Progress updated"
                }

            else:
                return {
                    "success": False,
                    "error": f"Unknown action: {action}",
                    "task_name": task_name,
                    "action": action
                }

            # Add common metadata
            result.update({
                "task_name": task_name,
                "session_id": self.session_manager.get_current_session(),
                "timestamp": datetime.now().isoformat(),
                "phase": enforcer.get_workflow_phase(task_name)[0].value
            })

            return result

        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "task_name": task_name,
                "action": action,
                "session_id": self.session_manager.get_current_session()
            }

    def session_manager_action(self, action: str, **kwargs) -> Dict[str, Any]:
        """
        Session manager actions - equivalent to mcp__serena__session_manager.

        Args:
            action: Action to perform ("info", "start", "switch", "list", "stats")
            **kwargs: Additional arguments for specific actions

        Returns:
            Dictionary with operation results
        """
        try:
            if action == "info":
                session_id = self.session_manager.get_current_session()
                if not session_id:
                    return {
                        "success": False,
                        "error": "No active session"
                    }

                session_info = self.session_manager.get_session_info(session_id)
                session_state = self.session_manager.get_session_state()

                session_info_dict = None
                if session_info:
                    session_info_dict = session_info.model_dump()
                    # Convert datetime objects to strings for Rich display
                    session_info_dict["created_at"] = session_info_dict["created_at"].strftime("%Y-%m-%d %H:%M:%S") if isinstance(session_info_dict["created_at"], datetime) else str(session_info_dict["created_at"])
                    session_info_dict["updated_at"] = session_info_dict["updated_at"].strftime("%Y-%m-%d %H:%M:%S") if isinstance(session_info_dict["updated_at"], datetime) else str(session_info_dict["updated_at"])

                return {
                    "success": True,
                    "session_id": session_id,
                    "session_info": session_info_dict,
                    "session_state": session_state,
                    "storage_path": str(self.storage_path)
                }

            elif action == "start":
                metadata = kwargs.get("metadata", {})
                session_id = self.session_manager.create_session(metadata)

                return {
                    "success": True,
                    "action": "start",
                    "session_id": session_id,
                    "message": "New session created"
                }

            elif action == "switch":
                target_session = kwargs.get("session_id")
                if not target_session:
                    return {
                        "success": False,
                        "error": "session_id required for switch action"
                    }

                success = self.session_manager.switch_session(target_session)
                return {
                    "success": success,
                    "action": "switch",
                    "session_id": target_session,
                    "message": "Session switched" if success else "Session not found"
                }

            elif action == "list":
                limit = kwargs.get("limit", 10)
                sessions = self.session_manager.list_sessions(limit)

                return {
                    "success": True,
                    "action": "list",
                    "sessions": [s.model_dump() for s in sessions],
                    "count": len(sessions)
                }

            elif action == "stats":
                stats = self.session_manager.get_session_stats()
                return {
                    "success": True,
                    "action": "stats",
                    **stats
                }

            else:
                return {
                    "success": False,
                    "error": f"Unknown session action: {action}"
                }

        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "action": action
            }

    def get_task_status(self, task_name: str) -> Dict[str, Any]:
        """
        Get comprehensive status for a task.

        Args:
            task_name: Name of the task

        Returns:
            Dictionary with task status information
        """
        enforcer = self._get_enforcer()

        try:
            current_phase, phase_message = enforcer.get_workflow_phase(task_name)
            files = enforcer.get_task_files(task_name)
            next_steps = enforcer.get_next_steps(task_name)
            validation_issues = enforcer.validate_file_integrity(task_name)

            return {
                "success": True,
                "task_name": task_name,
                "session_id": self.session_manager.get_current_session(),
                "current_phase": current_phase.value,
                "phase_message": phase_message,
                "files": {
                    file_type.value: str(path) if path else None
                    for file_type, path in files.items()
                },
                "next_steps": next_steps,
                "validation_issues": validation_issues,
                "timestamp": datetime.now().isoformat()
            }

        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "task_name": task_name
            }

    def list_tasks(self) -> Dict[str, Any]:
        """
        List all tasks in current session.

        Returns:
            Dictionary with task list and summary
        """
        try:
            session_id = self.session_manager.get_current_session()
            if not session_id:
                return {
                    "success": False,
                    "error": "No active session"
                }

            # System directories that should not be considered as tasks
            system_dirs = {'.context', 'sessions', '.git', '.DS_Store'}

            # Find all task directories
            tasks = []
            if self.storage_path.exists():
                for task_dir in self.storage_path.iterdir():
                    if task_dir.is_dir() and not task_dir.name.startswith('.') and task_dir.name not in system_dirs:
                        task_name = task_dir.name
                        task_status = self.get_task_status(task_name)
                        if task_status["success"]:
                            tasks.append({
                                "task_name": task_name,
                                "phase": task_status["current_phase"],
                                "files": task_status["files"],
                                "has_issues": bool(task_status["validation_issues"])
                            })

            return {
                "success": True,
                "session_id": session_id,
                "tasks": tasks,
                "count": len(tasks)
            }

        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }

    def get_task_context(self) -> Dict[str, Any]:
        """
        Get context for sub-agent coordination.

        Returns:
            Dictionary with current session and task context
        """
        session_id = self.session_manager.get_current_session()
        session_state = self.session_manager.get_session_state()

        return {
            "session_id": session_id,
            "storage_path": str(self.storage_path),
            "active_tasks": session_state.get("active_tasks", []),
            "timestamp": datetime.now().isoformat()
        }

    def cleanup(self, max_age_days: int = 30) -> Dict[str, Any]:
        """
        Clean up old sessions and stale locks.

        Args:
            max_age_days: Maximum age for cleanup

        Returns:
            Dictionary with cleanup results
        """
        try:
            # Clean up old sessions
            sessions_cleaned = self.session_manager.cleanup_old_sessions(max_age_days)

            # Clean up stale locks
            locks_cleaned = cleanup_stale_locks(self.storage_path)

            return {
                "success": True,
                "sessions_cleaned": sessions_cleaned,
                "locks_cleaned": locks_cleaned,
                "message": f"Cleaned up {sessions_cleaned} sessions and {locks_cleaned} stale locks"
            }

        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }