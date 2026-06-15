"""
ConfigurationHandler - Handles all configuration-related operations for TestRail

It manages configuration query operations including:
- Listing configurations and configuration groups for a project
"""

from beartype.typing import Tuple

from trcli.api.api_client import APIClient


class ConfigurationHandler:
    """Handles all configuration-related operations for TestRail"""

    def __init__(self, client: APIClient):
        """
        Initialize the ConfigurationHandler

        :param client: APIClient instance for making API calls
        """
        self.client = client

    def get_configs(self, project_id: int) -> Tuple[list, str]:
        """
        Retrieve configurations for a project grouped by configuration groups

        :param project_id: TestRail project ID
        :returns: Tuple with (list_of_config_groups, error_message)
                  Each group contains: id, name, project_id, configs (list)
        """
        response = self.client.send_get(f"get_configs/{project_id}")
        if response.error_message:
            return [], response.error_message
        return response.response_text, ""
