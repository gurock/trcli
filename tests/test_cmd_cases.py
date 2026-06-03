import pytest
from unittest import mock
from unittest.mock import MagicMock, patch
from click.testing import CliRunner

from trcli.cli import Environment
from trcli.commands import cmd_cases


class TestCmdCases:
    """Test class for cases command functionality"""

    def setup_method(self):
        """Set up test environment"""
        self.runner = CliRunner()
        self.environment = Environment(cmd="cases")
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

    @mock.patch("trcli.commands.cmd_cases.ProjectBasedClient")
    def test_get_case_success(self, mock_project_client):
        """Test successful case retrieval"""
        mock_client = self._setup_project_client_mock(mock_project_client)
        mock_client.api_request_handler.case_handler.get_case.return_value = (
            {
                "id": 123,
                "title": "Test Case Title",
                "section_id": 1,
                "suite_id": 2,
                "template_id": 1,
                "type_id": 1,
                "priority_id": 2,
                "refs": "JIRA-123",
                "created_by": 1,
                "created_on": 1234567890,
                "updated_by": 1,
                "updated_on": 1234567890,
                "labels": [{"id": 1, "title": "label1"}],
                "custom_steps": "Step 1\nStep 2",
            },
            "",
        )

        with patch.object(self.environment, "log") as mock_log, patch.object(
            self.environment, "set_parameters"
        ), patch.object(self.environment, "check_for_required_parameters"):
            result = self.runner.invoke(cmd_cases.get, ["--case-id", "123"], obj=self.environment)

            assert result.exit_code == 0
            mock_client.api_request_handler.case_handler.get_case.assert_called_once_with(123)
            assert mock_log.called

    @mock.patch("trcli.commands.cmd_cases.ProjectBasedClient")
    def test_get_case_json_output(self, mock_project_client):
        """Test case retrieval with JSON output"""
        mock_client = self._setup_project_client_mock(mock_project_client)
        case_data = {"id": 123, "title": "Test Case", "section_id": 1}
        mock_client.api_request_handler.case_handler.get_case.return_value = (case_data, "")

        with patch.object(self.environment, "set_parameters"), patch.object(
            self.environment, "check_for_required_parameters"
        ):
            result = self.runner.invoke(cmd_cases.get, ["--case-id", "123", "--json-output"], obj=self.environment)

            assert result.exit_code == 0
            # Check for prettified JSON (with newlines and indentation)
            assert '"id": 123' in result.output
            assert "\n" in result.output  # Prettified has newlines

    @mock.patch("trcli.commands.cmd_cases.ProjectBasedClient")
    def test_get_case_show_all_fields(self, mock_project_client):
        """Test case retrieval with show all fields"""
        mock_client = self._setup_project_client_mock(mock_project_client)
        mock_client.api_request_handler.case_handler.get_case.return_value = (
            {
                "id": 123,
                "title": "Test Case",
                "custom_field1": "value1",
                "custom_field2": "value2",
                "labels": [{"id": 1, "title": "label1"}, {"id": 2, "title": "label2"}],
            },
            "",
        )

        with patch.object(self.environment, "log") as mock_log, patch.object(
            self.environment, "set_parameters"
        ), patch.object(self.environment, "check_for_required_parameters"):
            result = self.runner.invoke(
                cmd_cases.get,
                ["--case-id", "123", "--show-all-fields"],
                obj=self.environment,
            )

            assert result.exit_code == 0
            assert mock_log.called

    @mock.patch("trcli.commands.cmd_cases.ProjectBasedClient")
    def test_get_case_api_error(self, mock_project_client):
        """Test case retrieval with API error"""
        mock_client = self._setup_project_client_mock(mock_project_client)
        mock_client.api_request_handler.case_handler.get_case.return_value = ({}, "Case not found")

        with patch.object(self.environment, "elog") as mock_elog, patch.object(
            self.environment, "set_parameters"
        ), patch.object(self.environment, "check_for_required_parameters"):
            result = self.runner.invoke(cmd_cases.get, ["--case-id", "999"], obj=self.environment)

            assert result.exit_code == 1
            mock_elog.assert_called_with("Error: Failed to retrieve case: Case not found")

    @mock.patch("trcli.commands.cmd_cases.ProjectBasedClient")
    def test_list_cases_success(self, mock_project_client):
        """Test successful cases listing"""
        mock_client = self._setup_project_client_mock(mock_project_client)
        mock_client.api_request_handler.case_handler.get_cases.return_value = (
            {
                "offset": 0,
                "limit": 250,
                "size": 2,
                "_links": {"next": None, "prev": None},
                "cases": [
                    {
                        "id": 1,
                        "title": "Case 1",
                        "section_id": 1,
                        "suite_id": 1,
                        "priority_id": 2,
                        "type_id": 1,
                        "labels": [],
                    },
                    {
                        "id": 2,
                        "title": "Case 2",
                        "section_id": 1,
                        "suite_id": 1,
                        "priority_id": 3,
                        "type_id": 1,
                        "labels": [{"id": 1, "title": "automated"}],
                    },
                ],
            },
            "",
        )

        with patch.object(self.environment, "log") as mock_log, patch.object(
            self.environment, "set_parameters"
        ), patch.object(self.environment, "check_for_required_parameters"):
            result = self.runner.invoke(cmd_cases.list, [], obj=self.environment)

            assert result.exit_code == 0
            mock_client.api_request_handler.case_handler.get_cases.assert_called_once_with(
                project_id=1, suite_id=None, priority_id=None, filter_text=None, limit=250, offset=0
            )
            assert mock_log.called

    @mock.patch("trcli.commands.cmd_cases.ProjectBasedClient")
    def test_list_cases_with_filters(self, mock_project_client):
        """Test cases listing with filters"""
        mock_client = self._setup_project_client_mock(mock_project_client)
        mock_client.api_request_handler.case_handler.get_cases.return_value = (
            {"offset": 0, "limit": 250, "size": 0, "_links": {}, "cases": []},
            "",
        )

        with patch.object(self.environment, "log") as mock_log, patch.object(
            self.environment, "set_parameters"
        ), patch.object(self.environment, "check_for_required_parameters"):
            result = self.runner.invoke(
                cmd_cases.list,
                ["--suite-id", "2", "--priority-id", "3,4", "--filter", "login"],
                obj=self.environment,
            )

            assert result.exit_code == 0
            mock_client.api_request_handler.case_handler.get_cases.assert_called_once_with(
                project_id=1, suite_id=2, priority_id="3,4", filter_text="login", limit=250, offset=0
            )

    @mock.patch("trcli.commands.cmd_cases.ProjectBasedClient")
    def test_list_cases_with_pagination(self, mock_project_client):
        """Test cases listing with pagination parameters"""
        mock_client = self._setup_project_client_mock(mock_project_client)
        mock_client.api_request_handler.case_handler.get_cases.return_value = (
            {
                "offset": 100,
                "limit": 50,
                "size": 50,
                "_links": {"next": "/api/v2/get_cases/1&offset=150", "prev": "/api/v2/get_cases/1&offset=50"},
                "cases": [{"id": i, "title": f"Case {i}"} for i in range(100, 150)],
            },
            "",
        )

        with patch.object(self.environment, "log") as mock_log, patch.object(
            self.environment, "set_parameters"
        ), patch.object(self.environment, "check_for_required_parameters"):
            result = self.runner.invoke(cmd_cases.list, ["--offset", "100", "--limit", "50"], obj=self.environment)

            assert result.exit_code == 0
            mock_client.api_request_handler.case_handler.get_cases.assert_called_once_with(
                project_id=1, suite_id=None, priority_id=None, filter_text=None, limit=50, offset=100
            )

    @mock.patch("trcli.commands.cmd_cases.ProjectBasedClient")
    def test_list_cases_json_output(self, mock_project_client):
        """Test cases listing with JSON output"""
        mock_client = self._setup_project_client_mock(mock_project_client)
        response_data = {"offset": 0, "limit": 250, "size": 1, "cases": [{"id": 1, "title": "Test"}]}
        mock_client.api_request_handler.case_handler.get_cases.return_value = (response_data, "")

        with patch.object(self.environment, "set_parameters"), patch.object(
            self.environment, "check_for_required_parameters"
        ):
            result = self.runner.invoke(cmd_cases.list, ["--json-output"], obj=self.environment)

            assert result.exit_code == 0
            # Check for prettified JSON (with newlines and indentation)
            assert '"offset": 0' in result.output
            assert "\n" in result.output  # Prettified has newlines

    @mock.patch("trcli.commands.cmd_cases.ProjectBasedClient")
    def test_list_cases_show_all_fields(self, mock_project_client):
        """Test cases listing with show all fields"""
        mock_client = self._setup_project_client_mock(mock_project_client)
        mock_client.api_request_handler.case_handler.get_cases.return_value = (
            {
                "offset": 0,
                "limit": 250,
                "size": 1,
                "cases": [
                    {
                        "id": 1,
                        "title": "Test Case",
                        "custom_field1": "value1",
                        "custom_field2": "value2",
                        "labels": [{"id": 1, "title": "label1"}],
                    }
                ],
            },
            "",
        )

        with patch.object(self.environment, "log") as mock_log, patch.object(
            self.environment, "set_parameters"
        ), patch.object(self.environment, "check_for_required_parameters"):
            result = self.runner.invoke(cmd_cases.list, ["--show-all-fields"], obj=self.environment)

            assert result.exit_code == 0
            assert mock_log.called

    @mock.patch("trcli.commands.cmd_cases.ProjectBasedClient")
    def test_list_cases_empty_result(self, mock_project_client):
        """Test cases listing with empty result"""
        mock_client = self._setup_project_client_mock(mock_project_client)
        mock_client.api_request_handler.case_handler.get_cases.return_value = (
            {"offset": 0, "limit": 250, "size": 0, "cases": []},
            "",
        )

        with patch.object(self.environment, "log") as mock_log, patch.object(
            self.environment, "set_parameters"
        ), patch.object(self.environment, "check_for_required_parameters"):
            result = self.runner.invoke(cmd_cases.list, [], obj=self.environment)

            assert result.exit_code == 0
            mock_log.assert_any_call("No cases found.")

    @mock.patch("trcli.commands.cmd_cases.ProjectBasedClient")
    def test_list_cases_api_error(self, mock_project_client):
        """Test cases listing with API error"""
        mock_client = self._setup_project_client_mock(mock_project_client)
        mock_client.api_request_handler.case_handler.get_cases.return_value = ({}, "Project not found")

        with patch.object(self.environment, "elog") as mock_elog, patch.object(
            self.environment, "set_parameters"
        ), patch.object(self.environment, "check_for_required_parameters"):
            result = self.runner.invoke(cmd_cases.list, [], obj=self.environment)

            assert result.exit_code == 1
            mock_elog.assert_called_with("Error: Failed to retrieve cases: Project not found")

    @mock.patch("trcli.commands.cmd_cases.ProjectBasedClient")
    def test_list_cases_with_next_link(self, mock_project_client):
        """Test cases listing shows pagination hint when next link is present"""
        mock_client = self._setup_project_client_mock(mock_project_client)
        mock_client.api_request_handler.case_handler.get_cases.return_value = (
            {
                "offset": 0,
                "limit": 250,
                "size": 250,
                "_links": {"next": "/api/v2/get_cases/1&offset=250", "prev": None},
                "cases": [{"id": i, "title": f"Case {i}"} for i in range(1, 251)],
            },
            "",
        )

        with patch.object(self.environment, "log") as mock_log, patch.object(
            self.environment, "set_parameters"
        ), patch.object(self.environment, "check_for_required_parameters"):
            result = self.runner.invoke(cmd_cases.list, [], obj=self.environment)

            assert result.exit_code == 0
            log_calls = [str(call) for call in mock_log.call_args_list]
            pagination_hint_found = any("More results available" in str(call) for call in log_calls)
            assert pagination_hint_found

    @mock.patch("trcli.commands.cmd_cases.ProjectBasedClient")
    def test_list_cases_with_labels_display(self, mock_project_client):
        """Test cases listing displays labels correctly"""
        mock_client = self._setup_project_client_mock(mock_project_client)
        mock_client.api_request_handler.case_handler.get_cases.return_value = (
            {
                "offset": 0,
                "limit": 250,
                "size": 1,
                "cases": [
                    {
                        "id": 1,
                        "title": "Test Case",
                        "section_id": 1,
                        "priority_id": 2,
                        "type_id": 1,
                        "labels": [{"id": 1, "title": "automated"}, {"id": 2, "title": "regression"}],
                    }
                ],
            },
            "",
        )

        with patch.object(self.environment, "log") as mock_log, patch.object(
            self.environment, "set_parameters"
        ), patch.object(self.environment, "check_for_required_parameters"):
            result = self.runner.invoke(cmd_cases.list, [], obj=self.environment)

            assert result.exit_code == 0
            log_calls_str = " ".join([str(call) for call in mock_log.call_args_list])
            assert "automated" in log_calls_str or "Labels" in log_calls_str

    @mock.patch("trcli.commands.cmd_cases.ProjectBasedClient")
    def test_get_case_with_project_id_from_config(self, mock_project_client):
        """Test case retrieval uses project_id from environment when not provided"""
        mock_client = self._setup_project_client_mock(mock_project_client, project_id=42)
        case_data = {"id": 123, "title": "Test Case", "section_id": 1}
        mock_client.api_request_handler.case_handler.get_case.return_value = (case_data, "")

        self.environment.project_id = 42

        with patch.object(self.environment, "log") as mock_log, patch.object(
            self.environment, "set_parameters"
        ), patch.object(self.environment, "check_for_required_parameters"):
            result = self.runner.invoke(cmd_cases.get, ["--case-id", "123"], obj=self.environment)

            assert result.exit_code == 0
            mock_client.api_request_handler.case_handler.get_case.assert_called_once_with(123)

    @mock.patch("trcli.commands.cmd_cases.ProjectBasedClient")
    def test_list_cases_with_project_id_from_config(self, mock_project_client):
        """Test cases listing uses project_id from environment when not provided"""
        mock_client = self._setup_project_client_mock(mock_project_client, project_id=99)
        mock_client.api_request_handler.case_handler.get_cases.return_value = (
            {"offset": 0, "limit": 250, "size": 1, "cases": [{"id": 1, "title": "Test"}]},
            "",
        )

        self.environment.project_id = 99

        with patch.object(self.environment, "log") as mock_log, patch.object(
            self.environment, "set_parameters"
        ), patch.object(self.environment, "check_for_required_parameters"):
            result = self.runner.invoke(cmd_cases.list, [], obj=self.environment)

            assert result.exit_code == 0
            mock_client.api_request_handler.case_handler.get_cases.assert_called_once_with(
                project_id=99, suite_id=None, priority_id=None, filter_text=None, limit=250, offset=0
            )

    @mock.patch("trcli.commands.cmd_cases.ProjectBasedClient")
    def test_get_case_with_project_name(self, mock_project_client):
        """Test case retrieval with project name from config"""
        mock_client = self._setup_project_client_mock(mock_project_client, project_id=42)
        case_data = {"id": 123, "title": "Test Case", "section_id": 1}
        mock_client.api_request_handler.case_handler.get_case.return_value = (case_data, "")

        # Set project name in environment (as if from config file)
        self.environment.project = "TRCLI AI Eval Single"
        self.environment.project_id = None  # No project_id, only name

        with patch.object(self.environment, "log") as mock_log, patch.object(
            self.environment, "set_parameters"
        ), patch.object(self.environment, "check_for_required_parameters"):
            result = self.runner.invoke(cmd_cases.get, ["--case-id", "123"], obj=self.environment)

            assert result.exit_code == 0
            # Verify resolve_project was called to convert name to ID
            mock_client.resolve_project.assert_called_once()
            mock_client.api_request_handler.case_handler.get_case.assert_called_once_with(123)

    @mock.patch("trcli.commands.cmd_cases.ProjectBasedClient")
    def test_list_cases_with_project_name(self, mock_project_client):
        """Test cases listing with project name from config"""
        mock_client = self._setup_project_client_mock(mock_project_client, project_id=99)
        mock_client.api_request_handler.case_handler.get_cases.return_value = (
            {"offset": 0, "limit": 250, "size": 1, "cases": [{"id": 1, "title": "Test"}]},
            "",
        )

        # Set project name in environment (as if from config file)
        self.environment.project = "TRCLI AI Eval Single"
        self.environment.project_id = None  # No project_id, only name

        with patch.object(self.environment, "log") as mock_log, patch.object(
            self.environment, "set_parameters"
        ), patch.object(self.environment, "check_for_required_parameters"):
            result = self.runner.invoke(cmd_cases.list, [], obj=self.environment)

            assert result.exit_code == 0
            # Verify resolve_project was called to convert name to ID
            mock_client.resolve_project.assert_called_once()
            mock_client.api_request_handler.case_handler.get_cases.assert_called_once_with(
                project_id=99, suite_id=None, priority_id=None, filter_text=None, limit=250, offset=0
            )
