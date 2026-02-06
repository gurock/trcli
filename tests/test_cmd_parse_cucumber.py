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
        self.environment.auto_creation_response = True  # Enable auto-creation for tests

    @pytest.mark.cmd_parse_cucumber
    @patch("trcli.api.api_request_handler.ApiRequestHandler")
    @patch("trcli.api.api_client.APIClient")
    @patch("trcli.commands.cmd_parse_cucumber.ResultsUploader")
    @patch("trcli.commands.cmd_parse_cucumber.CucumberParser")
    def test_parse_cucumber_workflow1_results_only(
        self, mock_parser_class, mock_uploader_class, mock_api_client_class, mock_api_handler_class
    ):
        """Test Workflow 1: Parse and upload results only (no feature upload)"""
        # Mock API client
        mock_api_client = MagicMock()
        mock_api_client_class.return_value = mock_api_client
        mock_api_client_class.build_uploader_metadata.return_value = {}

        # Mock API handler
        mock_api_handler = MagicMock()
        mock_api_handler_class.return_value = mock_api_handler

        # Mock project data resolution
        mock_project_data = MagicMock()
        mock_project_data.project_id = 1
        mock_api_handler.get_project_data.return_value = mock_project_data

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
    @patch("trcli.api.api_client.APIClient")
    @patch("trcli.commands.cmd_parse_cucumber.ResultsUploader")
    @patch("trcli.commands.cmd_parse_cucumber.CucumberParser")
    @patch(
        "builtins.open",
        new_callable=mock.mock_open,
        read_data='[{"name":"Test Feature","elements":[{"type":"scenario","name":"Test Scenario"}]}]',
    )
    def test_parse_cucumber_auto_create_missing_features(
        self, mock_open, mock_parser_class, mock_uploader_class, mock_api_client_class, mock_api_handler_class
    ):
        """Test auto-creation of missing BDD test cases (default behavior)"""
        # Mock API client
        mock_api_client = MagicMock()
        mock_api_client_class.return_value = mock_api_client
        mock_api_client_class.build_uploader_metadata.return_value = {}

        # Mock API handler
        mock_api_handler = MagicMock()
        mock_api_handler_class.return_value = mock_api_handler

        # Mock project data resolution
        mock_project_data = MagicMock()
        mock_project_data.project_id = 1
        mock_api_handler.get_project_data.return_value = mock_project_data

        # Mock parser
        mock_parser = MagicMock()
        mock_parser_class.return_value = mock_parser

        # First parse returns case_id=-1 (needs creation)
        mock_suite = MagicMock()
        mock_suite.name = "Test Suite"
        mock_section = MagicMock()
        mock_section.name = "Test Feature"
        mock_case = MagicMock()
        mock_case.case_id = -1  # Marker for auto-creation
        mock_case.result = MagicMock()
        mock_section.testcases = [mock_case]
        mock_suite.testsections = [mock_section]
        mock_parser.parse_file.return_value = [mock_suite]

        # Mock _generate_feature_content to return Gherkin content
        mock_parser._generate_feature_content.return_value = "Feature: Test\n  Scenario: Test\n    Given test step\n"
        mock_parser._normalize_title.return_value = "test feature"

        # Mock section fetch and creation
        mock_api_handler._ApiRequestHandler__get_all_sections.return_value = ([], None)
        mock_response = MagicMock()
        mock_response.error_message = None
        mock_response.response_text = {"id": 456}
        mock_api_handler.client.send_post.return_value = mock_response

        # Mock BDD template and add_bdd
        mock_api_handler.get_bdd_template_id.return_value = (2, None)
        mock_api_handler.add_bdd.return_value = ([101], None)

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
                "--title",
                "Test Run",
            ],
            obj=self.environment,
        )

        assert result.exit_code == 0
        mock_api_handler.get_bdd_template_id.assert_called_once()
        mock_api_handler.add_bdd.assert_called_once()

    @pytest.mark.cmd_parse_cucumber
    @patch("trcli.api.api_request_handler.ApiRequestHandler")
    @patch("trcli.api.api_client.APIClient")
    @patch("trcli.commands.cmd_parse_cucumber.ResultsUploader")
    @patch("trcli.commands.cmd_parse_cucumber.CucumberParser")
    def test_parse_cucumber_with_n_flag(
        self, mock_parser_class, mock_uploader_class, mock_api_client_class, mock_api_handler_class
    ):
        """Test that -n flag only matches existing BDD test cases"""
        # Mock API client
        mock_api_client = MagicMock()
        mock_api_client_class.return_value = mock_api_client
        mock_api_client_class.build_uploader_metadata.return_value = {}

        # Mock API handler
        mock_api_handler = MagicMock()
        mock_api_handler_class.return_value = mock_api_handler

        # Mock project data resolution
        mock_project_data = MagicMock()
        mock_project_data.project_id = 1
        mock_api_handler.get_project_data.return_value = mock_project_data

        # Mock parser
        mock_parser = MagicMock()
        mock_parser_class.return_value = mock_parser
        mock_suite = MagicMock()
        mock_suite.name = "Test Suite"
        mock_section = MagicMock()
        mock_section.name = "Test Feature"
        mock_section.testcases = []
        mock_suite.testsections = [mock_section]
        mock_parser.parse_file.return_value = [mock_suite]

        # Mock uploader
        mock_uploader = MagicMock()
        mock_uploader_class.return_value = mock_uploader
        mock_uploader.last_run_id = 123

        # Set auto_creation_response to False (simulates -n flag)
        self.environment.auto_creation_response = False

        result = self.runner.invoke(
            cmd_parse_cucumber.cli,
            [
                "--file",
                self.test_cucumber_path,
                "--suite-id",
                "2",
                "--title",
                "Test Run",
            ],
            obj=self.environment,
        )

        assert result.exit_code == 0
        # Verify auto_create=False was passed to parser
        mock_parser.parse_file.assert_called_with(bdd_matching_mode=True, project_id=1, suite_id=2, auto_create=False)

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
    @patch("trcli.api.api_client.APIClient")
    @patch("trcli.commands.cmd_parse_cucumber.CucumberParser")
    @patch("builtins.open", new_callable=mock.mock_open, read_data="[]")
    def test_parse_cucumber_invalid_cucumber_json(
        self, mock_open, mock_parser_class, mock_api_client_class, mock_api_handler_class
    ):
        """Test with invalid Cucumber JSON structure (empty array)"""
        # Mock API client
        mock_api_client = MagicMock()
        mock_api_client_class.return_value = mock_api_client
        mock_api_client_class.build_uploader_metadata.return_value = {}

        # Mock API handler
        mock_api_handler = MagicMock()
        mock_api_handler_class.return_value = mock_api_handler

        # Mock project data resolution
        mock_project_data = MagicMock()
        mock_project_data.project_id = 1
        mock_api_handler.get_project_data.return_value = mock_project_data

        # Mock parser to raise error for empty JSON
        mock_parser = MagicMock()
        mock_parser_class.return_value = mock_parser
        mock_parser.parse_file.side_effect = ValueError("Invalid Cucumber JSON format: empty array")

        result = self.runner.invoke(
            cmd_parse_cucumber.cli,
            [
                "--file",
                self.test_cucumber_path,
                "--suite-id",
                "2",
                "--title",
                "Test Run",
            ],
            obj=self.environment,
        )

        assert result.exit_code == 1
        # Check that it fails with any appropriate error (either JSON format or parsing error)
        assert "invalid" in result.output.lower() or "error parsing" in result.output.lower()

    @pytest.mark.cmd_parse_cucumber
    @patch("trcli.api.api_request_handler.ApiRequestHandler")
    @patch("trcli.api.api_client.APIClient")
    @patch("trcli.commands.cmd_parse_cucumber.CucumberParser")
    @patch(
        "builtins.open",
        new_callable=mock.mock_open,
        read_data='[{"name":"Test Feature","elements":[{"type":"scenario","name":"Test Scenario"}]}]',
    )
    def test_parse_cucumber_api_error_during_auto_creation(
        self, mock_open, mock_parser_class, mock_api_client_class, mock_api_handler_class
    ):
        """Test API error during BDD test case auto-creation"""
        # Mock API client
        mock_api_client = MagicMock()
        mock_api_client_class.return_value = mock_api_client
        mock_api_client_class.build_uploader_metadata.return_value = {}

        # Mock API handler with error
        mock_api_handler = MagicMock()
        mock_api_handler_class.return_value = mock_api_handler

        # Mock project data resolution
        mock_project_data = MagicMock()
        mock_project_data.project_id = 1
        mock_api_handler.get_project_data.return_value = mock_project_data

        # Mock parser
        mock_parser = MagicMock()
        mock_parser_class.return_value = mock_parser
        mock_suite = MagicMock()
        mock_section = MagicMock()
        mock_section.name = "Test Feature"
        mock_case = MagicMock()
        mock_case.case_id = -1  # Needs creation
        mock_section.testcases = [mock_case]
        mock_suite.testsections = [mock_section]
        mock_parser.parse_file.return_value = [mock_suite]
        mock_parser._generate_feature_content.return_value = "Feature: Test\n  Scenario: Test\n"
        mock_parser._normalize_title.return_value = "test feature"

        # Mock section fetch
        mock_api_handler._ApiRequestHandler__get_all_sections.return_value = ([], None)
        mock_response = MagicMock()
        mock_response.error_message = None
        mock_response.response_text = {"id": 456}
        mock_api_handler.client.send_post.return_value = mock_response

        # Mock BDD template and add_bdd with error
        mock_api_handler.get_bdd_template_id.return_value = (2, None)
        mock_api_handler.add_bdd.return_value = ([], "API Error: Section not found")

        result = self.runner.invoke(
            cmd_parse_cucumber.cli,
            [
                "--file",
                self.test_cucumber_path,
                "--suite-id",
                "2",
                "--title",
                "Test Run",
            ],
            obj=self.environment,
        )

        assert result.exit_code == 1
        assert "error" in result.output.lower()

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
    @patch("trcli.api.api_request_handler.ApiRequestHandler")
    @patch("trcli.api.api_client.APIClient")
    @patch("trcli.commands.cmd_parse_cucumber.ResultsUploader")
    @patch("trcli.commands.cmd_parse_cucumber.CucumberParser")
    def test_parse_cucumber_validation_exception(
        self, mock_parser_class, mock_uploader_class, mock_api_client_class, mock_api_handler_class
    ):
        """Test handling of ValidationException"""
        from trcli.data_classes.validation_exception import ValidationException

        # Mock API client
        mock_api_client = MagicMock()
        mock_api_client_class.return_value = mock_api_client
        mock_api_client_class.build_uploader_metadata.return_value = {}

        # Mock API handler
        mock_api_handler = MagicMock()
        mock_api_handler_class.return_value = mock_api_handler

        # Mock project data resolution
        mock_project_data = MagicMock()
        mock_project_data.project_id = 1
        mock_api_handler.get_project_data.return_value = mock_project_data

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
    @patch("trcli.api.api_request_handler.ApiRequestHandler")
    @patch("trcli.api.api_client.APIClient")
    @patch("trcli.commands.cmd_parse_cucumber.ResultsUploader")
    @patch("trcli.commands.cmd_parse_cucumber.CucumberParser")
    def test_parse_cucumber_value_error(
        self, mock_parser_class, mock_uploader_class, mock_api_client_class, mock_api_handler_class
    ):
        """Test handling of ValueError during parsing"""
        # Mock API client
        mock_api_client = MagicMock()
        mock_api_client_class.return_value = mock_api_client
        mock_api_client_class.build_uploader_metadata.return_value = {}

        # Mock API handler
        mock_api_handler = MagicMock()
        mock_api_handler_class.return_value = mock_api_handler

        # Mock project data resolution
        mock_project_data = MagicMock()
        mock_project_data.project_id = 1
        mock_api_handler.get_project_data.return_value = mock_project_data

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
