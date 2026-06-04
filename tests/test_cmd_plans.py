import pytest
from unittest import mock
from unittest.mock import MagicMock, patch
from click.testing import CliRunner

from trcli.cli import Environment
from trcli.commands import cmd_plans


class TestCmdPlans:
    """Test class for plans command functionality"""

    def setup_method(self):
        """Set up test environment"""
        self.runner = CliRunner()
        self.environment = Environment(cmd="plans")
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

    @mock.patch("trcli.commands.cmd_plans.ProjectBasedClient")
    def test_get_plan_success(self, mock_project_client):
        """Test successful plan retrieval"""
        mock_client = self._setup_project_client_mock(mock_project_client)
        mock_client.api_request_handler.plan_handler.get_plan.return_value = (
            {
                "id": 10,
                "name": "Release 1.0: Final (all browsers)",
                "description": "Comprehensive release testing",
                "milestone_id": 3,
                "assignedto_id": None,
                "is_completed": False,
                "completed_on": None,
                "passed_count": 445,
                "blocked_count": 99,
                "untested_count": 473,
                "retest_count": 107,
                "failed_count": 56,
                "project_id": 1,
                "created_on": 1646058671,
                "created_by": 1,
                "url": "https://testrail.io/index.php?/plans/view/10",
                "entries": [
                    {
                        "id": "75698796-61d5-46e8-9c14-d334351f12d0",
                        "suite_id": 1,
                        "name": "Browser test",
                        "runs": [
                            {
                                "id": 13,
                                "name": "Browser test",
                                "config": "Chrome",
                                "passed_count": 88,
                                "failed_count": 12,
                            }
                        ],
                    }
                ],
            },
            "",
        )

        with patch.object(self.environment, "log") as mock_log, patch.object(
            self.environment, "set_parameters"
        ), patch.object(self.environment, "check_for_required_parameters"):
            result = self.runner.invoke(cmd_plans.get, ["--plan-id", "10"], obj=self.environment)

            assert result.exit_code == 0
            mock_client.api_request_handler.plan_handler.get_plan.assert_called_once_with(10)
            assert mock_log.called

    @mock.patch("trcli.commands.cmd_plans.ProjectBasedClient")
    def test_get_plan_json_output(self, mock_project_client):
        """Test plan retrieval with JSON output"""
        mock_client = self._setup_project_client_mock(mock_project_client)
        plan_data = {
            "id": 10,
            "name": "Test Plan",
            "description": "Description",
            "project_id": 1,
            "is_completed": False,
            "passed_count": 100,
        }
        mock_client.api_request_handler.plan_handler.get_plan.return_value = (plan_data, "")

        with patch.object(self.environment, "set_parameters"), patch.object(
            self.environment, "check_for_required_parameters"
        ):
            result = self.runner.invoke(cmd_plans.get, ["--plan-id", "10", "--json-output"], obj=self.environment)

            assert result.exit_code == 0
            # Check for prettified JSON (with newlines and indentation)
            assert '"id": 10' in result.output
            assert "\n" in result.output  # Prettified has newlines

    @mock.patch("trcli.commands.cmd_plans.ProjectBasedClient")
    def test_get_plan_show_all_fields(self, mock_project_client):
        """Test plan retrieval with show all fields"""
        mock_client = self._setup_project_client_mock(mock_project_client)
        mock_client.api_request_handler.plan_handler.get_plan.return_value = (
            {
                "id": 10,
                "name": "Test Plan",
                "description": "Plan description",
                "project_id": 1,
                "milestone_id": 2,
                "is_completed": False,
                "passed_count": 100,
                "failed_count": 10,
                "custom_status1_count": 5,
                "custom_status2_count": 0,
                "entries": [],
            },
            "",
        )

        with patch.object(self.environment, "log") as mock_log, patch.object(
            self.environment, "set_parameters"
        ), patch.object(self.environment, "check_for_required_parameters"):
            result = self.runner.invoke(
                cmd_plans.get,
                ["--plan-id", "10", "--show-all-fields"],
                obj=self.environment,
            )

            assert result.exit_code == 0
            assert mock_log.called

    @mock.patch("trcli.commands.cmd_plans.ProjectBasedClient")
    def test_get_plan_api_error(self, mock_project_client):
        """Test plan retrieval with API error"""
        mock_client = self._setup_project_client_mock(mock_project_client)
        mock_client.api_request_handler.plan_handler.get_plan.return_value = ({}, "Plan not found")

        with patch.object(self.environment, "elog") as mock_elog, patch.object(
            self.environment, "set_parameters"
        ), patch.object(self.environment, "check_for_required_parameters"):
            result = self.runner.invoke(cmd_plans.get, ["--plan-id", "999"], obj=self.environment)

            assert result.exit_code == 1
            mock_elog.assert_called_with("Error: Failed to retrieve plan: Plan not found")

    @mock.patch("trcli.commands.cmd_plans.ProjectBasedClient")
    def test_list_plans_success(self, mock_project_client):
        """Test successful plans listing"""
        mock_client = self._setup_project_client_mock(mock_project_client)
        mock_client.api_request_handler.plan_handler.get_plans.return_value = (
            {
                "offset": 0,
                "limit": 250,
                "size": 2,
                "_links": {"next": None, "prev": None},
                "plans": [
                    {
                        "id": 1,
                        "name": "System test 1",
                        "description": "First system test",
                        "project_id": 1,
                        "is_completed": False,
                        "passed_count": 50,
                        "failed_count": 5,
                        "blocked_count": 2,
                        "untested_count": 10,
                    },
                    {
                        "id": 2,
                        "name": "System test 2",
                        "description": "Second system test",
                        "project_id": 1,
                        "is_completed": True,
                        "passed_count": 100,
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
            result = self.runner.invoke(cmd_plans.list, [], obj=self.environment)

            assert result.exit_code == 0
            mock_client.api_request_handler.plan_handler.get_plans.assert_called_once_with(
                project_id=1, limit=250, offset=0
            )
            assert mock_log.called

    @mock.patch("trcli.commands.cmd_plans.ProjectBasedClient")
    def test_list_plans_with_pagination(self, mock_project_client):
        """Test plans listing with pagination parameters"""
        mock_client = self._setup_project_client_mock(mock_project_client)
        mock_client.api_request_handler.plan_handler.get_plans.return_value = (
            {
                "offset": 100,
                "limit": 50,
                "size": 50,
                "_links": {"next": "/api/v2/get_plans/1&offset=150", "prev": "/api/v2/get_plans/1&offset=50"},
                "plans": [
                    {"id": i, "name": f"Plan {i}", "project_id": 1, "is_completed": False, "passed_count": 10}
                    for i in range(100, 150)
                ],
            },
            "",
        )

        with patch.object(self.environment, "log") as mock_log, patch.object(
            self.environment, "set_parameters"
        ), patch.object(self.environment, "check_for_required_parameters"):
            result = self.runner.invoke(cmd_plans.list, ["--offset", "100", "--limit", "50"], obj=self.environment)

            assert result.exit_code == 0
            mock_client.api_request_handler.plan_handler.get_plans.assert_called_once_with(
                project_id=1, limit=50, offset=100
            )

    @mock.patch("trcli.commands.cmd_plans.ProjectBasedClient")
    def test_list_plans_json_output(self, mock_project_client):
        """Test plans listing with JSON output"""
        mock_client = self._setup_project_client_mock(mock_project_client)
        response_data = {
            "offset": 0,
            "limit": 250,
            "size": 1,
            "plans": [{"id": 1, "name": "Test", "project_id": 1, "is_completed": False}],
        }
        mock_client.api_request_handler.plan_handler.get_plans.return_value = (response_data, "")

        with patch.object(self.environment, "set_parameters"), patch.object(
            self.environment, "check_for_required_parameters"
        ):
            result = self.runner.invoke(cmd_plans.list, ["--json-output"], obj=self.environment)

            assert result.exit_code == 0
            # Check for prettified JSON (with newlines and indentation)
            assert '"offset": 0' in result.output
            assert "\n" in result.output  # Prettified has newlines

    @mock.patch("trcli.commands.cmd_plans.ProjectBasedClient")
    def test_list_plans_show_all_fields(self, mock_project_client):
        """Test plans listing with show all fields"""
        mock_client = self._setup_project_client_mock(mock_project_client)
        mock_client.api_request_handler.plan_handler.get_plans.return_value = (
            {
                "offset": 0,
                "limit": 250,
                "size": 1,
                "plans": [
                    {
                        "id": 1,
                        "name": "Test Plan",
                        "description": "Description",
                        "project_id": 1,
                        "milestone_id": 2,
                        "is_completed": False,
                        "passed_count": 50,
                    }
                ],
            },
            "",
        )

        with patch.object(self.environment, "log") as mock_log, patch.object(
            self.environment, "set_parameters"
        ), patch.object(self.environment, "check_for_required_parameters"):
            result = self.runner.invoke(cmd_plans.list, ["--show-all-fields"], obj=self.environment)

            assert result.exit_code == 0
            assert mock_log.called

    @mock.patch("trcli.commands.cmd_plans.ProjectBasedClient")
    def test_list_plans_empty_result(self, mock_project_client):
        """Test plans listing with empty result"""
        mock_client = self._setup_project_client_mock(mock_project_client)
        mock_client.api_request_handler.plan_handler.get_plans.return_value = (
            {"offset": 0, "limit": 250, "size": 0, "plans": []},
            "",
        )

        with patch.object(self.environment, "log") as mock_log, patch.object(
            self.environment, "set_parameters"
        ), patch.object(self.environment, "check_for_required_parameters"):
            result = self.runner.invoke(cmd_plans.list, [], obj=self.environment)

            assert result.exit_code == 0
            mock_log.assert_any_call("No plans found.")

    @mock.patch("trcli.commands.cmd_plans.ProjectBasedClient")
    def test_list_plans_api_error(self, mock_project_client):
        """Test plans listing with API error"""
        mock_client = self._setup_project_client_mock(mock_project_client)
        mock_client.api_request_handler.plan_handler.get_plans.return_value = ({}, "Project not found")

        with patch.object(self.environment, "elog") as mock_elog, patch.object(
            self.environment, "set_parameters"
        ), patch.object(self.environment, "check_for_required_parameters"):
            result = self.runner.invoke(cmd_plans.list, [], obj=self.environment)

            assert result.exit_code == 1
            mock_elog.assert_called_with("Error: Failed to retrieve plans: Project not found")

    @mock.patch("trcli.commands.cmd_plans.ProjectBasedClient")
    def test_list_plans_with_next_link(self, mock_project_client):
        """Test plans listing shows pagination hint when next link is present"""
        mock_client = self._setup_project_client_mock(mock_project_client)
        mock_client.api_request_handler.plan_handler.get_plans.return_value = (
            {
                "offset": 0,
                "limit": 250,
                "size": 250,
                "_links": {"next": "/api/v2/get_plans/1&offset=250", "prev": None},
                "plans": [
                    {"id": i, "name": f"Plan {i}", "project_id": 1, "is_completed": False, "passed_count": 10}
                    for i in range(1, 251)
                ],
            },
            "",
        )

        with patch.object(self.environment, "log") as mock_log, patch.object(
            self.environment, "set_parameters"
        ), patch.object(self.environment, "check_for_required_parameters"):
            result = self.runner.invoke(cmd_plans.list, [], obj=self.environment)

            assert result.exit_code == 0
            log_calls = [str(call) for call in mock_log.call_args_list]
            pagination_hint_found = any("More results available" in str(call) for call in log_calls)
            assert pagination_hint_found

    @mock.patch("trcli.commands.cmd_plans.ProjectBasedClient")
    def test_get_plan_with_project_id_from_config(self, mock_project_client):
        """Test plan retrieval uses project_id from environment when not provided"""
        mock_client = self._setup_project_client_mock(mock_project_client, project_id=42)
        plan_data = {"id": 10, "name": "Test Plan", "description": "Desc", "project_id": 42, "is_completed": False}
        mock_client.api_request_handler.plan_handler.get_plan.return_value = (plan_data, "")

        self.environment.project_id = 42

        with patch.object(self.environment, "log") as mock_log, patch.object(
            self.environment, "set_parameters"
        ), patch.object(self.environment, "check_for_required_parameters"):
            result = self.runner.invoke(cmd_plans.get, ["--plan-id", "10"], obj=self.environment)

            assert result.exit_code == 0
            mock_client.api_request_handler.plan_handler.get_plan.assert_called_once_with(10)

    @mock.patch("trcli.commands.cmd_plans.ProjectBasedClient")
    def test_list_plans_with_project_id_from_config(self, mock_project_client):
        """Test plans listing uses project_id from environment when not provided"""
        mock_client = self._setup_project_client_mock(mock_project_client, project_id=99)
        mock_client.api_request_handler.plan_handler.get_plans.return_value = (
            {"offset": 0, "limit": 250, "size": 1, "plans": [{"id": 1, "name": "Test", "project_id": 99}]},
            "",
        )

        self.environment.project_id = 99

        with patch.object(self.environment, "log") as mock_log, patch.object(
            self.environment, "set_parameters"
        ), patch.object(self.environment, "check_for_required_parameters"):
            result = self.runner.invoke(cmd_plans.list, [], obj=self.environment)

            assert result.exit_code == 0
            mock_client.api_request_handler.plan_handler.get_plans.assert_called_once_with(
                project_id=99, limit=250, offset=0
            )

    @mock.patch("trcli.commands.cmd_plans.ProjectBasedClient")
    def test_get_plan_with_project_name(self, mock_project_client):
        """Test plan retrieval with project name from config"""
        mock_client = self._setup_project_client_mock(mock_project_client, project_id=42)
        plan_data = {"id": 10, "name": "Test Plan", "description": "Desc", "project_id": 42, "is_completed": False}
        mock_client.api_request_handler.plan_handler.get_plan.return_value = (plan_data, "")

        # Set project name in environment (as if from config file)
        self.environment.project = "TRCLI Test Project"
        self.environment.project_id = None  # No project_id, only name

        with patch.object(self.environment, "log") as mock_log, patch.object(
            self.environment, "set_parameters"
        ), patch.object(self.environment, "check_for_required_parameters"):
            result = self.runner.invoke(cmd_plans.get, ["--plan-id", "10"], obj=self.environment)

            assert result.exit_code == 0
            # Verify resolve_project was called to convert name to ID
            mock_client.resolve_project.assert_called_once()
            mock_client.api_request_handler.plan_handler.get_plan.assert_called_once_with(10)

    @mock.patch("trcli.commands.cmd_plans.ProjectBasedClient")
    def test_list_plans_with_project_name(self, mock_project_client):
        """Test plans listing with project name from config"""
        mock_client = self._setup_project_client_mock(mock_project_client, project_id=99)
        mock_client.api_request_handler.plan_handler.get_plans.return_value = (
            {"offset": 0, "limit": 250, "size": 1, "plans": [{"id": 1, "name": "Test", "project_id": 99}]},
            "",
        )

        # Set project name in environment (as if from config file)
        self.environment.project = "TRCLI Test Project"
        self.environment.project_id = None  # No project_id, only name

        with patch.object(self.environment, "log") as mock_log, patch.object(
            self.environment, "set_parameters"
        ), patch.object(self.environment, "check_for_required_parameters"):
            result = self.runner.invoke(cmd_plans.list, [], obj=self.environment)

            assert result.exit_code == 0
            # Verify resolve_project was called to convert name to ID
            mock_client.resolve_project.assert_called_once()
            mock_client.api_request_handler.plan_handler.get_plans.assert_called_once_with(
                project_id=99, limit=250, offset=0
            )
