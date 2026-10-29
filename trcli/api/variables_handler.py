"""
VariablesHandler - Handles all variables-related operations for TestRail

It manages all variable operations including:
- Retrieving variables
- Adding new variables
- Updating existing variables
- Deleting variables
"""

from beartype.typing import Tuple, Optional, Dict, Any

from trcli.api.api_client import APIClient
from trcli.cli import Environment


class VariablesHandler:
    """Handles all variables-related operations for TestRail"""

    def __init__(
        self,
        client: APIClient,
        environment: Environment,
    ):
        """
        Initialize the VariablesHandler

        :param client: APIClient instance for making API calls
        :param environment: Environment configuration
        """
        self.client = client
        self.environment = environment

    def get_variables(
        self,
        project_id: int,
        limit: int = 250,
        offset: int = 0,
    ) -> Tuple[dict, str]:
        """
        Retrieve variables for a project with pagination

        :param project_id: TestRail project ID
        :param limit: Maximum number of variables to return (default: 250)
        :param offset: Offset for pagination (default: 0)
        :returns: Tuple with (paginated_response_dict, error_message)
                  Response dict contains: variables, offset, limit, size, _links
        """
        # Build query parameters
        params = []
        if limit != 250:
            params.append(f"limit={limit}")
        if offset > 0:
            params.append(f"offset={offset}")

        # Build URL
        query_string = "&".join(params) if params else ""
        url = f"get_variables/{project_id}"
        if query_string:
            url = f"{url}&{query_string}"

        response = self.client.send_get(url)
        if response.error_message:
            return {}, response.error_message
        return response.response_text, ""

    def add_variable(
        self,
        project_id: int,
        name: str,
    ) -> Tuple[Dict[str, Any], str]:
        """
        Create a new variable

        :param project_id: TestRail project ID
        :param name: Name of the variable (required)
        :returns: Tuple with (created_variable_dict, error_message)
        """
        payload = {"name": name}

        response = self.client.send_post(f"add_variable/{project_id}", payload)
        if response.error_message:
            return {}, response.error_message

        return response.response_text, ""

    def update_variable(
        self,
        variable_id: int,
        name: str,
    ) -> Tuple[Dict[str, Any], str]:
        """
        Update an existing variable

        :param variable_id: TestRail variable ID
        :param name: New name for the variable (required)
        :returns: Tuple with (updated_variable_dict, error_message)
        """
        payload = {"name": name}

        response = self.client.send_post(f"update_variable/{variable_id}", payload)
        if response.error_message:
            return {}, response.error_message

        return response.response_text, ""

    def delete_variable(
        self,
        variable_id: int,
    ) -> Tuple[dict, str]:
        """
        Delete an existing variable

        Note: Deleting a variable also deletes corresponding values from datasets.

        :param variable_id: TestRail variable ID
        :returns: Tuple with (response_dict, error_message)
        """
        response = self.client.send_post(f"delete_variable/{variable_id}", {})
        if response.error_message:
            return {}, response.error_message

        return response.response_text, ""
