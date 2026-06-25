"""
ResultFieldHandler - Handles all result field-related operations for TestRail

It manages result field query operations including:
- Retrieving all test result custom fields
"""

from beartype.typing import Tuple

from trcli.api.api_client import APIClient


class ResultFieldHandler:
    """Handles all result field-related operations for TestRail"""

    def __init__(self, client: APIClient):
        """
        Initialize the ResultFieldHandler

        :param client: APIClient instance for making API calls
        """
        self.client = client

    def get_result_fields(self) -> Tuple[list, str]:
        """
        Retrieve all available test result custom fields

        :returns: Tuple with (result_fields_list, error_message)
        """
        response = self.client.send_get("get_result_fields")
        if response.error_message:
            return [], response.error_message
        return response.response_text, ""
