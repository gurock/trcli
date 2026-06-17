"""
CaseFieldHandler - Handles all case field-related operations for TestRail

It manages case field query operations including:
- Retrieving all available test case custom fields
"""

from beartype.typing import Tuple

from trcli.api.api_client import APIClient


class CaseFieldHandler:
    """Handles all case field-related operations for TestRail"""

    def __init__(self, client: APIClient):
        """
        Initialize the CaseFieldHandler

        :param client: APIClient instance for making API calls
        """
        self.client = client

    def get_case_fields(self) -> Tuple[list, str]:
        """
        Retrieve all available test case custom fields

        :returns: Tuple with (case_fields_list, error_message)
        """
        response = self.client.send_get("get_case_fields")
        if response.error_message:
            return [], response.error_message
        return response.response_text, ""
