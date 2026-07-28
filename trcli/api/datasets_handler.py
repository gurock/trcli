"""
DatasetsHandler - Handles all datasets-related operations for TestRail

It manages all dataset operations including:
- Retrieving individual datasets
- Listing all datasets
- Adding new datasets
- Updating existing datasets
- Deleting datasets
"""

from beartype.typing import Tuple, Optional, Dict, Any

from trcli.api.api_client import APIClient
from trcli.cli import Environment


class DatasetsHandler:
    """Handles all datasets-related operations for TestRail"""

    def __init__(
        self,
        client: APIClient,
        environment: Environment,
    ):
        """
        Initialize the DatasetsHandler

        :param client: APIClient instance for making API calls
        :param environment: Environment configuration
        """
        self.client = client
        self.environment = environment

    def get_dataset(self, dataset_id: int) -> Tuple[dict, str]:
        """
        Retrieve a single dataset by ID

        :param dataset_id: TestRail dataset ID
        :returns: Tuple with (dataset_data_dict, error_message)
        """
        response = self.client.send_get(f"get_dataset/{dataset_id}")
        if response.error_message:
            return {}, response.error_message
        return response.response_text, ""

    def get_datasets(
        self,
        project_id: int,
        limit: int = 250,
        offset: int = 0,
    ) -> Tuple[dict, str]:
        """
        Retrieve datasets for a project with pagination

        :param project_id: TestRail project ID
        :param limit: Maximum number of datasets to return (default: 250)
        :param offset: Offset for pagination (default: 0)
        :returns: Tuple with (paginated_response_dict, error_message)
                  Response dict contains: datasets, offset, limit, size, _links
        """
        # Build query parameters
        params = []
        if limit != 250:
            params.append(f"limit={limit}")
        if offset > 0:
            params.append(f"offset={offset}")

        # Build URL
        query_string = "&".join(params) if params else ""
        url = f"get_datasets/{project_id}"
        if query_string:
            url = f"{url}&{query_string}"

        response = self.client.send_get(url)
        if response.error_message:
            return {}, response.error_message
        return response.response_text, ""

    def add_dataset(
        self,
        project_id: int,
        name: str,
        variables: Optional[Dict[str, str]] = None,
    ) -> Tuple[Dict[str, Any], str]:
        """
        Create a new dataset

        :param project_id: TestRail project ID
        :param name: Name of the dataset (required)
        :param variables: Dictionary of variable_name: value pairs (optional)
        :returns: Tuple with (created_dataset_dict, error_message)
        """
        payload = {"name": name}

        if variables:
            payload["variables"] = variables

        response = self.client.send_post(f"add_dataset/{project_id}", payload)
        if response.error_message:
            return {}, response.error_message

        return response.response_text, ""

    def update_dataset(
        self,
        dataset_id: int,
        name: Optional[str] = None,
        variables: Optional[Dict[str, str]] = None,
    ) -> Tuple[Dict[str, Any], str]:
        """
        Update an existing dataset

        :param dataset_id: TestRail dataset ID
        :param name: New name for the dataset (optional)
        :param variables: Dictionary of variable_name: value pairs (optional)
        :returns: Tuple with (updated_dataset_dict, error_message)
        """
        payload = {}

        if name is not None:
            payload["name"] = name

        if variables:
            payload["variables"] = variables

        if not payload:
            return {}, "Error: At least one field (name or variables) must be provided for update"

        response = self.client.send_post(f"update_dataset/{dataset_id}", payload)
        if response.error_message:
            return {}, response.error_message

        return response.response_text, ""

    def delete_dataset(
        self,
        dataset_id: int,
    ) -> Tuple[dict, str]:
        """
        Delete an existing dataset

        Note: Cannot delete the Default dataset.
        Deleting a dataset also removes the dataset's values.

        :param dataset_id: TestRail dataset ID
        :returns: Tuple with (response_dict, error_message)
        """
        response = self.client.send_post(f"delete_dataset/{dataset_id}", {})
        if response.error_message:
            return {}, response.error_message

        return response.response_text, ""
