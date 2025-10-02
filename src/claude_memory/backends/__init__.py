"""
Memory storage backend abstraction.

Provides a protocol for different storage implementations,
allowing seamless switching between file-based and Claude memory tool storage.
"""

from typing import Protocol, Optional, List, Dict, Any
from pathlib import Path
from enum import Enum


class BackendType(Enum):
    """Available backend types."""
    FILE = "file"
    CLAUDE_TOOL = "claude-tool"
    AUTO = "auto"


class MemoryBackend(Protocol):
    """
    Protocol for memory storage backends.

    Defines the interface that all storage backends must implement.
    This abstraction allows the workflow enforcement layer to remain
    unchanged while supporting different storage mechanisms.
    """

    def read(self, path: Path) -> Optional[str]:
        """
        Read content from a file.

        Args:
            path: Path to the file

        Returns:
            File content or None if file doesn't exist
        """
        ...

    def write(self, path: Path, content: str) -> bool:
        """
        Write content to a file (create or overwrite).

        Args:
            path: Path to the file
            content: Content to write

        Returns:
            True if successful, False otherwise
        """
        ...

    def append(self, path: Path, content: str) -> bool:
        """
        Append content to an existing file.

        Args:
            path: Path to the file
            content: Content to append

        Returns:
            True if successful, False otherwise
        """
        ...

    def exists(self, path: Path) -> bool:
        """
        Check if a file or directory exists.

        Args:
            path: Path to check

        Returns:
            True if exists, False otherwise
        """
        ...

    def list_directory(self, path: Path) -> List[Path]:
        """
        List contents of a directory.

        Args:
            path: Directory path

        Returns:
            List of paths in the directory
        """
        ...

    def view(self, path: Path) -> Dict[str, Any]:
        """
        View file or directory contents with metadata.

        This is the enhanced operation that memory tools provide.
        For file backends, this is equivalent to read() with metadata.

        Args:
            path: Path to view

        Returns:
            Dictionary with content, metadata, and structure
        """
        ...

    def search(self, base_path: Path, pattern: str) -> List[Dict[str, Any]]:
        """
        Search for pattern across files.

        Args:
            base_path: Base directory to search in
            pattern: Search pattern (regex or text)

        Returns:
            List of matches with file paths and context
        """
        ...

    def delete(self, path: Path) -> bool:
        """
        Delete a file or directory.

        Args:
            path: Path to delete

        Returns:
            True if successful, False otherwise
        """
        ...

    def rename(self, old_path: Path, new_path: Path) -> bool:
        """
        Rename or move a file.

        Args:
            old_path: Current path
            new_path: New path

        Returns:
            True if successful, False otherwise
        """
        ...

    def make_readonly(self, path: Path) -> bool:
        """
        Make a file read-only (immutable).

        Args:
            path: Path to the file

        Returns:
            True if successful, False otherwise
        """
        ...

    def is_readonly(self, path: Path) -> bool:
        """
        Check if a file is read-only.

        Args:
            path: Path to the file

        Returns:
            True if read-only, False otherwise
        """
        ...

    def get_backend_type(self) -> BackendType:
        """
        Get the type of this backend.

        Returns:
            Backend type identifier
        """
        ...


def detect_available_backend() -> BackendType:
    """
    Detect which backend is available and recommended.

    Returns:
        Recommended backend type
    """
    # Try to detect if Claude memory tools are available
    try:
        # Check if we're running in a context with memory tools
        # This is a placeholder - actual detection would check for:
        # 1. Claude API client availability
        # 2. Beta header support
        # 3. Memory tool permissions

        # For now, default to FILE backend
        # In future, detect memory tool availability here
        return BackendType.FILE
    except Exception:
        return BackendType.FILE


def create_backend(backend_type: BackendType, storage_path: Path) -> MemoryBackend:
    """
    Factory function to create appropriate backend instance.

    Args:
        backend_type: Type of backend to create
        storage_path: Base storage path

    Returns:
        Backend instance

    Raises:
        ValueError: If backend type is not supported
    """
    if backend_type == BackendType.AUTO:
        backend_type = detect_available_backend()

    if backend_type == BackendType.FILE:
        from .file_backend import FileBackend
        return FileBackend(storage_path)
    elif backend_type == BackendType.CLAUDE_TOOL:
        from .claude_tool_backend import ClaudeToolBackend
        return ClaudeToolBackend(storage_path)
    else:
        raise ValueError(f"Unsupported backend type: {backend_type}")


__all__ = [
    "MemoryBackend",
    "BackendType",
    "detect_available_backend",
    "create_backend",
]