import pytest
from unittest.mock import MagicMock, patch

from trcli.api.api_request_handler import ApiRequestHandler
from trcli.api.api_client import APIClientResult
from trcli.cli import Environment
from trcli.data_classes.dataclass_testrail import TestRailSuite


class TestApiRequestHandlerReferences:
    """Test class for reference management API methods"""

    @pytest.fixture
    def references_handler(self):
        """Create an ApiRequestHandler instance for testing"""
        environment = Environment()
        environment.host = "https://test.testrail.com"
        environment.username = "test@example.com"
        environment.password = "password"
        
        mock_client = MagicMock()
        suite = TestRailSuite(name="Test Suite")
        
        handler = ApiRequestHandler(
            environment=environment,
            api_client=mock_client,
            suites_data=suite,
            verify=False
        )
        return handler

    def test_add_case_references_success(self, references_handler):
        """Test successful addition of references to a test case"""
        # Mock get_case response
        mock_get_case_response = APIClientResult(
            status_code=200,
            response_text={
                "id": 1,
                "title": "Test Case 1",
                "refs": "REQ-1, REQ-2"
            },
            error_message=None
        )
        
        # Mock update_case response
        mock_update_response = APIClientResult(
            status_code=200,
            response_text={"id": 1, "refs": "REQ-1, REQ-2, REQ-3, REQ-4"},
            error_message=None
        )
        
        with patch.object(references_handler.client, 'send_get', return_value=mock_get_case_response), \
             patch.object(references_handler.client, 'send_post', return_value=mock_update_response):
            
            success, error = references_handler.add_case_references(
                case_id=1,
                references=["REQ-3", "REQ-4"]
            )
            
            assert success is True
            assert error == ""
            
            # Verify the API calls
            references_handler.client.send_get.assert_called_once_with("get_case/1")
            references_handler.client.send_post.assert_called_once_with(
                "update_case/1", 
                {'refs': 'REQ-1,REQ-2,REQ-3,REQ-4'}
            )

    def test_add_case_references_no_existing_refs(self, references_handler):
        """Test adding references to a test case with no existing references"""
        # Mock get_case response with no refs
        mock_get_case_response = APIClientResult(
            status_code=200,
            response_text={
                "id": 1,
                "title": "Test Case 1",
                "refs": ""
            },
            error_message=None
        )
        
        # Mock update_case response
        mock_update_response = APIClientResult(
            status_code=200,
            response_text={"id": 1, "refs": "REQ-1, REQ-2"},
            error_message=None
        )
        
        with patch.object(references_handler.client, 'send_get', return_value=mock_get_case_response), \
             patch.object(references_handler.client, 'send_post', return_value=mock_update_response):
            
            success, error = references_handler.add_case_references(
                case_id=1,
                references=["REQ-1", "REQ-2"]
            )
            
            assert success is True
            assert error == ""
            
            # Verify the update call
            references_handler.client.send_post.assert_called_once_with(
                "update_case/1", 
                {'refs': 'REQ-1,REQ-2'}
            )

    def test_add_case_references_avoid_duplicates(self, references_handler):
        """Test that duplicate references are not added"""
        # Mock get_case response with existing refs
        mock_get_case_response = APIClientResult(
            status_code=200,
            response_text={
                "id": 1,
                "title": "Test Case 1",
                "refs": "REQ-1, REQ-2"
            },
            error_message=None
        )
        
        # Mock update_case response
        mock_update_response = APIClientResult(
            status_code=200,
            response_text={"id": 1, "refs": "REQ-1, REQ-2, REQ-3"},
            error_message=None
        )
        
        with patch.object(references_handler.client, 'send_get', return_value=mock_get_case_response), \
             patch.object(references_handler.client, 'send_post', return_value=mock_update_response):
            
            success, error = references_handler.add_case_references(
                case_id=1,
                references=["REQ-1", "REQ-3"]  # REQ-1 already exists
            )
            
            assert success is True
            assert error == ""
            
            # Verify only REQ-3 was added (no duplicate REQ-1)
            references_handler.client.send_post.assert_called_once_with(
                "update_case/1", 
                {'refs': 'REQ-1,REQ-2,REQ-3'}
            )

    def test_add_case_references_case_not_found(self, references_handler):
        """Test handling of non-existent test case"""
        mock_get_case_response = APIClientResult(
            status_code=404,
            response_text=None,
            error_message="Test case not found"
        )
        
        with patch.object(references_handler.client, 'send_get', return_value=mock_get_case_response):
            
            success, error = references_handler.add_case_references(
                case_id=999,
                references=["REQ-1"]
            )
            
            assert success is False
            assert error == "Failed to retrieve test case 999: Test case not found"

    def test_add_case_references_character_limit_exceeded(self, references_handler):
        """Test character limit validation"""
        # Mock get_case response with existing refs
        mock_get_case_response = APIClientResult(
            status_code=200,
            response_text={
                "id": 1,
                "title": "Test Case 1",
                "refs": "REQ-1" * 500  # Long existing refs
            },
            error_message=None
        )
        
        with patch.object(references_handler.client, 'send_get', return_value=mock_get_case_response):
            
            # Try to add more refs that would exceed 2000 chars (using unique refs to account for deduplication)
            long_refs = [f"REQ-{i}-" + "X" * 500 for i in range(5)]
            
            success, error = references_handler.add_case_references(
                case_id=1,
                references=long_refs
            )
            
            assert success is False
            assert "exceeds 2000 character limit" in error

    def test_add_case_references_deduplication(self, references_handler):
        """Test that duplicate references in input are deduplicated"""
        # Mock get_case response with existing refs
        mock_get_case_response = APIClientResult(
            status_code=200,
            response_text={
                "id": 1,
                "title": "Test Case 1",
                "refs": "REQ-1"
            },
            error_message=None
        )
        
        # Mock update_case response
        mock_update_response = APIClientResult(
            status_code=200,
            response_text={"id": 1, "refs": "REQ-1,REQ-2,REQ-3"},
            error_message=None
        )
        
        with patch.object(references_handler.client, 'send_get', return_value=mock_get_case_response), \
             patch.object(references_handler.client, 'send_post', return_value=mock_update_response):
            
            success, error = references_handler.add_case_references(
                case_id=1,
                references=["REQ-2", "REQ-2", "REQ-3", "REQ-2"]  # Duplicates should be removed
            )
            
            assert success is True
            assert error == ""
            
            # Verify the API call has deduplicated references
            references_handler.client.send_post.assert_called_once_with(
                "update_case/1", 
                {'refs': 'REQ-1,REQ-2,REQ-3'}  # Duplicates removed, order preserved
            )

    def test_update_case_references_success(self, references_handler):
        """Test successful update of references on a test case"""
        # Mock update_case response
        mock_update_response = APIClientResult(
            status_code=200,
            response_text={"id": 1, "refs": "REQ-3, REQ-4"},
            error_message=None
        )
        
        with patch.object(references_handler.client, 'send_post', return_value=mock_update_response):
            
            success, error = references_handler.update_case_references(
                case_id=1,
                references=["REQ-3", "REQ-4"]
            )
            
            assert success is True
            assert error == ""
            
            # Verify the API call
            references_handler.client.send_post.assert_called_once_with(
                "update_case/1", 
                {'refs': 'REQ-3,REQ-4'}
            )

    def test_update_case_references_character_limit_exceeded(self, references_handler):
        """Test character limit validation for update"""
        # Try to update with refs that exceed 2000 chars (using unique refs to account for deduplication)
        long_refs = [f"REQ-{i}-" + "X" * 500 for i in range(5)]
        
        success, error = references_handler.update_case_references(
            case_id=1,
            references=long_refs
        )
        
        assert success is False
        assert "exceeds 2000 character limit" in error

    def test_update_case_references_deduplication(self, references_handler):
        """Test that duplicate references in input are deduplicated"""
        # Mock update_case response
        mock_update_response = APIClientResult(
            status_code=200,
            response_text={"id": 1, "refs": "REQ-1,REQ-2"},
            error_message=None
        )
        
        with patch.object(references_handler.client, 'send_post', return_value=mock_update_response):
            
            success, error = references_handler.update_case_references(
                case_id=1,
                references=["REQ-1", "REQ-1", "REQ-2", "REQ-1"]  # Duplicates should be removed
            )
            
            assert success is True
            assert error == ""
            
            # Verify the API call has deduplicated references
            references_handler.client.send_post.assert_called_once_with(
                "update_case/1", 
                {'refs': 'REQ-1,REQ-2'}  # Duplicates removed, order preserved
            )

    def test_update_case_references_api_failure(self, references_handler):
        """Test API failure during update"""
        # Mock update_case response with failure
        mock_update_response = APIClientResult(
            status_code=400,
            response_text=None,
            error_message="Invalid test case ID"
        )
        
        with patch.object(references_handler.client, 'send_post', return_value=mock_update_response):
            
            success, error = references_handler.update_case_references(
                case_id=1,
                references=["REQ-1"]
            )
            
            assert success is False
            assert error == "Invalid test case ID"

    def test_delete_case_references_all_success(self, references_handler):
        """Test successful deletion of all references"""
        # Mock update_case response
        mock_update_response = APIClientResult(
            status_code=200,
            response_text={"id": 1, "refs": ""},
            error_message=None
        )
        
        with patch.object(references_handler.client, 'send_post', return_value=mock_update_response):
            
            success, error = references_handler.delete_case_references(
                case_id=1,
                specific_references=None  # Delete all
            )
            
            assert success is True
            assert error == ""
            
            # Verify the API call
            references_handler.client.send_post.assert_called_once_with(
                "update_case/1", 
                {'refs': ''}
            )

    def test_delete_case_references_specific_success(self, references_handler):
        """Test successful deletion of specific references"""
        # Mock get_case response
        mock_get_case_response = APIClientResult(
            status_code=200,
            response_text={
                "id": 1,
                "title": "Test Case 1",
                "refs": "REQ-1, REQ-2, REQ-3, REQ-4"
            },
            error_message=None
        )
        
        # Mock update_case response
        mock_update_response = APIClientResult(
            status_code=200,
            response_text={"id": 1, "refs": "REQ-1, REQ-4"},
            error_message=None
        )
        
        with patch.object(references_handler.client, 'send_get', return_value=mock_get_case_response), \
             patch.object(references_handler.client, 'send_post', return_value=mock_update_response):
            
            success, error = references_handler.delete_case_references(
                case_id=1,
                specific_references=["REQ-2", "REQ-3"]
            )
            
            assert success is True
            assert error == ""
            
            # Verify the API calls
            references_handler.client.send_get.assert_called_once_with("get_case/1")
            references_handler.client.send_post.assert_called_once_with(
                "update_case/1", 
                {'refs': 'REQ-1,REQ-4'}
            )

    def test_delete_case_references_no_existing_refs(self, references_handler):
        """Test deletion when no references exist"""
        # Mock get_case response with no refs
        mock_get_case_response = APIClientResult(
            status_code=200,
            response_text={
                "id": 1,
                "title": "Test Case 1",
                "refs": ""
            },
            error_message=None
        )
        
        with patch.object(references_handler.client, 'send_get', return_value=mock_get_case_response):
            
            success, error = references_handler.delete_case_references(
                case_id=1,
                specific_references=["REQ-1"]
            )
            
            assert success is True
            assert error == ""
            
            # Verify no update call was made since there were no refs to delete
            references_handler.client.send_post.assert_not_called()

    def test_delete_case_references_case_not_found(self, references_handler):
        """Test handling of non-existent test case during deletion"""
        mock_get_case_response = APIClientResult(
            status_code=404,
            response_text=None,
            error_message="Test case not found"
        )
        
        with patch.object(references_handler.client, 'send_get', return_value=mock_get_case_response):
            
            success, error = references_handler.delete_case_references(
                case_id=999,
                specific_references=["REQ-1"]
            )
            
            assert success is False
            assert error == "Failed to retrieve test case 999: Test case not found"

