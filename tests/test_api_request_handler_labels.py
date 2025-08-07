import pytest
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path
import json
from serde.json import from_json

from trcli.api.api_request_handler import ApiRequestHandler
from trcli.api.api_client import APIClient, APIClientResult
from trcli.cli import Environment
from trcli.data_classes.dataclass_testrail import TestRailSuite
from trcli.data_classes.data_parsers import MatchersParser
from tests.helpers.api_client_helpers import TEST_RAIL_URL


@pytest.fixture(scope="function")
def labels_handler():
    """Create an ApiRequestHandler instance for testing label methods"""
    api_client = APIClient(host_name=TEST_RAIL_URL)
    environment = Environment()
    environment.project = "Test Project"
    environment.batch_size = 10
    environment.case_matcher = MatchersParser.AUTO

    
    # Load test data
    json_path = Path(__file__).parent / "test_data/json/api_request_handler.json"
    with open(json_path) as file_json:
        json_string = json.dumps(json.load(file_json))
    test_input = from_json(TestRailSuite, json_string)
    
    api_request = ApiRequestHandler(environment, api_client, test_input, verify=False)
    return api_request


class TestApiRequestHandlerLabels:
    """Test class for label management API methods"""

    def test_add_label_success(self, labels_handler):
        """Test successful label addition"""
        # Mock the API client response
        mock_response = APIClientResult(
            status_code=200,
            response_text={"id": 1, "title": "Test Label"},
            error_message=None
        )
        
        with patch.object(labels_handler.client, 'send_post', return_value=mock_response):
            result, error = labels_handler.add_label(project_id=1, title="Test Label")
            
            assert error is None
            assert result["id"] == 1
            assert result["title"] == "Test Label"
            
            # Verify the API call was made with correct parameters
            labels_handler.client.send_post.assert_called_once_with(
                "add_label/1",
                payload=None,
                files={'title': (None, "Test Label")}
            )

    def test_add_label_api_error(self, labels_handler):
        """Test label addition with API error"""
        mock_response = APIClientResult(
            status_code=400,
            response_text=None,
            error_message="Label title already exists"
        )
        
        with patch.object(labels_handler.client, 'send_post', return_value=mock_response):
            result, error = labels_handler.add_label(project_id=1, title="Duplicate Label")
            
            assert error == "Label title already exists"
            assert result is None

    def test_add_label_multipart_format(self, labels_handler):
        """Test label addition uses multipart/form-data format"""
        mock_response = APIClientResult(
            status_code=200,
            response_text={"id": 1, "title": "Test Label"},
            error_message=None
        )
        
        with patch.object(labels_handler.client, 'send_post', return_value=mock_response):
            result, error = labels_handler.add_label(project_id=1, title="Test Label")
            
            assert error is None
            # Verify multipart/form-data format is used
            call_args = labels_handler.client.send_post.call_args
            assert call_args[1]['payload'] is None
            assert call_args[1]['files'] == {'title': (None, "Test Label")}

    def test_update_label_success(self, labels_handler):
        """Test successful label update"""
        mock_response = APIClientResult(
            status_code=200,
            response_text={"id": 1, "title": "Updated Label"},
            error_message=None
        )
        
        with patch.object(labels_handler.client, 'send_post', return_value=mock_response):
            result, error = labels_handler.update_label(
                label_id=1, project_id=1, title="Updated Label"
            )
            
            assert error is None
            assert result["id"] == 1
            assert result["title"] == "Updated Label"
            
            # Verify the API call was made with correct parameters
            labels_handler.client.send_post.assert_called_once_with(
                "update_label/1",
                payload=None,
                files={'project_id': (None, '1'), 'title': (None, "Updated Label")}
            )

    def test_update_label_api_error(self, labels_handler):
        """Test label update with API error"""
        mock_response = APIClientResult(
            status_code=403,
            response_text=None,
            error_message="No access to the project"
        )
        
        with patch.object(labels_handler.client, 'send_post', return_value=mock_response):
            result, error = labels_handler.update_label(
                label_id=1, project_id=1, title="Updated Label"
            )
            
            assert error == "No access to the project"
            assert result is None

    def test_get_label_success(self, labels_handler):
        """Test successful single label retrieval"""
        mock_response = APIClientResult(
            status_code=200,
            response_text={
                "id": 1,
                "title": "Test Label",
                "created_by": "2",
                "created_on": "1234567890"
            },
            error_message=None
        )
        
        with patch.object(labels_handler.client, 'send_get', return_value=mock_response):
            result, error = labels_handler.get_label(label_id=1)
            
            assert error is None
            assert result["id"] == 1
            assert result["title"] == "Test Label"
            assert result["created_by"] == "2"
            
            # Verify the API call was made with correct parameters
            labels_handler.client.send_get.assert_called_once_with("get_label/1")

    def test_get_label_not_found(self, labels_handler):
        """Test single label retrieval when label not found"""
        mock_response = APIClientResult(
            status_code=400,
            response_text=None,
            error_message="Label not found"
        )
        
        with patch.object(labels_handler.client, 'send_get', return_value=mock_response):
            result, error = labels_handler.get_label(label_id=999)
            
            assert error == "Label not found"
            assert result is None

    def test_get_labels_success(self, labels_handler):
        """Test successful labels listing"""
        mock_response = APIClientResult(
            status_code=200,
            response_text={
                "offset": 0,
                "limit": 250,
                "size": 2,
                "_links": {"next": None, "prev": None},
                "labels": [
                    {"id": 1, "title": "Label 1", "created_by": "2", "created_on": "1234567890"},
                    {"id": 2, "title": "Label 2", "created_by": "3", "created_on": "1234567891"}
                ]
            },
            error_message=None
        )
        
        with patch.object(labels_handler.client, 'send_get', return_value=mock_response):
            result, error = labels_handler.get_labels(project_id=1)
            
            assert error is None
            assert result["size"] == 2
            assert len(result["labels"]) == 2
            assert result["labels"][0]["id"] == 1
            assert result["labels"][1]["id"] == 2
            
            # Verify the API call was made with correct parameters
            labels_handler.client.send_get.assert_called_once_with("get_labels/1")

    def test_get_labels_with_pagination(self, labels_handler):
        """Test labels listing with custom pagination parameters"""
        mock_response = APIClientResult(
            status_code=200,
            response_text={
                "offset": 10,
                "limit": 5,
                "size": 0,
                "_links": {"next": None, "prev": None},
                "labels": []
            },
            error_message=None
        )
        
        with patch.object(labels_handler.client, 'send_get', return_value=mock_response):
            result, error = labels_handler.get_labels(project_id=1, offset=10, limit=5)
            
            assert error is None
            assert result["offset"] == 10
            assert result["limit"] == 5
            assert len(result["labels"]) == 0
            
            # Verify the API call was made with pagination parameters
            labels_handler.client.send_get.assert_called_once_with("get_labels/1&offset=10&limit=5")

    def test_get_labels_with_default_pagination(self, labels_handler):
        """Test labels listing with default pagination (should not add parameters)"""
        mock_response = APIClientResult(
            status_code=200,
            response_text={
                "offset": 0,
                "limit": 250,
                "size": 1,
                "labels": [{"id": 1, "title": "Label 1"}]
            },
            error_message=None
        )
        
        with patch.object(labels_handler.client, 'send_get', return_value=mock_response):
            result, error = labels_handler.get_labels(project_id=1, offset=0, limit=250)
            
            assert error is None
            # Should call without pagination parameters since they're defaults
            labels_handler.client.send_get.assert_called_once_with("get_labels/1")

    def test_get_labels_api_error(self, labels_handler):
        """Test labels listing with API error"""
        mock_response = APIClientResult(
            status_code=403,
            response_text=None,
            error_message="No access to the project"
        )
        
        with patch.object(labels_handler.client, 'send_get', return_value=mock_response):
            result, error = labels_handler.get_labels(project_id=1)
            
            assert error == "No access to the project"
            assert result is None

    def test_delete_labels_success(self, labels_handler):
        """Test successful label deletion"""
        mock_response = APIClientResult(
            status_code=200,
            response_text="Success",
            error_message=None
        )
        
        with patch.object(labels_handler.client, 'send_post', return_value=mock_response):
            success, error = labels_handler.delete_labels(label_ids=[1, 2, 3])
            
            assert success is True
            assert error is None
            
            # Verify the API call was made with correct parameters
            labels_handler.client.send_post.assert_called_once_with(
                "delete_labels",
                payload=None,
                files={"label_ids": (None, "1,2,3")}
            )

    def test_delete_label_single_id(self, labels_handler):
        """Test single label deletion"""
        mock_response = APIClientResult(
            status_code=200,
            response_text="Success",
            error_message=None
        )
        
        with patch.object(labels_handler.client, 'send_post', return_value=mock_response):
            success, error = labels_handler.delete_label(label_id=1)
            
            assert success is True
            assert error is None
            
            labels_handler.client.send_post.assert_called_once_with(
                "delete_label/1",
                payload=None
            )

    def test_delete_labels_batch(self, labels_handler):
        """Test batch label deletion with multiple IDs"""
        mock_response = APIClientResult(
            status_code=200,
            response_text="Success",
            error_message=None
        )
        
        with patch.object(labels_handler.client, 'send_post', return_value=mock_response):
            success, error = labels_handler.delete_labels(label_ids=[1, 2, 3])
            
            assert success is True
            assert error is None
            
            labels_handler.client.send_post.assert_called_once_with(
                "delete_labels",
                payload=None,
                files={"label_ids": (None, "1,2,3")}
            )

    def test_delete_labels_api_error(self, labels_handler):
        """Test label deletion with API error"""
        mock_response = APIClientResult(
            status_code=400,
            response_text=None,
            error_message="One or more labels not found"
        )
        
        with patch.object(labels_handler.client, 'send_post', return_value=mock_response):
            success, error = labels_handler.delete_labels(label_ids=[999, 1000])
            
            assert success is False
            assert error == "One or more labels not found"

    def test_delete_labels_forbidden(self, labels_handler):
        """Test label deletion with forbidden access"""
        mock_response = APIClientResult(
            status_code=403,
            response_text=None,
            error_message="No access to the project"
        )
        
        with patch.object(labels_handler.client, 'send_post', return_value=mock_response):
            success, error = labels_handler.delete_labels(label_ids=[1])
            
            assert success is False
            assert error == "No access to the project" 