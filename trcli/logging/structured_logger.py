"""
Structured Logger - Zero-dependency structured logging for TRCLI

Provides structured logging with NDJSON (Newline-Delimited JSON) output format,
compatible with all major log aggregation platforms (ELK, Splunk, CloudWatch, etc.)

Features:
- Standard log levels (DEBUG, INFO, WARNING, ERROR, CRITICAL)
- Structured fields (queryable, filterable, aggregatable)
- Correlation ID support for request tracing
- Context propagation (automatic field inheritance)
- Human-readable and JSON output formats
- Zero external dependencies (Python stdlib only)

Usage:
    from trcli.logging.structured_logger import LoggerFactory

    logger = LoggerFactory.get_logger("trcli.api")

    # Simple logging
    logger.info("Operation completed", duration=1.5, count=100)

    # With correlation context
    ctx_logger = logger.with_context(correlation_id="abc-123")
    ctx_logger.info("Processing started")
    ctx_logger.info("Processing finished")
"""

import json
import sys
import traceback
from datetime import datetime, timezone
from typing import Dict, Any, Optional, TextIO
from enum import IntEnum


class LogLevel(IntEnum):
    """Standard log levels compatible with Python logging and syslog"""

    DEBUG = 10
    INFO = 20
    WARNING = 30
    ERROR = 40
    CRITICAL = 50


class StructuredLogger:
    """
    Zero-dependency structured logger using standard Python libraries only.
    Outputs NDJSON format compatible with all major observability platforms.

    Example:
        logger = StructuredLogger("trcli.api", level=LogLevel.INFO)
        logger.info("Request completed", status_code=200, duration_ms=150)

        # Output:
        # {"timestamp":"2024-01-20T10:15:30.123456Z","level":"INFO","logger":"trcli.api","message":"Request completed","status_code":200,"duration_ms":150}
    """

    def __init__(
        self, name: str, level: LogLevel = LogLevel.INFO, output_stream: TextIO = None, format_style: str = "json"
    ):
        """
        Initialize structured logger.

        Args:
            name: Logger name (usually module path)
            level: Minimum log level to output
            output_stream: Output stream (default: sys.stderr)
            format_style: Output format - "json" or "text"
        """
        self.name = name
        self.level = level
        self.output_stream = output_stream or sys.stderr
        self.format_style = format_style
        self._context: Dict[str, Any] = {}
        self._sensitive_keys = {
            "password",
            "passwd",
            "pwd",
            "secret",
            "token",
            "api_key",
            "apikey",
            "authorization",
            "auth",
            "credential",
            "key",
        }

    def _should_log(self, level: LogLevel) -> bool:
        """Check if message should be logged based on level"""
        return level.value >= self.level.value

    def _sanitize_value(self, key: str, value: Any) -> Any:
        """
        Sanitize sensitive values to prevent credential leakage.

        Args:
            key: Field name
            value: Field value

        Returns:
            Sanitized value (original or masked)
        """
        # Check if key contains sensitive terms
        key_lower = str(key).lower()
        for sensitive_key in self._sensitive_keys:
            if sensitive_key in key_lower:
                # Mask sensitive data
                if isinstance(value, str):
                    if len(value) <= 4:
                        return "***"
                    # Show first 2 and last 2 chars
                    return f"{value[:2]}***{value[-2:]}"
                return "***REDACTED***"

        return value

    def _format_log(self, level: LogLevel, message: str, extra: Optional[Dict[str, Any]] = None) -> str:
        """
        Format log entry according to configured style.

        Args:
            level: Log level
            message: Log message
            extra: Additional structured fields

        Returns:
            Formatted log string
        """
        log_entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": level.name,
            "logger": self.name,
            "message": message,
        }

        # Add context (correlation IDs, etc.)
        if self._context:
            for key, value in self._context.items():
                log_entry[key] = self._sanitize_value(key, value)

        # Add extra fields
        if extra:
            for key, value in extra.items():
                log_entry[key] = self._sanitize_value(key, value)

        if self.format_style == "json":
            # NDJSON: one JSON object per line
            return json.dumps(log_entry, default=str)
        else:
            # Human-readable format
            timestamp = log_entry["timestamp"]
            level_str = f"[{log_entry['level']}]".ljust(10)
            logger_str = self.name.ljust(20)
            msg = log_entry["message"]

            # Format extra fields
            extra_parts = []
            for key, value in log_entry.items():
                if key not in ["timestamp", "level", "logger", "message"]:
                    extra_parts.append(f"{key}={value}")

            extra_str = ""
            if extra_parts:
                extra_str = " | " + " ".join(extra_parts)

            return f"{timestamp} {level_str} {logger_str} | {msg}{extra_str}"

    def _write(self, level: LogLevel, message: str, extra: Optional[Dict[str, Any]] = None, exc_info: bool = False):
        """
        Write log entry to output stream.

        Args:
            level: Log level
            message: Log message
            extra: Additional structured fields
            exc_info: Include exception traceback
        """
        if not self._should_log(level):
            return

        # Add exception info if requested
        if exc_info:
            if extra is None:
                extra = {}
            exc_type, exc_value, exc_tb = sys.exc_info()
            if exc_type is not None:
                extra["exception"] = {
                    "type": exc_type.__name__,
                    "message": str(exc_value),
                    "traceback": "".join(traceback.format_tb(exc_tb)),
                }

        log_line = self._format_log(level, message, extra)

        try:
            self.output_stream.write(log_line + "\n")
            self.output_stream.flush()
        except Exception:
            # Fallback to stderr if output stream fails
            if self.output_stream != sys.stderr:
                sys.stderr.write(f"Logging error: failed to write to output stream\n")
                sys.stderr.write(log_line + "\n")

    def debug(self, message: str, **extra):
        """
        Log debug message.

        Args:
            message: Log message
            **extra: Additional structured fields

        Example:
            logger.debug("Processing item", item_id=123, status="pending")
        """
        self._write(LogLevel.DEBUG, message, extra)

    def info(self, message: str, **extra):
        """
        Log info message.

        Args:
            message: Log message
            **extra: Additional structured fields

        Example:
            logger.info("Operation completed", duration=1.5, items=100)
        """
        self._write(LogLevel.INFO, message, extra)

    def warning(self, message: str, **extra):
        """
        Log warning message.

        Args:
            message: Log message
            **extra: Additional structured fields

        Example:
            logger.warning("Slow operation detected", duration=30.5, threshold=10.0)
        """
        self._write(LogLevel.WARNING, message, extra)

    def error(self, message: str, exc_info: bool = False, **extra):
        """
        Log error message.

        Args:
            message: Log message
            exc_info: Include exception traceback
            **extra: Additional structured fields

        Example:
            logger.error("Upload failed", exc_info=True, run_id=12345)
        """
        self._write(LogLevel.ERROR, message, extra, exc_info=exc_info)

    def critical(self, message: str, exc_info: bool = False, **extra):
        """
        Log critical message.

        Args:
            message: Log message
            exc_info: Include exception traceback
            **extra: Additional structured fields

        Example:
            logger.critical("System failure", exc_info=True, component="api")
        """
        self._write(LogLevel.CRITICAL, message, extra, exc_info=exc_info)

    def with_context(self, **context) -> "StructuredLogger":
        """
        Return a logger with additional context fields.

        Context fields are automatically added to all log entries from
        the returned logger instance.

        Args:
            **context: Context fields to add

        Returns:
            New logger instance with context

        Example:
            ctx_logger = logger.with_context(correlation_id="abc-123", user="admin")
            ctx_logger.info("Request started")
            ctx_logger.info("Request completed")
            # Both logs will include correlation_id and user fields
        """
        new_logger = StructuredLogger(self.name, self.level, self.output_stream, self.format_style)
        new_logger._context = {**self._context, **context}
        new_logger._sensitive_keys = self._sensitive_keys
        return new_logger

    def set_context(self, **context):
        """
        Set context for all subsequent logs from this logger.

        Args:
            **context: Context fields to add

        Example:
            logger.set_context(request_id="req-123")
            logger.info("Processing")
            # Log will include request_id
        """
        self._context.update(context)

    def clear_context(self):
        """
        Clear all context fields.

        Example:
            logger.clear_context()
        """
        self._context = {}

    def set_level(self, level: LogLevel):
        """
        Set minimum log level.

        Args:
            level: New log level

        Example:
            logger.set_level(LogLevel.DEBUG)
        """
        self.level = level


class LoggerFactory:
    """
    Factory for creating loggers with consistent configuration.

    Provides centralized configuration for all loggers in the application.
    """

    _default_level = LogLevel.INFO
    _default_format = "json"
    _default_stream = sys.stderr
    _loggers: Dict[str, StructuredLogger] = {}

    @classmethod
    def configure(cls, level: str = "INFO", format_style: str = "json", stream: TextIO = None):
        """
        Configure default logger settings.

        Args:
            level: Log level name (DEBUG, INFO, WARNING, ERROR, CRITICAL)
            format_style: Output format - "json" or "text"
            stream: Output stream (default: sys.stderr)

        Example:
            LoggerFactory.configure(level="DEBUG", format_style="text")
        """
        level_upper = level.upper()
        if level_upper in LogLevel.__members__:
            cls._default_level = LogLevel[level_upper]
        else:
            raise ValueError(f"Invalid log level: {level}. Must be one of: DEBUG, INFO, WARNING, ERROR, CRITICAL")

        if format_style not in ["json", "text"]:
            raise ValueError(f"Invalid format style: {format_style}. Must be 'json' or 'text'")

        cls._default_format = format_style

        if stream:
            cls._default_stream = stream

        # Update existing loggers
        for logger in cls._loggers.values():
            logger.level = cls._default_level
            logger.format_style = cls._default_format
            logger.output_stream = cls._default_stream

    @classmethod
    def get_logger(cls, name: str) -> StructuredLogger:
        """
        Get a logger instance with default configuration.

        Returns cached logger if already created for this name.

        Args:
            name: Logger name (usually module path)

        Returns:
            StructuredLogger instance

        Example:
            logger = LoggerFactory.get_logger("trcli.api")
        """
        if name not in cls._loggers:
            cls._loggers[name] = StructuredLogger(name, cls._default_level, cls._default_stream, cls._default_format)
        return cls._loggers[name]

    @classmethod
    def reset(cls):
        """
        Reset factory to defaults and clear all cached loggers.

        Useful for testing.
        """
        cls._default_level = LogLevel.INFO
        cls._default_format = "json"
        cls._default_stream = sys.stderr
        cls._loggers = {}
