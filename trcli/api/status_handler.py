"""
StatusHandler - Handles all status-related operations for TestRail

It manages status query operations including:
- Retrieving all test result statuses
- Retrieving all case statuses (TestRail Enterprise 7.3+)
"""

from beartype.typing import Tuple

from trcli.api.api_client import APIClient


class StatusHandler:
    """Handles all status-related operations for TestRail"""

    def __init__(self, client: APIClient):
        """
        Initialize the StatusHandler

        :param client: APIClient instance for making API calls
        """
        self.client = client

    def get_statuses(self, project_id: int) -> Tuple[list, str]:
        """
        Retrieve all test result statuses for a project

        :param project_id: TestRail project ID
        :returns: Tuple with (statuses_list, error_message)
        """
        response = self.client.send_get(f"get_statuses/{project_id}")
        if response.error_message:
            return [], response.error_message
        return response.response_text, ""

    def get_case_statuses(self) -> Tuple[list, str]:
        """
        Retrieve all case statuses (TestRail Enterprise 7.3+)

        :returns: Tuple with (case_statuses_list, error_message)
        """
        response = self.client.send_get("get_case_statuses")
        if response.error_message:
            return [], response.error_message
        return response.response_text, ""
