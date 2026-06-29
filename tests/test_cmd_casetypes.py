import pytest
from unittest import mock
from unittest.mock import MagicMock, patch
from click.testing import CliRunner

from trcli.cli import Environment
from trcli.commands import cmd_casetypes


class TestCmdCaseTypes:
    """Test class for casetypes command functionality"""

    def setup_method(self):
        """Set up test environment"""
        self.runner = CliRunner()
        self.environment = Environment(cmd="casetypes")
        self.environment.host = "https://test.testrail.com"
        self.environment.username = "test@example.com"
        self.environment.password = "password"
        self.environment.api_key = None

    def _setup_project_client_mock(self, mock_project_client):
        """Helper to setup ProjectBasedClient mock"""
        mock_client_instance = MagicMock()
        mock_project_client.return_value = mock_client_instance
        return mock_client_instance

    @mock.patch("trcli.commands.cmd_casetypes.ProjectBasedClient")
    def test_list_case_types_success(self, mock_project_client):
        """Test successful case types listing"""
        mock_client = self._setup_project_client_mock(mock_project_client)
        mock_client.api_request_handler.case_type_handler.get_case_types.return_value = (
            [
                {"id": 1, "is_default": False, "name": "Automated"},
                {"id": 2, "is_default": False, "name": "Functionality"},
                {"id": 3, "is_default": False, "name": "Performance"},
                {"id": 6, "is_default": True, "name": "Other"},
            ],
            "",
        )

        with patch.object(self.environment, "log") as mock_log, patch.object(
            self.environment, "set_parameters"
        ), patch.object(self.environment, "check_for_required_parameters"):
            result = self.runner.invoke(cmd_casetypes.list, [], obj=self.environment)

            assert result.exit_code == 0
            mock_client.api_request_handler.case_type_handler.get_case_types.assert_called_once()
            assert mock_log.called

    @mock.patch("trcli.commands.cmd_casetypes.ProjectBasedClient")
    def test_list_case_types_json_output(self, mock_project_client):
        """Test case types listing with JSON output"""
        mock_client = self._setup_project_client_mock(mock_project_client)
        case_types_data = [
            {"id": 1, "is_default": False, "name": "Automated"},
            {"id": 6, "is_default": True, "name": "Other"},
        ]
        mock_client.api_request_handler.case_type_handler.get_case_types.return_value = (case_types_data, "")

        with patch.object(self.environment, "set_parameters"), patch.object(
            self.environment, "check_for_required_parameters"
        ):
            result = self.runner.invoke(cmd_casetypes.list, ["--json-output"], obj=self.environment)

            assert result.exit_code == 0
            # Check for prettified JSON
            assert '"name": "Automated"' in result.output
            assert "\n" in result.output

    @mock.patch("trcli.commands.cmd_casetypes.ProjectBasedClient")
    def test_list_case_types_empty_result(self, mock_project_client):
        """Test case types listing with no case types (edge case)"""
        mock_client = self._setup_project_client_mock(mock_project_client)
        mock_client.api_request_handler.case_type_handler.get_case_types.return_value = ([], "")

        with patch.object(self.environment, "log") as mock_log, patch.object(
            self.environment, "set_parameters"
        ), patch.object(self.environment, "check_for_required_parameters"):
            result = self.runner.invoke(cmd_casetypes.list, [], obj=self.environment)

            assert result.exit_code == 0
            assert mock_log.called

    @mock.patch("trcli.commands.cmd_casetypes.ProjectBasedClient")
    def test_list_case_types_api_error(self, mock_project_client):
        """Test case types listing with API error"""
        mock_client = self._setup_project_client_mock(mock_project_client)
        mock_client.api_request_handler.case_type_handler.get_case_types.return_value = ([], "Connection timeout")

        with patch.object(self.environment, "elog") as mock_elog, patch.object(
            self.environment, "set_parameters"
        ), patch.object(self.environment, "check_for_required_parameters"):
            result = self.runner.invoke(cmd_casetypes.list, [], obj=self.environment)

            assert result.exit_code == 1
            mock_elog.assert_called_with("Error: Failed to retrieve case types: Connection timeout")

    @mock.patch("trcli.commands.cmd_casetypes.ProjectBasedClient")
    def test_list_case_types_default_marked(self, mock_project_client):
        """Test that default case type is properly marked"""
        mock_client = self._setup_project_client_mock(mock_project_client)
        mock_client.api_request_handler.case_type_handler.get_case_types.return_value = (
            [
                {"id": 1, "is_default": False, "name": "Automated"},
                {"id": 6, "is_default": True, "name": "Other"},
            ],
            "",
        )

        with patch.object(self.environment, "log") as mock_log, patch.object(
            self.environment, "set_parameters"
        ), patch.object(self.environment, "check_for_required_parameters"):
            result = self.runner.invoke(cmd_casetypes.list, [], obj=self.environment)

            assert result.exit_code == 0
            # Verify DEFAULT marker appears for the default case type
            log_calls = [str(call) for call in mock_log.call_args_list]
            assert any("[DEFAULT]" in str(call) for call in log_calls)
