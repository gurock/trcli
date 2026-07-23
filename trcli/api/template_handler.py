"""
Handler for TestRail template operations.
Provides methods to retrieve template information.
"""

from typing import List, Tuple, Dict


class TemplateHandler:
    """Handles template-related API operations."""

    def __init__(self, api_client):
        """
        Initialize TemplateHandler.

        Args:
            api_client: APIClient instance for making API calls
        """
        self.api_client = api_client

    def get_templates(self, project_id: int) -> Tuple[List[Dict], str]:
        """
        Get all templates (field layouts) for a project.

        Args:
            project_id: The ID of the project

        Returns:
            Tuple of (list of template dictionaries, error message)
            Template dict contains: id, name, i18n_custom_id, is_default
        """
        response = self.api_client.send_get(f"get_templates/{project_id}")

        if response.error_message:
            return [], response.error_message

        templates = response.response_text

        if not isinstance(templates, list):
            return [], "Invalid response format: expected list of templates"

        return templates, ""
