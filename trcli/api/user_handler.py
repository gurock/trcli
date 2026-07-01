"""
Handler for TestRail user operations.
Provides methods to retrieve user information.
"""

from typing import List, Tuple, Dict, Union, Optional


class UserHandler:
    """Handles user-related API operations."""

    def __init__(self, api_client):
        """
        Initialize UserHandler.

        Args:
            api_client: APIClient instance for making API calls
        """
        self.api_client = api_client

    def get_user(self, user_id: int) -> Tuple[Optional[Dict], str]:
        """
        Get a specific user by ID.

        Args:
            user_id: The ID of the user

        Returns:
            Tuple of (user dictionary, error message)
            User dict contains: id, email, name, role, role_id, is_active, is_admin, etc.
        """
        response = self.api_client.send_get(f"get_user/{user_id}")

        if response.error_message:
            return None, response.error_message

        user = response.response_text
        if not isinstance(user, dict):
            return None, "Invalid response format: expected user dictionary"

        return user, ""

    def get_current_user(self) -> Tuple[Optional[Dict], str]:
        """
        Get the current authenticated user.

        Returns:
            Tuple of (user dictionary, error message)
            User dict contains: id, email, name, role, role_id, is_active
        """
        response = self.api_client.send_get("get_current_user")

        if response.error_message:
            return None, response.error_message

        user = response.response_text
        if not isinstance(user, dict):
            return None, "Invalid response format: expected user dictionary"

        return user, ""

    def get_user_by_email(self, email: str) -> Tuple[Optional[Dict], str]:
        """
        Get a specific user by email address.

        Args:
            email: The email address of the user

        Returns:
            Tuple of (user dictionary, error message)
            User dict contains: id, email, name, role, role_id, is_active, is_admin, etc.
        """
        response = self.api_client.send_get(f"get_user_by_email&email={email}")

        if response.error_message:
            return None, response.error_message

        user = response.response_text
        if not isinstance(user, dict):
            return None, "Invalid response format: expected user dictionary"

        return user, ""

    def get_users(self, project_id: Optional[int] = None) -> Tuple[List[Dict], str]:
        """
        Get all users or users for a specific project.

        Args:
            project_id: Optional project ID to filter users by project access

        Returns:
            Tuple of (list of user dictionaries, error message)
            User dict contains: id, name, email (if no project), role, role_id (if project specified)
        """
        if project_id:
            endpoint = f"get_users/{project_id}"
        else:
            endpoint = "get_users"

        response = self.api_client.send_get(endpoint)

        if response.error_message:
            return [], response.error_message

        response_data = response.response_text

        # Handle paginated response format (with 'users' key) or direct list
        if isinstance(response_data, dict) and "users" in response_data:
            users = response_data["users"]
        elif isinstance(response_data, list):
            users = response_data
        else:
            return [], "Invalid response format: expected list of users or paginated response"

        return users, ""
