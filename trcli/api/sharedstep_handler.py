"""
Handler for TestRail sharedstep operations.
Provides methods to retrieve, create, and update sharedsteps.
"""

from typing import List, Tuple, Dict, Optional
from urllib.parse import urlencode


class SharedstepHandler:
    """Handles sharedstep-related API operations."""

    def __init__(self, api_client):
        """
        Initialize SharedstepHandler.

        Args:
            api_client: APIClient instance for making API calls
        """
        self.api_client = api_client

    def get_shared_steps(
        self,
        project_id: int,
        created_after: Optional[int] = None,
        created_before: Optional[int] = None,
        created_by: Optional[str] = None,
        updated_after: Optional[int] = None,
        updated_before: Optional[int] = None,
        refs: Optional[str] = None,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
    ) -> Tuple[List[Dict], str]:
        """
        Get all shared steps for a project with optional filtering.

        Args:
            project_id: The ID of the project
            created_after: Only return shared steps created after this date (UNIX timestamp)
            created_before: Only return shared steps created before this date (UNIX timestamp)
            created_by: Comma-separated list of creator user IDs
            updated_after: Only return shared steps updated after this date (UNIX timestamp)
            updated_before: Only return shared steps updated before this date (UNIX timestamp)
            refs: A single Reference ID (e.g. TR-123)
            limit: Limit the result to N shared steps
            offset: Skip N records

        Returns:
            Tuple of (list of shared step dictionaries, error message)
            Each shared step dict contains: id, title, project_id, created_by, created_on,
            updated_by, updated_on, custom_steps_separated, case_ids
        """
        # Build query parameters dictionary
        params = {}
        if created_after is not None:
            params["created_after"] = created_after
        if created_before is not None:
            params["created_before"] = created_before
        if created_by is not None:
            params["created_by"] = created_by
        if updated_after is not None:
            params["updated_after"] = updated_after
        if updated_before is not None:
            params["updated_before"] = updated_before
        if refs is not None:
            params["refs"] = refs
        if limit is not None:
            params["limit"] = limit
        if offset is not None:
            params["offset"] = offset

        # Build endpoint URL with properly encoded query string
        # Note: TestRail base URL already contains '?' (index.php?/api/v2/),
        # so we use '&' for query parameters, not '?'
        endpoint = f"get_shared_steps/{project_id}"
        if params:
            endpoint += "&" + urlencode(params)

        response = self.api_client.send_get(endpoint)

        if response.error_message:
            return [], response.error_message

        response_data = response.response_text

        # API returns paginated response with shared_steps array
        if isinstance(response_data, dict) and "shared_steps" in response_data:
            return response_data["shared_steps"], ""
        elif isinstance(response_data, list):
            # Fallback if API returns array directly
            return response_data, ""
        else:
            return [], "Invalid response format: expected shared steps data"

    def get_shared_step(self, shared_step_id: int) -> Tuple[Optional[Dict], str]:
        """
        Get details for a single shared step.

        Args:
            shared_step_id: The ID of the shared step

        Returns:
            Tuple of (shared step dictionary, error message)
            Shared step dict contains: id, title, project_id, created_by, created_on,
            updated_by, updated_on, custom_steps_separated, case_ids
        """
        response = self.api_client.send_get(f"get_shared_step/{shared_step_id}")

        if response.error_message:
            return None, response.error_message

        shared_step = response.response_text
        if not isinstance(shared_step, dict):
            return None, "Invalid response format: expected shared step dictionary"

        return shared_step, ""

    def add_shared_step(
        self, project_id: int, title: str, custom_steps_separated: List[Dict]
    ) -> Tuple[Optional[Dict], str]:
        """
        Create a new shared step.

        Args:
            project_id: The ID of the project
            title: The title for the shared step
            custom_steps_separated: Array of step objects with fields:
                - content: Step description
                - expected: Expected result
                - additional_info: Additional information
                - refs: Reference IDs

        Returns:
            Tuple of (created shared step dictionary, error message)
        """
        payload = {"title": title, "custom_steps_separated": custom_steps_separated}

        response = self.api_client.send_post(f"add_shared_step/{project_id}", payload)

        if response.error_message:
            return None, response.error_message

        shared_step = response.response_text
        if not isinstance(shared_step, dict):
            return None, "Invalid response format: expected shared step dictionary"

        return shared_step, ""

    def update_shared_step(
        self,
        shared_step_id: int,
        title: Optional[str] = None,
        custom_steps_separated: Optional[List[Dict]] = None,
    ) -> Tuple[Optional[Dict], str]:
        """
        Update an existing shared step (partial updates supported).

        Args:
            shared_step_id: The ID of the shared step to update
            title: New title for the shared step (optional)
            custom_steps_separated: New array of step objects (optional)
                When provided, ALL existing steps will be replaced

        Returns:
            Tuple of (updated shared step dictionary, error message)

        Note:
            TestRail API requires custom_steps_separated field in all updates.
            If only updating title, we fetch the existing steps and include them.
        """
        if title is None and custom_steps_separated is None:
            return None, "No fields provided for update"

        # If only title is being updated, we need to fetch existing steps
        # because TestRail API requires custom_steps_separated field
        if title is not None and custom_steps_separated is None:
            existing_step, error = self.get_shared_step(shared_step_id)
            if error:
                return None, f"Failed to fetch existing shared step: {error}"

            if not existing_step:
                return None, "Shared step not found"

            # Use existing steps in the update
            custom_steps_separated = existing_step.get("custom_steps_separated", [])

        # Build payload with required fields
        payload = {"custom_steps_separated": custom_steps_separated}

        if title is not None:
            payload["title"] = title

        response = self.api_client.send_post(f"update_shared_step/{shared_step_id}", payload)

        if response.error_message:
            return None, response.error_message

        shared_step = response.response_text
        if not isinstance(shared_step, dict):
            return None, "Invalid response format: expected shared step dictionary"

        return shared_step, ""

    def delete_shared_step(self, shared_step_id: int, keep_in_cases: bool = True) -> Tuple[bool, str]:
        """
        Delete an existing shared step.

        WARNING: Deleting shared test steps cannot be undone.
        By default, deleting a shared step set will keep the steps in all test cases
        which used the set. Use keep_in_cases=False to also remove the steps from test cases.

        Args:
            shared_step_id: The ID of the shared step to delete
            keep_in_cases: Keep steps in test cases (default: True).
                          Set to False to delete steps from test cases as well.

        Returns:
            Tuple of (success boolean, error message)
        """
        payload = {"keep_in_cases": 1 if keep_in_cases else 0}

        response = self.api_client.send_post(f"delete_shared_step/{shared_step_id}", payload)

        if response.error_message:
            return False, response.error_message

        # Successful deletion returns 200 with no data
        return True, ""
