import pytest
from unittest import mock
from unittest.mock import MagicMock, patch
from click.testing import CliRunner

from trcli.cli import Environment
from trcli.commands import cmd_priorities


class TestCmdPriorities:
    """Test class for priorities command functionality"""

    def setup_method(self):
        """Set up test environment"""
        self.runner = CliRunner()
        self.environment = Environment(cmd="priorities")
        self.environment.host = "https://test.testrail.com"
        self.environment.username = "test@example.com"
        self.environment.password = "password"
        self.environment.api_key = None

    def _setup_project_client_mock(self, mock_project_client):
        """Helper to setup ProjectBasedClient mock"""
        mock_client_instance = MagicMock()
        mock_project_client.return_value = mock_client_instance
        return mock_client_instance

    @mock.patch("trcli.commands.cmd_priorities.ProjectBasedClient")
    def test_list_priorities_success(self, mock_project_client):
        """Test successful priorities listing"""
        mock_client = self._setup_project_client_mock(mock_project_client)
        mock_client.api_request_handler.priority_handler.get_priorities.return_value = (
            [
                {
                    "id": 1,
                    "is_default": False,
                    "name": "1 - Don't Test",
                    "priority": 1,
                    "short_name": "1 - Don't",
                },
                {
                    "id": 2,
                    "is_default": False,
                    "name": "2 - Low",
                    "priority": 2,
                    "short_name": "2 - Low",
                },
                {
                    "id": 3,
                    "is_default": False,
                    "name": "3 - Medium",
                    "priority": 3,
                    "short_name": "3 - Med",
                },
                {
                    "id": 4,
                    "is_default": True,
                    "name": "4 - Must Test",
                    "priority": 4,
                    "short_name": "4 - Must",
                },
            ],
            "",
        )

        with patch.object(self.environment, "log") as mock_log, patch.object(
            self.environment, "set_parameters"
        ), patch.object(self.environment, "check_for_required_parameters"):
            result = self.runner.invoke(cmd_priorities.list, [], obj=self.environment)

            assert result.exit_code == 0
            mock_client.api_request_handler.priority_handler.get_priorities.assert_called_once()
            assert mock_log.called

    @mock.patch("trcli.commands.cmd_priorities.ProjectBasedClient")
    def test_list_priorities_json_output(self, mock_project_client):
        """Test priorities listing with JSON output"""
        mock_client = self._setup_project_client_mock(mock_project_client)
        priorities_data = [
            {
                "id": 1,
                "is_default": False,
                "name": "1 - Don't Test",
                "priority": 1,
                "short_name": "1 - Don't",
            },
            {
                "id": 4,
                "is_default": True,
                "name": "4 - Must Test",
                "priority": 4,
                "short_name": "4 - Must",
            },
        ]
        mock_client.api_request_handler.priority_handler.get_priorities.return_value = (priorities_data, "")

        with patch.object(self.environment, "set_parameters"), patch.object(
            self.environment, "check_for_required_parameters"
        ):
            result = self.runner.invoke(cmd_priorities.list, ["--json-output"], obj=self.environment)

            assert result.exit_code == 0
            # Check for prettified JSON
            assert '"name": "4 - Must Test"' in result.output
            assert "\n" in result.output

    @mock.patch("trcli.commands.cmd_priorities.ProjectBasedClient")
    def test_list_priorities_show_all_fields(self, mock_project_client):
        """Test priorities listing with show all fields"""
        mock_client = self._setup_project_client_mock(mock_project_client)
        mock_client.api_request_handler.priority_handler.get_priorities.return_value = (
            [
                {
                    "id": 1,
                    "is_default": False,
                    "name": "1 - Don't Test",
                    "priority": 1,
                    "short_name": "1 - Don't",
                },
                {
                    "id": 4,
                    "is_default": True,
                    "name": "4 - Must Test",
                    "priority": 4,
                    "short_name": "4 - Must",
                },
            ],
            "",
        )

        with patch.object(self.environment, "log") as mock_log, patch.object(
            self.environment, "set_parameters"
        ), patch.object(self.environment, "check_for_required_parameters"):
            result = self.runner.invoke(cmd_priorities.list, ["--show-all-fields"], obj=self.environment)

            assert result.exit_code == 0
            assert mock_log.called

    @mock.patch("trcli.commands.cmd_priorities.ProjectBasedClient")
    def test_list_priorities_empty_result(self, mock_project_client):
        """Test priorities listing with no priorities (edge case)"""
        mock_client = self._setup_project_client_mock(mock_project_client)
        mock_client.api_request_handler.priority_handler.get_priorities.return_value = ([], "")

        with patch.object(self.environment, "log") as mock_log, patch.object(
            self.environment, "set_parameters"
        ), patch.object(self.environment, "check_for_required_parameters"):
            result = self.runner.invoke(cmd_priorities.list, [], obj=self.environment)

            assert result.exit_code == 0
            assert mock_log.called

    @mock.patch("trcli.commands.cmd_priorities.ProjectBasedClient")
    def test_list_priorities_api_error(self, mock_project_client):
        """Test priorities listing with API error"""
        mock_client = self._setup_project_client_mock(mock_project_client)
        mock_client.api_request_handler.priority_handler.get_priorities.return_value = ([], "Connection timeout")

        with patch.object(self.environment, "elog") as mock_elog, patch.object(
            self.environment, "set_parameters"
        ), patch.object(self.environment, "check_for_required_parameters"):
            result = self.runner.invoke(cmd_priorities.list, [], obj=self.environment)

            assert result.exit_code == 1
            mock_elog.assert_called_with("Error: Failed to retrieve priorities: Connection timeout")

    @mock.patch("trcli.commands.cmd_priorities.ProjectBasedClient")
    def test_list_priorities_default_marked(self, mock_project_client):
        """Test that default priority is properly marked"""
        mock_client = self._setup_project_client_mock(mock_project_client)
        mock_client.api_request_handler.priority_handler.get_priorities.return_value = (
            [
                {
                    "id": 2,
                    "is_default": False,
                    "name": "2 - Low",
                    "priority": 2,
                    "short_name": "2 - Low",
                },
                {
                    "id": 3,
                    "is_default": True,
                    "name": "3 - Medium",
                    "priority": 3,
                    "short_name": "3 - Med",
                },
            ],
            "",
        )

        with patch.object(self.environment, "log") as mock_log, patch.object(
            self.environment, "set_parameters"
        ), patch.object(self.environment, "check_for_required_parameters"):
            result = self.runner.invoke(cmd_priorities.list, [], obj=self.environment)

            assert result.exit_code == 0
            # Verify DEFAULT marker appears for the default priority
            log_calls = [str(call) for call in mock_log.call_args_list]
            assert any("[DEFAULT]" in str(call) for call in log_calls)
