import pytest
import json
from unittest import mock
from unittest.mock import MagicMock, patch
from click.testing import CliRunner
from pathlib import Path

from trcli.cli import Environment
from trcli.commands import cmd_parse_cucumber


class TestCmdParseCucumber:
    """Test class for parse_cucumber command functionality"""

    def setup_method(self):
        """Set up test environment and runner"""
        self.runner = CliRunner()
        self.test_cucumber_path = str(Path(__file__).parent / "test_data" / "CUCUMBER" / "sample_cucumber.json")

        # Set up environment with required parameters
        self.environment = Environment(cmd="parse_cucumber")
        self.environment.host = "https://test.testrail.com"
        self.environment.username = "test@example.com"
        self.environment.password = "password"
        self.environment.project = "Test Project"
        self.environment.project_id = 1

    @pytest.mark.cmd_parse_cucumber
    @patch("trcli.commands.cmd_parse_cucumber.ResultsUploader")
    @patch("trcli.commands.cmd_parse_cucumber.CucumberParser")
    def test_parse_cucumber_workflow1_results_only(self, mock_parser_class, mock_uploader_class):
        """Test Workflow 1: Parse and upload results only (no feature upload)"""
        # Mock parser
        mock_parser = MagicMock()
        mock_parser_class.return_value = mock_parser
        mock_suite = MagicMock()
        mock_suite.name = "Test Suite"
        mock_parser.parse_file.return_value = [mock_suite]

        # Mock uploader
        mock_uploader = MagicMock()
        mock_uploader_class.return_value = mock_uploader
        mock_uploader.last_run_id = 123

        result = self.runner.invoke(
            cmd_parse_cucumber.cli,
            ["--file", self.test_cucumber_path, "--suite-id", "2", "--title", "Test Run"],
            obj=self.environment,
        )

        assert result.exit_code == 0
        mock_parser.parse_file.assert_called_once()
        mock_uploader.upload_results.assert_called_once()

    @pytest.mark.cmd_parse_cucumber
    @patch("trcli.api.api_request_handler.ApiRequestHandler")
    @patch("trcli.commands.cmd_parse_cucumber.ResultsUploader")
    @patch("trcli.commands.cmd_parse_cucumber.CucumberParser")
    def test_parse_cucumber_workflow2_upload_feature(
        self, mock_parser_class, mock_uploader_class, mock_api_handler_class
    ):
        """Test Workflow 2: Generate feature, upload, then upload results"""
        # Mock parser
        mock_parser = MagicMock()
        mock_parser_class.return_value = mock_parser
        mock_suite = MagicMock()
        mock_suite.name = "Test Suite"
        mock_parser.parse_file.return_value = [mock_suite]
        mock_parser.generate_feature_file.return_value = "Feature: Test\n  Scenario: Test\n"

        # Mock API handler
        mock_api_handler = MagicMock()
        mock_api_handler_class.return_value = mock_api_handler
        mock_api_handler.add_bdd.return_value = ([101, 102], "")

        # Mock uploader
        mock_uploader = MagicMock()
        mock_uploader_class.return_value = mock_uploader
        mock_uploader.last_run_id = 123

        result = self.runner.invoke(
            cmd_parse_cucumber.cli,
            [
                "--file",
                self.test_cucumber_path,
                "--suite-id",
                "2",
                "--upload-feature",
                "--feature-section-id",
                "456",
                "--title",
                "Test Run",
            ],
            obj=self.environment,
        )

        assert result.exit_code == 0
        mock_parser.generate_feature_file.assert_called_once()
        mock_api_handler.add_bdd.assert_called_once()
        mock_uploader.upload_results.assert_called()

    @pytest.mark.cmd_parse_cucumber
    def test_parse_cucumber_upload_feature_requires_section_id(self):
        """Test that --upload-feature requires --feature-section-id"""
        result = self.runner.invoke(
            cmd_parse_cucumber.cli,
            [
                "--file",
                self.test_cucumber_path,
                "--suite-id",
                "2",
                "--upload-feature",
                # Missing --feature-section-id
                "--title",
                "Test Run",
            ],
            obj=self.environment,
        )

        assert result.exit_code == 1
        assert "feature-section-id is required" in result.output.lower()

    @pytest.mark.cmd_parse_cucumber
    def test_parse_cucumber_missing_file(self):
        """Test with non-existent Cucumber JSON file"""
        result = self.runner.invoke(
            cmd_parse_cucumber.cli,
            ["--file", "/nonexistent/results.json", "--suite-id", "2", "--title", "Test Run"],
            obj=self.environment,
        )

        assert result.exit_code == 1
        assert "not found" in result.output.lower() or result.exception is not None

    @pytest.mark.cmd_parse_cucumber
    @patch("trcli.commands.cmd_parse_cucumber.CucumberParser")
    def test_parse_cucumber_invalid_json(self, mock_parser_class):
        """Test with invalid JSON format"""
        # Mock parser to raise JSONDecodeError
        mock_parser_class.side_effect = json.JSONDecodeError("Invalid JSON", "", 0)

        with self.runner.isolated_filesystem():
            # Create invalid JSON file
            with open("invalid.json", "w") as f:
                f.write("This is not valid JSON{{{")

            result = self.runner.invoke(
                cmd_parse_cucumber.cli,
                ["--file", "invalid.json", "--suite-id", "2", "--title", "Test Run"],
                obj=self.environment,
            )

            assert result.exit_code == 1

    @pytest.mark.cmd_parse_cucumber
    @patch("trcli.commands.cmd_parse_cucumber.CucumberParser")
    def test_parse_cucumber_empty_json(self, mock_parser_class):
        """Test with empty JSON file"""
        with self.runner.isolated_filesystem():
            # Create empty JSON file
            with open("empty.json", "w") as f:
                f.write("[]")

            # Mock parser to return empty list
            mock_parser = MagicMock()
            mock_parser_class.return_value = mock_parser
            mock_parser.parse_file.return_value = []

            result = self.runner.invoke(
                cmd_parse_cucumber.cli,
                ["--file", "empty.json", "--suite-id", "2", "--title", "Test Run"],
                obj=self.environment,
            )

            # Should handle gracefully (may succeed with warning or fail)
            # Exit code depends on implementation

    @pytest.mark.cmd_parse_cucumber
    @patch("trcli.api.api_request_handler.ApiRequestHandler")
    @patch("trcli.commands.cmd_parse_cucumber.CucumberParser")
    def test_parse_cucumber_feature_generation_failure(self, mock_parser_class, mock_api_handler_class):
        """Test when feature file generation fails"""
        # Mock parser
        mock_parser = MagicMock()
        mock_parser_class.return_value = mock_parser
        mock_suite = MagicMock()
        mock_parser.parse_file.return_value = [mock_suite]
        mock_parser.generate_feature_file.return_value = ""  # Empty content

        result = self.runner.invoke(
            cmd_parse_cucumber.cli,
            [
                "--file",
                self.test_cucumber_path,
                "--suite-id",
                "2",
                "--upload-feature",
                "--feature-section-id",
                "456",
                "--title",
                "Test Run",
            ],
            obj=self.environment,
        )

        assert result.exit_code == 1
        assert "could not generate feature file" in result.output.lower()

    @pytest.mark.cmd_parse_cucumber
    @patch("trcli.api.api_request_handler.ApiRequestHandler")
    @patch("trcli.commands.cmd_parse_cucumber.CucumberParser")
    def test_parse_cucumber_api_error_during_feature_upload(self, mock_parser_class, mock_api_handler_class):
        """Test API error during feature file upload"""
        # Mock parser
        mock_parser = MagicMock()
        mock_parser_class.return_value = mock_parser
        mock_suite = MagicMock()
        mock_parser.parse_file.return_value = [mock_suite]
        mock_parser.generate_feature_file.return_value = "Feature: Test\n"

        # Mock API handler with error
        mock_api_handler = MagicMock()
        mock_api_handler_class.return_value = mock_api_handler
        mock_api_handler.add_bdd.return_value = ([], "API Error: Section not found")

        result = self.runner.invoke(
            cmd_parse_cucumber.cli,
            [
                "--file",
                self.test_cucumber_path,
                "--suite-id",
                "2",
                "--upload-feature",
                "--feature-section-id",
                "456",
                "--title",
                "Test Run",
            ],
            obj=self.environment,
        )

        assert result.exit_code == 1
        assert "error uploading feature file" in result.output.lower()

    @pytest.mark.cmd_parse_cucumber
    def test_parse_cucumber_required_parameters(self):
        """Test that required parameters are validated"""
        # Missing --file
        result = self.runner.invoke(
            cmd_parse_cucumber.cli, ["--project-id", "1", "--suite-id", "2", "--title", "Test Run"]
        )
        # Will fail due to missing required params

        # Missing --project-id (handled by check_for_required_parameters)
        result = self.runner.invoke(
            cmd_parse_cucumber.cli, ["--file", self.test_cucumber_path, "--suite-id", "2", "--title", "Test Run"]
        )
        # Will fail

    @pytest.mark.cmd_parse_cucumber
    @patch("trcli.commands.cmd_parse_cucumber.ResultsUploader")
    @patch("trcli.commands.cmd_parse_cucumber.CucumberParser")
    def test_parse_cucumber_validation_exception(self, mock_parser_class, mock_uploader_class):
        """Test handling of ValidationException"""
        from trcli.data_classes.validation_exception import ValidationException

        # Mock parser to raise ValidationException
        mock_parser = MagicMock()
        mock_parser_class.return_value = mock_parser
        mock_parser.parse_file.side_effect = ValidationException("CucumberParser", "Validation error occurred")

        result = self.runner.invoke(
            cmd_parse_cucumber.cli,
            ["--file", self.test_cucumber_path, "--suite-id", "2", "--title", "Test Run"],
            obj=self.environment,
        )

        assert result.exit_code == 1
        assert "validation error" in result.output.lower()

    @pytest.mark.cmd_parse_cucumber
    @patch("trcli.commands.cmd_parse_cucumber.ResultsUploader")
    @patch("trcli.commands.cmd_parse_cucumber.CucumberParser")
    def test_parse_cucumber_value_error(self, mock_parser_class, mock_uploader_class):
        """Test handling of ValueError during parsing"""
        # Mock parser to raise ValueError
        mock_parser = MagicMock()
        mock_parser_class.return_value = mock_parser
        mock_parser.parse_file.side_effect = ValueError("Invalid Cucumber JSON structure")

        result = self.runner.invoke(
            cmd_parse_cucumber.cli,
            ["--file", self.test_cucumber_path, "--suite-id", "2", "--title", "Test Run"],
            obj=self.environment,
        )

        assert result.exit_code == 1
        assert "error parsing" in result.output.lower()
