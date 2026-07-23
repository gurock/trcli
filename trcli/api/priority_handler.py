"""
Handler for TestRail priority operations.
Provides methods to retrieve test case priority information.
"""

from typing import List, Tuple


class PriorityHandler:
    """Handles priority-related API operations."""

    def __init__(self, api_client):
        """
        Initialize PriorityHandler.

        Args:
            api_client: APIClient instance for making API calls
        """
        self.api_client = api_client

    def get_priorities(self) -> Tuple[List[dict], str]:
        """
        Get all available test case priorities.

        Returns:
            Tuple of (list of priority dictionaries, error message)
            Priority dict contains: id, name, short_name, priority, is_default
        """
        response = self.api_client.send_get("get_priorities")

        if response.error_message:
            return [], response.error_message

        priorities = response.response_text
        if not isinstance(priorities, list):
            return [], "Invalid response format: expected list of priorities"

        return priorities, ""
