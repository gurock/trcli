import pytest
from unittest import mock
from unittest.mock import MagicMock, patch
from click.testing import CliRunner

from trcli.cli import Environment
from trcli.commands import cmd_configurations


class TestCmdConfigurations:
    """Test class for configurations command functionality"""

    def setup_method(self):
        """Set up test environment"""
        self.runner = CliRunner()
        self.environment = Environment(cmd="configurations")
        self.environment.host = "https://test.testrail.com"
        self.environment.username = "test@example.com"
        self.environment.password = "password"
        self.environment.project = "Test Project"
        self.environment.project_id = 1

    def _setup_project_client_mock(self, mock_project_client, project_id=1):
        """Helper to setup ProjectBasedClient mock"""
        mock_client_instance = MagicMock()
        mock_project_client.return_value = mock_client_instance
        mock_client_instance.project.project_id = project_id
        return mock_client_instance

    @mock.patch("trcli.commands.cmd_configurations.ProjectBasedClient")
    def test_list_configurations_success(self, mock_project_client):
        """Test successful configurations listing"""
        mock_client = self._setup_project_client_mock(mock_project_client)
        mock_client.api_request_handler.configuration_handler.get_configs.return_value = (
            [
                {
                    "id": 1,
                    "name": "Browsers",
                    "project_id": 1,
                    "configs": [
                        {"id": 3, "name": "Chrome", "group_id": 1},
                        {"id": 4, "name": "Firefox", "group_id": 1},
                        {"id": 1, "name": "IE 10", "group_id": 1},
                        {"id": 2, "name": "IE 11", "group_id": 1},
                        {"id": 5, "name": "Safari", "group_id": 1},
                    ],
                }
            ],
            "",
        )

        with patch.object(self.environment, "log") as mock_log, patch.object(
            self.environment, "set_parameters"
        ), patch.object(self.environment, "check_for_required_parameters"):
            result = self.runner.invoke(cmd_configurations.list, [], obj=self.environment)

            assert result.exit_code == 0
            mock_client.api_request_handler.configuration_handler.get_configs.assert_called_once_with(project_id=1)
            assert mock_log.called

    @mock.patch("trcli.commands.cmd_configurations.ProjectBasedClient")
    def test_list_configurations_multiple_groups(self, mock_project_client):
        """Test configurations listing with multiple groups"""
        mock_client = self._setup_project_client_mock(mock_project_client)
        mock_client.api_request_handler.configuration_handler.get_configs.return_value = (
            [
                {
                    "id": 1,
                    "name": "Browsers",
                    "project_id": 1,
                    "configs": [
                        {"id": 1, "name": "Chrome", "group_id": 1},
                        {"id": 2, "name": "Firefox", "group_id": 1},
                    ],
                },
                {
                    "id": 2,
                    "name": "Operating Systems",
                    "project_id": 1,
                    "configs": [
                        {"id": 3, "name": "Windows 10", "group_id": 2},
                        {"id": 4, "name": "Ubuntu 20.04", "group_id": 2},
                        {"id": 5, "name": "macOS 11", "group_id": 2},
                    ],
                },
            ],
            "",
        )

        with patch.object(self.environment, "log") as mock_log, patch.object(
            self.environment, "set_parameters"
        ), patch.object(self.environment, "check_for_required_parameters"):
            result = self.runner.invoke(cmd_configurations.list, [], obj=self.environment)

            assert result.exit_code == 0
            assert mock_log.called

    @mock.patch("trcli.commands.cmd_configurations.ProjectBasedClient")
    def test_list_configurations_json_output(self, mock_project_client):
        """Test configurations listing with JSON output"""
        mock_client = self._setup_project_client_mock(mock_project_client)
        configs_data = [
            {
                "id": 1,
                "name": "Browsers",
                "project_id": 1,
                "configs": [{"id": 1, "name": "Chrome", "group_id": 1}],
            }
        ]
        mock_client.api_request_handler.configuration_handler.get_configs.return_value = (configs_data, "")

        with patch.object(self.environment, "set_parameters"), patch.object(
            self.environment, "check_for_required_parameters"
        ):
            result = self.runner.invoke(cmd_configurations.list, ["--json-output"], obj=self.environment)

            assert result.exit_code == 0
            # Check for prettified JSON
            assert '"Browsers"' in result.output
            assert "\n" in result.output

    @mock.patch("trcli.commands.cmd_configurations.ProjectBasedClient")
    def test_list_configurations_show_all_fields(self, mock_project_client):
        """Test configurations listing with show all fields"""
        mock_client = self._setup_project_client_mock(mock_project_client)
        mock_client.api_request_handler.configuration_handler.get_configs.return_value = (
            [
                {
                    "id": 1,
                    "name": "Browsers",
                    "project_id": 1,
                    "configs": [
                        {"id": 1, "name": "Chrome", "group_id": 1},
                        {"id": 2, "name": "Firefox", "group_id": 1},
                    ],
                }
            ],
            "",
        )

        with patch.object(self.environment, "log") as mock_log, patch.object(
            self.environment, "set_parameters"
        ), patch.object(self.environment, "check_for_required_parameters"):
            result = self.runner.invoke(cmd_configurations.list, ["--show-all-fields"], obj=self.environment)

            assert result.exit_code == 0
            assert mock_log.called

    @mock.patch("trcli.commands.cmd_configurations.ProjectBasedClient")
    def test_list_configurations_empty_result(self, mock_project_client):
        """Test configurations listing with no configuration groups"""
        mock_client = self._setup_project_client_mock(mock_project_client)
        mock_client.api_request_handler.configuration_handler.get_configs.return_value = ([], "")

        with patch.object(self.environment, "log") as mock_log, patch.object(
            self.environment, "set_parameters"
        ), patch.object(self.environment, "check_for_required_parameters"):
            result = self.runner.invoke(cmd_configurations.list, [], obj=self.environment)

            assert result.exit_code == 0
            assert mock_log.called

    @mock.patch("trcli.commands.cmd_configurations.ProjectBasedClient")
    def test_list_configurations_api_error(self, mock_project_client):
        """Test configurations listing with API error"""
        mock_client = self._setup_project_client_mock(mock_project_client)
        mock_client.api_request_handler.configuration_handler.get_configs.return_value = ([], "Project not found")

        with patch.object(self.environment, "elog") as mock_elog, patch.object(
            self.environment, "set_parameters"
        ), patch.object(self.environment, "check_for_required_parameters"):
            result = self.runner.invoke(cmd_configurations.list, [], obj=self.environment)

            assert result.exit_code == 1
            mock_elog.assert_called_with("Error: Failed to retrieve configurations: Project not found")

    @mock.patch("trcli.commands.cmd_configurations.ProjectBasedClient")
    def test_list_configurations_empty_configs_in_group(self, mock_project_client):
        """Test configurations listing with group that has no configs"""
        mock_client = self._setup_project_client_mock(mock_project_client)
        mock_client.api_request_handler.configuration_handler.get_configs.return_value = (
            [{"id": 1, "name": "Empty Group", "project_id": 1, "configs": []}],
            "",
        )

        with patch.object(self.environment, "log") as mock_log, patch.object(
            self.environment, "set_parameters"
        ), patch.object(self.environment, "check_for_required_parameters"):
            result = self.runner.invoke(cmd_configurations.list, [], obj=self.environment)

            assert result.exit_code == 0
            assert mock_log.called

    @mock.patch("trcli.commands.cmd_configurations.ProjectBasedClient")
    def test_list_configurations_with_project_id_from_config(self, mock_project_client):
        """Test list configurations using project_id from configuration"""
        mock_client = self._setup_project_client_mock(mock_project_client, project_id=5)
        self.environment.project_id = 5
        mock_client.api_request_handler.configuration_handler.get_configs.return_value = ([], "")

        with patch.object(self.environment, "log"), patch.object(self.environment, "set_parameters"), patch.object(
            self.environment, "check_for_required_parameters"
        ):
            result = self.runner.invoke(cmd_configurations.list, [], obj=self.environment)

            assert result.exit_code == 0
            mock_client.api_request_handler.configuration_handler.get_configs.assert_called_once_with(project_id=5)

    @mock.patch("trcli.commands.cmd_configurations.ProjectBasedClient")
    def test_list_configurations_with_project_name(self, mock_project_client):
        """Test list configurations using project name resolution"""
        mock_client = self._setup_project_client_mock(mock_project_client)
        self.environment.project = "Test Project"
        mock_client.api_request_handler.configuration_handler.get_configs.return_value = (
            [
                {
                    "id": 1,
                    "name": "Browsers",
                    "project_id": 1,
                    "configs": [{"id": 1, "name": "Chrome", "group_id": 1}],
                }
            ],
            "",
        )

        with patch.object(self.environment, "log"), patch.object(self.environment, "set_parameters"), patch.object(
            self.environment, "check_for_required_parameters"
        ):
            result = self.runner.invoke(cmd_configurations.list, [], obj=self.environment)

            assert result.exit_code == 0
