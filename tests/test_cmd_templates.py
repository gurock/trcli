import pytest
from unittest import mock
from unittest.mock import MagicMock, patch
from click.testing import CliRunner

from trcli.cli import Environment
from trcli.commands import cmd_templates


class TestCmdTemplates:
    """Test suite for the templates command."""

    def setup_method(self):
        """Set up test environment"""
        self.runner = CliRunner()
        self.environment = Environment(cmd="templates")
        self.environment.host = "https://test.testrail.com"
        self.environment.username = "test@example.com"
        self.environment.password = "password"
        self.environment.api_key = None

    def _setup_project_client_mock(self, mock_project_client):
        """Helper to setup ProjectBasedClient mock"""
        mock_client_instance = MagicMock()
        mock_project_client.return_value = mock_client_instance
        return mock_client_instance

    @mock.patch("trcli.commands.cmd_templates.ProjectBasedClient")
    def test_list_templates_success(self, mock_project_client):
        """Test successful listing of templates."""
        mock_client = self._setup_project_client_mock(mock_project_client)
        mock_client.api_request_handler.template_handler.get_templates.return_value = (
            [
                {"id": 1, "name": "Test Case (Text)", "i18n_custom_id": "templates_test_case_text", "is_default": True},
                {
                    "id": 2,
                    "name": "Test Case (Steps)",
                    "i18n_custom_id": "templates_test_case_steps",
                    "is_default": False,
                },
                {"id": 5, "name": "AI Evaluation", "i18n_custom_id": "templates_ai_evaluation", "is_default": False},
            ],
            "",
        )

        with patch.object(self.environment, "log") as mock_log, patch.object(
            self.environment, "set_parameters"
        ), patch.object(self.environment, "check_for_required_parameters"):
            result = self.runner.invoke(cmd_templates.list, ["--project-id", "1"], obj=self.environment)

            assert result.exit_code == 0
            assert mock_log.called
            mock_client.api_request_handler.template_handler.get_templates.assert_called_once_with(1)

    @mock.patch("trcli.commands.cmd_templates.ProjectBasedClient")
    def test_list_templates_json_output(self, mock_project_client):
        """Test listing templates with JSON output."""
        mock_client = self._setup_project_client_mock(mock_project_client)
        mock_client.api_request_handler.template_handler.get_templates.return_value = (
            [
                {"id": 1, "name": "Test Case (Text)", "i18n_custom_id": "templates_test_case_text", "is_default": True},
                {
                    "id": 2,
                    "name": "Test Case (Steps)",
                    "i18n_custom_id": "templates_test_case_steps",
                    "is_default": False,
                },
            ],
            "",
        )

        with patch.object(self.environment, "log") as mock_log, patch.object(
            self.environment, "set_parameters"
        ), patch.object(self.environment, "check_for_required_parameters"):
            result = self.runner.invoke(
                cmd_templates.list, ["--project-id", "1", "--json-output"], obj=self.environment
            )

            assert result.exit_code == 0
            assert '"id": 1' in result.output
            assert '"name": "Test Case (Text)"' in result.output

    @mock.patch("trcli.commands.cmd_templates.ProjectBasedClient")
    def test_list_templates_empty_result(self, mock_project_client):
        """Test listing templates when no results are found."""
        mock_client = self._setup_project_client_mock(mock_project_client)
        mock_client.api_request_handler.template_handler.get_templates.return_value = ([], "")

        with patch.object(self.environment, "log") as mock_log, patch.object(
            self.environment, "set_parameters"
        ), patch.object(self.environment, "check_for_required_parameters"):
            result = self.runner.invoke(cmd_templates.list, ["--project-id", "1"], obj=self.environment)

            assert result.exit_code == 0
            assert mock_log.called

    @mock.patch("trcli.commands.cmd_templates.ProjectBasedClient")
    def test_list_templates_api_error(self, mock_project_client):
        """Test handling of API errors when listing templates."""
        mock_client = self._setup_project_client_mock(mock_project_client)
        mock_client.api_request_handler.template_handler.get_templates.return_value = (
            [],
            "Project not found",
        )

        with patch.object(self.environment, "log") as mock_log, patch.object(
            self.environment, "set_parameters"
        ), patch.object(self.environment, "check_for_required_parameters"), patch.object(
            self.environment, "elog"
        ) as mock_elog:
            result = self.runner.invoke(cmd_templates.list, ["--project-id", "999"], obj=self.environment)

            assert result.exit_code == 1
            assert mock_elog.called

    def test_list_templates_invalid_id_zero(self):
        """Test validation rejects project ID of 0."""
        result = self.runner.invoke(cmd_templates.list, ["--project-id", "0"], obj=self.environment)

        assert result.exit_code != 0
        assert "0 is not in the range x>=1" in result.output

    def test_list_templates_invalid_id_negative(self):
        """Test validation rejects negative project ID."""
        result = self.runner.invoke(cmd_templates.list, ["--project-id", "-1"], obj=self.environment)

        assert result.exit_code != 0
        assert "-1 is not in the range x>=1" in result.output

    @mock.patch("trcli.commands.cmd_templates.ProjectBasedClient")
    def test_list_templates_displays_default_flag(self, mock_project_client):
        """Test that templates correctly show default flag."""
        mock_client = self._setup_project_client_mock(mock_project_client)
        mock_client.api_request_handler.template_handler.get_templates.return_value = (
            [
                {"id": 1, "name": "Test Case (Text)", "i18n_custom_id": "templates_test_case_text", "is_default": True},
                {"id": 5, "name": "AI Evaluation", "i18n_custom_id": "templates_ai_evaluation", "is_default": False},
            ],
            "",
        )

        with patch.object(self.environment, "log") as mock_log, patch.object(
            self.environment, "set_parameters"
        ), patch.object(self.environment, "check_for_required_parameters"):
            result = self.runner.invoke(cmd_templates.list, ["--project-id", "1"], obj=self.environment)

            assert result.exit_code == 0
            # Verify default flag is mentioned in logs
            log_calls = [str(call) for call in mock_log.call_args_list]
            default_yes = any("Default: Yes" in str(call) for call in log_calls)
            default_no = any("Default: No" in str(call) for call in log_calls)
            assert default_yes and default_no
