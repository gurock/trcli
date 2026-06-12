import pytest
from unittest import mock
from unittest.mock import MagicMock, patch
from click.testing import CliRunner

from trcli.cli import Environment
from trcli.commands import cmd_runs


class TestCmdRuns:
    """Test class for runs command functionality"""

    def setup_method(self):
        """Set up test environment"""
        self.runner = CliRunner()
        self.environment = Environment(cmd="runs")
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

    @mock.patch("trcli.commands.cmd_runs.ProjectBasedClient")
    def test_get_run_success(self, mock_project_client):
        """Test successful run retrieval"""
        mock_client = self._setup_project_client_mock(mock_project_client)
        mock_client.api_request_handler.run_handler.get_run.return_value = (
            {
                "id": 81,
                "name": "File Formats",
                "description": "Test file format handling",
                "suite_id": 4,
                "project_id": 1,
                "is_completed": False,
                "completed_on": None,
                "passed_count": 2,
                "failed_count": 2,
                "blocked_count": 0,
                "retest_count": 1,
                "untested_count": 3,
                "config": "Firefox, Ubuntu 12",
                "config_ids": [2, 6],
                "milestone_id": 7,
                "plan_id": 80,
                "assignedto_id": 6,
                "refs": "SAN-1",
                "include_all": False,
                "created_by": 1,
                "created_on": 1393845644,
                "url": "http://test.testrail.com/index.php?/runs/view/81",
            },
            "",
        )

        with patch.object(self.environment, "log") as mock_log, patch.object(
            self.environment, "set_parameters"
        ), patch.object(self.environment, "check_for_required_parameters"):
            result = self.runner.invoke(cmd_runs.get, ["--run-id", "81"], obj=self.environment)

            assert result.exit_code == 0
            mock_client.api_request_handler.run_handler.get_run.assert_called_once_with(81)
            assert mock_log.called

    @mock.patch("trcli.commands.cmd_runs.ProjectBasedClient")
    def test_get_run_json_output(self, mock_project_client):
        """Test run retrieval with JSON output"""
        mock_client = self._setup_project_client_mock(mock_project_client)
        run_data = {
            "id": 81,
            "name": "File Formats",
            "suite_id": 4,
            "is_completed": False,
            "passed_count": 2,
            "failed_count": 1,
        }
        mock_client.api_request_handler.run_handler.get_run.return_value = (run_data, "")

        with patch.object(self.environment, "set_parameters"), patch.object(
            self.environment, "check_for_required_parameters"
        ):
            result = self.runner.invoke(cmd_runs.get, ["--run-id", "81", "--json-output"], obj=self.environment)

            assert result.exit_code == 0
            # Check for prettified JSON (with newlines and indentation)
            assert '"id": 81' in result.output
            assert "\n" in result.output  # Prettified has newlines

    @mock.patch("trcli.commands.cmd_runs.ProjectBasedClient")
    def test_get_run_show_all_fields(self, mock_project_client):
        """Test run retrieval with show all fields"""
        mock_client = self._setup_project_client_mock(mock_project_client)
        mock_client.api_request_handler.run_handler.get_run.return_value = (
            {
                "id": 81,
                "name": "File Formats",
                "description": "Test description",
                "suite_id": 4,
                "project_id": 1,
                "is_completed": False,
                "passed_count": 2,
                "failed_count": 1,
                "blocked_count": 0,
                "retest_count": 0,
                "untested_count": 3,
                "config": "Firefox, Ubuntu 12",
                "config_ids": [2, 6],
                "milestone_id": 7,
                "plan_id": 80,
                "assignedto_id": 6,
                "refs": "SAN-1",
            },
            "",
        )

        with patch.object(self.environment, "log") as mock_log, patch.object(
            self.environment, "set_parameters"
        ), patch.object(self.environment, "check_for_required_parameters"):
            result = self.runner.invoke(cmd_runs.get, ["--run-id", "81", "--show-all-fields"], obj=self.environment)

            assert result.exit_code == 0
            assert mock_log.called

    @mock.patch("trcli.commands.cmd_runs.ProjectBasedClient")
    def test_get_run_api_error(self, mock_project_client):
        """Test run retrieval with API error"""
        mock_client = self._setup_project_client_mock(mock_project_client)
        mock_client.api_request_handler.run_handler.get_run.return_value = ({}, "Run not found")

        with patch.object(self.environment, "elog") as mock_elog, patch.object(
            self.environment, "set_parameters"
        ), patch.object(self.environment, "check_for_required_parameters"):
            result = self.runner.invoke(cmd_runs.get, ["--run-id", "999"], obj=self.environment)

            assert result.exit_code == 1
            mock_elog.assert_called_with("Error: Failed to retrieve run: Run not found")

    @mock.patch("trcli.commands.cmd_runs.ProjectBasedClient")
    def test_list_runs_success(self, mock_project_client):
        """Test successful runs listing"""
        mock_client = self._setup_project_client_mock(mock_project_client)
        mock_client.api_request_handler.run_handler.get_runs.return_value = (
            {
                "offset": 0,
                "limit": 250,
                "size": 2,
                "_links": {"next": None, "prev": None},
                "runs": [
                    {
                        "id": 81,
                        "name": "File Formats",
                        "suite_id": 4,
                        "is_completed": False,
                        "passed_count": 2,
                        "failed_count": 2,
                        "blocked_count": 0,
                        "untested_count": 3,
                    },
                    {
                        "id": 82,
                        "name": "System Tests",
                        "suite_id": 5,
                        "is_completed": True,
                        "passed_count": 10,
                        "failed_count": 0,
                        "blocked_count": 0,
                        "untested_count": 0,
                    },
                ],
            },
            "",
        )

        with patch.object(self.environment, "log") as mock_log, patch.object(
            self.environment, "set_parameters"
        ), patch.object(self.environment, "check_for_required_parameters"):
            result = self.runner.invoke(cmd_runs.list, [], obj=self.environment)

            assert result.exit_code == 0
            mock_client.api_request_handler.run_handler.get_runs.assert_called_once_with(
                project_id=1, limit=250, offset=0
            )
            assert mock_log.called

    @mock.patch("trcli.commands.cmd_runs.ProjectBasedClient")
    def test_list_runs_with_pagination(self, mock_project_client):
        """Test runs listing with pagination parameters"""
        mock_client = self._setup_project_client_mock(mock_project_client)
        mock_client.api_request_handler.run_handler.get_runs.return_value = (
            {
                "offset": 100,
                "limit": 50,
                "size": 50,
                "_links": {
                    "next": "/api/v2/get_runs/1&offset=150",
                    "prev": "/api/v2/get_runs/1&offset=50",
                },
                "runs": [{"id": i, "name": f"Run {i}", "suite_id": 1, "is_completed": False} for i in range(100, 150)],
            },
            "",
        )

        with patch.object(self.environment, "log") as mock_log, patch.object(
            self.environment, "set_parameters"
        ), patch.object(self.environment, "check_for_required_parameters"):
            result = self.runner.invoke(cmd_runs.list, ["--offset", "100", "--limit", "50"], obj=self.environment)

            assert result.exit_code == 0
            mock_client.api_request_handler.run_handler.get_runs.assert_called_once_with(
                project_id=1, limit=50, offset=100
            )

    @mock.patch("trcli.commands.cmd_runs.ProjectBasedClient")
    def test_list_runs_json_output(self, mock_project_client):
        """Test runs listing with JSON output"""
        mock_client = self._setup_project_client_mock(mock_project_client)
        response_data = {
            "offset": 0,
            "limit": 250,
            "size": 1,
            "runs": [{"id": 81, "name": "Test", "suite_id": 1, "is_completed": False}],
        }
        mock_client.api_request_handler.run_handler.get_runs.return_value = (response_data, "")

        with patch.object(self.environment, "set_parameters"), patch.object(
            self.environment, "check_for_required_parameters"
        ):
            result = self.runner.invoke(cmd_runs.list, ["--json-output"], obj=self.environment)

            assert result.exit_code == 0
            # Check for prettified JSON (with newlines and indentation)
            assert '"offset": 0' in result.output
            assert "\n" in result.output  # Prettified has newlines

    @mock.patch("trcli.commands.cmd_runs.ProjectBasedClient")
    def test_list_runs_show_all_fields(self, mock_project_client):
        """Test runs listing with show all fields"""
        mock_client = self._setup_project_client_mock(mock_project_client)
        mock_client.api_request_handler.run_handler.get_runs.return_value = (
            {
                "offset": 0,
                "limit": 250,
                "size": 1,
                "runs": [
                    {
                        "id": 81,
                        "name": "File Formats",
                        "description": "Test description",
                        "suite_id": 4,
                        "is_completed": False,
                        "passed_count": 2,
                        "failed_count": 1,
                        "blocked_count": 0,
                        "untested_count": 3,
                    }
                ],
            },
            "",
        )

        with patch.object(self.environment, "log") as mock_log, patch.object(
            self.environment, "set_parameters"
        ), patch.object(self.environment, "check_for_required_parameters"):
            result = self.runner.invoke(cmd_runs.list, ["--show-all-fields"], obj=self.environment)

            assert result.exit_code == 0
            assert mock_log.called

    @mock.patch("trcli.commands.cmd_runs.ProjectBasedClient")
    def test_list_runs_empty_result(self, mock_project_client):
        """Test runs listing with empty result"""
        mock_client = self._setup_project_client_mock(mock_project_client)
        mock_client.api_request_handler.run_handler.get_runs.return_value = (
            {"offset": 0, "limit": 250, "size": 0, "runs": []},
            "",
        )

        with patch.object(self.environment, "log") as mock_log, patch.object(
            self.environment, "set_parameters"
        ), patch.object(self.environment, "check_for_required_parameters"):
            result = self.runner.invoke(cmd_runs.list, [], obj=self.environment)

            assert result.exit_code == 0
            mock_log.assert_any_call("No runs found.")

    @mock.patch("trcli.commands.cmd_runs.ProjectBasedClient")
    def test_list_runs_api_error(self, mock_project_client):
        """Test runs listing with API error"""
        mock_client = self._setup_project_client_mock(mock_project_client)
        mock_client.api_request_handler.run_handler.get_runs.return_value = ({}, "Project not found")

        with patch.object(self.environment, "elog") as mock_elog, patch.object(
            self.environment, "set_parameters"
        ), patch.object(self.environment, "check_for_required_parameters"):
            result = self.runner.invoke(cmd_runs.list, [], obj=self.environment)

            assert result.exit_code == 1
            mock_elog.assert_called_with("Error: Failed to retrieve runs: Project not found")

    @mock.patch("trcli.commands.cmd_runs.ProjectBasedClient")
    def test_list_runs_with_next_link(self, mock_project_client):
        """Test runs listing shows pagination hint when next link is present"""
        mock_client = self._setup_project_client_mock(mock_project_client)
        mock_client.api_request_handler.run_handler.get_runs.return_value = (
            {
                "offset": 0,
                "limit": 250,
                "size": 250,
                "_links": {"next": "/api/v2/get_runs/1&offset=250", "prev": None},
                "runs": [{"id": i, "name": f"Run {i}", "suite_id": 1, "is_completed": False} for i in range(1, 251)],
            },
            "",
        )

        with patch.object(self.environment, "log") as mock_log, patch.object(
            self.environment, "set_parameters"
        ), patch.object(self.environment, "check_for_required_parameters"):
            result = self.runner.invoke(cmd_runs.list, [], obj=self.environment)

            assert result.exit_code == 0
            log_calls = [str(call) for call in mock_log.call_args_list]
            pagination_hint_found = any("More results available" in str(call) for call in log_calls)
            assert pagination_hint_found

    @mock.patch("trcli.commands.cmd_runs.ProjectBasedClient")
    def test_get_run_with_project_id_from_config(self, mock_project_client):
        """Test run retrieval uses project_id from environment when not provided"""
        mock_client = self._setup_project_client_mock(mock_project_client, project_id=42)
        run_data = {"id": 81, "name": "File Formats", "suite_id": 4, "is_completed": False}
        mock_client.api_request_handler.run_handler.get_run.return_value = (run_data, "")

        self.environment.project_id = 42

        with patch.object(self.environment, "log") as mock_log, patch.object(
            self.environment, "set_parameters"
        ), patch.object(self.environment, "check_for_required_parameters"):
            result = self.runner.invoke(cmd_runs.get, ["--run-id", "81"], obj=self.environment)

            assert result.exit_code == 0
            mock_client.api_request_handler.run_handler.get_run.assert_called_once_with(81)

    @mock.patch("trcli.commands.cmd_runs.ProjectBasedClient")
    def test_list_runs_with_project_id_from_config(self, mock_project_client):
        """Test runs listing uses project_id from environment when not provided"""
        mock_client = self._setup_project_client_mock(mock_project_client, project_id=99)
        mock_client.api_request_handler.run_handler.get_runs.return_value = (
            {"offset": 0, "limit": 250, "size": 1, "runs": [{"id": 81, "name": "Test", "suite_id": 1}]},
            "",
        )

        self.environment.project_id = 99

        with patch.object(self.environment, "log") as mock_log, patch.object(
            self.environment, "set_parameters"
        ), patch.object(self.environment, "check_for_required_parameters"):
            result = self.runner.invoke(cmd_runs.list, [], obj=self.environment)

            assert result.exit_code == 0
            mock_client.api_request_handler.run_handler.get_runs.assert_called_once_with(
                project_id=99, limit=250, offset=0
            )

    @mock.patch("trcli.commands.cmd_runs.ProjectBasedClient")
    def test_get_run_with_project_name(self, mock_project_client):
        """Test run retrieval with project name from config"""
        mock_client = self._setup_project_client_mock(mock_project_client, project_id=42)
        run_data = {"id": 81, "name": "File Formats", "suite_id": 4, "is_completed": False}
        mock_client.api_request_handler.run_handler.get_run.return_value = (run_data, "")

        # Set project name in environment (as if from config file)
        self.environment.project = "TRCLI Test Project"
        self.environment.project_id = None  # No project_id, only name

        with patch.object(self.environment, "log") as mock_log, patch.object(
            self.environment, "set_parameters"
        ), patch.object(self.environment, "check_for_required_parameters"):
            result = self.runner.invoke(cmd_runs.get, ["--run-id", "81"], obj=self.environment)

            assert result.exit_code == 0
            # Verify resolve_project was called to convert name to ID
            mock_client.resolve_project.assert_called_once()
            mock_client.api_request_handler.run_handler.get_run.assert_called_once_with(81)

    @mock.patch("trcli.commands.cmd_runs.ProjectBasedClient")
    def test_list_runs_with_project_name(self, mock_project_client):
        """Test runs listing with project name from config"""
        mock_client = self._setup_project_client_mock(mock_project_client, project_id=99)
        mock_client.api_request_handler.run_handler.get_runs.return_value = (
            {"offset": 0, "limit": 250, "size": 1, "runs": [{"id": 81, "name": "Test", "suite_id": 1}]},
            "",
        )

        # Set project name in environment (as if from config file)
        self.environment.project = "TRCLI Test Project"
        self.environment.project_id = None  # No project_id, only name

        with patch.object(self.environment, "log") as mock_log, patch.object(
            self.environment, "set_parameters"
        ), patch.object(self.environment, "check_for_required_parameters"):
            result = self.runner.invoke(cmd_runs.list, [], obj=self.environment)

            assert result.exit_code == 0
            # Verify resolve_project was called to convert name to ID
            mock_client.resolve_project.assert_called_once()
            mock_client.api_request_handler.run_handler.get_runs.assert_called_once_with(
                project_id=99, limit=250, offset=0
            )
