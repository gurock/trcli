"""
Integration tests for logging infrastructure

Tests end-to-end scenarios combining multiple components:
- Logger + File Handler
- Logger + Config
- Complete workflow tests
"""

import unittest
import tempfile
import shutil
import json
import os
from pathlib import Path
from io import StringIO

from trcli.logging import get_logger
from trcli.logging.structured_logger import LoggerFactory, LogLevel
from trcli.logging.file_handler import RotatingFileHandler
from trcli.logging.config import LoggingConfig


class TestEndToEndLogging(unittest.TestCase):
    """Test complete end-to-end logging scenarios"""

    def setUp(self):
        """Set up test fixtures"""
        self.temp_dir = tempfile.mkdtemp()
        self.log_file = Path(self.temp_dir) / "test.log"
        LoggerFactory.reset()

    def tearDown(self):
        """Clean up"""
        shutil.rmtree(self.temp_dir, ignore_errors=True)
        LoggerFactory.reset()

    def test_json_logging_to_file(self):
        """Test JSON logging to file"""
        # Setup file handler
        file_handler = RotatingFileHandler(str(self.log_file))
        LoggerFactory.configure(level="INFO", format_style="json", stream=file_handler)

        # Log some messages
        logger = get_logger("test.integration")
        logger.info("Message 1", field1="value1")
        logger.info("Message 2", field2="value2")

        file_handler.close()

        # Read and parse JSON logs
        content = self.log_file.read_text()
        lines = content.strip().split("\n")

        self.assertEqual(len(lines), 2)

        log1 = json.loads(lines[0])
        log2 = json.loads(lines[1])

        self.assertEqual(log1["message"], "Message 1")
        self.assertEqual(log1["field1"], "value1")
        self.assertEqual(log2["message"], "Message 2")
        self.assertEqual(log2["field2"], "value2")

    def test_text_logging_to_file(self):
        """Test text logging to file"""
        file_handler = RotatingFileHandler(str(self.log_file))
        LoggerFactory.configure(level="INFO", format_style="text", stream=file_handler)

        logger = get_logger("test.integration")
        logger.info("Test message", status="ok")

        file_handler.close()

        content = self.log_file.read_text()
        self.assertIn("[INFO]", content)
        self.assertIn("Test message", content)
        self.assertIn("status=ok", content)

    def test_correlation_id_workflow(self):
        """Test complete workflow with correlation IDs"""
        output = StringIO()
        LoggerFactory.configure(level="INFO", format_style="json", stream=output)

        logger = get_logger("test.workflow")

        # Simulate request workflow
        correlation_id = "abc-123-def"
        ctx_logger = logger.with_context(correlation_id=correlation_id)

        ctx_logger.info("Request received", endpoint="/api/upload")
        ctx_logger.info("Processing started", items=100)
        ctx_logger.info("Processing completed", status="success")

        output.seek(0)
        lines = output.getvalue().strip().split("\n")

        # All logs should have correlation_id
        for line in lines:
            log_entry = json.loads(line)
            self.assertEqual(log_entry["correlation_id"], correlation_id)

    def test_credential_sanitization_workflow(self):
        """Test credential sanitization in realistic scenario"""
        output = StringIO()
        LoggerFactory.configure(format_style="json", stream=output)

        logger = get_logger("test.security")

        # Simulate authentication flow
        logger.info(
            "Connecting to API",
            host="api.example.com",
            username="admin",
            password="secretPassword123",  # Should be sanitized
            api_key="sk_live_abc123def456",  # Should be sanitized
        )

        logger.info("API request", endpoint="/api/data", token="bearer_xyz789")  # Should be sanitized

        output.seek(0)
        content = output.getvalue()

        # Ensure credentials are not exposed
        self.assertNotIn("secretPassword123", content)
        self.assertNotIn("sk_live_abc123def456", content)
        self.assertNotIn("bearer_xyz789", content)

        # But ensure masking indicators are present
        self.assertIn("***", content)

    def test_multi_logger_scenario(self):
        """Test multiple loggers with different configurations"""
        output = StringIO()
        LoggerFactory.configure(level="INFO", format_style="json", stream=output)

        api_logger = get_logger("test.api")
        db_logger = get_logger("test.database")
        auth_logger = get_logger("test.auth")

        api_logger.info("API request", endpoint="/api/users")
        db_logger.info("Database query", table="users", operation="SELECT")
        auth_logger.info("User login", user="admin")

        output.seek(0)
        lines = output.getvalue().strip().split("\n")

        self.assertEqual(len(lines), 3)

        loggers_used = [json.loads(line)["logger"] for line in lines]
        self.assertIn("test.api", loggers_used)
        self.assertIn("test.database", loggers_used)
        self.assertIn("test.auth", loggers_used)

    def test_log_rotation_workflow(self):
        """Test log rotation in realistic scenario"""
        file_handler = RotatingFileHandler(str(self.log_file), max_bytes=500, backup_count=3)  # Small for testing

        LoggerFactory.configure(format_style="json", stream=file_handler)
        logger = get_logger("test.rotation")

        # Write enough logs to trigger rotation
        for i in range(50):
            logger.info(f"Log entry {i}", entry_num=i, data="x" * 20)

        file_handler.close()

        # Check that rotation occurred
        main_log = self.log_file
        backup1 = Path(f"{self.log_file}.1")

        self.assertTrue(main_log.exists())
        self.assertTrue(backup1.exists(), "Rotation should have created backup files")

    def test_error_handling_workflow(self):
        """Test error logging with exception info"""
        output = StringIO()
        LoggerFactory.configure(format_style="json", stream=output)

        logger = get_logger("test.errors")

        logger.info("Starting operation", operation_id=123)

        try:
            # Simulate error
            result = 1 / 0
        except ZeroDivisionError:
            logger.error("Operation failed", exc_info=True, operation_id=123)

        logger.info("Cleanup completed", operation_id=123)

        output.seek(0)
        lines = output.getvalue().strip().split("\n")

        # Find the error log
        error_log = None
        for line in lines:
            log_entry = json.loads(line)
            if log_entry["level"] == "ERROR":
                error_log = log_entry
                break

        self.assertIsNotNone(error_log)
        self.assertIn("exception", error_log)
        self.assertEqual(error_log["exception"]["type"], "ZeroDivisionError")


class TestConfigIntegration(unittest.TestCase):
    """Test integration with configuration system"""

    def setUp(self):
        """Set up test fixtures"""
        self.temp_dir = tempfile.mkdtemp()
        self.original_env = os.environ.copy()
        LoggerFactory.reset()

    def tearDown(self):
        """Clean up"""
        shutil.rmtree(self.temp_dir, ignore_errors=True)
        os.environ.clear()
        os.environ.update(self.original_env)
        LoggerFactory.reset()

    def test_config_file_integration(self):
        """Test loading configuration and using it"""
        config_file = Path(self.temp_dir) / "config.yml"
        log_file = Path(self.temp_dir) / "app.log"

        config_file.write_text(
            f"""
logging:
  level: DEBUG
  format: json
  output: file
  file_path: {log_file}
  max_bytes: 10485760
  backup_count: 5
"""
        )

        # Load and apply configuration
        LoggingConfig.setup_logging(str(config_file))

        # Use logger
        logger = get_logger("test.config")
        logger.debug("Debug message")
        logger.info("Info message")

        # Close any open file handlers
        for handler_logger in LoggerFactory._loggers.values():
            if hasattr(handler_logger.output_stream, "close"):
                handler_logger.output_stream.close()

        # Check that logs were written
        self.assertTrue(log_file.exists())

        content = log_file.read_text()
        self.assertIn("Debug message", content)
        self.assertIn("Info message", content)

    def test_env_var_integration(self):
        """Test environment variable configuration"""
        log_file = Path(self.temp_dir) / "env_test.log"

        os.environ["TRCLI_LOG_LEVEL"] = "WARNING"
        os.environ["TRCLI_LOG_FORMAT"] = "json"
        os.environ["TRCLI_LOG_OUTPUT"] = "file"
        os.environ["TRCLI_LOG_FILE"] = str(log_file)

        LoggingConfig.setup_logging()

        logger = get_logger("test.env")
        logger.debug("Debug - should not appear")
        logger.info("Info - should not appear")
        logger.warning("Warning - should appear")
        logger.error("Error - should appear")

        # Close file handler
        for handler_logger in LoggerFactory._loggers.values():
            if hasattr(handler_logger.output_stream, "close"):
                handler_logger.output_stream.close()

        content = log_file.read_text()

        # Only WARNING and above should be logged
        self.assertNotIn("Debug", content)
        self.assertNotIn("Info", content)
        self.assertIn("Warning", content)
        self.assertIn("Error", content)


class TestRealWorldScenarios(unittest.TestCase):
    """Test real-world usage scenarios"""

    def setUp(self):
        """Set up test fixtures"""
        self.output = StringIO()
        LoggerFactory.reset()
        LoggerFactory.configure(format_style="json", stream=self.output)

    def tearDown(self):
        """Clean up"""
        LoggerFactory.reset()

    def test_ci_cd_pipeline_scenario(self):
        """Test typical CI/CD usage"""
        logger = get_logger("trcli.ci")

        # Simulate test result upload
        logger.info("Test results processing started", run_id=12345, project="MyProject", total_tests=150)

        logger.info("Uploading to TestRail", endpoint="https://example.testrail.com", run_id=12345)

        logger.info("Upload completed", run_id=12345, uploaded=150, failed=0, duration_seconds=12.5, status="success")

        self.output.seek(0)
        logs = [json.loads(line) for line in self.output.getvalue().strip().split("\n")]

        # Verify logs are parseable and contain expected data
        self.assertEqual(len(logs), 3)
        self.assertTrue(all(log["level"] == "INFO" for log in logs))
        self.assertEqual(logs[-1]["status"], "success")

    def test_concurrent_uploads_scenario(self):
        """Test handling concurrent operations with correlation IDs"""
        logger = get_logger("trcli.concurrent")

        # Simulate two concurrent uploads
        upload1_logger = logger.with_context(correlation_id="upload-1", run_id=100)
        upload2_logger = logger.with_context(correlation_id="upload-2", run_id=200)

        upload1_logger.info("Upload started")
        upload2_logger.info("Upload started")
        upload1_logger.info("Upload progress", percent=50)
        upload2_logger.info("Upload progress", percent=30)
        upload1_logger.info("Upload completed")
        upload2_logger.info("Upload completed")

        self.output.seek(0)
        logs = [json.loads(line) for line in self.output.getvalue().strip().split("\n")]

        # Verify each upload can be traced
        upload1_logs = [log for log in logs if log.get("correlation_id") == "upload-1"]
        upload2_logs = [log for log in logs if log.get("correlation_id") == "upload-2"]

        self.assertEqual(len(upload1_logs), 3)
        self.assertEqual(len(upload2_logs), 3)


if __name__ == "__main__":
    unittest.main()
