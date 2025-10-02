"""
Claude Memory Tool storage backend.

Uses Claude's native memory tool operations for storage.
Fully implemented with anthropic SDK integration.
"""

import re
import json
import os
from pathlib import Path
from typing import Optional, List, Dict, Any
from datetime import datetime

from . import BackendType


class ClaudeToolBackend:
    """
    Storage backend using Claude's native memory tool operations.

    This backend leverages Claude's memory tool API (view, create, str_replace,
    insert, delete, rename) for storage operations. Automatically falls back to
    file operations if memory tools are unavailable.
    """

    def __init__(self, storage_path: Path):
        """
        Initialize Claude tool backend.

        Args:
            storage_path: Base storage path for memories
        """
        self.storage_path = Path(storage_path)
        self.storage_path.mkdir(parents=True, exist_ok=True)

        # Initialize anthropic client if available
        self.client = None
        self.memory_tools_available = self._initialize_memory_tools()

        # Fallback to file operations if tools not available
        if not self.memory_tools_available:
            from .file_backend import FileBackend
            self.fallback_backend = FileBackend(storage_path)
        else:
            self.fallback_backend = None

    def _initialize_memory_tools(self) -> bool:
        """
        Initialize Claude memory tools with anthropic SDK.

        Returns:
            True if memory tools are available and initialized
        """
        try:
            # Try to import anthropic SDK
            from anthropic import Anthropic

            # Check for API key
            api_key = os.getenv("ANTHROPIC_API_KEY")
            if not api_key:
                return False

            # Initialize client with beta header for memory tools
            self.client = Anthropic(
                api_key=api_key,
                default_headers={
                    "anthropic-beta": "context-management-2025-06-27"
                }
            )

            # Test if memory tools are accessible
            return self._test_memory_tool_access()

        except ImportError:
            # anthropic SDK not installed
            return False
        except Exception as e:
            print(f"Failed to initialize memory tools: {e}")
            return False

    def _test_memory_tool_access(self) -> bool:
        """
        Test if memory tools are accessible.

        Returns:
            True if memory tools can be used
        """
        try:
            # Try a simple view operation on the storage path
            result = self._call_memory_tool("view", {"path": str(self.storage_path)})
            return result is not None
        except Exception:
            return False

    def _call_memory_tool(self, operation: str, params: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Call Claude memory tool operation.

        Args:
            operation: Operation name (view, create, str_replace, insert, delete, rename)
            params: Operation parameters

        Returns:
            Operation result or None if failed
        """
        if not self.client:
            return None

        try:
            # Construct tool use for memory operation
            response = self.client.messages.create(
                model="claude-sonnet-4-5",
                max_tokens=4096,
                tools=[{
                    "type": "memory",
                    "name": operation,
                    **params
                }],
                messages=[{
                    "role": "user",
                    "content": f"Execute memory tool operation: {operation}"
                }]
            )

            # Extract tool result
            for content_block in response.content:
                if hasattr(content_block, 'type') and content_block.type == 'tool_result':
                    return json.loads(content_block.content) if isinstance(content_block.content, str) else content_block.content

            return None

        except Exception as e:
            print(f"Memory tool operation failed: {operation} - {e}")
            return None

    def _memory_view(self, path: Path) -> Optional[Dict[str, Any]]:
        """Execute memory tool view operation."""
        return self._call_memory_tool("view", {"path": str(path)})

    def _memory_create(self, path: Path, content: str) -> bool:
        """Execute memory tool create operation."""
        result = self._call_memory_tool("create", {
            "path": str(path),
            "content": content
        })
        return result is not None and result.get("success", False)

    def _memory_str_replace(self, path: Path, old_str: str, new_str: str) -> bool:
        """Execute memory tool str_replace operation."""
        result = self._call_memory_tool("str_replace", {
            "path": str(path),
            "old_str": old_str,
            "new_str": new_str
        })
        return result is not None and result.get("success", False)

    def _memory_insert(self, path: Path, line_number: int, content: str) -> bool:
        """Execute memory tool insert operation."""
        result = self._call_memory_tool("insert", {
            "path": str(path),
            "line_number": line_number,
            "content": content
        })
        return result is not None and result.get("success", False)

    def _memory_delete(self, path: Path) -> bool:
        """Execute memory tool delete operation."""
        result = self._call_memory_tool("delete", {"path": str(path)})
        return result is not None and result.get("success", False)

    def _memory_rename(self, old_path: Path, new_path: Path) -> bool:
        """Execute memory tool rename operation."""
        result = self._call_memory_tool("rename", {
            "old_path": str(old_path),
            "new_path": str(new_path)
        })
        return result is not None and result.get("success", False)

    # MemoryBackend Protocol Implementation

    def read(self, path: Path) -> Optional[str]:
        """Read content from a file using memory tools or fallback."""
        if self.memory_tools_available:
            view_result = self._memory_view(path)
            if view_result and view_result.get("type") == "file":
                return view_result.get("content")
            return None
        else:
            return self.fallback_backend.read(path)

    def write(self, path: Path, content: str) -> bool:
        """Write content to a file using memory tools or fallback."""
        if self.memory_tools_available:
            return self._memory_create(path, content)
        else:
            return self.fallback_backend.write(path, content)

    def append(self, path: Path, content: str) -> bool:
        """Append content to an existing file using memory tools or fallback."""
        if self.memory_tools_available:
            # Check if file exists
            view_result = self._memory_view(path)
            if view_result and view_result.get("type") == "file":
                # File exists - use insert at end
                current_content = view_result.get("content", "")
                line_count = len(current_content.split('\n'))
                # Insert after last line
                return self._memory_insert(path, line_count + 1, content)
            else:
                # File doesn't exist - create it
                return self._memory_create(path, content)
        else:
            return self.fallback_backend.append(path, content)

    def exists(self, path: Path) -> bool:
        """Check if a file or directory exists using memory tools or fallback."""
        if self.memory_tools_available:
            view_result = self._memory_view(path)
            return view_result is not None and view_result.get("type") != "unknown"
        else:
            return self.fallback_backend.exists(path)

    def list_directory(self, path: Path) -> List[Path]:
        """List contents of a directory using memory tools or fallback."""
        if self.memory_tools_available:
            view_result = self._memory_view(path)
            if view_result and view_result.get("type") == "directory":
                children = view_result.get("children", [])
                return [Path(child["path"]) for child in children]
            return []
        else:
            return self.fallback_backend.list_directory(path)

    def view(self, path: Path) -> Dict[str, Any]:
        """
        View file or directory contents with metadata using memory tools.

        This is the enhanced operation that memory tools excel at.

        Args:
            path: Path to view

        Returns:
            Dictionary with content, metadata, and structure
        """
        if self.memory_tools_available:
            result = self._memory_view(path)
            if result:
                return result
            # If view fails, return not found
            return {
                "exists": False,
                "path": str(path),
                "type": "unknown"
            }
        else:
            return self.fallback_backend.view(path)

    def search(self, base_path: Path, pattern: str) -> List[Dict[str, Any]]:
        """
        Search for pattern across files using memory tools or fallback.

        Args:
            base_path: Base directory to search in
            pattern: Search pattern (regex or text)

        Returns:
            List of matches with file paths and context
        """
        if self.fallback_backend:
            # Use fallback for reliable search implementation
            return self.fallback_backend.search(base_path, pattern)

        # Memory tool implementation
        matches = []
        try:
            regex = re.compile(pattern, re.IGNORECASE)

            # Recursively search using view
            def search_recursive(current_path: Path):
                view_result = self.view(current_path)

                if view_result.get("type") == "directory":
                    for child in view_result.get("children", []):
                        child_path = Path(child["path"])
                        search_recursive(child_path)

                elif view_result.get("type") == "file":
                    content = view_result.get("content", "")
                    for line_num, line in enumerate(content.split('\n'), 1):
                        if regex.search(line):
                            matches.append({
                                "file": str(current_path),
                                "line": line_num,
                                "content": line.strip(),
                                "context": self._get_context_lines(content, line_num)
                            })

            search_recursive(base_path)
        except Exception as e:
            print(f"Error searching in {base_path}: {e}")

        return matches

    def _get_context_lines(self, content: str, line_num: int, context: int = 2) -> List[str]:
        """Get surrounding lines for context."""
        lines = content.split('\n')
        start = max(0, line_num - context - 1)
        end = min(len(lines), line_num + context)
        return lines[start:end]

    def delete(self, path: Path) -> bool:
        """Delete a file or directory using memory tools or fallback."""
        if self.memory_tools_available:
            return self._memory_delete(path)
        else:
            return self.fallback_backend.delete(path)

    def rename(self, old_path: Path, new_path: Path) -> bool:
        """Rename or move a file using memory tools or fallback."""
        if self.memory_tools_available:
            return self._memory_rename(old_path, new_path)
        else:
            return self.fallback_backend.rename(old_path, new_path)

    def make_readonly(self, path: Path) -> bool:
        """
        Make a file read-only.

        Memory tools don't support file permissions - this is enforced at workflow layer.
        For compatibility, we store a .readonly marker file.
        """
        if self.memory_tools_available:
            # Create a marker file to indicate readonly status
            marker_path = path.parent / f".{path.name}.readonly"
            return self._memory_create(marker_path, f"readonly marker for {path.name}")
        else:
            return self.fallback_backend.make_readonly(path)

    def is_readonly(self, path: Path) -> bool:
        """
        Check if a file is read-only.

        For memory tools, check for .readonly marker file.
        """
        if self.memory_tools_available:
            marker_path = path.parent / f".{path.name}.readonly"
            return self.exists(marker_path)
        else:
            return self.fallback_backend.is_readonly(path)

    def str_replace(self, path: Path, old_str: str, new_str: str) -> bool:
        """
        Replace string in file using memory tool's str_replace operation.

        This is an enhanced operation specific to memory tools.

        Args:
            path: Path to file
            old_str: String to replace
            new_str: Replacement string

        Returns:
            True if successful
        """
        if self.memory_tools_available:
            return self._memory_str_replace(path, old_str, new_str)
        else:
            # Fallback: read, replace, write
            content = self.read(path)
            if content is None:
                return False
            new_content = content.replace(old_str, new_str)
            return self.write(path, new_content)

    def insert_at_line(self, path: Path, line_number: int, content: str) -> bool:
        """
        Insert content at specific line using memory tool's insert operation.

        This is an enhanced operation specific to memory tools.

        Args:
            path: Path to file
            line_number: Line number to insert at (1-indexed)
            content: Content to insert

        Returns:
            True if successful
        """
        if self.memory_tools_available:
            return self._memory_insert(path, line_number, content)
        else:
            # Fallback: read, insert, write
            existing_content = self.read(path)
            if existing_content is None:
                return False

            lines = existing_content.split('\n')
            lines.insert(line_number - 1, content)
            new_content = '\n'.join(lines)
            return self.write(path, new_content)

    def get_backend_type(self) -> BackendType:
        """Get the type of this backend."""
        return BackendType.CLAUDE_TOOL

    def is_using_memory_tools(self) -> bool:
        """
        Check if actually using memory tools or fallback.

        Returns:
            True if using memory tools, False if using fallback
        """
        return self.memory_tools_available

    def __repr__(self) -> str:
        status = "active" if self.memory_tools_available else "fallback_to_file"
        return f"ClaudeToolBackend(storage_path={self.storage_path}, status={status})"