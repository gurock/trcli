"""
Handler for TestRail case type operations.
Provides methods to retrieve test case type information.
"""

from typing import List, Tuple


class CaseTypeHandler:
    """Handles case type-related API operations."""

    def __init__(self, api_client):
        """
        Initialize CaseTypeHandler.

        Args:
            api_client: APIClient instance for making API calls
        """
        self.api_client = api_client

    def get_case_types(self) -> Tuple[List[dict], str]:
        """
        Get all available test case types.

        Returns:
            Tuple of (list of case type dictionaries, error message)
            Case type dict contains: id, name, is_default
        """
        response = self.api_client.send_get("get_case_types")

        if response.error_message:
            return [], response.error_message

        case_types = response.response_text
        if not isinstance(case_types, list):
            return [], "Invalid response format: expected list of case types"

        return case_types, ""
