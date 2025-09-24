"""
Session manager for Claude Memory System.

Handles session creation, persistence, and coordination across projects.
"""

import json
import hashlib
import os
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional, Any, List
from pydantic import BaseModel, Field

from .file_lock import file_lock


class SessionInfo(BaseModel):
    """Session information model."""
    session_id: str
    project_path: str
    created_at: datetime
    updated_at: datetime
    active_tasks: List[str] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class SessionManager:
    """Manages sessions for the Claude Memory System."""

    def __init__(self, storage_path: Optional[Path] = None):
        """
        Initialize session manager.

        Args:
            storage_path: Custom storage path (defaults to auto-resolved)
        """
        self.storage_path = storage_path or self._resolve_storage_path()
        self.sessions_dir = self.storage_path / "sessions"
        self.sessions_dir.mkdir(parents=True, exist_ok=True)

        self.session_file = self.storage_path / ".session_id"
        self.session_state_file = self.storage_path / ".session_state.json"

    def _resolve_storage_path(self) -> Path:
        """
        Resolve storage path using priority order:
        1. Environment variable CLAUDE_MEMORY_PATH
        2. Project-local .claude/memories/
        3. User home directory with project hash
        """
        # 1. Environment variable
        if env_path := os.getenv('CLAUDE_MEMORY_PATH'):
            return Path(env_path)

        # 2. Project-local .claude/memories/
        cwd = Path.cwd()
        claude_dir = cwd / '.claude'
        if claude_dir.exists():
            return claude_dir / 'memories'

        # 3. User home directory with project hash
        project_hash = hashlib.md5(str(cwd).encode()).hexdigest()[:8]
        return Path.home() / '.claude-memories' / project_hash

    def _generate_session_id(self) -> str:
        """Generate a unique session ID."""
        timestamp = int(time.time() * 1000)
        random_part = hashlib.md5(f"{timestamp}{os.getpid()}".encode()).hexdigest()[:8]
        return random_part

    def get_current_session(self) -> Optional[str]:
        """Get the current session ID."""
        if self.session_file.exists():
            try:
                with open(self.session_file, 'r') as f:
                    return f.read().strip()
            except OSError:
                pass
        return None

    def create_session(self, metadata: Optional[Dict[str, Any]] = None) -> str:
        """
        Create a new session.

        Args:
            metadata: Optional metadata for the session

        Returns:
            New session ID
        """
        session_id = self._generate_session_id()
        current_time = datetime.now()

        session_info = SessionInfo(
            session_id=session_id,
            project_path=str(Path.cwd()),
            created_at=current_time,
            updated_at=current_time,
            metadata=metadata or {}
        )

        # Save session info
        session_info_file = self.sessions_dir / f"{session_id}.json"
        with file_lock(session_info_file):
            with open(session_info_file, 'w') as f:
                json.dump(session_info.model_dump(), f, indent=2, default=str)

        # Update current session
        with file_lock(self.session_file):
            with open(self.session_file, 'w') as f:
                f.write(session_id)

        # Initialize session state
        self._update_session_state({
            "session_id": session_id,
            "active_tasks": [],
            "created_at": current_time.isoformat(),
            "updated_at": current_time.isoformat()
        })

        return session_id

    def get_session_info(self, session_id: Optional[str] = None) -> Optional[SessionInfo]:
        """
        Get session information.

        Args:
            session_id: Session ID (defaults to current session)

        Returns:
            Session information or None if not found
        """
        if session_id is None:
            session_id = self.get_current_session()

        if not session_id:
            return None

        session_info_file = self.sessions_dir / f"{session_id}.json"
        if not session_info_file.exists():
            return None

        try:
            with open(session_info_file, 'r') as f:
                data = json.load(f)
            return SessionInfo(**data)
        except (OSError, json.JSONDecodeError, ValueError):
            return None

    def update_session_tasks(self, task_name: str, action: str = "add") -> None:
        """
        Update active tasks for current session.

        Args:
            task_name: Name of the task
            action: "add" to add task, "remove" to remove task
        """
        session_id = self.get_current_session()
        if not session_id:
            return

        session_info = self.get_session_info(session_id)
        if not session_info:
            return

        # Update active tasks
        if action == "add" and task_name not in session_info.active_tasks:
            session_info.active_tasks.append(task_name)
        elif action == "remove" and task_name in session_info.active_tasks:
            session_info.active_tasks.remove(task_name)

        session_info.updated_at = datetime.now()

        # Save updated session info
        session_info_file = self.sessions_dir / f"{session_id}.json"
        with file_lock(session_info_file):
            with open(session_info_file, 'w') as f:
                json.dump(session_info.model_dump(), f, indent=2, default=str)

        # Update session state
        self._update_session_state({
            "session_id": session_id,
            "active_tasks": session_info.active_tasks,
            "updated_at": session_info.updated_at.isoformat()
        })

    def list_sessions(self, limit: int = 10) -> List[SessionInfo]:
        """
        List recent sessions.

        Args:
            limit: Maximum number of sessions to return

        Returns:
            List of session information
        """
        sessions = []

        for session_file in self.sessions_dir.glob("*.json"):
            try:
                with open(session_file, 'r') as f:
                    data = json.load(f)
                sessions.append(SessionInfo(**data))
            except (OSError, json.JSONDecodeError, ValueError):
                continue

        # Sort by updated_at descending
        sessions.sort(key=lambda s: s.updated_at, reverse=True)
        return sessions[:limit]

    def switch_session(self, session_id: str) -> bool:
        """
        Switch to an existing session.

        Args:
            session_id: Target session ID

        Returns:
            True if successful, False if session not found
        """
        session_info = self.get_session_info(session_id)
        if not session_info:
            return False

        # Update current session
        with file_lock(self.session_file):
            with open(self.session_file, 'w') as f:
                f.write(session_id)

        # Update session state
        self._update_session_state({
            "session_id": session_id,
            "active_tasks": session_info.active_tasks,
            "updated_at": datetime.now().isoformat()
        })

        return True

    def cleanup_old_sessions(self, max_age_days: int = 30) -> int:
        """
        Clean up old session files.

        Args:
            max_age_days: Maximum age for sessions before cleanup

        Returns:
            Number of sessions cleaned up
        """
        current_time = datetime.now()
        cleaned_count = 0

        for session_file in self.sessions_dir.glob("*.json"):
            try:
                with open(session_file, 'r') as f:
                    data = json.load(f)

                session_info = SessionInfo(**data)
                age_days = (current_time - session_info.updated_at).days

                if age_days > max_age_days:
                    session_file.unlink()
                    cleaned_count += 1

            except (OSError, json.JSONDecodeError, ValueError):
                # Remove corrupted session files
                try:
                    session_file.unlink()
                    cleaned_count += 1
                except OSError:
                    pass

        return cleaned_count

    def get_session_stats(self) -> Dict[str, Any]:
        """Get statistics about sessions."""
        sessions = self.list_sessions(limit=1000)  # Get all sessions

        total_sessions = len(sessions)
        active_sessions = len([s for s in sessions if s.active_tasks])
        current_session = self.get_current_session()

        project_paths = {s.project_path for s in sessions}

        return {
            "total_sessions": total_sessions,
            "active_sessions": active_sessions,
            "current_session": current_session,
            "unique_projects": len(project_paths),
            "storage_path": str(self.storage_path)
        }

    def _update_session_state(self, state: Dict[str, Any]) -> None:
        """Update session state file."""
        with file_lock(self.session_state_file):
            with open(self.session_state_file, 'w') as f:
                json.dump(state, f, indent=2)

    def get_session_state(self) -> Dict[str, Any]:
        """Get current session state."""
        if not self.session_state_file.exists():
            return {}

        try:
            with open(self.session_state_file, 'r') as f:
                return json.load(f)
        except (OSError, json.JSONDecodeError):
            return {}