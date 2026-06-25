import pytest
from unittest import mock
from unittest.mock import MagicMock, patch
from click.testing import CliRunner

from trcli.cli import Environment
from trcli.commands import cmd_statuses


class TestCmdStatuses:
    """Test class for statuses command functionality"""

    def setup_method(self):
        """Set up test environment"""
        self.runner = CliRunner()
        self.environment = Environment(cmd="statuses")
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

    # Tests for 'statuses all' subcommand
    @mock.patch("trcli.commands.cmd_statuses.ProjectBasedClient")
    def test_list_all_statuses_success(self, mock_project_client):
        """Test successful test result statuses listing"""
        mock_client = self._setup_project_client_mock(mock_project_client)
        mock_client.api_request_handler.status_handler.get_statuses.return_value = (
            [
                {
                    "id": 1,
                    "name": "passed",
                    "label": "Passed",
                    "is_system": True,
                    "is_untested": False,
                    "is_final": True,
                    "color_dark": 12709313,
                    "color_medium": 14527786,
                    "color_bright": 15394764,
                },
                {
                    "id": 5,
                    "name": "failed",
                    "label": "Failed",
                    "is_system": True,
                    "is_untested": False,
                    "is_final": True,
                    "color_dark": 12396910,
                    "color_medium": 15829135,
                    "color_bright": 16434723,
                },
            ],
            "",
        )

        with patch.object(self.environment, "log") as mock_log, patch.object(
            self.environment, "set_parameters"
        ), patch.object(self.environment, "check_for_required_parameters"):
            result = self.runner.invoke(cmd_statuses.all, [], obj=self.environment)

            assert result.exit_code == 0
            mock_client.api_request_handler.status_handler.get_statuses.assert_called_once_with(project_id=1)
            assert mock_log.called

    @mock.patch("trcli.commands.cmd_statuses.ProjectBasedClient")
    def test_list_all_statuses_json_output(self, mock_project_client):
        """Test statuses listing with JSON output"""
        mock_client = self._setup_project_client_mock(mock_project_client)
        statuses_data = [
            {
                "id": 1,
                "name": "passed",
                "label": "Passed",
                "is_system": True,
                "is_untested": False,
                "is_final": True,
                "color_dark": 12709313,
                "color_medium": 14527786,
                "color_bright": 15394764,
            },
        ]
        mock_client.api_request_handler.status_handler.get_statuses.return_value = (statuses_data, "")

        with patch.object(self.environment, "set_parameters"), patch.object(
            self.environment, "check_for_required_parameters"
        ):
            result = self.runner.invoke(cmd_statuses.all, ["--json-output"], obj=self.environment)

            assert result.exit_code == 0
            assert '"id": 1' in result.output
            assert '"name": "passed"' in result.output
            assert "\n" in result.output

    @mock.patch("trcli.commands.cmd_statuses.ProjectBasedClient")
    def test_list_all_statuses_show_all_fields(self, mock_project_client):
        """Test statuses listing with show all fields"""
        mock_client = self._setup_project_client_mock(mock_project_client)
        mock_client.api_request_handler.status_handler.get_statuses.return_value = (
            [
                {
                    "id": 1,
                    "name": "passed",
                    "label": "Passed",
                    "is_system": True,
                    "is_untested": False,
                    "is_final": True,
                    "color_dark": 12709313,
                    "color_medium": 14527786,
                    "color_bright": 15394764,
                }
            ],
            "",
        )

        with patch.object(self.environment, "log") as mock_log, patch.object(
            self.environment, "set_parameters"
        ), patch.object(self.environment, "check_for_required_parameters"):
            result = self.runner.invoke(cmd_statuses.all, ["--show-all-fields"], obj=self.environment)

            assert result.exit_code == 0
            assert mock_log.called

    @mock.patch("trcli.commands.cmd_statuses.ProjectBasedClient")
    def test_list_all_statuses_empty_result(self, mock_project_client):
        """Test statuses listing with no statuses"""
        mock_client = self._setup_project_client_mock(mock_project_client)
        mock_client.api_request_handler.status_handler.get_statuses.return_value = ([], "")

        with patch.object(self.environment, "log") as mock_log, patch.object(
            self.environment, "set_parameters"
        ), patch.object(self.environment, "check_for_required_parameters"):
            result = self.runner.invoke(cmd_statuses.all, [], obj=self.environment)

            assert result.exit_code == 0
            assert mock_log.called

    @mock.patch("trcli.commands.cmd_statuses.ProjectBasedClient")
    def test_list_all_statuses_api_error(self, mock_project_client):
        """Test statuses listing with API error"""
        mock_client = self._setup_project_client_mock(mock_project_client)
        mock_client.api_request_handler.status_handler.get_statuses.return_value = ([], "Project not found")

        with patch.object(self.environment, "elog") as mock_elog, patch.object(
            self.environment, "set_parameters"
        ), patch.object(self.environment, "check_for_required_parameters"):
            result = self.runner.invoke(cmd_statuses.all, [], obj=self.environment)

            assert result.exit_code == 1
            mock_elog.assert_called_with("Error: Failed to retrieve statuses: Project not found")

    # Tests for 'statuses case' subcommand
    @mock.patch("trcli.commands.cmd_statuses.ProjectBasedClient")
    def test_list_case_statuses_success(self, mock_project_client):
        """Test successful case statuses listing"""
        mock_client = self._setup_project_client_mock(mock_project_client)
        mock_client.api_request_handler.status_handler.get_case_statuses.return_value = (
            [
                {
                    "case_status_id": 1,
                    "name": "Approved",
                    "abbreviation": None,
                    "is_default": False,
                    "is_approved": True,
                },
                {
                    "case_status_id": 2,
                    "name": "Draft",
                    "abbreviation": "DFT",
                    "is_default": True,
                    "is_approved": False,
                },
            ],
            "",
        )

        with patch.object(self.environment, "log") as mock_log, patch.object(
            self.environment, "set_parameters"
        ), patch.object(self.environment, "check_for_required_parameters"):
            result = self.runner.invoke(cmd_statuses.case, [], obj=self.environment)

            assert result.exit_code == 0
            mock_client.api_request_handler.status_handler.get_case_statuses.assert_called_once()
            assert mock_log.called

    @mock.patch("trcli.commands.cmd_statuses.ProjectBasedClient")
    def test_list_case_statuses_json_output(self, mock_project_client):
        """Test case statuses listing with JSON output"""
        mock_client = self._setup_project_client_mock(mock_project_client)
        case_statuses_data = [
            {
                "case_status_id": 1,
                "name": "Approved",
                "abbreviation": None,
                "is_default": False,
                "is_approved": True,
            },
        ]
        mock_client.api_request_handler.status_handler.get_case_statuses.return_value = (case_statuses_data, "")

        with patch.object(self.environment, "set_parameters"), patch.object(
            self.environment, "check_for_required_parameters"
        ):
            result = self.runner.invoke(cmd_statuses.case, ["--json-output"], obj=self.environment)

            assert result.exit_code == 0
            assert '"case_status_id": 1' in result.output
            assert '"name": "Approved"' in result.output
            assert "\n" in result.output

    @mock.patch("trcli.commands.cmd_statuses.ProjectBasedClient")
    def test_list_case_statuses_show_all_fields(self, mock_project_client):
        """Test case statuses listing with show all fields"""
        mock_client = self._setup_project_client_mock(mock_project_client)
        mock_client.api_request_handler.status_handler.get_case_statuses.return_value = (
            [
                {
                    "case_status_id": 2,
                    "name": "Draft",
                    "abbreviation": "DFT",
                    "is_default": True,
                    "is_approved": False,
                }
            ],
            "",
        )

        with patch.object(self.environment, "log") as mock_log, patch.object(
            self.environment, "set_parameters"
        ), patch.object(self.environment, "check_for_required_parameters"):
            result = self.runner.invoke(cmd_statuses.case, ["--show-all-fields"], obj=self.environment)

            assert result.exit_code == 0
            assert mock_log.called

    @mock.patch("trcli.commands.cmd_statuses.ProjectBasedClient")
    def test_list_case_statuses_empty_result(self, mock_project_client):
        """Test case statuses listing with no case statuses"""
        mock_client = self._setup_project_client_mock(mock_project_client)
        mock_client.api_request_handler.status_handler.get_case_statuses.return_value = ([], "")

        with patch.object(self.environment, "log") as mock_log, patch.object(
            self.environment, "set_parameters"
        ), patch.object(self.environment, "check_for_required_parameters"):
            result = self.runner.invoke(cmd_statuses.case, [], obj=self.environment)

            assert result.exit_code == 0
            assert mock_log.called

    @mock.patch("trcli.commands.cmd_statuses.ProjectBasedClient")
    def test_list_case_statuses_api_error(self, mock_project_client):
        """Test case statuses listing with API error"""
        mock_client = self._setup_project_client_mock(mock_project_client)
        mock_client.api_request_handler.status_handler.get_case_statuses.return_value = (
            [],
            "API endpoint not found",
        )

        with patch.object(self.environment, "elog") as mock_elog, patch.object(
            self.environment, "set_parameters"
        ), patch.object(self.environment, "check_for_required_parameters"):
            result = self.runner.invoke(cmd_statuses.case, [], obj=self.environment)

            assert result.exit_code == 1
            # Check that the error was logged (should be called at least once for the error message)
            assert mock_elog.called

    @mock.patch("trcli.commands.cmd_statuses.ProjectBasedClient")
    def test_list_case_statuses_with_abbreviation_none(self, mock_project_client):
        """Test case statuses with None abbreviation"""
        mock_client = self._setup_project_client_mock(mock_project_client)
        mock_client.api_request_handler.status_handler.get_case_statuses.return_value = (
            [
                {
                    "case_status_id": 1,
                    "name": "Approved",
                    "abbreviation": None,
                    "is_default": False,
                    "is_approved": True,
                }
            ],
            "",
        )

        with patch.object(self.environment, "log") as mock_log, patch.object(
            self.environment, "set_parameters"
        ), patch.object(self.environment, "check_for_required_parameters"):
            result = self.runner.invoke(cmd_statuses.case, ["--show-all-fields"], obj=self.environment)

            assert result.exit_code == 0
            assert mock_log.called
