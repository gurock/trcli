"""
MilestoneHandler - Handles all milestone-related operations for TestRail

It manages milestone query operations including:
- Retrieving a single milestone by ID
- Listing milestones for a project
"""

from beartype.typing import Tuple

from trcli.api.api_client import APIClient


class MilestoneHandler:
    """Handles all milestone-related operations for TestRail"""

    def __init__(self, client: APIClient):
        """
        Initialize the MilestoneHandler

        :param client: APIClient instance for making API calls
        """
        self.client = client

    def get_milestone(self, milestone_id: int) -> Tuple[dict, str]:
        """
        Retrieve a single milestone by ID

        :param milestone_id: TestRail milestone ID
        :returns: Tuple with (milestone_data_dict, error_message)
        """
        response = self.client.send_get(f"get_milestone/{milestone_id}")
        if response.error_message:
            return {}, response.error_message
        return response.response_text, ""

    def get_milestones(
        self,
        project_id: int,
        limit: int = 250,
        offset: int = 0,
    ) -> Tuple[dict, str]:
        """
        Retrieve milestones for a project with pagination

        :param project_id: TestRail project ID
        :param limit: Maximum number of milestones to return (default: 250)
        :param offset: Offset for pagination (default: 0)
        :returns: Tuple with (paginated_response_dict, error_message)
                  Response dict contains: milestones, offset, limit, size, _links
        """
        # Build query parameters
        params = []
        if limit != 250:
            params.append(f"limit={limit}")
        if offset > 0:
            params.append(f"offset={offset}")

        # Build URL
        query_string = "&".join(params) if params else ""
        url = f"get_milestones/{project_id}"
        if query_string:
            url = f"{url}&{query_string}"

        response = self.client.send_get(url)
        if response.error_message:
            return {}, response.error_message
        return response.response_text, ""
