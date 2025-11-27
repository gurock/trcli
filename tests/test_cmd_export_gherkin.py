import pytest
from unittest import mock
from unittest.mock import MagicMock, patch
from click.testing import CliRunner
from pathlib import Path

from trcli.cli import Environment
from trcli.commands import cmd_export_gherkin


class TestCmdExportGherkin:
    """Test class for export_gherkin command functionality"""

    def setup_method(self):
        """Set up test environment and runner"""
        self.runner = CliRunner()
        self.sample_feature_content = """@smoke
Feature: User Login
  As a user
  I want to log in

  Scenario: Successful login
    Given I am on the login page
    When I enter valid credentials
    Then I should see the dashboard
"""

        # Set up environment with required parameters
        self.environment = Environment(cmd="export_gherkin")
        self.environment.host = "https://test.testrail.com"
        self.environment.username = "test@example.com"
        self.environment.password = "password"
        self.environment.project = "Test Project"
        self.environment.project_id = 1

    @pytest.mark.cmd_export_gherkin
    @patch("trcli.commands.cmd_export_gherkin.ApiRequestHandler")
    @patch("trcli.commands.cmd_export_gherkin.APIClient")
    def test_export_gherkin_success_to_file(self, mock_api_client_class, mock_api_handler_class):
        """Test successful export to file"""
        # Mock API client
        mock_api_client = MagicMock()
        mock_api_client_class.return_value = mock_api_client
        mock_api_client_class.build_uploader_metadata.return_value = {}

        # Mock API request handler
        mock_handler = MagicMock()
        mock_api_handler_class.return_value = mock_handler
        mock_handler.get_bdd.return_value = (self.sample_feature_content, "")

        with self.runner.isolated_filesystem():
            result = self.runner.invoke(
                cmd_export_gherkin.cli, ["--case-id", "456", "--output", "exported.feature"], obj=self.environment
            )

            assert result.exit_code == 0
            assert "successfully exported" in result.output.lower()
            assert "exported.feature" in result.output

            # Verify file was created with correct content
            with open("exported.feature", "r") as f:
                content = f.read()
                assert "Feature: User Login" in content
                assert "@smoke" in content

    @pytest.mark.cmd_export_gherkin
    @patch("trcli.commands.cmd_export_gherkin.ApiRequestHandler")
    @patch("trcli.commands.cmd_export_gherkin.APIClient")
    def test_export_gherkin_success_to_stdout(self, mock_api_client_class, mock_api_handler_class):
        """Test successful export to stdout"""
        # Mock API client
        mock_api_client = MagicMock()
        mock_api_client_class.return_value = mock_api_client
        mock_api_client_class.build_uploader_metadata.return_value = {}

        # Mock API request handler
        mock_handler = MagicMock()
        mock_api_handler_class.return_value = mock_handler
        mock_handler.get_bdd.return_value = (self.sample_feature_content, "")

        result = self.runner.invoke(cmd_export_gherkin.cli, ["--case-id", "456"], obj=self.environment)

        assert result.exit_code == 0
        # Content should be printed to stdout
        assert "Feature: User Login" in result.output
        assert "@smoke" in result.output

    @pytest.mark.cmd_export_gherkin
    @patch("trcli.commands.cmd_export_gherkin.ApiRequestHandler")
    @patch("trcli.commands.cmd_export_gherkin.APIClient")
    def test_export_gherkin_verbose_logging(self, mock_api_client_class, mock_api_handler_class):
        """Test export with verbose logging"""
        # Mock API client
        mock_api_client = MagicMock()
        mock_api_client_class.return_value = mock_api_client
        mock_api_client_class.build_uploader_metadata.return_value = {}

        # Mock API request handler
        mock_handler = MagicMock()
        mock_api_handler_class.return_value = mock_handler
        mock_handler.get_bdd.return_value = (self.sample_feature_content, "")

        result = self.runner.invoke(cmd_export_gherkin.cli, ["--case-id", "456", "--verbose"], obj=self.environment)

        assert result.exit_code == 0

    @pytest.mark.cmd_export_gherkin
    @patch("trcli.commands.cmd_export_gherkin.ApiRequestHandler")
    @patch("trcli.commands.cmd_export_gherkin.APIClient")
    def test_export_gherkin_api_error_case_not_found(self, mock_api_client_class, mock_api_handler_class):
        """Test API error when case not found"""
        # Mock API client
        mock_api_client = MagicMock()
        mock_api_client_class.return_value = mock_api_client
        mock_api_client_class.build_uploader_metadata.return_value = {}

        # Mock API request handler with error
        mock_handler = MagicMock()
        mock_api_handler_class.return_value = mock_handler
        mock_handler.get_bdd.return_value = ("", "Failed to retrieve BDD test case (HTTP 404)")

        result = self.runner.invoke(cmd_export_gherkin.cli, ["--case-id", "99999"], obj=self.environment)

        assert result.exit_code == 1
        assert "error" in result.output.lower()

    @pytest.mark.cmd_export_gherkin
    @patch("trcli.commands.cmd_export_gherkin.ApiRequestHandler")
    @patch("trcli.commands.cmd_export_gherkin.APIClient")
    def test_export_gherkin_empty_content(self, mock_api_client_class, mock_api_handler_class):
        """Test when no BDD content is returned"""
        # Mock API client
        mock_api_client = MagicMock()
        mock_api_client_class.return_value = mock_api_client
        mock_api_client_class.build_uploader_metadata.return_value = {}

        # Mock API request handler with empty content
        mock_handler = MagicMock()
        mock_api_handler_class.return_value = mock_handler
        mock_handler.get_bdd.return_value = ("", "")  # Empty content, no error

        result = self.runner.invoke(cmd_export_gherkin.cli, ["--case-id", "456"], obj=self.environment)

        assert result.exit_code == 1
        assert "no bdd content found" in result.output.lower()

    @pytest.mark.cmd_export_gherkin
    def test_export_gherkin_required_parameters(self):
        """Test that required parameters are validated"""
        # Missing --case-id
        result = self.runner.invoke(cmd_export_gherkin.cli, ["--project-id", "1"])
        assert result.exit_code == 2  # Click error for missing required option

        # Missing --project-id (handled by check_for_required_parameters)
        result = self.runner.invoke(cmd_export_gherkin.cli, ["--case-id", "456"])
        # Will fail due to missing required params

    @pytest.mark.cmd_export_gherkin
    def test_export_gherkin_invalid_case_id(self):
        """Test with invalid case ID (negative or zero)"""
        result = self.runner.invoke(cmd_export_gherkin.cli, ["--case-id", "-1"], obj=self.environment)

        # Click IntRange validation should catch this
        assert result.exit_code == 2

    @pytest.mark.cmd_export_gherkin
    @patch("trcli.commands.cmd_export_gherkin.ApiRequestHandler")
    @patch("trcli.commands.cmd_export_gherkin.APIClient")
    @patch("builtins.open", side_effect=PermissionError("Permission denied"))
    def test_export_gherkin_permission_error(self, mock_open, mock_api_client_class, mock_api_handler_class):
        """Test file write permission error"""
        # Mock API client
        mock_api_client = MagicMock()
        mock_api_client_class.return_value = mock_api_client
        mock_api_client_class.build_uploader_metadata.return_value = {}

        # Mock API request handler
        mock_handler = MagicMock()
        mock_api_handler_class.return_value = mock_handler
        mock_handler.get_bdd.return_value = (self.sample_feature_content, "")

        result = self.runner.invoke(
            cmd_export_gherkin.cli,
            ["--case-id", "456", "--output", "/root/no_permission.feature"],
            obj=self.environment,
        )

        assert result.exit_code == 1
        # Check for various error messages related to file writing
        assert (
            "permission denied" in result.output.lower()
            or "read-only file system" in result.output.lower()
            or "error writing file" in result.output.lower()
        )

    @pytest.mark.cmd_export_gherkin
    @patch("trcli.commands.cmd_export_gherkin.ApiRequestHandler")
    @patch("trcli.commands.cmd_export_gherkin.APIClient")
    def test_export_gherkin_create_nested_directory(self, mock_api_client_class, mock_api_handler_class):
        """Test that parent directories are created if they don't exist"""
        # Mock API client
        mock_api_client = MagicMock()
        mock_api_client_class.return_value = mock_api_client
        mock_api_client_class.build_uploader_metadata.return_value = {}

        # Mock API request handler
        mock_handler = MagicMock()
        mock_api_handler_class.return_value = mock_handler
        mock_handler.get_bdd.return_value = (self.sample_feature_content, "")

        with self.runner.isolated_filesystem():
            output_path = "nested/dir/exported.feature"
            result = self.runner.invoke(
                cmd_export_gherkin.cli, ["--case-id", "456", "--output", output_path], obj=self.environment
            )

            assert result.exit_code == 0
            # Verify nested directory was created
            assert Path(output_path).exists()
            assert Path(output_path).is_file()

    @pytest.mark.cmd_export_gherkin
    @patch("trcli.commands.cmd_export_gherkin.ApiRequestHandler")
    @patch("trcli.commands.cmd_export_gherkin.APIClient")
    def test_export_gherkin_unicode_content(self, mock_api_client_class, mock_api_handler_class):
        """Test export with unicode characters"""
        unicode_content = """@test
Feature: Tëst with ūnīcödé 测试
  Scenario: Test scenario
    Given test step with émojis 🎉
"""
        # Mock API client
        mock_api_client = MagicMock()
        mock_api_client_class.return_value = mock_api_client
        mock_api_client_class.build_uploader_metadata.return_value = {}

        # Mock API request handler
        mock_handler = MagicMock()
        mock_api_handler_class.return_value = mock_handler
        mock_handler.get_bdd.return_value = (unicode_content, "")

        with self.runner.isolated_filesystem():
            result = self.runner.invoke(
                cmd_export_gherkin.cli, ["--case-id", "456", "--output", "unicode.feature"], obj=self.environment
            )

            assert result.exit_code == 0

            # Verify unicode content is preserved
            with open("unicode.feature", "r", encoding="utf-8") as f:
                content = f.read()
                assert "ūnīcödé" in content
                assert "测试" in content
                assert "🎉" in content
