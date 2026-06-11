import pytest
from unittest import mock
from unittest.mock import MagicMock, patch
from click.testing import CliRunner

from trcli.cli import Environment
from trcli.commands import cmd_suites


class TestCmdSuites:
    """Test class for suites command functionality"""

    def setup_method(self):
        """Set up test environment"""
        self.runner = CliRunner()
        self.environment = Environment(cmd="suites")
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

    @mock.patch("trcli.commands.cmd_suites.ProjectBasedClient")
    def test_get_suite_success(self, mock_project_client):
        """Test successful suite retrieval"""
        mock_client = self._setup_project_client_mock(mock_project_client)
        mock_client.api_request_handler.suite_handler.get_suite.return_value = (
            {
                "id": 1,
                "name": "Setup & Installation",
                "description": "Test suite for setup and installation",
                "project_id": 1,
                "url": "http://testrail/index.php?/suites/view/1",
            },
            "",
        )

        with patch.object(self.environment, "log") as mock_log, patch.object(
            self.environment, "set_parameters"
        ), patch.object(self.environment, "check_for_required_parameters"):
            result = self.runner.invoke(cmd_suites.get, ["--suite-id", "1"], obj=self.environment)

            assert result.exit_code == 0
            mock_client.api_request_handler.suite_handler.get_suite.assert_called_once_with(1)
            assert mock_log.called

    @mock.patch("trcli.commands.cmd_suites.ProjectBasedClient")
    def test_get_suite_json_output(self, mock_project_client):
        """Test suite retrieval with JSON output"""
        mock_client = self._setup_project_client_mock(mock_project_client)
        suite_data = {"id": 1, "name": "Test Suite", "description": "Description", "project_id": 1}
        mock_client.api_request_handler.suite_handler.get_suite.return_value = (suite_data, "")

        with patch.object(self.environment, "set_parameters"), patch.object(
            self.environment, "check_for_required_parameters"
        ):
            result = self.runner.invoke(cmd_suites.get, ["--suite-id", "1", "--json-output"], obj=self.environment)

            assert result.exit_code == 0
            # Check for prettified JSON (with newlines and indentation)
            assert '"id": 1' in result.output
            assert "\n" in result.output  # Prettified has newlines

    @mock.patch("trcli.commands.cmd_suites.ProjectBasedClient")
    def test_get_suite_show_all_fields(self, mock_project_client):
        """Test suite retrieval with show all fields"""
        mock_client = self._setup_project_client_mock(mock_project_client)
        mock_client.api_request_handler.suite_handler.get_suite.return_value = (
            {
                "id": 1,
                "name": "Test Suite",
                "description": "Suite description",
                "project_id": 1,
                "url": "http://testrail/suites/view/1",
                "custom_field1": "value1",
                "is_completed": False,
            },
            "",
        )

        with patch.object(self.environment, "log") as mock_log, patch.object(
            self.environment, "set_parameters"
        ), patch.object(self.environment, "check_for_required_parameters"):
            result = self.runner.invoke(
                cmd_suites.get,
                ["--suite-id", "1", "--show-all-fields"],
                obj=self.environment,
            )

            assert result.exit_code == 0
            assert mock_log.called

    @mock.patch("trcli.commands.cmd_suites.ProjectBasedClient")
    def test_get_suite_api_error(self, mock_project_client):
        """Test suite retrieval with API error"""
        mock_client = self._setup_project_client_mock(mock_project_client)
        mock_client.api_request_handler.suite_handler.get_suite.return_value = ({}, "Suite not found")

        with patch.object(self.environment, "elog") as mock_elog, patch.object(
            self.environment, "set_parameters"
        ), patch.object(self.environment, "check_for_required_parameters"):
            result = self.runner.invoke(cmd_suites.get, ["--suite-id", "999"], obj=self.environment)

            assert result.exit_code == 1
            mock_elog.assert_called_with("Error: Failed to retrieve suite: Suite not found")

    @mock.patch("trcli.commands.cmd_suites.ProjectBasedClient")
    def test_list_suites_success(self, mock_project_client):
        """Test successful suites listing"""
        mock_client = self._setup_project_client_mock(mock_project_client)
        mock_client.api_request_handler.suite_handler.get_suites.return_value = (
            {
                "offset": 0,
                "limit": 250,
                "size": 2,
                "_links": {"next": None, "prev": None},
                "suites": [
                    {
                        "id": 1,
                        "name": "Setup & Installation",
                        "description": "Setup tests",
                        "project_id": 1,
                    },
                    {
                        "id": 2,
                        "name": "Document Editing",
                        "description": "Document editing tests",
                        "project_id": 1,
                    },
                ],
            },
            "",
        )

        with patch.object(self.environment, "log") as mock_log, patch.object(
            self.environment, "set_parameters"
        ), patch.object(self.environment, "check_for_required_parameters"):
            result = self.runner.invoke(cmd_suites.list, [], obj=self.environment)

            assert result.exit_code == 0
            mock_client.api_request_handler.suite_handler.get_suites.assert_called_once_with(
                project_id=1, limit=250, offset=0
            )
            assert mock_log.called

    @mock.patch("trcli.commands.cmd_suites.ProjectBasedClient")
    def test_list_suites_with_pagination(self, mock_project_client):
        """Test suites listing with pagination parameters"""
        mock_client = self._setup_project_client_mock(mock_project_client)
        mock_client.api_request_handler.suite_handler.get_suites.return_value = (
            {
                "offset": 100,
                "limit": 50,
                "size": 50,
                "_links": {"next": "/api/v2/get_suites/1&offset=150", "prev": "/api/v2/get_suites/1&offset=50"},
                "suites": [{"id": i, "name": f"Suite {i}", "project_id": 1} for i in range(100, 150)],
            },
            "",
        )

        with patch.object(self.environment, "log") as mock_log, patch.object(
            self.environment, "set_parameters"
        ), patch.object(self.environment, "check_for_required_parameters"):
            result = self.runner.invoke(cmd_suites.list, ["--offset", "100", "--limit", "50"], obj=self.environment)

            assert result.exit_code == 0
            mock_client.api_request_handler.suite_handler.get_suites.assert_called_once_with(
                project_id=1, limit=50, offset=100
            )

    @mock.patch("trcli.commands.cmd_suites.ProjectBasedClient")
    def test_list_suites_json_output(self, mock_project_client):
        """Test suites listing with JSON output"""
        mock_client = self._setup_project_client_mock(mock_project_client)
        response_data = {"offset": 0, "limit": 250, "size": 1, "suites": [{"id": 1, "name": "Test", "project_id": 1}]}
        mock_client.api_request_handler.suite_handler.get_suites.return_value = (response_data, "")

        with patch.object(self.environment, "set_parameters"), patch.object(
            self.environment, "check_for_required_parameters"
        ):
            result = self.runner.invoke(cmd_suites.list, ["--json-output"], obj=self.environment)

            assert result.exit_code == 0
            # Check for prettified JSON (with newlines and indentation)
            assert '"offset": 0' in result.output
            assert "\n" in result.output  # Prettified has newlines

    @mock.patch("trcli.commands.cmd_suites.ProjectBasedClient")
    def test_list_suites_show_all_fields(self, mock_project_client):
        """Test suites listing with show all fields"""
        mock_client = self._setup_project_client_mock(mock_project_client)
        mock_client.api_request_handler.suite_handler.get_suites.return_value = (
            {
                "offset": 0,
                "limit": 250,
                "size": 1,
                "suites": [
                    {
                        "id": 1,
                        "name": "Test Suite",
                        "description": "Description",
                        "project_id": 1,
                        "url": "http://testrail/suites/view/1",
                    }
                ],
            },
            "",
        )

        with patch.object(self.environment, "log") as mock_log, patch.object(
            self.environment, "set_parameters"
        ), patch.object(self.environment, "check_for_required_parameters"):
            result = self.runner.invoke(cmd_suites.list, ["--show-all-fields"], obj=self.environment)

            assert result.exit_code == 0
            assert mock_log.called

    @mock.patch("trcli.commands.cmd_suites.ProjectBasedClient")
    def test_list_suites_empty_result(self, mock_project_client):
        """Test suites listing with empty result"""
        mock_client = self._setup_project_client_mock(mock_project_client)
        mock_client.api_request_handler.suite_handler.get_suites.return_value = (
            {"offset": 0, "limit": 250, "size": 0, "suites": []},
            "",
        )

        with patch.object(self.environment, "log") as mock_log, patch.object(
            self.environment, "set_parameters"
        ), patch.object(self.environment, "check_for_required_parameters"):
            result = self.runner.invoke(cmd_suites.list, [], obj=self.environment)

            assert result.exit_code == 0
            mock_log.assert_any_call("No suites found.")

    @mock.patch("trcli.commands.cmd_suites.ProjectBasedClient")
    def test_list_suites_api_error(self, mock_project_client):
        """Test suites listing with API error"""
        mock_client = self._setup_project_client_mock(mock_project_client)
        mock_client.api_request_handler.suite_handler.get_suites.return_value = ({}, "Project not found")

        with patch.object(self.environment, "elog") as mock_elog, patch.object(
            self.environment, "set_parameters"
        ), patch.object(self.environment, "check_for_required_parameters"):
            result = self.runner.invoke(cmd_suites.list, [], obj=self.environment)

            assert result.exit_code == 1
            mock_elog.assert_called_with("Error: Failed to retrieve suites: Project not found")

    @mock.patch("trcli.commands.cmd_suites.ProjectBasedClient")
    def test_list_suites_with_next_link(self, mock_project_client):
        """Test suites listing shows pagination hint when next link is present"""
        mock_client = self._setup_project_client_mock(mock_project_client)
        mock_client.api_request_handler.suite_handler.get_suites.return_value = (
            {
                "offset": 0,
                "limit": 250,
                "size": 250,
                "_links": {"next": "/api/v2/get_suites/1&offset=250", "prev": None},
                "suites": [{"id": i, "name": f"Suite {i}", "project_id": 1} for i in range(1, 251)],
            },
            "",
        )

        with patch.object(self.environment, "log") as mock_log, patch.object(
            self.environment, "set_parameters"
        ), patch.object(self.environment, "check_for_required_parameters"):
            result = self.runner.invoke(cmd_suites.list, [], obj=self.environment)

            assert result.exit_code == 0
            log_calls = [str(call) for call in mock_log.call_args_list]
            pagination_hint_found = any("More results available" in str(call) for call in log_calls)
            assert pagination_hint_found

    @mock.patch("trcli.commands.cmd_suites.ProjectBasedClient")
    def test_get_suite_with_project_id_from_config(self, mock_project_client):
        """Test suite retrieval uses project_id from environment when not provided"""
        mock_client = self._setup_project_client_mock(mock_project_client, project_id=42)
        suite_data = {"id": 1, "name": "Test Suite", "description": "Desc", "project_id": 42}
        mock_client.api_request_handler.suite_handler.get_suite.return_value = (suite_data, "")

        self.environment.project_id = 42

        with patch.object(self.environment, "log") as mock_log, patch.object(
            self.environment, "set_parameters"
        ), patch.object(self.environment, "check_for_required_parameters"):
            result = self.runner.invoke(cmd_suites.get, ["--suite-id", "1"], obj=self.environment)

            assert result.exit_code == 0
            mock_client.api_request_handler.suite_handler.get_suite.assert_called_once_with(1)

    @mock.patch("trcli.commands.cmd_suites.ProjectBasedClient")
    def test_list_suites_with_project_id_from_config(self, mock_project_client):
        """Test suites listing uses project_id from environment when not provided"""
        mock_client = self._setup_project_client_mock(mock_project_client, project_id=99)
        mock_client.api_request_handler.suite_handler.get_suites.return_value = (
            {"offset": 0, "limit": 250, "size": 1, "suites": [{"id": 1, "name": "Test", "project_id": 99}]},
            "",
        )

        self.environment.project_id = 99

        with patch.object(self.environment, "log") as mock_log, patch.object(
            self.environment, "set_parameters"
        ), patch.object(self.environment, "check_for_required_parameters"):
            result = self.runner.invoke(cmd_suites.list, [], obj=self.environment)

            assert result.exit_code == 0
            mock_client.api_request_handler.suite_handler.get_suites.assert_called_once_with(
                project_id=99, limit=250, offset=0
            )

    @mock.patch("trcli.commands.cmd_suites.ProjectBasedClient")
    def test_get_suite_with_project_name(self, mock_project_client):
        """Test suite retrieval with project name from config"""
        mock_client = self._setup_project_client_mock(mock_project_client, project_id=42)
        suite_data = {"id": 1, "name": "Test Suite", "description": "Desc", "project_id": 42}
        mock_client.api_request_handler.suite_handler.get_suite.return_value = (suite_data, "")

        # Set project name in environment (as if from config file)
        self.environment.project = "TRCLI Test Project"
        self.environment.project_id = None  # No project_id, only name

        with patch.object(self.environment, "log") as mock_log, patch.object(
            self.environment, "set_parameters"
        ), patch.object(self.environment, "check_for_required_parameters"):
            result = self.runner.invoke(cmd_suites.get, ["--suite-id", "1"], obj=self.environment)

            assert result.exit_code == 0
            # Verify resolve_project was called to convert name to ID
            mock_client.resolve_project.assert_called_once()
            mock_client.api_request_handler.suite_handler.get_suite.assert_called_once_with(1)

    @mock.patch("trcli.commands.cmd_suites.ProjectBasedClient")
    def test_list_suites_with_project_name(self, mock_project_client):
        """Test suites listing with project name from config"""
        mock_client = self._setup_project_client_mock(mock_project_client, project_id=99)
        mock_client.api_request_handler.suite_handler.get_suites.return_value = (
            {"offset": 0, "limit": 250, "size": 1, "suites": [{"id": 1, "name": "Test", "project_id": 99}]},
            "",
        )

        # Set project name in environment (as if from config file)
        self.environment.project = "TRCLI Test Project"
        self.environment.project_id = None  # No project_id, only name

        with patch.object(self.environment, "log") as mock_log, patch.object(
            self.environment, "set_parameters"
        ), patch.object(self.environment, "check_for_required_parameters"):
            result = self.runner.invoke(cmd_suites.list, [], obj=self.environment)

            assert result.exit_code == 0
            # Verify resolve_project was called to convert name to ID
            mock_client.resolve_project.assert_called_once()
            mock_client.api_request_handler.suite_handler.get_suites.assert_called_once_with(
                project_id=99, limit=250, offset=0
            )
