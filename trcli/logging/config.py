"""
Configuration System - Simple logging configuration for TRCLI

Provides centralized configuration loading from multiple sources
with precedence handling and environment variable substitution.
"""

import os
import sys
import re
from pathlib import Path
from typing import Dict, Any, Optional


class LoggingConfig:
    """
    Centralized logging configuration for TRCLI.

    Reads from file, environment variables, or CLI flags with
    proper precedence handling.

    Example configuration file (trcli_config.yml):
        logging:
          enabled: true       # Must be true to enable logging (default: false)
          level: INFO
          format: json        # json or text
          output: file        # stderr, stdout, file
          file_path: /var/log/trcli/app.log
          max_bytes: 10485760  # 10MB
          backup_count: 5
    """

    DEFAULT_CONFIG = {
        "enabled": False,
        "level": "INFO",
        "format": "json",  # json or text
        "output": "stderr",  # stderr, stdout, file
        "file_path": None,
        "max_bytes": 10485760,  # 10MB
        "backup_count": 5,
    }

    @classmethod
    def load(cls, config_path: Optional[str] = None) -> Dict[str, Any]:
        """
        Load configuration from multiple sources.

        Precedence: CLI > Environment > File > Default

        Args:
            config_path: Path to configuration file

        Returns:
            Configuration dictionary

        Example:
            config = LoggingConfig.load("trcli_config.yml")
        """
        config = cls.DEFAULT_CONFIG.copy()

        # 1. Load from file
        if config_path and Path(config_path).exists():
            file_config = cls._load_from_file(config_path)
            if file_config and "logging" in file_config:
                config.update(file_config["logging"])

        # 2. Override with environment variables
        config = cls._apply_env_overrides(config)

        # 3. Substitute environment variables in values
        config = cls._substitute_env_vars(config)

        return config

    @classmethod
    def _load_from_file(cls, config_path: str) -> Optional[Dict[str, Any]]:
        """
        Load configuration from YAML file.

        Args:
            config_path: Path to configuration file

        Returns:
            Configuration dictionary or None if error
        """
        try:
            # Try to import yaml
            import yaml

            with open(config_path) as f:
                return yaml.safe_load(f)
        except ImportError:
            # YAML not available, try simple parsing
            sys.stderr.write(
                "Warning: PyYAML not installed, using simple config parser. "
                "Install PyYAML for full configuration support.\n"
            )
            return cls._load_simple_config(config_path)
        except Exception as e:
            sys.stderr.write(f"Error loading config file {config_path}: {e}\n")
            return None

    @classmethod
    def _load_simple_config(cls, config_path: str) -> Optional[Dict[str, Any]]:
        """
        Load configuration using simple key=value parser.

        Fallback for when PyYAML is not available.

        Args:
            config_path: Path to configuration file

        Returns:
            Configuration dictionary or None if error
        """
        try:
            config = {"logging": {}}
            with open(config_path) as f:
                for line in f:
                    line = line.strip()
                    # Skip comments and empty lines
                    if not line or line.startswith("#"):
                        continue
                    # Parse key=value
                    if "=" in line:
                        key, value = line.split("=", 1)
                        key = key.strip()
                        value = value.strip().strip('"').strip("'")
                        # Convert known numeric values
                        if key in ["max_bytes", "backup_count"]:
                            try:
                                value = int(value)
                            except ValueError:
                                pass
                        config["logging"][key] = value
            return config
        except Exception as e:
            sys.stderr.write(f"Error parsing config file {config_path}: {e}\n")
            return None

    @classmethod
    def _apply_env_overrides(cls, config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Apply environment variable overrides.

        Environment variables:
            TRCLI_LOG_ENABLED: Enable/disable logging (true, false, yes, no, 1, 0)
            TRCLI_LOG_LEVEL: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
            TRCLI_LOG_FORMAT: Output format (json, text)
            TRCLI_LOG_OUTPUT: Output destination (stderr, stdout, file)
            TRCLI_LOG_FILE: Log file path
            TRCLI_LOG_MAX_BYTES: Max log file size before rotation
            TRCLI_LOG_BACKUP_COUNT: Number of backup files to keep

        Args:
            config: Configuration dictionary

        Returns:
            Updated configuration dictionary
        """
        # Boolean override for enabled flag
        if "TRCLI_LOG_ENABLED" in os.environ:
            enabled_value = os.environ["TRCLI_LOG_ENABLED"].lower()
            config["enabled"] = enabled_value in ("true", "yes", "1", "on")

        # Simple overrides
        env_mappings = {
            "TRCLI_LOG_LEVEL": "level",
            "TRCLI_LOG_FORMAT": "format",
            "TRCLI_LOG_OUTPUT": "output",
            "TRCLI_LOG_FILE": "file_path",
        }

        for env_var, config_key in env_mappings.items():
            if env_var in os.environ:
                config[config_key] = os.environ[env_var]

        # Numeric overrides
        if "TRCLI_LOG_MAX_BYTES" in os.environ:
            try:
                config["max_bytes"] = int(os.environ["TRCLI_LOG_MAX_BYTES"])
            except ValueError:
                pass

        if "TRCLI_LOG_BACKUP_COUNT" in os.environ:
            try:
                config["backup_count"] = int(os.environ["TRCLI_LOG_BACKUP_COUNT"])
            except ValueError:
                pass

        return config

    @classmethod
    def _substitute_env_vars(cls, config: Any) -> Any:
        """
        Recursively substitute environment variables in configuration.

        Supports ${VAR_NAME} syntax.

        Example:
            file_path: /var/log/${ENVIRONMENT}/trcli.log
            With ENVIRONMENT=production, becomes:
            file_path: /var/log/production/trcli.log

        Args:
            config: Configuration value (string, dict, list, etc.)

        Returns:
            Configuration with substituted values
        """
        if isinstance(config, str):
            # Substitute environment variables
            def replace_env(match):
                var_name = match.group(1)
                return os.environ.get(var_name, match.group(0))

            return re.sub(r"\$\{([^}]+)\}", replace_env, config)

        elif isinstance(config, dict):
            return {k: cls._substitute_env_vars(v) for k, v in config.items()}

        elif isinstance(config, list):
            return [cls._substitute_env_vars(item) for item in config]

        else:
            return config

    @classmethod
    def setup_logging(cls, config_path: Optional[str] = None, **overrides):
        """
        Setup logging based on configuration.

        Args:
            config_path: Path to configuration file
            **overrides: Configuration overrides (e.g., level="DEBUG")

        Example:
            LoggingConfig.setup_logging(
                config_path="trcli_config.yml",
                level="DEBUG",
                format="text"
            )
        """
        from trcli.logging.structured_logger import LoggerFactory
        from trcli.logging.file_handler import RotatingFileHandler

        # Load configuration
        config = cls.load(config_path)
        config.update(overrides)

        if not config.get("enabled", True):
            from trcli.logging.structured_logger import LoggerFactory, LogLevel
            import os

            # Set log level to maximum to effectively disable all logging
            LoggerFactory.configure(level="CRITICAL", format_style="json", stream=open(os.devnull, "w"))
            return

        # Determine output stream
        output_type = config.get("output", "stderr")

        if output_type == "stdout":
            stream = sys.stdout
        elif output_type == "stderr":
            stream = sys.stderr
        elif output_type == "file":
            file_path = config.get("file_path")
            if not file_path:
                sys.stderr.write("Warning: file output selected but no file_path specified, using stderr\n")
                stream = sys.stderr
            else:
                stream = RotatingFileHandler(
                    file_path, max_bytes=config.get("max_bytes", 10485760), backup_count=config.get("backup_count", 5)
                )
        else:
            stream = sys.stderr

        # Configure logger factory
        LoggerFactory.configure(
            level=config.get("level", "INFO"), format_style=config.get("format", "json"), stream=stream
        )

    @classmethod
    def validate(cls, config: Dict[str, Any]) -> tuple:
        """
        Validate configuration.

        Args:
            config: Configuration dictionary

        Returns:
            Tuple of (is_valid, error_message)

        Example:
            is_valid, error = LoggingConfig.validate(config)
            if not is_valid:
                print(f"Invalid configuration: {error}")
        """
        # Validate log level
        valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        level = config.get("level", "INFO").upper()
        if level not in valid_levels:
            return False, f"Invalid log level '{level}'. Must be one of: {', '.join(valid_levels)}"

        # Validate format
        valid_formats = ["json", "text"]
        format_style = config.get("format", "json")
        if format_style not in valid_formats:
            return False, f"Invalid format '{format_style}'. Must be one of: {', '.join(valid_formats)}"

        # Validate output
        valid_outputs = ["stderr", "stdout", "file"]
        output = config.get("output", "stderr")
        if output not in valid_outputs:
            return False, f"Invalid output '{output}'. Must be one of: {', '.join(valid_outputs)}"

        # Validate file output config
        if output == "file" and not config.get("file_path"):
            return False, "file_path required when output is 'file'"

        return True, ""
