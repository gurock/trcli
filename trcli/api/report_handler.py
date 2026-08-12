"""
Handler for TestRail report operations.
Provides methods to retrieve and generate reports.
"""

from typing import List, Tuple, Dict, Optional


class ReportHandler:
    """Handles report-related API operations."""

    def __init__(self, api_client):
        """
        Initialize ReportHandler.

        Args:
            api_client: APIClient instance for making API calls
        """
        self.api_client = api_client

    def get_reports(self, project_id: int) -> Tuple[List[Dict], str]:
        """
        Get all available report templates for a project.

        Args:
            project_id: The ID of the project

        Returns:
            Tuple of (list of report dictionaries, error message)
            Report dict contains: id, name, description, notify_user, notify_link,
            notify_link_recipients, notify_attachment, notify_attachment_html_format,
            notify_attachment_pdf_format, and report-specific fields
        """
        response = self.api_client.send_get(f"get_reports/{project_id}")

        if response.error_message:
            return [], response.error_message

        response_data = response.response_text

        if not isinstance(response_data, list):
            return [], "Invalid response format: expected list of reports"

        return response_data, ""

    def get_cross_project_reports(self) -> Tuple[List[Dict], str]:
        """
        Get all available cross-project report templates (Enterprise only).

        Returns:
            Tuple of (list of report dictionaries, error message)
            Report dict contains: id, name, description, project_ids, include_open_milestones,
            include_completed_milestones, include_open_runs_and_plans,
            include_completed_runs_and_plans, report_timeframe, included_statuses,
            content_hide_links, notify_user, notify_link, notify_attachment, etc.
        """
        response = self.api_client.send_get("get_cross_project_reports")

        if response.error_message:
            return [], response.error_message

        response_data = response.response_text

        if not isinstance(response_data, list):
            return [], "Invalid response format: expected list of cross-project reports"

        return response_data, ""

    def run_report(self, report_template_id: int) -> Tuple[Optional[Dict], str]:
        """
        Execute a report and get URLs for accessing it.

        Args:
            report_template_id: The ID of the report template to execute

        Returns:
            Tuple of (report URLs dictionary, error message)
            URLs dict contains: report_url, report_html, report_pdf
        """
        response = self.api_client.send_get(f"run_report/{report_template_id}")

        if response.error_message:
            return None, response.error_message

        report_urls = response.response_text
        if not isinstance(report_urls, dict):
            return None, "Invalid response format: expected report URLs dictionary"

        return report_urls, ""

    def run_cross_project_report(self, report_template_id: int) -> Tuple[Optional[Dict], str]:
        """
        Execute a cross-project report and get URLs for accessing it (Enterprise only).

        Args:
            report_template_id: The ID of the cross-project report template to execute

        Returns:
            Tuple of (report URLs dictionary, error message)
            URLs dict contains: report_url, report_html, report_pdf
        """
        response = self.api_client.send_get(f"run_cross_project_report/{report_template_id}")

        if response.error_message:
            return None, response.error_message

        report_urls = response.response_text
        if not isinstance(report_urls, dict):
            return None, "Invalid response format: expected report URLs dictionary"

        return report_urls, ""
