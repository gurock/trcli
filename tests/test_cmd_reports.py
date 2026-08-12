import pytest
from unittest import mock
from unittest.mock import MagicMock, patch
from click.testing import CliRunner

from trcli.cli import Environment
from trcli.commands import cmd_reports


class TestCmdReports:
    """Test suite for the reports command."""

    def setup_method(self):
        """Set up test environment"""
        self.runner = CliRunner()
        self.environment = Environment(cmd="reports")
        self.environment.host = "https://test.testrail.com"
        self.environment.username = "test@example.com"
        self.environment.password = "password"
        self.environment.api_key = None

    def _setup_project_client_mock(self, mock_project_client):
        """Helper to setup ProjectBasedClient mock"""
        mock_client_instance = MagicMock()
        mock_project_client.return_value = mock_client_instance
        return mock_client_instance

    @mock.patch("trcli.commands.cmd_reports.ProjectBasedClient")
    def test_list_reports_success(self, mock_project_client):
        """Test successful listing of reports for a project."""
        mock_client = self._setup_project_client_mock(mock_project_client)
        mock_client.api_request_handler.report_handler.get_reports.return_value = (
            [
                {
                    "id": 1,
                    "name": "Activity Summary (Cases)",
                    "description": "Test report",
                    "notify_user": True,
                },
                {"id": 2, "name": "Coverage Report", "description": "Coverage analysis", "notify_user": False},
            ],
            "",
        )

        with patch.object(self.environment, "log") as mock_log, patch.object(
            self.environment, "set_parameters"
        ), patch.object(self.environment, "check_for_required_parameters"):
            result = self.runner.invoke(cmd_reports.list, ["--project-id", "1"], obj=self.environment)

            assert result.exit_code == 0
            assert mock_log.called
            mock_client.api_request_handler.report_handler.get_reports.assert_called_once_with(1)

    @mock.patch("trcli.commands.cmd_reports.ProjectBasedClient")
    def test_list_reports_json_output(self, mock_project_client):
        """Test listing reports with JSON output."""
        mock_client = self._setup_project_client_mock(mock_project_client)
        mock_client.api_request_handler.report_handler.get_reports.return_value = (
            [{"id": 1, "name": "Test Report", "description": "Test"}],
            "",
        )

        with patch.object(self.environment, "log") as mock_log, patch.object(
            self.environment, "set_parameters"
        ), patch.object(self.environment, "check_for_required_parameters"):
            result = self.runner.invoke(cmd_reports.list, ["--project-id", "1", "--json-output"], obj=self.environment)

            assert result.exit_code == 0
            assert '"id": 1' in result.output
            assert '"name": "Test Report"' in result.output

    @mock.patch("trcli.commands.cmd_reports.ProjectBasedClient")
    def test_list_reports_with_all_fields(self, mock_project_client):
        """Test listing reports with all fields displayed."""
        mock_client = self._setup_project_client_mock(mock_project_client)
        mock_client.api_request_handler.report_handler.get_reports.return_value = (
            [
                {
                    "id": 1,
                    "name": "Test Report",
                    "description": "Test description",
                    "notify_user": True,
                    "notify_link": True,
                    "notify_link_recipients": "user@example.com",
                    "notify_attachment": True,
                    "notify_attachment_html_format": True,
                    "notify_attachment_pdf_format": False,
                }
            ],
            "",
        )

        with patch.object(self.environment, "log") as mock_log, patch.object(
            self.environment, "set_parameters"
        ), patch.object(self.environment, "check_for_required_parameters"):
            result = self.runner.invoke(
                cmd_reports.list, ["--project-id", "1", "--show-all-fields"], obj=self.environment
            )

            assert result.exit_code == 0
            assert mock_log.called

    @mock.patch("trcli.commands.cmd_reports.ProjectBasedClient")
    def test_list_reports_api_error(self, mock_project_client):
        """Test handling of API errors when listing reports."""
        mock_client = self._setup_project_client_mock(mock_project_client)
        mock_client.api_request_handler.report_handler.get_reports.return_value = (
            [],
            "Invalid or unknown project",
        )

        with patch.object(self.environment, "log") as mock_log, patch.object(
            self.environment, "set_parameters"
        ), patch.object(self.environment, "check_for_required_parameters"), patch.object(
            self.environment, "elog"
        ) as mock_elog:
            result = self.runner.invoke(cmd_reports.list, ["--project-id", "999"], obj=self.environment)

            assert result.exit_code == 1
            assert mock_elog.called

    def test_list_reports_no_project_id_no_cross_project(self):
        """Test that list requires project-id or cross-project flag."""
        with patch.object(self.environment, "log") as mock_log, patch.object(
            self.environment, "set_parameters"
        ), patch.object(self.environment, "check_for_required_parameters"), patch.object(
            self.environment, "elog"
        ) as mock_elog:
            result = self.runner.invoke(cmd_reports.list, [], obj=self.environment)

            assert result.exit_code == 1
            assert mock_elog.called

    @mock.patch("trcli.commands.cmd_reports.ProjectBasedClient")
    def test_list_cross_project_reports_success(self, mock_project_client):
        """Test successful listing of cross-project reports."""
        mock_client = self._setup_project_client_mock(mock_project_client)
        mock_client.api_request_handler.report_handler.get_cross_project_reports.return_value = (
            [
                {
                    "id": 1,
                    "name": "Test Execution Projects Summary",
                    "description": "Cross-project summary",
                    "project_ids": [1, 2, 3],
                    "report_timeframe": "90 days",
                }
            ],
            "",
        )

        with patch.object(self.environment, "log") as mock_log, patch.object(
            self.environment, "set_parameters"
        ), patch.object(self.environment, "check_for_required_parameters"):
            result = self.runner.invoke(cmd_reports.list, ["--cross-project"], obj=self.environment)

            assert result.exit_code == 0
            assert mock_log.called
            mock_client.api_request_handler.report_handler.get_cross_project_reports.assert_called_once()

    @mock.patch("trcli.commands.cmd_reports.ProjectBasedClient")
    def test_list_cross_project_reports_enterprise_error(self, mock_project_client):
        """Test handling of Enterprise-only error for cross-project reports."""
        mock_client = self._setup_project_client_mock(mock_project_client)
        mock_client.api_request_handler.report_handler.get_cross_project_reports.return_value = (
            [],
            "Access denied",
        )

        with patch.object(self.environment, "log") as mock_log, patch.object(
            self.environment, "set_parameters"
        ), patch.object(self.environment, "check_for_required_parameters"), patch.object(
            self.environment, "elog"
        ) as mock_elog:
            result = self.runner.invoke(cmd_reports.list, ["--cross-project"], obj=self.environment)

            assert result.exit_code == 1
            assert mock_elog.called

    @mock.patch("trcli.commands.cmd_reports.ProjectBasedClient")
    def test_generate_report_by_id_success(self, mock_project_client):
        """Test successful report generation by ID."""
        mock_client = self._setup_project_client_mock(mock_project_client)

        # Need to mock get_reports to get report name
        mock_client.api_request_handler.report_handler.get_reports.return_value = (
            [{"id": 5, "name": "Test Report", "description": "Test"}],
            "",
        )

        mock_client.api_request_handler.report_handler.run_report.return_value = (
            {
                "report_url": "https://test.testrail.com/reports/view/123",
                "report_html": "https://test.testrail.com/reports/get_html/123",
                "report_pdf": "https://test.testrail.com/reports/get_pdf/123",
            },
            "",
        )

        with patch.object(self.environment, "log") as mock_log, patch.object(
            self.environment, "set_parameters"
        ), patch.object(self.environment, "check_for_required_parameters"):
            result = self.runner.invoke(
                cmd_reports.generate, ["--project-id", "1", "--report-id", "5"], obj=self.environment
            )

            assert result.exit_code == 0
            assert mock_log.called
            mock_client.api_request_handler.report_handler.run_report.assert_called_once_with(5)

    @mock.patch("trcli.commands.cmd_reports.ProjectBasedClient")
    def test_generate_report_shows_all_urls(self, mock_project_client):
        """Test that report generation shows all URLs (View, HTML, PDF)."""
        mock_client = self._setup_project_client_mock(mock_project_client)

        # Need to mock get_reports to get report name
        mock_client.api_request_handler.report_handler.get_reports.return_value = (
            [{"id": 5, "name": "Coverage Report", "description": "Test"}],
            "",
        )

        mock_client.api_request_handler.report_handler.run_report.return_value = (
            {
                "report_url": "https://test.testrail.com/reports/view/123",
                "report_html": "https://test.testrail.com/reports/get_html/123",
                "report_pdf": "https://test.testrail.com/reports/get_pdf/123",
            },
            "",
        )

        with patch.object(self.environment, "log") as mock_log, patch.object(
            self.environment, "set_parameters"
        ), patch.object(self.environment, "check_for_required_parameters"):
            result = self.runner.invoke(
                cmd_reports.generate, ["--project-id", "1", "--report-id", "5"], obj=self.environment
            )

            assert result.exit_code == 0
            assert mock_log.called
            # Check that all URL types are mentioned in the logs
            log_calls = [str(call) for call in mock_log.call_args_list]
            assert any("View:" in str(call) for call in log_calls)
            assert any("HTML:" in str(call) for call in log_calls)
            assert any("PDF:" in str(call) for call in log_calls)

    @mock.patch("trcli.commands.cmd_reports.ProjectBasedClient")
    def test_generate_report_by_name_success(self, mock_project_client):
        """Test successful report generation by name."""
        mock_client = self._setup_project_client_mock(mock_project_client)

        # Mock list reports to find report by name
        mock_client.api_request_handler.report_handler.get_reports.return_value = (
            [
                {"id": 1, "name": "Activity Summary", "description": "Test"},
                {"id": 2, "name": "Coverage Report", "description": "Coverage"},
            ],
            "",
        )

        # Mock run report
        mock_client.api_request_handler.report_handler.run_report.return_value = (
            {
                "report_url": "https://test.testrail.com/reports/view/123",
                "report_html": "https://test.testrail.com/reports/get_html/123",
                "report_pdf": "https://test.testrail.com/reports/get_pdf/123",
            },
            "",
        )

        with patch.object(self.environment, "log") as mock_log, patch.object(
            self.environment, "set_parameters"
        ), patch.object(self.environment, "check_for_required_parameters"):
            result = self.runner.invoke(
                cmd_reports.generate, ["--project-id", "1", "--report", "Coverage"], obj=self.environment
            )

            assert result.exit_code == 0
            assert mock_log.called
            mock_client.api_request_handler.report_handler.get_reports.assert_called_once_with(1)
            mock_client.api_request_handler.report_handler.run_report.assert_called_once_with(2)

    @mock.patch("trcli.commands.cmd_reports.ProjectBasedClient")
    def test_generate_multiple_reports_by_name(self, mock_project_client):
        """Test generation of multiple reports matching a name pattern."""
        mock_client = self._setup_project_client_mock(mock_project_client)

        # Mock list reports to find multiple matches
        mock_client.api_request_handler.report_handler.get_reports.return_value = (
            [
                {"id": 1, "name": "Activity Summary (Cases)", "description": "Test1"},
                {"id": 2, "name": "Activity Summary (Runs)", "description": "Test2"},
                {"id": 3, "name": "Coverage Report", "description": "Coverage"},
            ],
            "",
        )

        # Mock run report to return different URLs for each
        def run_report_side_effect(report_id):
            return (
                {
                    "report_url": f"https://test.testrail.com/reports/view/{report_id * 100}",
                    "report_html": f"https://test.testrail.com/reports/get_html/{report_id * 100}",
                    "report_pdf": f"https://test.testrail.com/reports/get_pdf/{report_id * 100}",
                },
                "",
            )

        mock_client.api_request_handler.report_handler.run_report.side_effect = run_report_side_effect

        with patch.object(self.environment, "log") as mock_log, patch.object(
            self.environment, "set_parameters"
        ), patch.object(self.environment, "check_for_required_parameters"):
            result = self.runner.invoke(
                cmd_reports.generate, ["--project-id", "1", "--report", "Activity"], obj=self.environment
            )

            assert result.exit_code == 0
            assert mock_log.called
            # Should have called run_report twice (for both Activity Summary reports)
            assert mock_client.api_request_handler.report_handler.run_report.call_count == 2
            # Verify both reports were generated
            log_calls = [str(call) for call in mock_log.call_args_list]
            assert any("Activity Summary (Cases)" in str(call) for call in log_calls)
            assert any("Activity Summary (Runs)" in str(call) for call in log_calls)

    @mock.patch("trcli.commands.cmd_reports.ProjectBasedClient")
    def test_generate_report_name_not_found(self, mock_project_client):
        """Test report generation when report name is not found."""
        mock_client = self._setup_project_client_mock(mock_project_client)

        mock_client.api_request_handler.report_handler.get_reports.return_value = (
            [
                {"id": 1, "name": "Activity Summary", "description": "Test"},
                {"id": 2, "name": "Coverage Report", "description": "Coverage"},
            ],
            "",
        )

        with patch.object(self.environment, "log") as mock_log, patch.object(
            self.environment, "set_parameters"
        ), patch.object(self.environment, "check_for_required_parameters"), patch.object(
            self.environment, "elog"
        ) as mock_elog:
            result = self.runner.invoke(
                cmd_reports.generate, ["--project-id", "1", "--report", "NonExistent"], obj=self.environment
            )

            assert result.exit_code == 1
            assert mock_elog.called

    def test_generate_report_no_id_or_name(self):
        """Test that generate requires either report-id or report name."""
        with patch.object(self.environment, "log") as mock_log, patch.object(
            self.environment, "set_parameters"
        ), patch.object(self.environment, "check_for_required_parameters"), patch.object(
            self.environment, "elog"
        ) as mock_elog:
            result = self.runner.invoke(cmd_reports.generate, ["--project-id", "1"], obj=self.environment)

            assert result.exit_code == 1
            assert mock_elog.called

    def test_generate_report_both_id_and_name(self):
        """Test that generate rejects both report-id and report name."""
        with patch.object(self.environment, "log") as mock_log, patch.object(
            self.environment, "set_parameters"
        ), patch.object(self.environment, "check_for_required_parameters"), patch.object(
            self.environment, "elog"
        ) as mock_elog:
            result = self.runner.invoke(
                cmd_reports.generate,
                ["--project-id", "1", "--report-id", "5", "--report", "Coverage"],
                obj=self.environment,
            )

            assert result.exit_code == 1
            assert mock_elog.called

    @mock.patch("trcli.commands.cmd_reports.ProjectBasedClient")
    def test_generate_report_json_output(self, mock_project_client):
        """Test report generation with JSON output."""
        mock_client = self._setup_project_client_mock(mock_project_client)

        # Need to mock get_reports to get report name
        mock_client.api_request_handler.report_handler.get_reports.return_value = (
            [{"id": 5, "name": "Test Report", "description": "Test"}],
            "",
        )

        mock_client.api_request_handler.report_handler.run_report.return_value = (
            {
                "report_url": "https://test.testrail.com/reports/view/123",
                "report_html": "https://test.testrail.com/reports/get_html/123",
                "report_pdf": "https://test.testrail.com/reports/get_pdf/123",
            },
            "",
        )

        with patch.object(self.environment, "log") as mock_log, patch.object(
            self.environment, "set_parameters"
        ), patch.object(self.environment, "check_for_required_parameters"):
            result = self.runner.invoke(
                cmd_reports.generate, ["--project-id", "1", "--report-id", "5", "--json-output"], obj=self.environment
            )

            assert result.exit_code == 0
            # JSON output now contains report name, id, and urls
            assert '"name"' in result.output
            assert '"urls"' in result.output

    @mock.patch("trcli.commands.cmd_reports.ProjectBasedClient")
    def test_generate_report_api_error(self, mock_project_client):
        """Test handling of API errors when generating report."""
        mock_client = self._setup_project_client_mock(mock_project_client)

        # Need to mock get_reports to get report name
        mock_client.api_request_handler.report_handler.get_reports.return_value = (
            [{"id": 999, "name": "Test Report", "description": "Test"}],
            "",
        )

        mock_client.api_request_handler.report_handler.run_report.return_value = (
            None,
            "Invalid report template ID",
        )

        with patch.object(self.environment, "log") as mock_log, patch.object(
            self.environment, "set_parameters"
        ), patch.object(self.environment, "check_for_required_parameters"), patch.object(
            self.environment, "elog"
        ) as mock_elog:
            result = self.runner.invoke(
                cmd_reports.generate, ["--project-id", "1", "--report-id", "999"], obj=self.environment
            )

            assert result.exit_code == 1
            assert mock_elog.called

    @mock.patch("trcli.commands.cmd_reports.ProjectBasedClient")
    def test_generate_cross_project_report_success(self, mock_project_client):
        """Test successful cross-project report generation."""
        mock_client = self._setup_project_client_mock(mock_project_client)

        # Need to mock get_cross_project_reports to get report name
        mock_client.api_request_handler.report_handler.get_cross_project_reports.return_value = (
            [{"id": 3, "name": "Cross-Project Report", "description": "Test"}],
            "",
        )

        mock_client.api_request_handler.report_handler.run_cross_project_report.return_value = (
            {
                "report_url": "https://test.testrail.com/cross_project_reports/view/123",
                "report_html": "https://test.testrail.com/cross_project_reports/get_html/123",
                "report_pdf": "https://test.testrail.com/cross_project_reports/get_pdf/123",
            },
            "",
        )

        with patch.object(self.environment, "log") as mock_log, patch.object(
            self.environment, "set_parameters"
        ), patch.object(self.environment, "check_for_required_parameters"):
            result = self.runner.invoke(
                cmd_reports.generate, ["--cross-project", "--report-id", "3"], obj=self.environment
            )

            assert result.exit_code == 0
            assert mock_log.called
            mock_client.api_request_handler.report_handler.run_cross_project_report.assert_called_once_with(3)

    def test_generate_report_no_project_id_without_cross_project(self):
        """Test that generate requires project-id when not using cross-project."""
        with patch.object(self.environment, "log") as mock_log, patch.object(
            self.environment, "set_parameters"
        ), patch.object(self.environment, "check_for_required_parameters"), patch.object(
            self.environment, "elog"
        ) as mock_elog:
            result = self.runner.invoke(cmd_reports.generate, ["--report-id", "5"], obj=self.environment)

            assert result.exit_code == 1
            assert mock_elog.called

    @mock.patch("trcli.commands.cmd_reports.ProjectBasedClient")
    def test_list_reports_uses_environment_project_id(self, mock_project_client):
        """Test that list uses project_id from environment when not provided."""
        # Set project_id in environment
        self.environment.project_id = 42

        mock_client = self._setup_project_client_mock(mock_project_client)
        mock_client.api_request_handler.report_handler.get_reports.return_value = (
            [{"id": 1, "name": "Test Report", "description": "Test"}],
            "",
        )

        with patch.object(self.environment, "log") as mock_log, patch.object(
            self.environment, "set_parameters"
        ), patch.object(self.environment, "check_for_required_parameters"):
            result = self.runner.invoke(cmd_reports.list, [], obj=self.environment)

            assert result.exit_code == 0
            mock_client.api_request_handler.report_handler.get_reports.assert_called_once_with(42)

    @mock.patch("trcli.commands.cmd_reports.ProjectBasedClient")
    def test_generate_report_uses_environment_project_id(self, mock_project_client):
        """Test that generate uses project_id from environment when not provided."""
        # Set project_id in environment
        self.environment.project_id = 42

        mock_client = self._setup_project_client_mock(mock_project_client)

        # Need to mock get_reports to get report name
        mock_client.api_request_handler.report_handler.get_reports.return_value = (
            [{"id": 5, "name": "Test Report", "description": "Test"}],
            "",
        )

        mock_client.api_request_handler.report_handler.run_report.return_value = (
            {
                "report_url": "https://test.testrail.com/reports/view/123",
                "report_html": "https://test.testrail.com/reports/get_html/123",
                "report_pdf": "https://test.testrail.com/reports/get_pdf/123",
            },
            "",
        )

        with patch.object(self.environment, "log") as mock_log, patch.object(
            self.environment, "set_parameters"
        ), patch.object(self.environment, "check_for_required_parameters"):
            result = self.runner.invoke(cmd_reports.generate, ["--report-id", "5"], obj=self.environment)

            assert result.exit_code == 0
            mock_client.api_request_handler.report_handler.run_report.assert_called_once_with(5)

    @mock.patch("trcli.commands.cmd_reports.ProjectBasedClient")
    def test_list_reports_resolves_project_name(self, mock_project_client):
        """Test that list resolves project name to project_id via ProjectBasedClient."""
        # Set project name in environment (no project_id)
        self.environment.project = "My Project"
        self.environment.project_id = None

        mock_client = self._setup_project_client_mock(mock_project_client)

        # Mock the project resolution
        mock_project = MagicMock()
        mock_project.project_id = 99
        mock_client.project = mock_project

        mock_client.api_request_handler.report_handler.get_reports.return_value = (
            [{"id": 1, "name": "Test Report", "description": "Test"}],
            "",
        )

        with patch.object(self.environment, "log") as mock_log, patch.object(
            self.environment, "set_parameters"
        ), patch.object(self.environment, "check_for_required_parameters"):
            result = self.runner.invoke(cmd_reports.list, [], obj=self.environment)

            assert result.exit_code == 0
            # Verify resolve_project was called
            mock_client.resolve_project.assert_called_once()
            # Verify get_reports was called with resolved project_id
            mock_client.api_request_handler.report_handler.get_reports.assert_called_once_with(99)

    @mock.patch("trcli.commands.cmd_reports.ProjectBasedClient")
    def test_generate_report_resolves_project_name(self, mock_project_client):
        """Test that generate resolves project name to project_id via ProjectBasedClient."""
        # Set project name in environment (no project_id)
        self.environment.project = "My Project"
        self.environment.project_id = None

        mock_client = self._setup_project_client_mock(mock_project_client)

        # Mock the project resolution
        mock_project = MagicMock()
        mock_project.project_id = 99
        mock_client.project = mock_project

        # Need to mock get_reports to get report name
        mock_client.api_request_handler.report_handler.get_reports.return_value = (
            [{"id": 5, "name": "Test Report", "description": "Test"}],
            "",
        )

        mock_client.api_request_handler.report_handler.run_report.return_value = (
            {
                "report_url": "https://test.testrail.com/reports/view/123",
                "report_html": "https://test.testrail.com/reports/get_html/123",
                "report_pdf": "https://test.testrail.com/reports/get_pdf/123",
            },
            "",
        )

        with patch.object(self.environment, "log") as mock_log, patch.object(
            self.environment, "set_parameters"
        ), patch.object(self.environment, "check_for_required_parameters"):
            result = self.runner.invoke(cmd_reports.generate, ["--report-id", "5"], obj=self.environment)

            assert result.exit_code == 0
            # Verify resolve_project was called
            mock_client.resolve_project.assert_called_once()
            # Verify run_report was called with report_id
            mock_client.api_request_handler.report_handler.run_report.assert_called_once_with(5)
