import pytest
from unittest.mock import MagicMock

from trcli.api.sharedstep_handler import SharedstepHandler


class TestSharedstepHandler:
    """Test suite for SharedstepHandler class."""

    def setup_method(self):
        """Set up test environment"""
        self.api_client = MagicMock()
        self.handler = SharedstepHandler(self.api_client)

    def test_get_sharedsteps_success(self):
        """Test successful retrieval of sharedsteps."""
        mock_response = MagicMock()
        mock_response.error_message = ""
        mock_response.response_text = {
            "offset": 0,
            "limit": 250,
            "size": 2,
            "_links": {"next": None, "prev": None},
            "shared_steps": [
                {
                    "id": 1,
                    "title": "Login Steps",
                    "project_id": 1,
                    "created_by": 1,
                    "created_on": 1612555977,
                    "updated_by": 1,
                    "updated_on": 1612555977,
                    "custom_steps_separated": [
                        {"content": "Open browser", "expected": "Browser opens", "additional_info": None, "refs": None}
                    ],
                    "case_ids": [25],
                },
                {
                    "id": 2,
                    "title": "Logout Steps",
                    "project_id": 1,
                    "created_by": 1,
                    "created_on": 1612555980,
                    "updated_by": 1,
                    "updated_on": 1612555980,
                    "custom_steps_separated": [
                        {
                            "content": "Click logout",
                            "expected": "User logged out",
                            "additional_info": None,
                            "refs": None,
                        }
                    ],
                    "case_ids": [26],
                },
            ],
        }
        self.api_client.send_get.return_value = mock_response

        sharedsteps, error = self.handler.get_shared_steps(project_id=1)

        assert error == ""
        assert len(sharedsteps) == 2
        assert sharedsteps[0]["id"] == 1
        assert sharedsteps[0]["title"] == "Login Steps"
        assert sharedsteps[1]["id"] == 2
        self.api_client.send_get.assert_called_once_with("get_shared_steps/1")

    def test_get_sharedsteps_with_filters(self):
        """Test retrieval of sharedsteps with filter parameters."""
        mock_response = MagicMock()
        mock_response.error_message = ""
        mock_response.response_text = {"shared_steps": []}
        self.api_client.send_get.return_value = mock_response

        sharedsteps, error = self.handler.get_shared_steps(
            project_id=1, created_by="1,2", refs="TR-123", limit=50, offset=10
        )

        assert error == ""
        assert sharedsteps == []
        # Verify query parameters are included
        call_args = self.api_client.send_get.call_args[0][0]
        assert "get_shared_steps/1" in call_args
        assert "created_by=1,2" in call_args
        assert "refs=TR-123" in call_args
        assert "limit=50" in call_args
        assert "offset=10" in call_args

    def test_get_sharedsteps_api_error(self):
        """Test handling of API errors when getting sharedsteps."""
        mock_response = MagicMock()
        mock_response.error_message = "Invalid or unknown project"
        self.api_client.send_get.return_value = mock_response

        sharedsteps, error = self.handler.get_shared_steps(project_id=999)

        assert error == "Invalid or unknown project"
        assert sharedsteps == []

    def test_get_sharedsteps_array_response(self):
        """Test handling of array response format (fallback)."""
        mock_response = MagicMock()
        mock_response.error_message = ""
        mock_response.response_text = [
            {"id": 1, "title": "Step 1"},
            {"id": 2, "title": "Step 2"},
        ]
        self.api_client.send_get.return_value = mock_response

        sharedsteps, error = self.handler.get_shared_steps(project_id=1)

        assert error == ""
        assert len(sharedsteps) == 2

    def test_get_sharedsteps_invalid_response(self):
        """Test handling of invalid response format."""
        mock_response = MagicMock()
        mock_response.error_message = ""
        mock_response.response_text = "invalid"
        self.api_client.send_get.return_value = mock_response

        sharedsteps, error = self.handler.get_shared_steps(project_id=1)

        assert "Invalid response format" in error
        assert sharedsteps == []

    def test_get_sharedstep_success(self):
        """Test successful retrieval of a single sharedstep."""
        mock_response = MagicMock()
        mock_response.error_message = ""
        mock_response.response_text = {
            "id": 1,
            "title": "Default Login",
            "project_id": 2,
            "created_by": 1,
            "created_on": 1612555977,
            "updated_by": 1,
            "updated_on": 1612555977,
            "custom_steps_separated": [
                {
                    "content": "Navigate to https://localhost/some_app",
                    "additional_info": None,
                    "expected": "Login screen loads",
                    "refs": "TR-123",
                },
                {
                    "content": "Enter Valid Credentials",
                    "additional_info": None,
                    "expected": "Logged in and redirected to dashboard",
                    "refs": None,
                },
            ],
            "case_ids": [25],
        }
        self.api_client.send_get.return_value = mock_response

        sharedstep, error = self.handler.get_shared_step(shared_step_id=1)

        assert error == ""
        assert sharedstep is not None
        assert sharedstep["id"] == 1
        assert sharedstep["title"] == "Default Login"
        assert len(sharedstep["custom_steps_separated"]) == 2
        self.api_client.send_get.assert_called_once_with("get_shared_step/1")

    def test_get_sharedstep_api_error(self):
        """Test handling of API errors when getting a single sharedstep."""
        mock_response = MagicMock()
        mock_response.error_message = "Invalid or unknown sharedstep"
        self.api_client.send_get.return_value = mock_response

        sharedstep, error = self.handler.get_shared_step(shared_step_id=999)

        assert error == "Invalid or unknown sharedstep"
        assert sharedstep is None

    def test_get_sharedstep_invalid_response(self):
        """Test handling of invalid response format for single sharedstep."""
        mock_response = MagicMock()
        mock_response.error_message = ""
        mock_response.response_text = ["not", "a", "dict"]
        self.api_client.send_get.return_value = mock_response

        sharedstep, error = self.handler.get_shared_step(shared_step_id=1)

        assert "Invalid response format" in error
        assert sharedstep is None

    def test_add_sharedstep_success(self):
        """Test successful creation of a sharedstep."""
        mock_response = MagicMock()
        mock_response.error_message = ""
        mock_response.response_text = {
            "id": 1,
            "title": "First Step",
            "project_id": 2,
            "created_by": 1,
            "created_on": 1612555977,
            "updated_by": 1,
            "updated_on": 1612555977,
            "custom_steps_separated": [
                {
                    "content": "Open home page",
                    "additional_info": "Must be a new browser session",
                    "expected": "Login page loads",
                    "refs": "RF-1",
                },
                {"content": "Log In", "additional_info": None, "expected": None, "refs": None},
            ],
            "case_ids": [],
        }
        self.api_client.send_post.return_value = mock_response

        steps = [
            {
                "content": "Open home page",
                "additional_info": "Must be a new browser session",
                "expected": "Login page loads",
                "refs": "RF-1",
            },
            {"content": "Log In"},
        ]

        sharedstep, error = self.handler.add_shared_step(project_id=2, title="First Step", custom_steps_separated=steps)

        assert error == ""
        assert sharedstep is not None
        assert sharedstep["id"] == 1
        assert sharedstep["title"] == "First Step"
        assert len(sharedstep["custom_steps_separated"]) == 2

        # Verify the POST payload
        call_args = self.api_client.send_post.call_args
        assert call_args[0][0] == "add_shared_step/2"
        payload = call_args[0][1]
        assert payload["title"] == "First Step"
        assert len(payload["custom_steps_separated"]) == 2

    def test_add_sharedstep_api_error(self):
        """Test handling of API errors when creating a sharedstep."""
        mock_response = MagicMock()
        mock_response.error_message = "Insufficient permissions"
        self.api_client.send_post.return_value = mock_response

        steps = [{"content": "Step 1"}]
        sharedstep, error = self.handler.add_shared_step(project_id=1, title="Test", custom_steps_separated=steps)

        assert error == "Insufficient permissions"
        assert sharedstep is None

    def test_add_sharedstep_invalid_response(self):
        """Test handling of invalid response format when creating a sharedstep."""
        mock_response = MagicMock()
        mock_response.error_message = ""
        mock_response.response_text = "not a dict"
        self.api_client.send_post.return_value = mock_response

        steps = [{"content": "Step 1"}]
        sharedstep, error = self.handler.add_shared_step(project_id=1, title="Test", custom_steps_separated=steps)

        assert "Invalid response format" in error
        assert sharedstep is None

    def test_update_sharedstep_title_only(self):
        """Test updating only the title of a sharedstep."""
        mock_response = MagicMock()
        mock_response.error_message = ""
        mock_response.response_text = {
            "id": 1,
            "title": "Updated Title",
            "project_id": 2,
            "created_by": 1,
            "created_on": 1612555977,
            "updated_by": 1,
            "updated_on": 1612555999,
            "custom_steps_separated": [{"content": "Old step"}],
            "case_ids": [],
        }
        self.api_client.send_post.return_value = mock_response

        sharedstep, error = self.handler.update_shared_step(shared_step_id=1, title="Updated Title")

        assert error == ""
        assert sharedstep is not None
        assert sharedstep["title"] == "Updated Title"

        # Verify only title was sent
        call_args = self.api_client.send_post.call_args
        assert call_args[0][0] == "update_shared_step/1"
        payload = call_args[0][1]
        assert payload == {"title": "Updated Title"}

    def test_update_sharedstep_steps_only(self):
        """Test updating only the steps of a sharedstep."""
        mock_response = MagicMock()
        mock_response.error_message = ""
        mock_response.response_text = {
            "id": 1,
            "title": "Same Title",
            "project_id": 2,
            "created_by": 1,
            "created_on": 1612555977,
            "updated_by": 1,
            "updated_on": 1612555999,
            "custom_steps_separated": [{"content": "New step"}],
            "case_ids": [],
        }
        self.api_client.send_post.return_value = mock_response

        new_steps = [{"content": "New step"}]
        sharedstep, error = self.handler.update_shared_step(shared_step_id=1, custom_steps_separated=new_steps)

        assert error == ""
        assert sharedstep is not None

        # Verify only steps were sent
        call_args = self.api_client.send_post.call_args
        payload = call_args[0][1]
        assert payload == {"custom_steps_separated": new_steps}

    def test_update_sharedstep_both_fields(self):
        """Test updating both title and steps."""
        mock_response = MagicMock()
        mock_response.error_message = ""
        mock_response.response_text = {
            "id": 1,
            "title": "New Title",
            "custom_steps_separated": [{"content": "New step"}],
        }
        self.api_client.send_post.return_value = mock_response

        new_steps = [{"content": "New step"}]
        sharedstep, error = self.handler.update_shared_step(
            shared_step_id=1, title="New Title", custom_steps_separated=new_steps
        )

        assert error == ""
        assert sharedstep is not None

        # Verify both fields were sent
        call_args = self.api_client.send_post.call_args
        payload = call_args[0][1]
        assert "title" in payload
        assert "custom_steps_separated" in payload

    def test_update_sharedstep_no_fields(self):
        """Test updating with no fields provided."""
        sharedstep, error = self.handler.update_shared_step(shared_step_id=1)

        assert error == "No fields provided for update"
        assert sharedstep is None
        # API should not be called
        self.api_client.send_post.assert_not_called()

    def test_update_sharedstep_api_error(self):
        """Test handling of API errors when updating a sharedstep."""
        mock_response = MagicMock()
        mock_response.error_message = "Invalid or unknown test"
        self.api_client.send_post.return_value = mock_response

        sharedstep, error = self.handler.update_shared_step(shared_step_id=999, title="Test")

        assert error == "Invalid or unknown test"
        assert sharedstep is None

    def test_update_sharedstep_invalid_response(self):
        """Test handling of invalid response format when updating."""
        mock_response = MagicMock()
        mock_response.error_message = ""
        mock_response.response_text = ["invalid"]
        self.api_client.send_post.return_value = mock_response

        sharedstep, error = self.handler.update_shared_step(shared_step_id=1, title="Test")

        assert "Invalid response format" in error
        assert sharedstep is None

    def test_delete_sharedstep_keep_in_cases_default(self):
        """Test successful deletion with default keep_in_cases=True."""
        mock_response = MagicMock()
        mock_response.error_message = ""
        self.api_client.send_post.return_value = mock_response

        success, error = self.handler.delete_shared_step(shared_step_id=1)

        assert error == ""
        assert success is True
        # Verify the API call
        call_args = self.api_client.send_post.call_args
        assert call_args[0][0] == "delete_shared_step/1"
        assert call_args[0][1] == {"keep_in_cases": 1}

    def test_delete_sharedstep_keep_in_cases_true(self):
        """Test successful deletion with explicit keep_in_cases=True."""
        mock_response = MagicMock()
        mock_response.error_message = ""
        self.api_client.send_post.return_value = mock_response

        success, error = self.handler.delete_shared_step(shared_step_id=5, keep_in_cases=True)

        assert error == ""
        assert success is True
        call_args = self.api_client.send_post.call_args
        assert call_args[0][0] == "delete_shared_step/5"
        assert call_args[0][1] == {"keep_in_cases": 1}

    def test_delete_sharedstep_keep_in_cases_false(self):
        """Test successful deletion with keep_in_cases=False."""
        mock_response = MagicMock()
        mock_response.error_message = ""
        self.api_client.send_post.return_value = mock_response

        success, error = self.handler.delete_shared_step(shared_step_id=10, keep_in_cases=False)

        assert error == ""
        assert success is True
        call_args = self.api_client.send_post.call_args
        assert call_args[0][0] == "delete_shared_step/10"
        assert call_args[0][1] == {"keep_in_cases": 0}

    def test_delete_sharedstep_api_error(self):
        """Test handling of API errors when deleting."""
        mock_response = MagicMock()
        mock_response.error_message = "Invalid or unknown shared step"
        self.api_client.send_post.return_value = mock_response

        success, error = self.handler.delete_shared_step(shared_step_id=999)

        assert error == "Invalid or unknown shared step"
        assert success is False
