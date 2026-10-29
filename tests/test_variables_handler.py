import pytest
from unittest.mock import MagicMock

from trcli.api.variables_handler import VariablesHandler
from trcli.api.api_client import APIClient
from trcli.cli import Environment


class TestVariablesHandler:
    """Test class for VariablesHandler"""

    def setup_method(self):
        """Set up test fixtures"""
        self.mock_client = MagicMock(spec=APIClient)
        self.environment = Environment()
        self.environment.host = "https://test.testrail.com"
        self.handler = VariablesHandler(client=self.mock_client, environment=self.environment)

    def test_get_variables_success(self):
        """Test retrieving variables list with default parameters"""
        variables_data = {
            "variables": [
                {"id": 1, "name": "browser"},
                {"id": 2, "name": "environment"},
            ],
            "offset": 0,
            "limit": 250,
            "size": 2,
            "_links": {},
        }
        mock_response = MagicMock()
        mock_response.error_message = None
        mock_response.response_text = variables_data
        self.mock_client.send_get.return_value = mock_response

        result, error = self.handler.get_variables(project_id=1)

        assert result == variables_data
        assert error == ""
        self.mock_client.send_get.assert_called_once_with("get_variables/1")

    def test_get_variables_with_pagination(self):
        """Test retrieving variables with custom pagination"""
        variables_data = {"variables": [], "offset": 250, "limit": 100, "size": 0, "_links": {}}
        mock_response = MagicMock()
        mock_response.error_message = None
        mock_response.response_text = variables_data
        self.mock_client.send_get.return_value = mock_response

        result, error = self.handler.get_variables(project_id=1, limit=100, offset=250)

        assert result == variables_data
        assert error == ""
        self.mock_client.send_get.assert_called_once_with("get_variables/1&limit=100&offset=250")

    def test_get_variables_with_limit_only(self):
        """Test retrieving variables with custom limit only"""
        variables_data = {"variables": [], "offset": 0, "limit": 50, "size": 0, "_links": {}}
        mock_response = MagicMock()
        mock_response.error_message = None
        mock_response.response_text = variables_data
        self.mock_client.send_get.return_value = mock_response

        result, error = self.handler.get_variables(project_id=1, limit=50)

        assert result == variables_data
        assert error == ""
        self.mock_client.send_get.assert_called_once_with("get_variables/1&limit=50")

    def test_get_variables_with_offset_only(self):
        """Test retrieving variables with custom offset only"""
        variables_data = {"variables": [], "offset": 100, "limit": 250, "size": 0, "_links": {}}
        mock_response = MagicMock()
        mock_response.error_message = None
        mock_response.response_text = variables_data
        self.mock_client.send_get.return_value = mock_response

        result, error = self.handler.get_variables(project_id=1, offset=100)

        assert result == variables_data
        assert error == ""
        self.mock_client.send_get.assert_called_once_with("get_variables/1&offset=100")

    def test_get_variables_error(self):
        """Test retrieving variables with API error"""
        mock_response = MagicMock()
        mock_response.error_message = "Project not found"
        mock_response.response_text = None
        self.mock_client.send_get.return_value = mock_response

        result, error = self.handler.get_variables(project_id=999)

        assert result == {}
        assert error == "Project not found"

    def test_add_variable_success(self):
        """Test adding a variable"""
        created_variable = {"id": 456, "name": "browser"}
        mock_response = MagicMock()
        mock_response.error_message = None
        mock_response.response_text = created_variable
        self.mock_client.send_post.return_value = mock_response

        result, error = self.handler.add_variable(project_id=1, name="browser")

        assert result == created_variable
        assert error == ""
        self.mock_client.send_post.assert_called_once_with("add_variable/1", {"name": "browser"})

    def test_add_variable_with_underscore(self):
        """Test adding a variable with underscore in name"""
        created_variable = {"id": 457, "name": "api_endpoint"}
        mock_response = MagicMock()
        mock_response.error_message = None
        mock_response.response_text = created_variable
        self.mock_client.send_post.return_value = mock_response

        result, error = self.handler.add_variable(project_id=1, name="api_endpoint")

        assert result == created_variable
        assert error == ""
        self.mock_client.send_post.assert_called_once_with("add_variable/1", {"name": "api_endpoint"})

    def test_add_variable_error(self):
        """Test adding a variable with API error"""
        mock_response = MagicMock()
        mock_response.error_message = "Invalid variable name"
        mock_response.response_text = None
        self.mock_client.send_post.return_value = mock_response

        result, error = self.handler.add_variable(project_id=1, name="invalid-name")

        assert result == {}
        assert error == "Invalid variable name"

    def test_add_variable_duplicate_error(self):
        """Test adding a duplicate variable"""
        mock_response = MagicMock()
        mock_response.error_message = "Variable with this name already exists"
        mock_response.response_text = None
        self.mock_client.send_post.return_value = mock_response

        result, error = self.handler.add_variable(project_id=1, name="browser")

        assert result == {}
        assert error == "Variable with this name already exists"

    def test_update_variable_success(self):
        """Test updating a variable"""
        updated_variable = {"id": 123, "name": "new_browser"}
        mock_response = MagicMock()
        mock_response.error_message = None
        mock_response.response_text = updated_variable
        self.mock_client.send_post.return_value = mock_response

        result, error = self.handler.update_variable(variable_id=123, name="new_browser")

        assert result == updated_variable
        assert error == ""
        self.mock_client.send_post.assert_called_once_with("update_variable/123", {"name": "new_browser"})

    def test_update_variable_rename(self):
        """Test renaming a variable"""
        updated_variable = {"id": 456, "name": "environment_type"}
        mock_response = MagicMock()
        mock_response.error_message = None
        mock_response.response_text = updated_variable
        self.mock_client.send_post.return_value = mock_response

        result, error = self.handler.update_variable(variable_id=456, name="environment_type")

        assert result == updated_variable
        assert error == ""
        self.mock_client.send_post.assert_called_once_with("update_variable/456", {"name": "environment_type"})

    def test_update_variable_error(self):
        """Test updating a variable with API error"""
        mock_response = MagicMock()
        mock_response.error_message = "Variable not found"
        mock_response.response_text = None
        self.mock_client.send_post.return_value = mock_response

        result, error = self.handler.update_variable(variable_id=999, name="new_name")

        assert result == {}
        assert error == "Variable not found"

    def test_update_variable_duplicate_name_error(self):
        """Test updating variable to a name that already exists"""
        mock_response = MagicMock()
        mock_response.error_message = "Variable with this name already exists"
        mock_response.response_text = None
        self.mock_client.send_post.return_value = mock_response

        result, error = self.handler.update_variable(variable_id=123, name="browser")

        assert result == {}
        assert error == "Variable with this name already exists"

    def test_delete_variable_success(self):
        """Test deleting a variable"""
        mock_response = MagicMock()
        mock_response.error_message = None
        mock_response.response_text = {}
        self.mock_client.send_post.return_value = mock_response

        result, error = self.handler.delete_variable(variable_id=123)

        assert result == {}
        assert error == ""
        self.mock_client.send_post.assert_called_once_with("delete_variable/123", {})

    def test_delete_variable_error(self):
        """Test deleting a variable with API error"""
        mock_response = MagicMock()
        mock_response.error_message = "Variable not found"
        mock_response.response_text = None
        self.mock_client.send_post.return_value = mock_response

        result, error = self.handler.delete_variable(variable_id=999)

        assert result == {}
        assert error == "Variable not found"

    def test_delete_variable_in_use_warning(self):
        """Test deleting a variable that's in use (should succeed with warning)"""
        mock_response = MagicMock()
        mock_response.error_message = None
        mock_response.response_text = {}
        self.mock_client.send_post.return_value = mock_response

        result, error = self.handler.delete_variable(variable_id=123)

        assert result == {}
        assert error == ""
        # Note: API handles cascade deletion of values, no error returned
