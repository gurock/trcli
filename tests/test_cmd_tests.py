import pytest
from unittest import mock
from unittest.mock import MagicMock, patch
from click.testing import CliRunner

from trcli.cli import Environment
from trcli.commands import cmd_tests


class TestCmdTests:
    """Test suite for the tests command."""

    def setup_method(self):
        """Set up test environment"""
        self.runner = CliRunner()
        self.environment = Environment(cmd="tests")
        self.environment.host = "https://test.testrail.com"
        self.environment.username = "test@example.com"
        self.environment.password = "password"
        self.environment.api_key = None

    def _setup_project_client_mock(self, mock_project_client):
        """Helper to setup ProjectBasedClient mock"""
        mock_client_instance = MagicMock()
        mock_project_client.return_value = mock_client_instance
        return mock_client_instance

    @mock.patch("trcli.commands.cmd_tests.ProjectBasedClient")
    def test_get_test_success(self, mock_project_client):
        """Test successful test retrieval by ID."""
        mock_client = self._setup_project_client_mock(mock_project_client)
        mock_client.api_request_handler.test_handler.get_test.return_value = (
            {
                "id": 100,
                "title": "Verify line spacing",
                "case_id": 1,
                "run_id": 1,
                "status_id": 5,
                "assignedto_id": 1,
                "priority_id": 2,
                "type_id": 4,
            },
            "",
        )

        with patch.object(self.environment, "log") as mock_log, patch.object(
            self.environment, "set_parameters"
        ), patch.object(self.environment, "check_for_required_parameters"):
            result = self.runner.invoke(cmd_tests.get, ["--test-id", "100"], obj=self.environment)

            assert result.exit_code == 0
            assert mock_log.called
            mock_client.api_request_handler.test_handler.get_test.assert_called_once_with(100, None)

    @mock.patch("trcli.commands.cmd_tests.ProjectBasedClient")
    def test_get_test_json_output(self, mock_project_client):
        """Test test retrieval with JSON output."""
        mock_client = self._setup_project_client_mock(mock_project_client)
        mock_client.api_request_handler.test_handler.get_test.return_value = (
            {"id": 100, "title": "Verify line spacing", "case_id": 1, "run_id": 1, "status_id": 5},
            "",
        )

        with patch.object(self.environment, "log") as mock_log, patch.object(
            self.environment, "set_parameters"
        ), patch.object(self.environment, "check_for_required_parameters"):
            result = self.runner.invoke(cmd_tests.get, ["--test-id", "100", "--json-output"], obj=self.environment)

            assert result.exit_code == 0
            assert '"id": 100' in result.output
            assert '"title": "Verify line spacing"' in result.output

    @mock.patch("trcli.commands.cmd_tests.ProjectBasedClient")
    def test_get_test_api_error(self, mock_project_client):
        """Test handling of API errors when getting a test."""
        mock_client = self._setup_project_client_mock(mock_project_client)
        mock_client.api_request_handler.test_handler.get_test.return_value = (None, "Test not found")

        with patch.object(self.environment, "log") as mock_log, patch.object(
            self.environment, "set_parameters"
        ), patch.object(self.environment, "check_for_required_parameters"), patch.object(
            self.environment, "elog"
        ) as mock_elog:
            result = self.runner.invoke(cmd_tests.get, ["--test-id", "999"], obj=self.environment)

            assert result.exit_code == 1
            assert mock_elog.called

    @mock.patch("trcli.commands.cmd_tests.ProjectBasedClient")
    def test_list_tests_success(self, mock_project_client):
        """Test successful listing of all tests."""
        mock_client = self._setup_project_client_mock(mock_project_client)
        mock_client.api_request_handler.test_handler.get_tests.return_value = (
            [
                {"id": 1, "title": "Test 1", "case_id": 1, "run_id": 1, "status_id": 1},
                {"id": 2, "title": "Test 2", "case_id": 2, "run_id": 1, "status_id": 5},
            ],
            "",
        )

        with patch.object(self.environment, "log") as mock_log, patch.object(
            self.environment, "set_parameters"
        ), patch.object(self.environment, "check_for_required_parameters"):
            result = self.runner.invoke(cmd_tests.list, ["--run-id", "1"], obj=self.environment)

            assert result.exit_code == 0
            assert mock_log.called
            mock_client.api_request_handler.test_handler.get_tests.assert_called_once_with(
                run_id=1, status_id=None, limit=None, offset=None, label_id=None
            )

    @mock.patch("trcli.commands.cmd_tests.ProjectBasedClient")
    def test_list_tests_with_filters(self, mock_project_client):
        """Test listing tests with filters (status_id, limit, offset)."""
        mock_client = self._setup_project_client_mock(mock_project_client)
        mock_client.api_request_handler.test_handler.get_tests.return_value = (
            [{"id": 1, "title": "Failed Test", "case_id": 1, "run_id": 1, "status_id": 5}],
            "",
        )

        with patch.object(self.environment, "log") as mock_log, patch.object(
            self.environment, "set_parameters"
        ), patch.object(self.environment, "check_for_required_parameters"):
            result = self.runner.invoke(
                cmd_tests.list,
                ["--run-id", "1", "--status-id", "4,5", "--limit", "10", "--offset", "5"],
                obj=self.environment,
            )

            assert result.exit_code == 0
            assert mock_log.called
            mock_client.api_request_handler.test_handler.get_tests.assert_called_once_with(
                run_id=1, status_id="4,5", limit=10, offset=5, label_id=None
            )

    @mock.patch("trcli.commands.cmd_tests.ProjectBasedClient")
    def test_list_tests_with_label_filter(self, mock_project_client):
        """Test listing tests with label filter."""
        mock_client = self._setup_project_client_mock(mock_project_client)
        mock_client.api_request_handler.test_handler.get_tests.return_value = (
            [{"id": 1, "title": "Labeled Test", "case_id": 1, "run_id": 1, "status_id": 1}],
            "",
        )

        with patch.object(self.environment, "log") as mock_log, patch.object(
            self.environment, "set_parameters"
        ), patch.object(self.environment, "check_for_required_parameters"):
            result = self.runner.invoke(cmd_tests.list, ["--run-id", "1", "--label-id", "1,2"], obj=self.environment)

            assert result.exit_code == 0
            assert mock_log.called
            mock_client.api_request_handler.test_handler.get_tests.assert_called_once_with(
                run_id=1, status_id=None, limit=None, offset=None, label_id="1,2"
            )

    @mock.patch("trcli.commands.cmd_tests.ProjectBasedClient")
    def test_list_tests_json_output(self, mock_project_client):
        """Test listing tests with JSON output."""
        mock_client = self._setup_project_client_mock(mock_project_client)
        mock_client.api_request_handler.test_handler.get_tests.return_value = (
            [
                {"id": 1, "title": "Test 1", "case_id": 1, "run_id": 1, "status_id": 1},
                {"id": 2, "title": "Test 2", "case_id": 2, "run_id": 1, "status_id": 5},
            ],
            "",
        )

        with patch.object(self.environment, "log") as mock_log, patch.object(
            self.environment, "set_parameters"
        ), patch.object(self.environment, "check_for_required_parameters"):
            result = self.runner.invoke(cmd_tests.list, ["--run-id", "1", "--json-output"], obj=self.environment)

            assert result.exit_code == 0
            assert '"id": 1' in result.output
            assert '"title": "Test 1"' in result.output

    @mock.patch("trcli.commands.cmd_tests.ProjectBasedClient")
    def test_list_tests_empty_result(self, mock_project_client):
        """Test listing tests when no results are found."""
        mock_client = self._setup_project_client_mock(mock_project_client)
        mock_client.api_request_handler.test_handler.get_tests.return_value = ([], "")

        with patch.object(self.environment, "log") as mock_log, patch.object(
            self.environment, "set_parameters"
        ), patch.object(self.environment, "check_for_required_parameters"):
            result = self.runner.invoke(cmd_tests.list, ["--run-id", "1"], obj=self.environment)

            assert result.exit_code == 0
            assert mock_log.called

    @mock.patch("trcli.commands.cmd_tests.ProjectBasedClient")
    def test_list_tests_api_error(self, mock_project_client):
        """Test handling of API errors when listing tests."""
        mock_client = self._setup_project_client_mock(mock_project_client)
        mock_client.api_request_handler.test_handler.get_tests.return_value = ([], "Run not found")

        with patch.object(self.environment, "log") as mock_log, patch.object(
            self.environment, "set_parameters"
        ), patch.object(self.environment, "check_for_required_parameters"), patch.object(
            self.environment, "elog"
        ) as mock_elog:
            result = self.runner.invoke(cmd_tests.list, ["--run-id", "999"], obj=self.environment)

            assert result.exit_code == 1
            assert mock_elog.called

    @mock.patch("trcli.commands.cmd_tests.ProjectBasedClient")
    def test_list_tests_with_pagination(self, mock_project_client):
        """Test listing tests with pagination parameters."""
        mock_client = self._setup_project_client_mock(mock_project_client)
        mock_client.api_request_handler.test_handler.get_tests.return_value = (
            [
                {"id": 11, "title": "Test 11", "case_id": 11, "run_id": 1, "status_id": 1},
                {"id": 12, "title": "Test 12", "case_id": 12, "run_id": 1, "status_id": 1},
            ],
            "",
        )

        with patch.object(self.environment, "log") as mock_log, patch.object(
            self.environment, "set_parameters"
        ), patch.object(self.environment, "check_for_required_parameters"):
            result = self.runner.invoke(
                cmd_tests.list, ["--run-id", "1", "--limit", "2", "--offset", "10"], obj=self.environment
            )

            assert result.exit_code == 0
            assert mock_log.called
            mock_client.api_request_handler.test_handler.get_tests.assert_called_once_with(
                run_id=1, status_id=None, limit=2, offset=10, label_id=None
            )

    def test_get_test_invalid_id_zero(self):
        """Test validation rejects test ID of 0."""
        result = self.runner.invoke(cmd_tests.get, ["--test-id", "0"], obj=self.environment)

        assert result.exit_code != 0
        assert "0 is not in the range x>=1" in result.output

    def test_get_test_invalid_id_negative(self):
        """Test validation rejects negative test ID."""
        result = self.runner.invoke(cmd_tests.get, ["--test-id", "-1"], obj=self.environment)

        assert result.exit_code != 0
        assert "-1 is not in the range x>=1" in result.output

    def test_list_tests_invalid_run_id_zero(self):
        """Test validation rejects run ID of 0."""
        result = self.runner.invoke(cmd_tests.list, ["--run-id", "0"], obj=self.environment)

        assert result.exit_code != 0
        assert "0 is not in the range x>=1" in result.output

    def test_list_tests_invalid_run_id_negative(self):
        """Test validation rejects negative run ID."""
        result = self.runner.invoke(cmd_tests.list, ["--run-id", "-1"], obj=self.environment)

        assert result.exit_code != 0
        assert "-1 is not in the range x>=1" in result.output

    @mock.patch("trcli.commands.cmd_tests.ProjectBasedClient")
    def test_get_test_with_labels(self, mock_project_client):
        """Test test retrieval with labels displayed."""
        mock_client = self._setup_project_client_mock(mock_project_client)
        mock_client.api_request_handler.test_handler.get_test.return_value = (
            {
                "id": 100,
                "title": "Test with labels",
                "case_id": 1,
                "run_id": 1,
                "status_id": 5,
                "labels": [
                    {"id": 1, "title": "label1"},
                    {"id": 2, "title": "label2"},
                ],
            },
            "",
        )

        with patch.object(self.environment, "log") as mock_log, patch.object(
            self.environment, "set_parameters"
        ), patch.object(self.environment, "check_for_required_parameters"):
            result = self.runner.invoke(cmd_tests.get, ["--test-id", "100", "--show-all-fields"], obj=self.environment)

            assert result.exit_code == 0
            assert mock_log.called
            # Verify labels are mentioned in logs
            log_calls = [str(call) for call in mock_log.call_args_list]
            labels_mentioned = any("Labels: 2 label(s)" in str(call) for call in log_calls)
            assert labels_mentioned
