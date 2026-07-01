import pytest
from unittest import mock
from unittest.mock import MagicMock, patch
from click.testing import CliRunner

from trcli.cli import Environment
from trcli.commands import cmd_projects


class TestCmdProjects:
    """Test suite for the projects command."""

    def setup_method(self):
        """Set up test environment"""
        self.runner = CliRunner()
        self.environment = Environment(cmd="projects")
        self.environment.host = "https://test.testrail.com"
        self.environment.username = "test@example.com"
        self.environment.password = "password"
        self.environment.api_key = None

    def _setup_project_client_mock(self, mock_project_client):
        """Helper to setup ProjectBasedClient mock"""
        mock_client_instance = MagicMock()
        mock_project_client.return_value = mock_client_instance
        return mock_client_instance

    @mock.patch("trcli.commands.cmd_projects.ProjectBasedClient")
    def test_get_project_success(self, mock_project_client):
        """Test successful project retrieval by ID."""
        mock_client = self._setup_project_client_mock(mock_project_client)
        mock_client.api_request_handler.project_handler.get_project.return_value = (
            {"id": 1, "name": "Test Project", "is_completed": False, "suite_mode": 3},
            "",
        )

        with patch.object(self.environment, "log") as mock_log, patch.object(
            self.environment, "set_parameters"
        ), patch.object(self.environment, "check_for_required_parameters"):
            result = self.runner.invoke(cmd_projects.get, ["--project-id", "1"], obj=self.environment)

            assert result.exit_code == 0
            assert mock_log.called
            mock_client.api_request_handler.project_handler.get_project.assert_called_once_with(1)

    @mock.patch("trcli.commands.cmd_projects.ProjectBasedClient")
    def test_get_project_with_all_fields(self, mock_project_client):
        """Test project retrieval with all fields displayed."""
        mock_client = self._setup_project_client_mock(mock_project_client)
        mock_client.api_request_handler.project_handler.get_project.return_value = (
            {
                "id": 1,
                "name": "Test Project",
                "announcement": "Welcome!",
                "completed_on": 1389968184,
                "default_role_id": 3,
                "default_role": "Tester",
                "is_completed": False,
                "show_announcement": True,
                "suite_mode": 3,
                "url": "https://test.testrail.io/projects/1",
                "users": [{"id": 5}],
                "groups": [],
            },
            "",
        )

        with patch.object(self.environment, "log") as mock_log, patch.object(
            self.environment, "set_parameters"
        ), patch.object(self.environment, "check_for_required_parameters"):
            result = self.runner.invoke(
                cmd_projects.get, ["--project-id", "1", "--show-all-fields"], obj=self.environment
            )

            assert result.exit_code == 0
            assert mock_log.called

    @mock.patch("trcli.commands.cmd_projects.ProjectBasedClient")
    def test_get_project_json_output(self, mock_project_client):
        """Test project retrieval with JSON output."""
        mock_client = self._setup_project_client_mock(mock_project_client)
        mock_client.api_request_handler.project_handler.get_project.return_value = (
            {"id": 1, "name": "Test Project", "is_completed": False, "suite_mode": 3},
            "",
        )

        with patch.object(self.environment, "log") as mock_log, patch.object(
            self.environment, "set_parameters"
        ), patch.object(self.environment, "check_for_required_parameters"):
            result = self.runner.invoke(cmd_projects.get, ["--project-id", "1", "--json-output"], obj=self.environment)

            assert result.exit_code == 0
            assert '"id": 1' in result.output
            assert '"name": "Test Project"' in result.output

    @mock.patch("trcli.commands.cmd_projects.ProjectBasedClient")
    def test_get_project_api_error(self, mock_project_client):
        """Test handling of API errors when getting a project."""
        mock_client = self._setup_project_client_mock(mock_project_client)
        mock_client.api_request_handler.project_handler.get_project.return_value = (
            None,
            "Project not found",
        )

        with patch.object(self.environment, "log") as mock_log, patch.object(
            self.environment, "set_parameters"
        ), patch.object(self.environment, "check_for_required_parameters"), patch.object(
            self.environment, "elog"
        ) as mock_elog:
            result = self.runner.invoke(cmd_projects.get, ["--project-id", "999"], obj=self.environment)

            assert result.exit_code == 1
            assert mock_elog.called

    @mock.patch("trcli.commands.cmd_projects.ProjectBasedClient")
    def test_list_projects_success(self, mock_project_client):
        """Test successful listing of all projects."""
        mock_client = self._setup_project_client_mock(mock_project_client)
        mock_client.api_request_handler.project_handler.get_projects.return_value = (
            [
                {"id": 1, "name": "Project A", "is_completed": False, "suite_mode": 1},
                {"id": 2, "name": "Project B", "is_completed": True, "suite_mode": 3},
            ],
            "",
        )

        with patch.object(self.environment, "log") as mock_log, patch.object(
            self.environment, "set_parameters"
        ), patch.object(self.environment, "check_for_required_parameters"):
            result = self.runner.invoke(cmd_projects.list, [], obj=self.environment)

            assert result.exit_code == 0
            assert mock_log.called
            mock_client.api_request_handler.project_handler.get_projects.assert_called_once_with(
                is_completed=None, limit=None, offset=None
            )

    @mock.patch("trcli.commands.cmd_projects.ProjectBasedClient")
    def test_list_projects_with_filters(self, mock_project_client):
        """Test listing projects with filters (is_completed, limit, offset)."""
        mock_client = self._setup_project_client_mock(mock_project_client)
        mock_client.api_request_handler.project_handler.get_projects.return_value = (
            [{"id": 1, "name": "Active Project", "is_completed": False, "suite_mode": 1}],
            "",
        )

        with patch.object(self.environment, "log") as mock_log, patch.object(
            self.environment, "set_parameters"
        ), patch.object(self.environment, "check_for_required_parameters"):
            result = self.runner.invoke(
                cmd_projects.list, ["--is-completed", "0", "--limit", "10", "--offset", "5"], obj=self.environment
            )

            assert result.exit_code == 0
            assert mock_log.called
            mock_client.api_request_handler.project_handler.get_projects.assert_called_once_with(
                is_completed=0, limit=10, offset=5
            )

    @mock.patch("trcli.commands.cmd_projects.ProjectBasedClient")
    def test_list_projects_completed_only(self, mock_project_client):
        """Test listing only completed projects."""
        mock_client = self._setup_project_client_mock(mock_project_client)
        mock_client.api_request_handler.project_handler.get_projects.return_value = (
            [{"id": 2, "name": "Completed Project", "is_completed": True, "suite_mode": 2}],
            "",
        )

        with patch.object(self.environment, "log") as mock_log, patch.object(
            self.environment, "set_parameters"
        ), patch.object(self.environment, "check_for_required_parameters"):
            result = self.runner.invoke(cmd_projects.list, ["--is-completed", "1"], obj=self.environment)

            assert result.exit_code == 0
            assert mock_log.called
            mock_client.api_request_handler.project_handler.get_projects.assert_called_once_with(
                is_completed=1, limit=None, offset=None
            )

    @mock.patch("trcli.commands.cmd_projects.ProjectBasedClient")
    def test_list_projects_json_output(self, mock_project_client):
        """Test listing projects with JSON output."""
        mock_client = self._setup_project_client_mock(mock_project_client)
        mock_client.api_request_handler.project_handler.get_projects.return_value = (
            [
                {"id": 1, "name": "Project A", "is_completed": False, "suite_mode": 1},
                {"id": 2, "name": "Project B", "is_completed": True, "suite_mode": 3},
            ],
            "",
        )

        with patch.object(self.environment, "log") as mock_log, patch.object(
            self.environment, "set_parameters"
        ), patch.object(self.environment, "check_for_required_parameters"):
            result = self.runner.invoke(cmd_projects.list, ["--json-output"], obj=self.environment)

            assert result.exit_code == 0
            assert '"id": 1' in result.output
            assert '"name": "Project A"' in result.output

    @mock.patch("trcli.commands.cmd_projects.ProjectBasedClient")
    def test_list_projects_empty_result(self, mock_project_client):
        """Test listing projects when no results are found."""
        mock_client = self._setup_project_client_mock(mock_project_client)
        mock_client.api_request_handler.project_handler.get_projects.return_value = ([], "")

        with patch.object(self.environment, "log") as mock_log, patch.object(
            self.environment, "set_parameters"
        ), patch.object(self.environment, "check_for_required_parameters"):
            result = self.runner.invoke(cmd_projects.list, [], obj=self.environment)

            assert result.exit_code == 0
            assert mock_log.called

    @mock.patch("trcli.commands.cmd_projects.ProjectBasedClient")
    def test_list_projects_api_error(self, mock_project_client):
        """Test handling of API errors when listing projects."""
        mock_client = self._setup_project_client_mock(mock_project_client)
        mock_client.api_request_handler.project_handler.get_projects.return_value = (
            [],
            "Connection error",
        )

        with patch.object(self.environment, "log") as mock_log, patch.object(
            self.environment, "set_parameters"
        ), patch.object(self.environment, "check_for_required_parameters"), patch.object(
            self.environment, "elog"
        ) as mock_elog:
            result = self.runner.invoke(cmd_projects.list, [], obj=self.environment)

            assert result.exit_code == 1
            assert mock_elog.called

    @mock.patch("trcli.commands.cmd_projects.ProjectBasedClient")
    def test_list_projects_with_pagination(self, mock_project_client):
        """Test listing projects with pagination parameters."""
        mock_client = self._setup_project_client_mock(mock_project_client)
        mock_client.api_request_handler.project_handler.get_projects.return_value = (
            [
                {"id": 11, "name": "Project 11", "is_completed": False, "suite_mode": 1},
                {"id": 12, "name": "Project 12", "is_completed": False, "suite_mode": 1},
            ],
            "",
        )

        with patch.object(self.environment, "log") as mock_log, patch.object(
            self.environment, "set_parameters"
        ), patch.object(self.environment, "check_for_required_parameters"):
            result = self.runner.invoke(cmd_projects.list, ["--limit", "2", "--offset", "10"], obj=self.environment)

            assert result.exit_code == 0
            assert mock_log.called
            mock_client.api_request_handler.project_handler.get_projects.assert_called_once_with(
                is_completed=None, limit=2, offset=10
            )
