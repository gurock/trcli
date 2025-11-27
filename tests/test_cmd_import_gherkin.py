import pytest
import json
from unittest import mock
from unittest.mock import MagicMock, patch
from click.testing import CliRunner
from pathlib import Path

from trcli.cli import Environment
from trcli.commands import cmd_import_gherkin


class TestCmdImportGherkin:
    """Test class for import_gherkin command functionality"""

    def setup_method(self):
        """Set up test environment and runner"""
        self.runner = CliRunner()
        self.test_feature_path = str(Path(__file__).parent / "test_data" / "FEATURE" / "sample_bdd.feature")

        # Set up environment with required parameters
        self.environment = Environment(cmd="import_gherkin")
        self.environment.host = "https://test.testrail.com"
        self.environment.username = "test@example.com"
        self.environment.password = "password"
        self.environment.project = "Test Project"
        self.environment.project_id = 1

    @pytest.mark.cmd_import_gherkin
    @patch("trcli.commands.cmd_import_gherkin.ApiRequestHandler")
    @patch("trcli.commands.cmd_import_gherkin.APIClient")
    def test_import_gherkin_success(self, mock_api_client_class, mock_api_handler_class):
        """Test successful feature file upload"""
        # Mock API client
        mock_api_client = MagicMock()
        mock_api_client_class.return_value = mock_api_client
        mock_api_client_class.build_uploader_metadata.return_value = {}

        # Mock API request handler
        mock_handler = MagicMock()
        mock_api_handler_class.return_value = mock_handler
        mock_handler.add_bdd.return_value = ([456], "")  # Success: case ID 456, no error

        with self.runner.isolated_filesystem():
            # Create test feature file
            with open("test.feature", "w") as f:
                f.write("Feature: Test\n  Scenario: Test scenario\n    Given test step\n")

            result = self.runner.invoke(
                cmd_import_gherkin.cli, ["--file", "test.feature", "--section-id", "123"], obj=self.environment
            )

            assert result.exit_code == 0
            assert "successfully uploaded" in result.output.lower()
            assert "456" in result.output

    @pytest.mark.cmd_import_gherkin
    @patch("trcli.commands.cmd_import_gherkin.ApiRequestHandler")
    @patch("trcli.commands.cmd_import_gherkin.APIClient")
    def test_import_gherkin_json_output(self, mock_api_client_class, mock_api_handler_class):
        """Test feature file upload with JSON output"""
        # Mock API client
        mock_api_client = MagicMock()
        mock_api_client_class.return_value = mock_api_client
        mock_api_client_class.build_uploader_metadata.return_value = {}

        # Mock API request handler
        mock_handler = MagicMock()
        mock_api_handler_class.return_value = mock_handler
        mock_handler.add_bdd.return_value = ([101, 102], "")  # Success: 2 case IDs

        with self.runner.isolated_filesystem():
            # Create test feature file
            with open("test.feature", "w") as f:
                f.write("Feature: Test\n  Scenario: Test 1\n  Scenario: Test 2\n")

            result = self.runner.invoke(
                cmd_import_gherkin.cli,
                ["--file", "test.feature", "--section-id", "123", "--json-output"],
                obj=self.environment,
            )

            assert result.exit_code == 0
            # Output contains logging messages + JSON, extract JSON (starts with '{')
            json_start = result.output.find("{")
            assert json_start >= 0, "No JSON found in output"
            json_str = result.output[json_start:]
            output_data = json.loads(json_str)
            assert "case_ids" in output_data
            assert output_data["case_ids"] == [101, 102]
            assert output_data["count"] == 2

    @pytest.mark.cmd_import_gherkin
    @patch("trcli.commands.cmd_import_gherkin.ApiRequestHandler")
    @patch("trcli.commands.cmd_import_gherkin.APIClient")
    def test_import_gherkin_verbose_logging(self, mock_api_client_class, mock_api_handler_class):
        """Test feature file upload with verbose logging"""
        # Mock API client
        mock_api_client = MagicMock()
        mock_api_client_class.return_value = mock_api_client
        mock_api_client_class.build_uploader_metadata.return_value = {}

        # Mock API request handler
        mock_handler = MagicMock()
        mock_api_handler_class.return_value = mock_handler
        mock_handler.add_bdd.return_value = ([456], "")

        with self.runner.isolated_filesystem():
            with open("test.feature", "w") as f:
                f.write("Feature: Test\n  Scenario: Test\n")

            result = self.runner.invoke(
                cmd_import_gherkin.cli,
                ["--file", "test.feature", "--section-id", "123", "--verbose"],
                obj=self.environment,
            )

            assert result.exit_code == 0
            # Verbose output should show API endpoint
            # (verbose logs might not appear in captured output but command should succeed)

    @pytest.mark.cmd_import_gherkin
    def test_import_gherkin_missing_file(self):
        """Test with non-existent file"""
        result = self.runner.invoke(
            cmd_import_gherkin.cli, ["--file", "/nonexistent/file.feature", "--section-id", "123"], obj=self.environment
        )

        # Click returns exit code 2 for invalid parameter (file doesn't exist)
        assert result.exit_code in [1, 2]

    @pytest.mark.cmd_import_gherkin
    @patch("trcli.commands.cmd_import_gherkin.ApiRequestHandler")
    @patch("trcli.commands.cmd_import_gherkin.APIClient")
    def test_import_gherkin_empty_file(self, mock_api_client_class, mock_api_handler_class):
        """Test with empty feature file"""
        with self.runner.isolated_filesystem():
            # Create empty file
            with open("empty.feature", "w") as f:
                f.write("")

            result = self.runner.invoke(
                cmd_import_gherkin.cli, ["--file", "empty.feature", "--section-id", "123"], obj=self.environment
            )

            assert result.exit_code == 1
            assert "empty" in result.output.lower()

    @pytest.mark.cmd_import_gherkin
    @patch("trcli.commands.cmd_import_gherkin.ApiRequestHandler")
    @patch("trcli.commands.cmd_import_gherkin.APIClient")
    def test_import_gherkin_api_error(self, mock_api_client_class, mock_api_handler_class):
        """Test API error handling"""
        # Mock API client
        mock_api_client = MagicMock()
        mock_api_client_class.return_value = mock_api_client
        mock_api_client_class.build_uploader_metadata.return_value = {}

        # Mock API request handler with error
        mock_handler = MagicMock()
        mock_api_handler_class.return_value = mock_handler
        mock_handler.add_bdd.return_value = ([], "API Error: Section not found")

        with self.runner.isolated_filesystem():
            with open("test.feature", "w") as f:
                f.write("Feature: Test\n  Scenario: Test\n")

            result = self.runner.invoke(
                cmd_import_gherkin.cli, ["--file", "test.feature", "--section-id", "999"], obj=self.environment
            )

            assert result.exit_code == 1
            assert "error" in result.output.lower()
            assert "section not found" in result.output.lower()

    @pytest.mark.cmd_import_gherkin
    @patch("trcli.commands.cmd_import_gherkin.ApiRequestHandler")
    @patch("trcli.commands.cmd_import_gherkin.APIClient")
    def test_import_gherkin_no_cases_created(self, mock_api_client_class, mock_api_handler_class):
        """Test when no case IDs are returned from API"""
        # Mock API client
        mock_api_client = MagicMock()
        mock_api_client_class.return_value = mock_api_client
        mock_api_client_class.build_uploader_metadata.return_value = {}

        # Mock API request handler with empty case IDs
        mock_handler = MagicMock()
        mock_api_handler_class.return_value = mock_handler
        mock_handler.add_bdd.return_value = ([], "")  # No error, but no cases created

        with self.runner.isolated_filesystem():
            with open("test.feature", "w") as f:
                f.write("Feature: Test\n  Scenario: Test\n")

            result = self.runner.invoke(
                cmd_import_gherkin.cli, ["--file", "test.feature", "--section-id", "123"], obj=self.environment
            )

            assert result.exit_code == 0  # Not an error, just a warning
            assert "warning" in result.output.lower()
            assert "no case" in result.output.lower()

    @pytest.mark.cmd_import_gherkin
    def test_import_gherkin_required_parameters(self):
        """Test that required parameters are validated"""
        # Missing --file
        result = self.runner.invoke(cmd_import_gherkin.cli, ["--section-id", "123", "--project-id", "1"])
        assert result.exit_code == 2  # Click error for missing required option

        # Missing --section-id
        with self.runner.isolated_filesystem():
            with open("test.feature", "w") as f:
                f.write("Feature: Test\n")

            result = self.runner.invoke(cmd_import_gherkin.cli, ["--file", "test.feature", "--project-id", "1"])
            assert result.exit_code == 2

    @pytest.mark.cmd_import_gherkin
    @patch("trcli.commands.cmd_import_gherkin.ApiRequestHandler")
    @patch("trcli.commands.cmd_import_gherkin.APIClient")
    def test_import_gherkin_invalid_section_id(self, mock_api_client_class, mock_api_handler_class):
        """Test with invalid section ID (negative number)"""
        result = self.runner.invoke(
            cmd_import_gherkin.cli,
            ["--file", self.test_feature_path, "--section-id", "-1"],  # Invalid: negative
            obj=self.environment,
        )

        # Click IntRange validation should catch this
        assert result.exit_code == 2

    @pytest.mark.cmd_import_gherkin
    @patch("trcli.commands.cmd_import_gherkin.ApiRequestHandler")
    @patch("trcli.commands.cmd_import_gherkin.APIClient")
    def test_import_gherkin_unicode_content(self, mock_api_client_class, mock_api_handler_class):
        """Test feature file with unicode characters"""
        # Mock API client
        mock_api_client = MagicMock()
        mock_api_client_class.return_value = mock_api_client
        mock_api_client_class.build_uploader_metadata.return_value = {}

        # Mock API request handler
        mock_handler = MagicMock()
        mock_api_handler_class.return_value = mock_handler
        mock_handler.add_bdd.return_value = ([456], "")

        with self.runner.isolated_filesystem():
            # Create feature file with unicode
            with open("unicode.feature", "w", encoding="utf-8") as f:
                f.write("Feature: Tëst with ūnīcödé\n  Scenario: Test 测试\n    Given test\n")

            result = self.runner.invoke(
                cmd_import_gherkin.cli, ["--file", "unicode.feature", "--section-id", "123"], obj=self.environment
            )

            assert result.exit_code == 0
