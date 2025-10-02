"""
Claude Memory System - Portable memory system with pluggable backends.

A standalone, portable memory system that implements the three-file workflow:
- Scratchpad (mutable exploration)
- Plan (write-once planning)
- Progress (append-only tracking)

Features:
- Pluggable storage backends (File, Claude Memory Tools)
- Cross-platform file locking
- Sub-agent coordination via hooks
- Global CLI installation with uv
- Project-agnostic storage
"""

from .core.memory_manager import MemoryManager
from .core.session_manager import SessionManager
from .core.workflow_enforcer import WorkflowEnforcer
from .api import MemoryAPI

# Backend classes
from .backends import (
    MemoryBackend,
    BackendType,
    create_backend,
    detect_available_backend,
)

__version__ = "2.0.0"
__all__ = [
    "MemoryManager",
    "SessionManager",
    "WorkflowEnforcer",
    "MemoryAPI",
    # Backend exports
    "MemoryBackend",
    "BackendType",
    "create_backend",
    "detect_available_backend",
]