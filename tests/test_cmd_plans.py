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

    @mock.patch("trcli.commands.cmd_plans.ProjectBasedClient")
    def test_add_plan_success(self, mock_project_client):
        """Test successful plan creation"""
        mock_client = self._setup_project_client_mock(mock_project_client)
        mock_client.api_request_handler.plan_handler.add_plan.return_value = (
            {
                "id": 100,
                "name": "Test Plan",
                "description": "Test Description",
                "url": "https://test.testrail.com/index.php?/plans/view/100",
                "project_id": 1,
                "entries": [],
            },
            "",
        )

        with patch.object(self.environment, "log") as mock_log, patch.object(
            self.environment, "set_parameters"
        ), patch.object(self.environment, "check_for_required_parameters"):
            result = self.runner.invoke(cmd_plans.add, ["--name", "Test Plan"], obj=self.environment)

            assert result.exit_code == 0
            mock_client.resolve_project.assert_called_once()
            mock_client.api_request_handler.plan_handler.add_plan.assert_called_once()

    @mock.patch("trcli.commands.cmd_plans.ProjectBasedClient")
    def test_add_plan_with_description(self, mock_project_client):
        """Test plan creation with description"""
        mock_client = self._setup_project_client_mock(mock_project_client)
        mock_client.api_request_handler.plan_handler.add_plan.return_value = (
            {
                "id": 100,
                "name": "Test Plan",
                "description": "Test Description",
                "url": "https://test.testrail.com/index.php?/plans/view/100",
                "project_id": 1,
                "entries": [],
            },
            "",
        )

        with patch.object(self.environment, "log"), patch.object(self.environment, "set_parameters"), patch.object(
            self.environment, "check_for_required_parameters"
        ):
            result = self.runner.invoke(
                cmd_plans.add, ["--name", "Test Plan", "--description", "Test Description"], obj=self.environment
            )

            assert result.exit_code == 0

    @mock.patch("trcli.commands.cmd_plans.ProjectBasedClient")
    def test_add_plan_with_entries_json(self, mock_project_client):
        """Test plan creation with entries as JSON string"""
        mock_client = self._setup_project_client_mock(mock_project_client)
        mock_client.api_request_handler.plan_handler.add_plan.return_value = (
            {
                "id": 100,
                "name": "Test Plan",
                "url": "https://test.testrail.com/index.php?/plans/view/100",
                "project_id": 1,
                "entries": [
                    {
                        "suite_id": 1,
                        "name": "Test Run",
                        "runs": [
                            {
                                "id": 1,
                                "untested_count": 5,
                                "passed_count": 0,
                                "failed_count": 0,
                                "blocked_count": 0,
                                "retest_count": 0,
                            }
                        ],
                    }
                ],
            },
            "",
        )

        with patch.object(self.environment, "log"), patch.object(self.environment, "set_parameters"), patch.object(
            self.environment, "check_for_required_parameters"
        ):
            result = self.runner.invoke(
                cmd_plans.add, ["--name", "Test Plan", "--entries", '[{"suite_id": 1}]'], obj=self.environment
            )

            assert result.exit_code == 0

    @mock.patch("trcli.commands.cmd_plans.ProjectBasedClient")
    def test_add_plan_api_error(self, mock_project_client):
        """Test handling of API errors when creating plan"""
        mock_client = self._setup_project_client_mock(mock_project_client)
        mock_client.api_request_handler.plan_handler.add_plan.return_value = ({}, "API Error")

        with patch.object(self.environment, "log"), patch.object(self.environment, "set_parameters"), patch.object(
            self.environment, "check_for_required_parameters"
        ), patch.object(self.environment, "elog") as mock_elog:
            result = self.runner.invoke(cmd_plans.add, ["--name", "Test Plan"], obj=self.environment)

            assert result.exit_code == 1
            assert mock_elog.called

    @mock.patch("trcli.commands.cmd_plans.ProjectBasedClient")
    def test_add_plan_json_output(self, mock_project_client):
        """Test plan creation with JSON output"""
        mock_client = self._setup_project_client_mock(mock_project_client)
        mock_client.api_request_handler.plan_handler.add_plan.return_value = (
            {
                "id": 100,
                "name": "Test Plan",
                "url": "https://test.testrail.com/index.php?/plans/view/100",
                "project_id": 1,
            },
            "",
        )

        with patch.object(self.environment, "log"), patch.object(self.environment, "set_parameters"), patch.object(
            self.environment, "check_for_required_parameters"
        ):
            result = self.runner.invoke(cmd_plans.add, ["--name", "Test Plan", "--json-output"], obj=self.environment)

            assert result.exit_code == 0
            assert '"id": 100' in result.output
            assert '"name": "Test Plan"' in result.output

    def test_add_plan_invalid_entries_json(self):
        """Test validation of invalid JSON in entries parameter"""
        result = self.runner.invoke(
            cmd_plans.add, ["--name", "Test Plan", "--entries", "invalid json"], obj=self.environment
        )

        assert result.exit_code == 1

    @mock.patch("trcli.commands.cmd_plans.ProjectBasedClient")
    def test_add_plan_with_dates(self, mock_project_client):
        """Test plan creation with start and due dates in MM/DD/YYYY format"""
        mock_client = self._setup_project_client_mock(mock_project_client)
        mock_client.api_request_handler.plan_handler.add_plan.return_value = (
            {
                "id": 100,
                "name": "Test Plan",
                "url": "https://test.testrail.com/index.php?/plans/view/100",
                "project_id": 1,
                "entries": [],
            },
            "",
        )

        with patch.object(self.environment, "log"), patch.object(self.environment, "set_parameters"), patch.object(
            self.environment, "check_for_required_parameters"
        ):
            result = self.runner.invoke(
                cmd_plans.add,
                ["--name", "Test Plan", "--start-on", "01/15/2022", "--due-on", "02/15/2022"],
                obj=self.environment,
            )

            assert result.exit_code == 0
            # Verify that add_plan was called with converted timestamps
            call_kwargs = mock_client.api_request_handler.plan_handler.add_plan.call_args[1]
            assert call_kwargs["start_on"] is not None
            assert call_kwargs["due_on"] is not None
            # Verify timestamps are integers
            assert isinstance(call_kwargs["start_on"], int)
            assert isinstance(call_kwargs["due_on"], int)

    def test_add_plan_mutually_exclusive_entries(self):
        """Test validation of mutually exclusive --entries and --entries-file"""
        import tempfile
        import os

        # Create a temporary file for entries-file parameter
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            f.write("[]")
            temp_file = f.name

        try:
            with patch.object(self.environment, "check_for_required_parameters"), patch.object(
                self.environment, "elog"
            ) as mock_elog:
                result = self.runner.invoke(
                    cmd_plans.add,
                    ["--name", "Test Plan", "--entries", "[]", "--entries-file", temp_file],
                    obj=self.environment,
                )

                assert result.exit_code == 1
                assert mock_elog.called
                assert "cannot be used together" in str(mock_elog.call_args)
        finally:
            # Clean up temp file
            if os.path.exists(temp_file):
                os.unlink(temp_file)

    @mock.patch("trcli.commands.cmd_plans.ProjectBasedClient")
    def test_add_plan_with_multi_config_entries(self, mock_project_client):
        """Test plan creation with multi-configuration entries"""
        mock_client = self._setup_project_client_mock(mock_project_client)
        mock_client.api_request_handler.plan_handler.add_plan.return_value = (
            {
                "id": 100,
                "name": "Multi-Config Plan",
                "url": "https://test.testrail.com/index.php?/plans/view/100",
                "project_id": 1,
                "entries": [
                    {
                        "suite_id": 1,
                        "name": "Browser Tests",
                        "config_ids": [1, 2],
                        "runs": [
                            {
                                "id": 1,
                                "name": "Browser Tests - Chrome",
                                "config": "Chrome",
                                "untested_count": 5,
                                "passed_count": 0,
                                "failed_count": 0,
                                "blocked_count": 0,
                                "retest_count": 0,
                            },
                            {
                                "id": 2,
                                "name": "Browser Tests - Firefox",
                                "config": "Firefox",
                                "untested_count": 5,
                                "passed_count": 0,
                                "failed_count": 0,
                                "blocked_count": 0,
                                "retest_count": 0,
                            },
                        ],
                    }
                ],
            },
            "",
        )

        entries_json = '[{"suite_id": 1, "name": "Browser Tests", "config_ids": [1, 2], "runs": [{"config_ids": [1, 2], "case_ids": [10, 11, 12]}]}]'

        with patch.object(self.environment, "log"), patch.object(self.environment, "set_parameters"), patch.object(
            self.environment, "check_for_required_parameters"
        ):
            result = self.runner.invoke(
                cmd_plans.add, ["--name", "Multi-Config Plan", "--entries", entries_json], obj=self.environment
            )

            assert result.exit_code == 0
            # Verify that add_plan was called
            mock_client.api_request_handler.plan_handler.add_plan.assert_called_once()
            # Verify the entries structure was passed correctly
            call_kwargs = mock_client.api_request_handler.plan_handler.add_plan.call_args[1]
            assert call_kwargs["entries"] is not None
            assert len(call_kwargs["entries"]) == 1
            assert call_kwargs["entries"][0]["config_ids"] == [1, 2]
            assert call_kwargs["entries"][0]["runs"][0]["config_ids"] == [1, 2]

    @mock.patch("trcli.commands.cmd_plans.ProjectBasedClient")
    def test_add_plan_with_plan_format_json(self, mock_project_client):
        """Test plan creation with plan-format JSON (includes name, description in JSON)"""
        mock_client = self._setup_project_client_mock(mock_project_client)
        mock_client.api_request_handler.plan_handler.add_plan.return_value = (
            {
                "id": 100,
                "name": "Plan from JSON",
                "description": "JSON Description",
                "url": "https://test.testrail.com/index.php?/plans/view/100",
                "project_id": 1,
                "entries": [
                    {
                        "suite_id": 1,
                        "name": "Test Run",
                        "runs": [
                            {
                                "id": 1,
                                "untested_count": 5,
                                "passed_count": 0,
                                "failed_count": 0,
                                "blocked_count": 0,
                                "retest_count": 0,
                            }
                        ],
                    }
                ],
            },
            "",
        )

        # Plan format JSON with name, description, entries
        plan_json = '{"name": "Plan from JSON", "description": "JSON Description", "entries": [{"suite_id": 1, "include_all": true}]}'

        with patch.object(self.environment, "log"), patch.object(self.environment, "set_parameters"), patch.object(
            self.environment, "check_for_required_parameters"
        ):
            result = self.runner.invoke(cmd_plans.add, ["--entries", plan_json], obj=self.environment)

            assert result.exit_code == 0
            # Verify that add_plan was called with values from JSON
            call_kwargs = mock_client.api_request_handler.plan_handler.add_plan.call_args[1]
            assert call_kwargs["name"] == "Plan from JSON"
            assert call_kwargs["description"] == "JSON Description"
            assert call_kwargs["entries"] is not None

    @mock.patch("trcli.commands.cmd_plans.ProjectBasedClient")
    def test_add_plan_cli_overrides_json(self, mock_project_client):
        """Test that CLI arguments override JSON values"""
        mock_client = self._setup_project_client_mock(mock_project_client)
        mock_client.api_request_handler.plan_handler.add_plan.return_value = (
            {
                "id": 100,
                "name": "CLI Plan Name",
                "url": "https://test.testrail.com/index.php?/plans/view/100",
                "project_id": 1,
                "entries": [],
            },
            "",
        )

        # JSON with name, but CLI also provides name
        plan_json = '{"name": "JSON Plan Name", "entries": [{"suite_id": 1, "include_all": true}]}'

        with patch.object(self.environment, "log") as mock_log, patch.object(
            self.environment, "set_parameters"
        ), patch.object(self.environment, "check_for_required_parameters"):
            result = self.runner.invoke(
                cmd_plans.add, ["--name", "CLI Plan Name", "--entries", plan_json], obj=self.environment
            )

            assert result.exit_code == 0
            # Verify CLI name was used
            call_kwargs = mock_client.api_request_handler.plan_handler.add_plan.call_args[1]
            assert call_kwargs["name"] == "CLI Plan Name"
            # Verify warning was logged
            mock_log.assert_any_call("Note: Using --name 'CLI Plan Name' instead of JSON name 'JSON Plan Name'")
