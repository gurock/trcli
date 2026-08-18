"""
DynamicFilterHandler - Handles dynamic filter field discovery operations for TestRail

This handler manages the discovery of available fields for dynamic filtering,
which enables auto-updating test runs that continuously synchronize with test case repository.
"""

from beartype.typing import Tuple, List, Dict, Any

from trcli.api.api_client import APIClient
from trcli.cli import Environment


class DynamicFilterHandler:
    """Handles dynamic filter field discovery operations for TestRail"""

    def __init__(
        self,
        client: APIClient,
        environment: Environment,
    ):
        """
        Initialize the DynamicFilterHandler

        :param client: APIClient instance for making API calls
        :param environment: Environment configuration
        """
        self.client = client
        self.environment = environment

    def get_dynamic_filter_fields(self, project_id: int) -> Tuple[List[Dict[str, Any]], str]:
        """
        Retrieve available fields for dynamic filtering in a project.

        This endpoint returns the canonical list of fields available for dynamic filtering,
        matching the TestRail UI exactly. Includes both system fields and active custom fields.

        :param project_id: TestRail project ID
        :returns: Tuple with (fields_list, error_message)
                  fields_list contains dicts with keys: type_id, system_name, label,
                  and optionally sub_filters (operators) and options (for dropdowns)
        """
        response = self.client.send_get(f"get_dynamic_filter_fields/{project_id}")
        if response.error_message:
            return [], response.error_message
        return response.response_text, ""
