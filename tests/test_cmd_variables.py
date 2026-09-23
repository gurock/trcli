import pytest
import json
from unittest import mock
from unittest.mock import MagicMock, patch
from click.testing import CliRunner

from trcli.cli import Environment
from trcli.commands import cmd_variables


class TestCmdVariables:
    """Test class for variables command functionality"""

    def setup_method(self):
        """Set up test environment"""
        self.runner = CliRunner()
        self.environment = Environment(cmd="variables")
        self.environment.host = "https://test.testrail.com"
        self.environment.username = "test@example.com"
        self.environment.password = "password"
        self.environment.api_key = None
        self.environment.project = "Test Project"

    def _setup_project_client_mock(self, mock_project_client):
        """Helper to setup ProjectBasedClient mock"""
        mock_client_instance = MagicMock()
        mock_project_client.return_value = mock_client_instance
        mock_client_instance.project.project_id = 1
        return mock_client_instance

    @mock.patch("trcli.commands.cmd_variables.ProjectBasedClient")
    def test_list_variables_success(self, mock_project_client):
        """Test successful variables listing"""
        mock_client = self._setup_project_client_mock(mock_project_client)
        mock_client.api_request_handler.variables_handler.get_variables.return_value = (
            {
                "variables": [
                    {"id": 1, "name": "browser"},
                    {"id": 2, "name": "environment"},
                ],
                "offset": 0,
                "limit": 250,
                "size": 2,
                "_links": {},
            },
            "",
        )

        with patch.object(self.environment, "log") as mock_log, patch.object(
            self.environment, "set_parameters"
        ), patch.object(self.environment, "check_for_required_parameters"):
            result = self.runner.invoke(cmd_variables.list, [], obj=self.environment)

            assert result.exit_code == 0
            mock_client.api_request_handler.variables_handler.get_variables.assert_called_once_with(
                project_id=1, limit=250, offset=0
            )
            assert mock_log.called

    @mock.patch("trcli.commands.cmd_variables.ProjectBasedClient")
    def test_list_variables_with_pagination(self, mock_project_client):
        """Test variables listing with custom pagination"""
        mock_client = self._setup_project_client_mock(mock_project_client)
        mock_client.api_request_handler.variables_handler.get_variables.return_value = (
            {"variables": [], "offset": 100, "limit": 50, "size": 0, "_links": {}},
            "",
        )

        with patch.object(self.environment, "log") as mock_log, patch.object(
            self.environment, "set_parameters"
        ), patch.object(self.environment, "check_for_required_parameters"):
            result = self.runner.invoke(cmd_variables.list, ["--offset", "100", "--limit", "50"], obj=self.environment)

            assert result.exit_code == 0
            mock_client.api_request_handler.variables_handler.get_variables.assert_called_once_with(
                project_id=1, limit=50, offset=100
            )

    @mock.patch("trcli.commands.cmd_variables.ProjectBasedClient")
    def test_list_variables_json_output(self, mock_project_client):
        """Test variables listing with JSON output"""
        mock_client = self._setup_project_client_mock(mock_project_client)
        variables_data = {
            "variables": [{"id": 1, "name": "browser"}],
            "offset": 0,
            "limit": 250,
            "size": 1,
            "_links": {},
        }
        mock_client.api_request_handler.variables_handler.get_variables.return_value = (variables_data, "")

        with patch.object(self.environment, "log"), patch.object(self.environment, "set_parameters"), patch.object(
            self.environment, "check_for_required_parameters"
        ):
            result = self.runner.invoke(cmd_variables.list, ["--json-output"], obj=self.environment)

            assert result.exit_code == 0
            # Try to parse JSON from output
            output_lines = result.output.strip().split("\n")
            json_output = None
            for line in output_lines:
                try:
                    json_output = json.loads(line)
                    break
                except json.JSONDecodeError:
                    continue

            if json_output is None:
                import re

                json_match = re.search(r"\{.*\}", result.output, re.DOTALL)
                if json_match:
                    json_output = json.loads(json_match.group(0))

            assert json_output == variables_data

    @mock.patch("trcli.commands.cmd_variables.ProjectBasedClient")
    def test_list_variables_empty(self, mock_project_client):
        """Test listing when no variables exist"""
        mock_client = self._setup_project_client_mock(mock_project_client)
        mock_client.api_request_handler.variables_handler.get_variables.return_value = (
            {"variables": [], "offset": 0, "limit": 250, "size": 0, "_links": {}},
            "",
        )

        with patch.object(self.environment, "log") as mock_log, patch.object(
            self.environment, "set_parameters"
        ), patch.object(self.environment, "check_for_required_parameters"):
            result = self.runner.invoke(cmd_variables.list, [], obj=self.environment)

            assert result.exit_code == 0
            # Check that "No variables found" message was logged
            log_calls = [str(call) for call in mock_log.call_args_list]
            assert any("No variables found" in str(call) for call in log_calls)

    @mock.patch("trcli.commands.cmd_variables.ProjectBasedClient")
    def test_list_variables_api_error(self, mock_project_client):
        """Test listing variables when API returns error"""
        mock_client = self._setup_project_client_mock(mock_project_client)
        mock_client.api_request_handler.variables_handler.get_variables.return_value = ({}, "API Error occurred")

        with patch.object(self.environment, "elog") as mock_elog, patch.object(
            self.environment, "set_parameters"
        ), patch.object(self.environment, "check_for_required_parameters"):
            result = self.runner.invoke(cmd_variables.list, [], obj=self.environment)

            assert result.exit_code == 1
            assert mock_elog.called

    @mock.patch("trcli.commands.cmd_variables.ProjectBasedClient")
    def test_add_variable_success(self, mock_project_client):
        """Test adding a variable"""
        mock_client = self._setup_project_client_mock(mock_project_client)
        created_variable = {"id": 456, "name": "browser"}
        mock_client.api_request_handler.variables_handler.add_variable.return_value = (created_variable, "")

        with patch.object(self.environment, "log") as mock_log, patch.object(
            self.environment, "set_parameters"
        ), patch.object(self.environment, "check_for_required_parameters"):
            result = self.runner.invoke(cmd_variables.add, ["--name", "browser"], obj=self.environment)

            assert result.exit_code == 0
            mock_client.api_request_handler.variables_handler.add_variable.assert_called_once_with(
                project_id=1, name="browser"
            )
            assert mock_log.called

    @mock.patch("trcli.commands.cmd_variables.ProjectBasedClient")
    def test_add_variable_with_underscore(self, mock_project_client):
        """Test adding a variable with underscore"""
        mock_client = self._setup_project_client_mock(mock_project_client)
        created_variable = {"id": 457, "name": "api_endpoint"}
        mock_client.api_request_handler.variables_handler.add_variable.return_value = (created_variable, "")

        with patch.object(self.environment, "log") as mock_log, patch.object(
            self.environment, "set_parameters"
        ), patch.object(self.environment, "check_for_required_parameters"):
            result = self.runner.invoke(cmd_variables.add, ["--name", "api_endpoint"], obj=self.environment)

            assert result.exit_code == 0
            mock_client.api_request_handler.variables_handler.add_variable.assert_called_once_with(
                project_id=1, name="api_endpoint"
            )

    @mock.patch("trcli.commands.cmd_variables.ProjectBasedClient")
    def test_add_variable_json_output(self, mock_project_client):
        """Test adding a variable with JSON output"""
        mock_client = self._setup_project_client_mock(mock_project_client)
        created_variable = {"id": 456, "name": "browser"}
        mock_client.api_request_handler.variables_handler.add_variable.return_value = (created_variable, "")

        with patch.object(self.environment, "log"), patch.object(self.environment, "set_parameters"), patch.object(
            self.environment, "check_for_required_parameters"
        ):
            result = self.runner.invoke(cmd_variables.add, ["--name", "browser", "--json-output"], obj=self.environment)

            assert result.exit_code == 0
            # Verify JSON in output
            assert '"id": 456' in result.output
            assert '"name": "browser"' in result.output

    @mock.patch("trcli.commands.cmd_variables.ProjectBasedClient")
    def test_add_variable_api_error(self, mock_project_client):
        """Test adding a variable when API returns error"""
        mock_client = self._setup_project_client_mock(mock_project_client)
        mock_client.api_request_handler.variables_handler.add_variable.return_value = ({}, "API Error occurred")

        with patch.object(self.environment, "elog") as mock_elog, patch.object(
            self.environment, "set_parameters"
        ), patch.object(self.environment, "check_for_required_parameters"):
            result = self.runner.invoke(cmd_variables.add, ["--name", "test"], obj=self.environment)

            assert result.exit_code == 1
            assert mock_elog.called

    @mock.patch("trcli.commands.cmd_variables.ProjectBasedClient")
    def test_update_variable_success(self, mock_project_client):
        """Test updating a variable"""
        mock_client = self._setup_project_client_mock(mock_project_client)
        updated_variable = {"id": 123, "name": "new_browser"}
        mock_client.api_request_handler.variables_handler.update_variable.return_value = (updated_variable, "")

        with patch.object(self.environment, "log") as mock_log, patch.object(
            self.environment, "set_parameters"
        ), patch.object(self.environment, "check_for_required_parameters"):
            result = self.runner.invoke(
                cmd_variables.update, ["--variable-id", "123", "--name", "new_browser"], obj=self.environment
            )

            assert result.exit_code == 0
            mock_client.api_request_handler.variables_handler.update_variable.assert_called_once_with(
                variable_id=123, name="new_browser"
            )
            assert mock_log.called

    @mock.patch("trcli.commands.cmd_variables.ProjectBasedClient")
    def test_update_variable_json_output(self, mock_project_client):
        """Test updating a variable with JSON output"""
        mock_client = self._setup_project_client_mock(mock_project_client)
        updated_variable = {"id": 123, "name": "new_browser"}
        mock_client.api_request_handler.variables_handler.update_variable.return_value = (updated_variable, "")

        with patch.object(self.environment, "log"), patch.object(self.environment, "set_parameters"), patch.object(
            self.environment, "check_for_required_parameters"
        ):
            result = self.runner.invoke(
                cmd_variables.update,
                ["--variable-id", "123", "--name", "new_browser", "--json-output"],
                obj=self.environment,
            )

            assert result.exit_code == 0
            assert '"id": 123' in result.output
            assert '"name": "new_browser"' in result.output

    @mock.patch("trcli.commands.cmd_variables.ProjectBasedClient")
    def test_update_variable_api_error(self, mock_project_client):
        """Test updating a variable when API returns error"""
        mock_client = self._setup_project_client_mock(mock_project_client)
        mock_client.api_request_handler.variables_handler.update_variable.return_value = ({}, "Variable not found")

        with patch.object(self.environment, "elog") as mock_elog, patch.object(
            self.environment, "set_parameters"
        ), patch.object(self.environment, "check_for_required_parameters"):
            result = self.runner.invoke(
                cmd_variables.update, ["--variable-id", "999", "--name", "new_name"], obj=self.environment
            )

            assert result.exit_code == 1
            assert mock_elog.called

    @mock.patch("trcli.commands.cmd_variables.ProjectBasedClient")
    def test_delete_variable_success(self, mock_project_client):
        """Test deleting a variable"""
        mock_client = self._setup_project_client_mock(mock_project_client)
        mock_client.api_request_handler.variables_handler.delete_variable.return_value = ({}, "")

        with patch.object(self.environment, "log") as mock_log, patch.object(
            self.environment, "set_parameters"
        ), patch.object(self.environment, "check_for_required_parameters"):
            result = self.runner.invoke(cmd_variables.delete, ["--variable-id", "123"], obj=self.environment)

            assert result.exit_code == 0
            mock_client.api_request_handler.variables_handler.delete_variable.assert_called_once_with(variable_id=123)
            assert mock_log.called

    @mock.patch("trcli.commands.cmd_variables.ProjectBasedClient")
    def test_delete_variable_api_error(self, mock_project_client):
        """Test deleting a variable when API returns error"""
        mock_client = self._setup_project_client_mock(mock_project_client)
        mock_client.api_request_handler.variables_handler.delete_variable.return_value = ({}, "Variable not found")

        with patch.object(self.environment, "elog") as mock_elog, patch.object(
            self.environment, "set_parameters"
        ), patch.object(self.environment, "check_for_required_parameters"):
            result = self.runner.invoke(cmd_variables.delete, ["--variable-id", "999"], obj=self.environment)

            assert result.exit_code == 1
            assert mock_elog.called
