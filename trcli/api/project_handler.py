"""
Handler for TestRail project operations.
Provides methods to retrieve project information.
"""

from typing import List, Tuple, Dict, Optional


class ProjectHandler:
    """Handles project-related API operations."""

    def __init__(self, api_client):
        """
        Initialize ProjectHandler.

        Args:
            api_client: APIClient instance for making API calls
        """
        self.api_client = api_client

    def get_project(self, project_id: int) -> Tuple[Optional[Dict], str]:
        """
        Get a specific project by ID.

        Args:
            project_id: The ID of the project

        Returns:
            Tuple of (project dictionary, error message)
            Project dict contains: id, name, announcement, completed_on, is_completed,
            suite_mode, show_announcement, url, users, groups, default_role_id, default_role
        """
        response = self.api_client.send_get(f"get_project/{project_id}")

        if response.error_message:
            return None, response.error_message

        project = response.response_text
        if not isinstance(project, dict):
            return None, "Invalid response format: expected project dictionary"

        return project, ""

    def get_projects(
        self, is_completed: Optional[int] = None, limit: Optional[int] = None, offset: Optional[int] = None
    ) -> Tuple[List[Dict], str]:
        """
        Get all projects with optional filters.

        Args:
            is_completed: Optional filter - 1 for completed projects, 0 for active projects
            limit: Optional limit for pagination (default: 250)
            offset: Optional offset for pagination (default: 0)

        Returns:
            Tuple of (list of project dictionaries, error message)
            Project dict contains: id, name, announcement, is_completed, suite_mode, etc.
        """
        # Build endpoint with query parameters
        params = []
        if is_completed is not None:
            params.append(f"is_completed={is_completed}")
        if limit is not None:
            params.append(f"limit={limit}")
        if offset is not None:
            params.append(f"offset={offset}")

        endpoint = "get_projects"
        if params:
            endpoint += "&" + "&".join(params)

        response = self.api_client.send_get(endpoint)

        if response.error_message:
            return [], response.error_message

        response_data = response.response_text

        # Handle paginated response format (with 'projects' key) or direct list
        if isinstance(response_data, dict) and "projects" in response_data:
            projects = response_data["projects"]
        elif isinstance(response_data, list):
            projects = response_data
        else:
            return [], "Invalid response format: expected list of projects or paginated response"

        return projects, ""
