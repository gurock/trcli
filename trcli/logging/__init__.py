"""
TRCLI Logging Module - Core Edition

Zero-dependency, vendor-neutral logging infrastructure for TRCLI.
Simplified to include only essential features for CLI tools.

Provides:
- Structured logging (NDJSON and text formats)
- File output with automatic rotation
- Flexible configuration (file, env vars, CLI flags)
- Credential sanitization
- Correlation ID support
- Zero external dependencies

Usage:
    from trcli.logging import get_logger

    logger = get_logger("trcli.module")
    logger.info("Operation completed", duration=1.5, items=100)

Configuration:
    # Via environment variables
    export TRCLI_LOG_LEVEL=DEBUG
    export TRCLI_LOG_FORMAT=json
    export TRCLI_LOG_FILE=/var/log/trcli/app.log

    # Via configuration file
    from trcli.logging.config import LoggingConfig
    LoggingConfig.setup_logging(config_path="trcli_config.yml")
"""

from trcli.logging.structured_logger import LoggerFactory, StructuredLogger, LogLevel

__all__ = [
    "LoggerFactory",
    "StructuredLogger",
    "LogLevel",
    "get_logger",
]


def get_logger(name: str) -> StructuredLogger:
    """
    Get a logger instance with default configuration.

    Args:
        name: Logger name (usually module path like "trcli.api.client")

    Returns:
        StructuredLogger instance

    Example:
        logger = get_logger("trcli.api")
        logger.info("Request completed", status_code=200, duration=1.5)
    """
    return LoggerFactory.get_logger(name)
