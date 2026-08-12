import pytest
from unittest.mock import MagicMock

from trcli.api.report_handler import ReportHandler


class TestReportHandler:
    """Test suite for ReportHandler class."""

    def setup_method(self):
        """Set up test environment"""
        self.api_client = MagicMock()
        self.handler = ReportHandler(self.api_client)

    def test_get_reports_success(self):
        """Test successful retrieval of project reports."""
        mock_response = MagicMock()
        mock_response.error_message = ""
        mock_response.response_text = [
            {
                "id": 1,
                "name": "Activity Summary (Cases)",
                "description": "Test report",
                "notify_user": True,
                "notify_link": False,
            },
            {
                "id": 2,
                "name": "Coverage Report",
                "description": "Coverage analysis",
                "notify_user": False,
                "notify_link": True,
            },
        ]
        self.api_client.send_get.return_value = mock_response

        reports, error = self.handler.get_reports(project_id=1)

        assert error == ""
        assert len(reports) == 2
        assert reports[0]["id"] == 1
        assert reports[0]["name"] == "Activity Summary (Cases)"
        assert reports[1]["id"] == 2
        self.api_client.send_get.assert_called_once_with("get_reports/1")

    def test_get_reports_api_error(self):
        """Test handling of API errors when getting reports."""
        mock_response = MagicMock()
        mock_response.error_message = "Invalid or unknown project"
        self.api_client.send_get.return_value = mock_response

        reports, error = self.handler.get_reports(project_id=999)

        assert error == "Invalid or unknown project"
        assert reports == []
        self.api_client.send_get.assert_called_once_with("get_reports/999")

    def test_get_reports_invalid_response_format(self):
        """Test handling of invalid response format."""
        mock_response = MagicMock()
        mock_response.error_message = ""
        mock_response.response_text = {"invalid": "format"}  # Should be a list
        self.api_client.send_get.return_value = mock_response

        reports, error = self.handler.get_reports(project_id=1)

        assert "Invalid response format" in error
        assert reports == []

    def test_get_reports_empty_list(self):
        """Test handling of empty reports list."""
        mock_response = MagicMock()
        mock_response.error_message = ""
        mock_response.response_text = []
        self.api_client.send_get.return_value = mock_response

        reports, error = self.handler.get_reports(project_id=1)

        assert error == ""
        assert reports == []

    def test_get_cross_project_reports_success(self):
        """Test successful retrieval of cross-project reports."""
        mock_response = MagicMock()
        mock_response.error_message = ""
        mock_response.response_text = [
            {
                "id": 1,
                "name": "Test Execution Projects Summary",
                "description": "Multi-project summary",
                "project_ids": [1, 2, 3],
                "include_open_milestones": True,
                "report_timeframe": "90 days",
            }
        ]
        self.api_client.send_get.return_value = mock_response

        reports, error = self.handler.get_cross_project_reports()

        assert error == ""
        assert len(reports) == 1
        assert reports[0]["id"] == 1
        assert reports[0]["name"] == "Test Execution Projects Summary"
        assert reports[0]["project_ids"] == [1, 2, 3]
        self.api_client.send_get.assert_called_once_with("get_cross_project_reports")

    def test_get_cross_project_reports_enterprise_only_error(self):
        """Test handling of non-Enterprise access error."""
        mock_response = MagicMock()
        mock_response.error_message = "Access denied"
        self.api_client.send_get.return_value = mock_response

        reports, error = self.handler.get_cross_project_reports()

        assert error == "Access denied"
        assert reports == []

    def test_get_cross_project_reports_invalid_response(self):
        """Test handling of invalid response format for cross-project reports."""
        mock_response = MagicMock()
        mock_response.error_message = ""
        mock_response.response_text = "not a list"
        self.api_client.send_get.return_value = mock_response

        reports, error = self.handler.get_cross_project_reports()

        assert "Invalid response format" in error
        assert reports == []

    def test_run_report_success(self):
        """Test successful report execution."""
        mock_response = MagicMock()
        mock_response.error_message = ""
        mock_response.response_text = {
            "report_url": "https://example.testrail.com/index.php?/reports/view/383",
            "report_html": "https://example.testrail.com/index.php?/reports/get_html/383",
            "report_pdf": "https://example.testrail.com/index.php?/reports/get_pdf/383",
        }
        self.api_client.send_get.return_value = mock_response

        report_urls, error = self.handler.run_report(report_template_id=5)

        assert error == ""
        assert report_urls is not None
        assert "report_url" in report_urls
        assert "report_html" in report_urls
        assert "report_pdf" in report_urls
        assert "view/383" in report_urls["report_url"]
        self.api_client.send_get.assert_called_once_with("run_report/5")

    def test_run_report_invalid_template_id(self):
        """Test handling of invalid report template ID."""
        mock_response = MagicMock()
        mock_response.error_message = "Invalid report template ID"
        self.api_client.send_get.return_value = mock_response

        report_urls, error = self.handler.run_report(report_template_id=999)

        assert error == "Invalid report template ID"
        assert report_urls is None

    def test_run_report_invalid_response_format(self):
        """Test handling of invalid response format when running report."""
        mock_response = MagicMock()
        mock_response.error_message = ""
        mock_response.response_text = ["not", "a", "dict"]
        self.api_client.send_get.return_value = mock_response

        report_urls, error = self.handler.run_report(report_template_id=5)

        assert "Invalid response format" in error
        assert report_urls is None

    def test_run_cross_project_report_success(self):
        """Test successful cross-project report execution."""
        mock_response = MagicMock()
        mock_response.error_message = ""
        mock_response.response_text = {
            "report_url": "https://example.testrail.com/index.php?/cross_project_reports/view/383",
            "report_html": "https://example.testrail.com/index.php?/cross_project_reports/get_html/383",
            "report_pdf": "https://example.testrail.com/index.php?/cross_project_reports/get_pdf/383",
        }
        self.api_client.send_get.return_value = mock_response

        report_urls, error = self.handler.run_cross_project_report(report_template_id=3)

        assert error == ""
        assert report_urls is not None
        assert "cross_project_reports" in report_urls["report_url"]
        assert "cross_project_reports" in report_urls["report_html"]
        assert "cross_project_reports" in report_urls["report_pdf"]
        self.api_client.send_get.assert_called_once_with("run_cross_project_report/3")

    def test_run_cross_project_report_no_access(self):
        """Test handling of no access error for cross-project report."""
        mock_response = MagicMock()
        mock_response.error_message = "No access to the project"
        self.api_client.send_get.return_value = mock_response

        report_urls, error = self.handler.run_cross_project_report(report_template_id=3)

        assert error == "No access to the project"
        assert report_urls is None

    def test_run_cross_project_report_invalid_response(self):
        """Test handling of invalid response format for cross-project report execution."""
        mock_response = MagicMock()
        mock_response.error_message = ""
        mock_response.response_text = "invalid response"
        self.api_client.send_get.return_value = mock_response

        report_urls, error = self.handler.run_cross_project_report(report_template_id=3)

        assert "Invalid response format" in error
        assert report_urls is None
