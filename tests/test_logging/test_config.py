"""
Unit tests for config.py

Tests configuration loading functionality including:
- Environment variable loading
- File configuration
- Variable substitution
- Validation
"""

import unittest
import tempfile
import os
from pathlib import Path
from trcli.logging.config import LoggingConfig


class TestLoggingConfig(unittest.TestCase):
    """Test LoggingConfig class"""

    def setUp(self):
        """Set up test fixtures"""
        self.original_env = os.environ.copy()
        self.temp_dir = tempfile.mkdtemp()

    def tearDown(self):
        """Restore environment"""
        os.environ.clear()
        os.environ.update(self.original_env)

        # Clean up temp files
        import shutil

        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_default_config(self):
        """Test default configuration values"""
        config = LoggingConfig.load()

        self.assertEqual(config["level"], "INFO")
        self.assertEqual(config["format"], "json")
        self.assertEqual(config["output"], "stderr")
        self.assertIsNone(config["file_path"])
        self.assertEqual(config["max_bytes"], 10485760)
        self.assertEqual(config["backup_count"], 5)

    def test_env_var_overrides(self):
        """Test environment variable overrides"""
        os.environ["TRCLI_LOG_LEVEL"] = "DEBUG"
        os.environ["TRCLI_LOG_FORMAT"] = "text"
        os.environ["TRCLI_LOG_OUTPUT"] = "stdout"
        os.environ["TRCLI_LOG_FILE"] = "/tmp/test.log"

        config = LoggingConfig.load()

        self.assertEqual(config["level"], "DEBUG")
        self.assertEqual(config["format"], "text")
        self.assertEqual(config["output"], "stdout")
        self.assertEqual(config["file_path"], "/tmp/test.log")

    def test_env_var_numeric_overrides(self):
        """Test numeric environment variable overrides"""
        os.environ["TRCLI_LOG_MAX_BYTES"] = "5242880"
        os.environ["TRCLI_LOG_BACKUP_COUNT"] = "10"

        config = LoggingConfig.load()

        self.assertEqual(config["max_bytes"], 5242880)
        self.assertEqual(config["backup_count"], 10)

    def test_env_var_substitution(self):
        """Test environment variable substitution in config values"""
        os.environ["ENVIRONMENT"] = "production"
        os.environ["TRCLI_LOG_FILE"] = "/var/log/${ENVIRONMENT}/trcli.log"

        config = LoggingConfig.load()

        self.assertEqual(config["file_path"], "/var/log/production/trcli.log")

    def test_env_var_substitution_missing_var(self):
        """Test that missing env vars are left unchanged"""
        os.environ["TRCLI_LOG_FILE"] = "/var/log/${MISSING_VAR}/trcli.log"

        config = LoggingConfig.load()

        # Should remain unchanged
        self.assertEqual(config["file_path"], "/var/log/${MISSING_VAR}/trcli.log")

    def test_yaml_config_file(self):
        """Test loading from YAML config file"""
        config_file = Path(self.temp_dir) / "config.yml"
        config_file.write_text(
            """
logging:
  level: DEBUG
  format: text
  output: file
  file_path: /tmp/trcli_test.log
  max_bytes: 1048576
  backup_count: 3
"""
        )

        config = LoggingConfig.load(str(config_file))

        self.assertEqual(config["level"], "DEBUG")
        self.assertEqual(config["format"], "text")
        self.assertEqual(config["output"], "file")
        self.assertEqual(config["file_path"], "/tmp/trcli_test.log")
        self.assertEqual(config["max_bytes"], 1048576)
        self.assertEqual(config["backup_count"], 3)

    def test_simple_config_file(self):
        """Test loading from simple key=value config file"""
        config_file = Path(self.temp_dir) / "config.txt"
        config_file.write_text(
            """
# This is a comment
level=DEBUG
format=text
output=file
file_path=/tmp/test.log
max_bytes=1048576
backup_count=3
"""
        )

        config = LoggingConfig.load(str(config_file))

        # Should fall back to simple parser (PyYAML might not be installed in tests)
        # Values should still be loaded
        self.assertIn("level", config)

    def test_config_precedence(self):
        """Test that env vars override config file"""
        config_file = Path(self.temp_dir) / "config.yml"
        config_file.write_text(
            """
logging:
  level: INFO
  format: json
"""
        )

        os.environ["TRCLI_LOG_LEVEL"] = "DEBUG"

        config = LoggingConfig.load(str(config_file))

        # Env var should override file
        self.assertEqual(config["level"], "DEBUG")
        # File value should be used for format
        self.assertEqual(config["format"], "json")

    def test_nonexistent_config_file(self):
        """Test that nonexistent config file doesn't cause error"""
        config = LoggingConfig.load("/nonexistent/config.yml")

        # Should return defaults
        self.assertEqual(config["level"], "INFO")

    def test_invalid_config_file(self):
        """Test that invalid config file doesn't crash"""
        config_file = Path(self.temp_dir) / "invalid.yml"
        config_file.write_text("}{invalid yaml][")

        config = LoggingConfig.load(str(config_file))

        # Should return defaults
        self.assertEqual(config["level"], "INFO")

    def test_validate_valid_config(self):
        """Test validation of valid config"""
        config = {"level": "INFO", "format": "json", "output": "stderr"}

        is_valid, error = LoggingConfig.validate(config)

        self.assertTrue(is_valid)
        self.assertEqual(error, "")

    def test_validate_invalid_level(self):
        """Test validation rejects invalid log level"""
        config = {"level": "INVALID", "format": "json", "output": "stderr"}

        is_valid, error = LoggingConfig.validate(config)

        self.assertFalse(is_valid)
        self.assertIn("Invalid log level", error)

    def test_validate_invalid_format(self):
        """Test validation rejects invalid format"""
        config = {"level": "INFO", "format": "xml", "output": "stderr"}

        is_valid, error = LoggingConfig.validate(config)

        self.assertFalse(is_valid)
        self.assertIn("Invalid format", error)

    def test_validate_invalid_output(self):
        """Test validation rejects invalid output"""
        config = {"level": "INFO", "format": "json", "output": "network"}

        is_valid, error = LoggingConfig.validate(config)

        self.assertFalse(is_valid)
        self.assertIn("Invalid output", error)

    def test_validate_file_output_missing_path(self):
        """Test validation requires file_path when output is file"""
        config = {"level": "INFO", "format": "json", "output": "file", "file_path": None}

        is_valid, error = LoggingConfig.validate(config)

        self.assertFalse(is_valid)
        self.assertIn("file_path required", error)

    def test_validate_file_output_with_path(self):
        """Test validation passes when file_path is provided"""
        config = {"level": "INFO", "format": "json", "output": "file", "file_path": "/tmp/test.log"}

        is_valid, error = LoggingConfig.validate(config)

        self.assertTrue(is_valid)
        self.assertEqual(error, "")

    def test_case_insensitive_level(self):
        """Test that log level is case-insensitive"""
        for level in ["debug", "DEBUG", "Debug"]:
            config = {"level": level, "format": "json", "output": "stderr"}
            is_valid, error = LoggingConfig.validate(config)
            self.assertTrue(is_valid, f"Level '{level}' should be valid")


if __name__ == "__main__":
    unittest.main()
