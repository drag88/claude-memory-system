"""
File-based storage backend.

Wraps existing file operations to implement the MemoryBackend protocol.
This maintains 100% backward compatibility with the current system.
"""

import os
import re
import stat
from pathlib import Path
from typing import Optional, List, Dict, Any
from datetime import datetime

from . import BackendType


class FileBackend:
    """
    File-based storage backend using standard filesystem operations.

    This backend wraps the current file I/O operations to implement
    the MemoryBackend protocol, ensuring backward compatibility.
    """

    def __init__(self, storage_path: Path):
        """
        Initialize file backend.

        Args:
            storage_path: Base storage path for memories
        """
        self.storage_path = Path(storage_path)
        self.storage_path.mkdir(parents=True, exist_ok=True)

    def read(self, path: Path) -> Optional[str]:
        """Read content from a file."""
        try:
            if not path.exists():
                return None
            return path.read_text(encoding='utf-8')
        except Exception as e:
            print(f"Error reading file {path}: {e}")
            return None

    def write(self, path: Path, content: str) -> bool:
        """Write content to a file (create or overwrite)."""
        try:
            # Create parent directories if needed
            path.parent.mkdir(parents=True, exist_ok=True)

            # Write content
            path.write_text(content, encoding='utf-8')
            return True
        except Exception as e:
            print(f"Error writing file {path}: {e}")
            return False

    def append(self, path: Path, content: str) -> bool:
        """Append content to an existing file."""
        try:
            # Create file if it doesn't exist
            if not path.exists():
                return self.write(path, content)

            # Append to existing file
            with open(path, 'a', encoding='utf-8') as f:
                f.write(content)
            return True
        except Exception as e:
            print(f"Error appending to file {path}: {e}")
            return False

    def exists(self, path: Path) -> bool:
        """Check if a file or directory exists."""
        return path.exists()

    def list_directory(self, path: Path) -> List[Path]:
        """List contents of a directory."""
        try:
            if not path.exists() or not path.is_dir():
                return []
            return list(path.iterdir())
        except Exception as e:
            print(f"Error listing directory {path}: {e}")
            return []

    def view(self, path: Path) -> Dict[str, Any]:
        """
        View file or directory contents with metadata.

        For file backend, this provides similar structure to memory tool view.

        Args:
            path: Path to view

        Returns:
            Dictionary with content, metadata, and structure
        """
        try:
            if not path.exists():
                return {
                    "exists": False,
                    "path": str(path),
                    "type": "unknown"
                }

            if path.is_file():
                content = self.read(path)
                stats = path.stat()

                return {
                    "exists": True,
                    "path": str(path),
                    "type": "file",
                    "content": content,
                    "size": stats.st_size,
                    "modified": datetime.fromtimestamp(stats.st_mtime).isoformat(),
                    "readonly": self.is_readonly(path)
                }
            elif path.is_dir():
                children = self.list_directory(path)

                return {
                    "exists": True,
                    "path": str(path),
                    "type": "directory",
                    "children": [
                        {
                            "name": child.name,
                            "path": str(child),
                            "type": "file" if child.is_file() else "directory"
                        }
                        for child in children
                    ],
                    "count": len(children)
                }
            else:
                return {
                    "exists": True,
                    "path": str(path),
                    "type": "other"
                }
        except Exception as e:
            return {
                "exists": False,
                "path": str(path),
                "type": "error",
                "error": str(e)
            }

    def search(self, base_path: Path, pattern: str) -> List[Dict[str, Any]]:
        """
        Search for pattern across files.

        Args:
            base_path: Base directory to search in
            pattern: Search pattern (regex or text)

        Returns:
            List of matches with file paths and context
        """
        matches = []

        try:
            # Compile regex pattern
            regex = re.compile(pattern, re.IGNORECASE)

            # Walk through directory tree
            for root, dirs, files in os.walk(base_path):
                # Skip system directories
                dirs[:] = [d for d in dirs if not d.startswith('.')]

                for filename in files:
                    if filename.startswith('.'):
                        continue

                    file_path = Path(root) / filename

                    try:
                        content = self.read(file_path)
                        if content:
                            # Search for pattern
                            for line_num, line in enumerate(content.split('\n'), 1):
                                if regex.search(line):
                                    matches.append({
                                        "file": str(file_path),
                                        "line": line_num,
                                        "content": line.strip(),
                                        "context": self._get_context_lines(content, line_num)
                                    })
                    except Exception:
                        continue

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
        """Delete a file or directory."""
        try:
            if not path.exists():
                return True

            if path.is_file():
                path.unlink()
            elif path.is_dir():
                import shutil
                shutil.rmtree(path)

            return True
        except Exception as e:
            print(f"Error deleting {path}: {e}")
            return False

    def rename(self, old_path: Path, new_path: Path) -> bool:
        """Rename or move a file."""
        try:
            if not old_path.exists():
                return False

            # Create parent directory for new path if needed
            new_path.parent.mkdir(parents=True, exist_ok=True)

            # Rename/move
            old_path.rename(new_path)
            return True
        except Exception as e:
            print(f"Error renaming {old_path} to {new_path}: {e}")
            return False

    def make_readonly(self, path: Path) -> bool:
        """Make a file read-only (immutable)."""
        try:
            if not path.exists():
                return False

            # Remove write permissions
            current_permissions = path.stat().st_mode
            readonly_permissions = current_permissions & ~(stat.S_IWUSR | stat.S_IWGRP | stat.S_IWOTH)
            path.chmod(readonly_permissions)
            return True
        except Exception as e:
            print(f"Error making {path} readonly: {e}")
            return False

    def is_readonly(self, path: Path) -> bool:
        """Check if a file is read-only."""
        try:
            if not path.exists():
                return False
            return not os.access(path, os.W_OK)
        except Exception:
            return False

    def get_backend_type(self) -> BackendType:
        """Get the type of this backend."""
        return BackendType.FILE

    def __repr__(self) -> str:
        return f"FileBackend(storage_path={self.storage_path})"