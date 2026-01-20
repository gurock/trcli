"""
File Handler - Zero-dependency rotating file handler for TRCLI

Provides file output with automatic rotation based on file size,
without requiring any external dependencies.

Features:
- Automatic log rotation when file reaches max size
- Configurable number of backup files
- Thread-safe write operations
- Automatic directory creation
- Zero external dependencies (Python stdlib only)

Usage:
    from trcli.logging.file_handler import RotatingFileHandler

    handler = RotatingFileHandler(
        filepath="/var/log/trcli/app.log",
        max_bytes=10485760,  # 10MB
        backup_count=5
    )

    handler.write("Log message\n")
    handler.close()
"""

import os
from pathlib import Path
from threading import Lock
from typing import Optional


class RotatingFileHandler:
    """
    Simple rotating file handler without external dependencies.

    Rotates log files when they reach a specified size, keeping a
    configurable number of backup files.

    Example:
        handler = RotatingFileHandler("/var/log/trcli/app.log", max_bytes=10485760)
        handler.write('{"timestamp": "2024-01-20", "message": "Test"}\n')
        handler.close()
    """

    def __init__(
        self, filepath: str, max_bytes: int = 10485760, backup_count: int = 5, encoding: str = "utf-8"  # 10MB
    ):
        """
        Initialize rotating file handler.

        Args:
            filepath: Path to log file
            max_bytes: Maximum file size before rotation (default: 10MB)
            backup_count: Number of backup files to keep (default: 5)
            encoding: File encoding (default: utf-8)
        """
        self.filepath = Path(filepath)
        self.max_bytes = max_bytes
        self.backup_count = backup_count
        self.encoding = encoding
        self._file = None
        self._lock = Lock()
        self._ensure_directory()

    def _ensure_directory(self):
        """Create log directory if it doesn't exist"""
        self.filepath.parent.mkdir(parents=True, exist_ok=True)

    def write(self, content: str):
        """
        Write content to file with automatic rotation.

        Args:
            content: Content to write (should include newline if needed)

        Example:
            handler.write("Log entry\n")
        """
        with self._lock:
            # Check if rotation needed before writing
            if self._should_rotate():
                self._rotate()

            # Open file if not already open
            if self._file is None or self._file.closed:
                self._file = open(self.filepath, "a", encoding=self.encoding)

            # Write content
            self._file.write(content)
            self._file.flush()
            os.fsync(self._file.fileno())  # Ensure data is written to disk

    def _should_rotate(self) -> bool:
        """
        Check if file should be rotated based on size.

        Returns:
            True if rotation needed, False otherwise
        """
        # If file doesn't exist, no rotation needed
        if not self.filepath.exists():
            return False

        # Check file size
        try:
            file_size = self.filepath.stat().st_size
            return file_size >= self.max_bytes
        except OSError:
            # If we can't check size, assume no rotation needed
            return False

    def _rotate(self):
        """
        Rotate log files.

        Closes current file, renames existing backup files, and
        moves current file to .1.

        Rotation pattern:
            app.log     -> app.log.1
            app.log.1   -> app.log.2
            app.log.2   -> app.log.3
            ...
            app.log.N   -> deleted (if N >= backup_count)
        """
        # Close current file
        if self._file and not self._file.closed:
            self._file.close()
            self._file = None

        # Delete oldest backup if it exists
        oldest_backup = Path(f"{self.filepath}.{self.backup_count}")
        if oldest_backup.exists():
            try:
                oldest_backup.unlink()
            except OSError:
                pass  # Ignore errors deleting old backups

        # Rotate existing backup files
        for i in range(self.backup_count - 1, 0, -1):
            src = Path(f"{self.filepath}.{i}")
            dst = Path(f"{self.filepath}.{i + 1}")
            if src.exists():
                try:
                    src.replace(dst)
                except OSError:
                    pass  # Ignore errors during rotation

        # Move current file to .1
        if self.filepath.exists():
            try:
                self.filepath.replace(Path(f"{self.filepath}.1"))
            except OSError:
                pass  # Ignore errors moving current file

    def flush(self):
        """
        Flush file buffer.

        Ensures all buffered data is written to disk.
        """
        with self._lock:
            if self._file and not self._file.closed:
                self._file.flush()
                os.fsync(self._file.fileno())

    def close(self):
        """
        Close file handle.

        Should be called when done writing to ensure data is flushed.
        """
        with self._lock:
            if self._file and not self._file.closed:
                self._file.flush()
                self._file.close()
                self._file = None

    def __enter__(self):
        """Context manager entry"""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        self.close()

    def __del__(self):
        """Destructor - ensure file is closed"""
        try:
            self.close()
        except Exception:
            pass  # Ignore errors in destructor


class MultiFileHandler:
    """
    Write to multiple files simultaneously.

    Useful for writing to multiple locations (e.g., local file + shared storage).

    Example:
        handler = MultiFileHandler([
            RotatingFileHandler("/var/log/trcli/app.log"),
            RotatingFileHandler("/mnt/shared/logs/app.log")
        ])
        handler.write("Log entry\n")
    """

    def __init__(self, handlers: list):
        """
        Initialize multi-file handler.

        Args:
            handlers: List of file handlers
        """
        self.handlers = handlers

    def write(self, content: str):
        """
        Write content to all handlers.

        Args:
            content: Content to write
        """
        for handler in self.handlers:
            try:
                handler.write(content)
            except Exception:
                # Continue writing to other handlers even if one fails
                pass

    def flush(self):
        """Flush all handlers"""
        for handler in self.handlers:
            try:
                handler.flush()
            except Exception:
                pass

    def close(self):
        """Close all handlers"""
        for handler in self.handlers:
            try:
                handler.close()
            except Exception:
                pass

    def __enter__(self):
        """Context manager entry"""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        self.close()
