"""
PlanHandler - Handles all plan-related operations for TestRail

It manages all plan operations including:
- Retrieving individual plans
- Listing plans with pagination
"""

from beartype.typing import Tuple

from trcli.api.api_client import APIClient
from trcli.cli import Environment


class PlanHandler:
    """Handles all plan-related operations for TestRail"""

    def __init__(
        self,
        client: APIClient,
        environment: Environment,
    ):
        """
        Initialize the PlanHandler

        :param client: APIClient instance for making API calls
        :param environment: Environment configuration
        """
        self.client = client
        self.environment = environment

    def get_plan(self, plan_id: int) -> Tuple[dict, str]:
        """
        Retrieve a single test plan by ID

        :param plan_id: TestRail plan ID
        :returns: Tuple with (plan_data_dict, error_message)
        """
        response = self.client.send_get(f"get_plan/{plan_id}")
        if response.error_message:
            return {}, response.error_message
        return response.response_text, ""

    def get_plans(
        self,
        project_id: int,
        limit: int = 250,
        offset: int = 0,
    ) -> Tuple[dict, str]:
        """
        Retrieve test plans for a project with pagination

        :param project_id: TestRail project ID
        :param limit: Maximum number of plans to return (default: 250)
        :param offset: Offset for pagination (default: 0)
        :returns: Tuple with (paginated_response_dict, error_message)
                  Response dict contains: plans, offset, limit, size, _links
        """
        # Build query parameters
        params = []
        if limit != 250:
            params.append(f"limit={limit}")
        if offset > 0:
            params.append(f"offset={offset}")

        # Build URL
        query_string = "&".join(params) if params else ""
        url = f"get_plans/{project_id}"
        if query_string:
            url = f"{url}&{query_string}"

        response = self.client.send_get(url)
        if response.error_message:
            return {}, response.error_message
        return response.response_text, ""
