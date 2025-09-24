"""
Claude Memory System - Portable file-based memory for Claude Code.

A standalone, portable memory system that implements the three-file workflow:
- Scratchpad (mutable exploration)
- Plan (write-once planning)
- Progress (append-only tracking)

Features:
- Cross-platform file locking
- Sub-agent coordination via hooks
- Global CLI installation with uv
- Project-agnostic storage
"""

from .core.memory_manager import MemoryManager
from .core.session_manager import SessionManager
from .core.workflow_enforcer import WorkflowEnforcer
from .api import MemoryAPI

__version__ = "1.0.0"
__all__ = [
    "MemoryManager",
    "SessionManager",
    "WorkflowEnforcer",
    "MemoryAPI",
]