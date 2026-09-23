"""
GroupsHandler - Handles all group-related operations for TestRail

It manages all group operations including:
- Retrieving individual groups
- Listing groups with pagination
"""

from beartype.typing import Tuple, Dict, Any

from trcli.api.api_client import APIClient
from trcli.cli import Environment


class GroupsHandler:
    """Handles all group-related operations for TestRail"""

    def __init__(
        self,
        client: APIClient,
        environment: Environment,
    ):
        """
        Initialize the GroupsHandler

        :param client: APIClient instance for making API calls
        :param environment: Environment configuration
        """
        self.client = client
        self.environment = environment

    def get_group(self, group_id: int) -> Tuple[dict, str]:
        """
        Retrieve a single group by ID

        :param group_id: TestRail group ID
        :returns: Tuple with (group_data_dict, error_message)
        """
        response = self.client.send_get(f"get_group/{group_id}")
        if response.error_message:
            return {}, response.error_message
        return response.response_text, ""

    def get_groups(
        self,
        limit: int = 250,
        offset: int = 0,
    ) -> Tuple[dict, str]:
        """
        Retrieve groups with pagination

        :param limit: Maximum number of groups to return (default: 250)
        :param offset: Offset for pagination (default: 0)
        :returns: Tuple with (paginated_response_dict, error_message)
                  Response dict contains: groups, offset, limit, size, _links
        """
        # Build query parameters
        params = []
        if offset > 0:
            params.append(f"offset={offset}")
        if limit != 250:
            params.append(f"limit={limit}")

        # Build URL
        url = "get_groups"
        if params:
            url += "&" + "&".join(params)

        response = self.client.send_get(url)
        if response.error_message:
            return {}, response.error_message
        return response.response_text, ""
