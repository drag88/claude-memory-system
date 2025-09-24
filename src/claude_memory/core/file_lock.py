"""
Cross-platform file locking utilities using portalocker.

Provides thread-safe and process-safe file locking for memory operations.
"""

import os
import time
from pathlib import Path
from typing import Optional, Union
from contextlib import contextmanager

try:
    import portalocker
except ImportError:
    raise ImportError(
        "portalocker is required for file locking. "
        "Install with: uv add portalocker"
    )


class FileLock:
    """Cross-platform file locking using portalocker."""

    def __init__(
        self,
        file_path: Union[str, Path],
        timeout: float = 30.0,
        retry_delay: float = 0.1
    ):
        self.file_path = Path(file_path)
        self.timeout = timeout
        self.retry_delay = retry_delay
        self.lock_file_path = self.file_path.with_suffix(f"{self.file_path.suffix}.lock")
        self._lock_handle: Optional[int] = None

    def acquire(self) -> bool:
        """
        Acquire exclusive lock on the file.

        Returns:
            True if lock acquired successfully, False if timeout
        """
        start_time = time.time()

        # Ensure parent directory exists
        self.lock_file_path.parent.mkdir(parents=True, exist_ok=True)

        while time.time() - start_time < self.timeout:
            try:
                # Open lock file
                self._lock_handle = os.open(
                    str(self.lock_file_path),
                    os.O_CREAT | os.O_WRONLY | os.O_TRUNC
                )

                # Try to acquire exclusive lock (non-blocking)
                portalocker.lock(self._lock_handle, portalocker.LOCK_EX | portalocker.LOCK_NB)

                # Write process info to lock file
                lock_info = f"pid:{os.getpid()}\ntime:{time.time()}\nfile:{self.file_path}\n"
                os.write(self._lock_handle, lock_info.encode())

                return True

            except (OSError, portalocker.LockException):
                # Lock is held by another process
                if self._lock_handle is not None:
                    try:
                        os.close(self._lock_handle)
                    except OSError:
                        pass
                    self._lock_handle = None

                time.sleep(self.retry_delay)
                continue

        return False

    def release(self) -> None:
        """Release the file lock."""
        if self._lock_handle is not None:
            try:
                portalocker.unlock(self._lock_handle)
                os.close(self._lock_handle)
            except OSError:
                pass
            finally:
                self._lock_handle = None

            # Clean up lock file
            try:
                self.lock_file_path.unlink()
            except FileNotFoundError:
                pass

    def is_locked(self) -> bool:
        """Check if the file is currently locked."""
        return self._lock_handle is not None

    def __enter__(self):
        """Context manager entry."""
        if not self.acquire():
            raise TimeoutError(
                f"Could not acquire lock for {self.file_path} "
                f"within {self.timeout} seconds"
            )
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.release()


@contextmanager
def file_lock(
    file_path: Union[str, Path],
    timeout: float = 30.0,
    retry_delay: float = 0.1
):
    """
    Context manager for file locking.

    Args:
        file_path: Path to file to lock
        timeout: Maximum time to wait for lock
        retry_delay: Delay between lock attempts

    Example:
        with file_lock("memory.md"):
            # File operations here are atomic
            pass
    """
    lock = FileLock(file_path, timeout, retry_delay)
    try:
        if not lock.acquire():
            raise TimeoutError(
                f"Could not acquire lock for {file_path} "
                f"within {timeout} seconds"
            )
        yield lock
    finally:
        lock.release()


def cleanup_stale_locks(directory: Union[str, Path], max_age_seconds: int = 300) -> int:
    """
    Clean up stale lock files in a directory.

    Args:
        directory: Directory to scan for lock files
        max_age_seconds: Maximum age for lock files before considering them stale

    Returns:
        Number of stale locks cleaned up
    """
    directory = Path(directory)
    if not directory.exists():
        return 0

    cleaned_count = 0
    current_time = time.time()

    for lock_file in directory.rglob("*.lock"):
        try:
            # Check if lock file is stale
            file_age = current_time - lock_file.stat().st_mtime

            if file_age > max_age_seconds:
                # Try to read lock info
                try:
                    with open(lock_file, 'r') as f:
                        content = f.read()

                    # Extract PID if available
                    if "pid:" in content:
                        pid_line = [line for line in content.split('\n') if line.startswith('pid:')]
                        if pid_line:
                            pid = int(pid_line[0].split(':')[1])

                            # Check if process still exists
                            try:
                                os.kill(pid, 0)  # Signal 0 doesn't kill, just checks existence
                                continue  # Process still exists, don't remove lock
                            except (ProcessLookupError, OSError):
                                pass  # Process is gone, safe to remove

                except (OSError, ValueError):
                    pass  # Can't read lock file or parse PID, assume stale

                # Remove stale lock
                try:
                    lock_file.unlink()
                    cleaned_count += 1
                except OSError:
                    pass

        except OSError:
            continue

    return cleaned_count