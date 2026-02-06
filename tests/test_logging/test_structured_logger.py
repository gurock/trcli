"""
Unit tests for structured_logger.py

Tests the core logging functionality including:
- Log levels
- Structured fields
- Credential sanitization
- Context propagation
- Output formats (JSON and text)
"""

import unittest
import json
import sys
from io import StringIO
from trcli.logging.structured_logger import StructuredLogger, LoggerFactory, LogLevel


class TestLogLevel(unittest.TestCase):
    """Test LogLevel enum"""

    def test_log_levels(self):
        """Test that log levels have correct values"""
        self.assertEqual(LogLevel.DEBUG, 10)
        self.assertEqual(LogLevel.INFO, 20)
        self.assertEqual(LogLevel.WARNING, 30)
        self.assertEqual(LogLevel.ERROR, 40)
        self.assertEqual(LogLevel.CRITICAL, 50)

    def test_log_level_ordering(self):
        """Test that log levels are properly ordered"""
        self.assertLess(LogLevel.DEBUG, LogLevel.INFO)
        self.assertLess(LogLevel.INFO, LogLevel.WARNING)
        self.assertLess(LogLevel.WARNING, LogLevel.ERROR)
        self.assertLess(LogLevel.ERROR, LogLevel.CRITICAL)


class TestStructuredLogger(unittest.TestCase):
    """Test StructuredLogger class"""

    def setUp(self):
        """Set up test fixtures"""
        self.output = StringIO()
        self.logger = StructuredLogger(
            "test.logger", level=LogLevel.DEBUG, output_stream=self.output, format_style="json"
        )

    def tearDown(self):
        """Clean up"""
        self.output.close()

    def test_logger_initialization(self):
        """Test logger is initialized correctly"""
        self.assertEqual(self.logger.name, "test.logger")
        self.assertEqual(self.logger.level, LogLevel.DEBUG)
        self.assertEqual(self.logger.format_style, "json")

    def test_log_level_filtering(self):
        """Test that log level filtering works"""
        # Set level to INFO
        self.logger.level = LogLevel.INFO

        # DEBUG should not log
        self.logger.debug("Debug message")
        self.assertEqual(self.output.getvalue(), "")

        # INFO should log
        self.logger.info("Info message")
        self.assertIn("Info message", self.output.getvalue())

    def test_json_format(self):
        """Test JSON output format"""
        self.logger.info("Test message", field1="value1", field2=123)

        output = self.output.getvalue()
        log_entry = json.loads(output.strip())

        self.assertEqual(log_entry["level"], "INFO")
        self.assertEqual(log_entry["logger"], "test.logger")
        self.assertEqual(log_entry["message"], "Test message")
        self.assertEqual(log_entry["field1"], "value1")
        self.assertEqual(log_entry["field2"], 123)
        self.assertIn("timestamp", log_entry)

    def test_text_format(self):
        """Test text output format"""
        text_logger = StructuredLogger(
            "test.logger", level=LogLevel.INFO, output_stream=self.output, format_style="text"
        )

        text_logger.info("Test message", field1="value1")

        output = self.output.getvalue()
        self.assertIn("[INFO]", output)
        self.assertIn("test.logger", output)
        self.assertIn("Test message", output)
        self.assertIn("field1=value1", output)

    def test_credential_sanitization(self):
        """Test that sensitive fields are sanitized"""
        self.logger.info(
            "Auth configured",
            password="secret123",
            api_key="sk_live_abc123def456",
            token="bearer_xyz789",
            username="admin",  # Not sensitive
        )

        output = self.output.getvalue()
        log_entry = json.loads(output.strip())

        # Sensitive fields should be masked
        self.assertNotEqual(log_entry["password"], "secret123")
        self.assertIn("***", log_entry["password"])

        self.assertNotEqual(log_entry["api_key"], "sk_live_abc123def456")
        self.assertIn("***", log_entry["api_key"])

        self.assertNotEqual(log_entry["token"], "bearer_xyz789")
        self.assertIn("***", log_entry["token"])

        # Non-sensitive field should not be masked
        self.assertEqual(log_entry["username"], "admin")

    def test_context_propagation(self):
        """Test that context fields are included in logs"""
        ctx_logger = self.logger.with_context(correlation_id="abc-123", request_id=456)

        ctx_logger.info("Test message")

        output = self.output.getvalue()
        log_entry = json.loads(output.strip())

        self.assertEqual(log_entry["correlation_id"], "abc-123")
        self.assertEqual(log_entry["request_id"], 456)

    def test_context_inheritance(self):
        """Test that context is inherited in new logger instance"""
        ctx_logger = self.logger.with_context(user="admin")
        ctx_logger2 = ctx_logger.with_context(action="upload")

        ctx_logger2.info("Test message")

        output = self.output.getvalue()
        log_entry = json.loads(output.strip())

        # Both context fields should be present
        self.assertEqual(log_entry["user"], "admin")
        self.assertEqual(log_entry["action"], "upload")

    def test_set_context(self):
        """Test set_context method"""
        self.logger.set_context(correlation_id="xyz-789")
        self.logger.info("Message 1")

        self.logger.set_context(request_id=123)
        self.logger.info("Message 2")

        output = self.output.getvalue()
        lines = output.strip().split("\n")

        log1 = json.loads(lines[0])
        log2 = json.loads(lines[1])

        # First log should have correlation_id
        self.assertEqual(log1["correlation_id"], "xyz-789")

        # Second log should have both (set_context updates, doesn't replace)
        self.assertEqual(log2["correlation_id"], "xyz-789")
        self.assertEqual(log2["request_id"], 123)

    def test_clear_context(self):
        """Test clear_context method"""
        self.logger.set_context(correlation_id="abc-123")
        self.logger.info("Message 1")

        self.logger.clear_context()
        self.logger.info("Message 2")

        output = self.output.getvalue()
        lines = output.strip().split("\n")

        log1 = json.loads(lines[0])
        log2 = json.loads(lines[1])

        # First log should have context
        self.assertIn("correlation_id", log1)

        # Second log should not have context
        self.assertNotIn("correlation_id", log2)

    def test_exception_logging(self):
        """Test exception info is included when exc_info=True"""
        try:
            raise ValueError("Test error")
        except ValueError:
            self.logger.error("Error occurred", exc_info=True)

        output = self.output.getvalue()
        log_entry = json.loads(output.strip())

        self.assertEqual(log_entry["level"], "ERROR")
        self.assertIn("exception", log_entry)
        self.assertEqual(log_entry["exception"]["type"], "ValueError")
        self.assertEqual(log_entry["exception"]["message"], "Test error")
        self.assertIn("traceback", log_entry["exception"])

    def test_all_log_levels(self):
        """Test all log level methods"""
        self.logger.debug("Debug message")
        self.logger.info("Info message")
        self.logger.warning("Warning message")
        self.logger.error("Error message")
        self.logger.critical("Critical message")

        output = self.output.getvalue()
        lines = output.strip().split("\n")

        self.assertEqual(len(lines), 5)

        levels = [json.loads(line)["level"] for line in lines]
        self.assertEqual(levels, ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"])


class TestLoggerFactory(unittest.TestCase):
    """Test LoggerFactory class"""

    def setUp(self):
        """Reset factory before each test"""
        LoggerFactory.reset()

    def tearDown(self):
        """Reset factory after each test"""
        LoggerFactory.reset()

    def test_factory_defaults(self):
        """Test factory default configuration"""
        logger = LoggerFactory.get_logger("test")

        self.assertEqual(logger.level, LogLevel.INFO)
        self.assertEqual(logger.format_style, "json")
        self.assertEqual(logger.output_stream, sys.stderr)

    def test_factory_configure(self):
        """Test factory configuration"""
        output = StringIO()
        LoggerFactory.configure(level="DEBUG", format_style="text", stream=output)

        logger = LoggerFactory.get_logger("test")

        self.assertEqual(logger.level, LogLevel.DEBUG)
        self.assertEqual(logger.format_style, "text")
        self.assertEqual(logger.output_stream, output)

    def test_factory_invalid_level(self):
        """Test that invalid log level raises error"""
        with self.assertRaises(ValueError):
            LoggerFactory.configure(level="INVALID")

    def test_factory_invalid_format(self):
        """Test that invalid format raises error"""
        with self.assertRaises(ValueError):
            LoggerFactory.configure(format_style="xml")

    def test_factory_caches_loggers(self):
        """Test that factory caches logger instances"""
        logger1 = LoggerFactory.get_logger("test")
        logger2 = LoggerFactory.get_logger("test")

        # Should be the same instance
        self.assertIs(logger1, logger2)

    def test_factory_different_names(self):
        """Test that different names create different loggers"""
        logger1 = LoggerFactory.get_logger("test1")
        logger2 = LoggerFactory.get_logger("test2")

        # Should be different instances
        self.assertIsNot(logger1, logger2)
        self.assertEqual(logger1.name, "test1")
        self.assertEqual(logger2.name, "test2")

    def test_factory_updates_existing_loggers(self):
        """Test that configure updates existing loggers"""
        logger = LoggerFactory.get_logger("test")
        original_level = logger.level

        # Reconfigure
        LoggerFactory.configure(level="DEBUG")

        # Existing logger should be updated
        self.assertNotEqual(logger.level, original_level)
        self.assertEqual(logger.level, LogLevel.DEBUG)

    def test_factory_reset(self):
        """Test factory reset clears cache"""
        LoggerFactory.get_logger("test1")
        LoggerFactory.get_logger("test2")

        # Reset
        LoggerFactory.reset()

        # Check that defaults are restored
        self.assertEqual(LoggerFactory._default_level, LogLevel.INFO)
        self.assertEqual(LoggerFactory._default_format, "json")
        self.assertEqual(len(LoggerFactory._loggers), 0)


class TestCredentialSanitization(unittest.TestCase):
    """Test credential sanitization in detail"""

    def setUp(self):
        """Set up test fixtures"""
        self.output = StringIO()
        self.logger = StructuredLogger("test", output_stream=self.output, format_style="json")

    def tearDown(self):
        """Clean up"""
        self.output.close()

    def test_sanitize_password(self):
        """Test password sanitization"""
        self.logger.info("Test", password="secret123")

        log_entry = json.loads(self.output.getvalue().strip())
        self.assertNotEqual(log_entry["password"], "secret123")
        self.assertIn("***", log_entry["password"])

    def test_sanitize_api_key(self):
        """Test API key sanitization"""
        self.logger.info("Test", api_key="sk_live_123456")

        log_entry = json.loads(self.output.getvalue().strip())
        self.assertNotEqual(log_entry["api_key"], "sk_live_123456")

    def test_sanitize_token(self):
        """Test token sanitization"""
        self.logger.info("Test", token="bearer_xyz789")

        log_entry = json.loads(self.output.getvalue().strip())
        self.assertNotEqual(log_entry["token"], "bearer_xyz789")

    def test_sanitize_short_password(self):
        """Test short password sanitization"""
        self.logger.info("Test", password="123")

        log_entry = json.loads(self.output.getvalue().strip())
        self.assertEqual(log_entry["password"], "***")

    def test_no_sanitization_non_sensitive(self):
        """Test that non-sensitive fields are not sanitized"""
        self.logger.info("Test", username="admin", host="example.com", port=8080)

        log_entry = json.loads(self.output.getvalue().strip())
        self.assertEqual(log_entry["username"], "admin")
        self.assertEqual(log_entry["host"], "example.com")
        self.assertEqual(log_entry["port"], 8080)

    def test_sanitize_in_context(self):
        """Test that context fields are also sanitized"""
        ctx_logger = self.logger.with_context(password="secret")
        ctx_logger.info("Test")

        log_entry = json.loads(self.output.getvalue().strip())
        self.assertNotEqual(log_entry["password"], "secret")


if __name__ == "__main__":
    unittest.main()
