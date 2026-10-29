import pytest
from unittest.mock import MagicMock

from trcli.api.datasets_handler import DatasetsHandler
from trcli.api.api_client import APIClient
from trcli.cli import Environment


class TestDatasetsHandler:
    """Test class for DatasetsHandler"""

    def setup_method(self):
        """Set up test fixtures"""
        self.mock_client = MagicMock(spec=APIClient)
        self.environment = Environment()
        self.environment.host = "https://test.testrail.com"
        self.handler = DatasetsHandler(client=self.mock_client, environment=self.environment)

    def test_get_dataset_success(self):
        """Test retrieving a single dataset by ID"""
        dataset_data = {
            "id": 123,
            "name": "Chrome_Dataset",
            "variables": [
                {"name": "browser", "value": "Chrome"},
                {"name": "version", "value": "120.0"},
            ],
        }
        mock_response = MagicMock()
        mock_response.error_message = None
        mock_response.response_text = dataset_data
        self.mock_client.send_get.return_value = mock_response

        result, error = self.handler.get_dataset(dataset_id=123)

        assert result == dataset_data
        assert error == ""
        self.mock_client.send_get.assert_called_once_with("get_dataset/123")

    def test_get_dataset_error(self):
        """Test retrieving a dataset with API error"""
        mock_response = MagicMock()
        mock_response.error_message = "Dataset not found"
        mock_response.response_text = None
        self.mock_client.send_get.return_value = mock_response

        result, error = self.handler.get_dataset(dataset_id=999)

        assert result == {}
        assert error == "Dataset not found"

    def test_get_datasets_success(self):
        """Test retrieving datasets list with default parameters"""
        datasets_data = {
            "datasets": [
                {"id": 1, "name": "Default", "variables": []},
                {"id": 2, "name": "Test_Dataset", "variables": [{"name": "browser", "value": "Chrome"}]},
            ],
            "offset": 0,
            "limit": 250,
            "size": 2,
            "_links": {},
        }
        mock_response = MagicMock()
        mock_response.error_message = None
        mock_response.response_text = datasets_data
        self.mock_client.send_get.return_value = mock_response

        result, error = self.handler.get_datasets(project_id=1)

        assert result == datasets_data
        assert error == ""
        self.mock_client.send_get.assert_called_once_with("get_datasets/1")

    def test_get_datasets_with_pagination(self):
        """Test retrieving datasets with custom pagination"""
        datasets_data = {"datasets": [], "offset": 250, "limit": 100, "size": 0, "_links": {}}
        mock_response = MagicMock()
        mock_response.error_message = None
        mock_response.response_text = datasets_data
        self.mock_client.send_get.return_value = mock_response

        result, error = self.handler.get_datasets(project_id=1, limit=100, offset=250)

        assert result == datasets_data
        assert error == ""
        self.mock_client.send_get.assert_called_once_with("get_datasets/1&limit=100&offset=250")

    def test_get_datasets_error(self):
        """Test retrieving datasets with API error"""
        mock_response = MagicMock()
        mock_response.error_message = "Project not found"
        mock_response.response_text = None
        self.mock_client.send_get.return_value = mock_response

        result, error = self.handler.get_datasets(project_id=999)

        assert result == {}
        assert error == "Project not found"

    def test_add_dataset_with_variables(self):
        """Test adding a dataset with variables"""
        variables = {"browser": "Chrome", "version": "120.0"}
        created_dataset = {
            "id": 456,
            "name": "Chrome_Dataset",
            "variables": [
                {"name": "browser", "value": "Chrome"},
                {"name": "version", "value": "120.0"},
            ],
        }
        mock_response = MagicMock()
        mock_response.error_message = None
        mock_response.response_text = created_dataset
        self.mock_client.send_post.return_value = mock_response

        result, error = self.handler.add_dataset(project_id=1, name="Chrome_Dataset", variables=variables)

        assert result == created_dataset
        assert error == ""
        self.mock_client.send_post.assert_called_once_with(
            "add_dataset/1", {"name": "Chrome_Dataset", "variables": variables}
        )

    def test_add_dataset_without_variables(self):
        """Test adding a dataset without variables (None should send empty object)"""
        created_dataset = {"id": 456, "name": "Firefox_Dataset", "variables": []}
        mock_response = MagicMock()
        mock_response.error_message = None
        mock_response.response_text = created_dataset
        self.mock_client.send_post.return_value = mock_response

        result, error = self.handler.add_dataset(project_id=1, name="Firefox_Dataset", variables=None)

        assert result == created_dataset
        assert error == ""
        # Verify that empty object {} is sent when variables=None
        self.mock_client.send_post.assert_called_once_with(
            "add_dataset/1", {"name": "Firefox_Dataset", "variables": {}}
        )

    def test_add_dataset_with_empty_variables_dict(self):
        """Test adding a dataset with explicit empty variables dict"""
        created_dataset = {"id": 456, "name": "Edge_Dataset", "variables": []}
        mock_response = MagicMock()
        mock_response.error_message = None
        mock_response.response_text = created_dataset
        self.mock_client.send_post.return_value = mock_response

        result, error = self.handler.add_dataset(project_id=1, name="Edge_Dataset", variables={})

        assert result == created_dataset
        assert error == ""
        # Verify that empty object {} is sent when variables={}
        self.mock_client.send_post.assert_called_once_with("add_dataset/1", {"name": "Edge_Dataset", "variables": {}})

    def test_add_dataset_error(self):
        """Test adding a dataset with API error"""
        mock_response = MagicMock()
        mock_response.error_message = "Invalid variable name"
        mock_response.response_text = None
        self.mock_client.send_post.return_value = mock_response

        result, error = self.handler.add_dataset(project_id=1, name="Test_Dataset", variables={"invalid-var": "value"})

        assert result == {}
        assert error == "Invalid variable name"

    def test_update_dataset_name_only(self):
        """Test updating dataset name only (should send empty variables object)"""
        updated_dataset = {
            "id": 123,
            "name": "Chrome_Latest",
            "variables": [{"name": "browser", "value": "Chrome"}],
        }
        mock_response = MagicMock()
        mock_response.error_message = None
        mock_response.response_text = updated_dataset
        self.mock_client.send_post.return_value = mock_response

        result, error = self.handler.update_dataset(dataset_id=123, name="Chrome_Latest", variables=None)

        assert result == updated_dataset
        assert error == ""
        # Verify that empty object {} is sent when variables=None
        self.mock_client.send_post.assert_called_once_with(
            "update_dataset/123", {"name": "Chrome_Latest", "variables": {}}
        )

    def test_update_dataset_variables_only(self):
        """Test updating dataset variables only"""
        variables = {"browser": "Chrome", "version": "121.0"}
        updated_dataset = {
            "id": 456,
            "name": "Chrome_Dataset",
            "variables": [
                {"name": "browser", "value": "Chrome"},
                {"name": "version", "value": "121.0"},
            ],
        }
        mock_response = MagicMock()
        mock_response.error_message = None
        mock_response.response_text = updated_dataset
        self.mock_client.send_post.return_value = mock_response

        result, error = self.handler.update_dataset(dataset_id=456, name=None, variables=variables)

        assert result == updated_dataset
        assert error == ""
        self.mock_client.send_post.assert_called_once_with("update_dataset/456", {"variables": variables})

    def test_update_dataset_with_empty_variables(self):
        """Test updating dataset with explicit empty variables object"""
        updated_dataset = {
            "id": 123,
            "name": "Chrome_Latest",
            "variables": [{"name": "browser", "value": "Chrome"}],
        }
        mock_response = MagicMock()
        mock_response.error_message = None
        mock_response.response_text = updated_dataset
        self.mock_client.send_post.return_value = mock_response

        result, error = self.handler.update_dataset(dataset_id=123, name="Chrome_Latest", variables={})

        assert result == updated_dataset
        assert error == ""
        # Verify that empty object {} is sent when variables={}
        self.mock_client.send_post.assert_called_once_with(
            "update_dataset/123", {"name": "Chrome_Latest", "variables": {}}
        )

    def test_update_dataset_both_fields(self):
        """Test updating both name and variables"""
        variables = {"api_url": "https://api.prod.com", "timeout": "30"}
        updated_dataset = {
            "id": 789,
            "name": "Production_Environment",
            "variables": [
                {"name": "api_url", "value": "https://api.prod.com"},
                {"name": "timeout", "value": "30"},
            ],
        }
        mock_response = MagicMock()
        mock_response.error_message = None
        mock_response.response_text = updated_dataset
        self.mock_client.send_post.return_value = mock_response

        result, error = self.handler.update_dataset(dataset_id=789, name="Production_Environment", variables=variables)

        assert result == updated_dataset
        assert error == ""
        self.mock_client.send_post.assert_called_once_with(
            "update_dataset/789", {"name": "Production_Environment", "variables": variables}
        )

    def test_update_dataset_no_fields(self):
        """Test updating dataset with no fields provided (should return error)"""
        result, error = self.handler.update_dataset(dataset_id=123, name=None, variables=None)

        assert result == {}
        assert "At least one field" in error
        # Verify no API call was made
        self.mock_client.send_post.assert_not_called()

    def test_update_dataset_error(self):
        """Test updating dataset with API error"""
        mock_response = MagicMock()
        mock_response.error_message = "Dataset not found"
        mock_response.response_text = None
        self.mock_client.send_post.return_value = mock_response

        result, error = self.handler.update_dataset(dataset_id=999, name="New_Name")

        assert result == {}
        assert error == "Dataset not found"

    def test_delete_dataset_success(self):
        """Test deleting a dataset"""
        mock_response = MagicMock()
        mock_response.error_message = None
        mock_response.response_text = {}
        self.mock_client.send_post.return_value = mock_response

        result, error = self.handler.delete_dataset(dataset_id=123)

        assert result == {}
        assert error == ""
        self.mock_client.send_post.assert_called_once_with("delete_dataset/123", {})

    def test_delete_dataset_error(self):
        """Test deleting a dataset with API error"""
        mock_response = MagicMock()
        mock_response.error_message = "Cannot delete Default dataset"
        mock_response.response_text = None
        self.mock_client.send_post.return_value = mock_response

        result, error = self.handler.delete_dataset(dataset_id=1)

        assert result == {}
        assert error == "Cannot delete Default dataset"
