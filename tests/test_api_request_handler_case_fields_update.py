"""
Unit tests for update_existing_case_references with case fields support.
Tests the fix for the bug where custom case fields were not being updated.
"""

import pytest
from unittest.mock import MagicMock, patch

from trcli.api.api_request_handler import ApiRequestHandler
from trcli.api.api_client import APIClientResult
from trcli.cli import Environment
from trcli.data_classes.dataclass_testrail import TestRailSuite


class TestUpdateExistingCaseReferencesWithFields:
    """Test class for update_existing_case_references with custom fields"""

    @pytest.fixture
    def handler(self):
        """Create an ApiRequestHandler instance for testing"""
        environment = Environment()
        environment.host = "https://test.testrail.com"
        environment.username = "test@example.com"
        environment.password = "password"

        mock_client = MagicMock()
        suite = TestRailSuite(name="Test Suite")

        handler = ApiRequestHandler(environment=environment, api_client=mock_client, suites_data=suite, verify=False)
        return handler

    def test_update_case_with_refs_and_custom_fields(self, handler):
        """Test updating case with both references and custom fields"""
        # Mock get_case response
        mock_get_case_response = APIClientResult(
            status_code=200, response_text={"id": 1, "title": "Test Case 1", "refs": "REQ-1"}, error_message=None
        )

        # Mock update_case response
        mock_update_response = APIClientResult(
            status_code=200,
            response_text={
                "id": 1,
                "refs": "REQ-1,REQ-2",
                "custom_preconds": "Updated precondition",
                "custom_automation_type": 2,
            },
            error_message=None,
        )

        case_fields = {"custom_preconds": "Updated precondition", "custom_automation_type": 2}

        with patch.object(handler.client, "send_get", return_value=mock_get_case_response), patch.object(
            handler.client, "send_post", return_value=mock_update_response
        ):

            success, error, added_refs, skipped_refs, updated_fields = handler.update_existing_case_references(
                case_id=1, junit_refs="REQ-2", case_fields=case_fields, strategy="append"
            )

            assert success is True
            assert error is None
            assert added_refs == ["REQ-2"]
            assert skipped_refs == []
            assert set(updated_fields) == {"custom_preconds", "custom_automation_type"}

            # Verify the API call included both refs and custom fields
            handler.client.send_post.assert_called_once()
            call_args = handler.client.send_post.call_args
            assert call_args[0][0] == "update_case/1"
            update_data = call_args[0][1]
            assert update_data["refs"] == "REQ-1,REQ-2"
            assert update_data["custom_preconds"] == "Updated precondition"
            assert update_data["custom_automation_type"] == 2

    def test_update_case_with_only_custom_fields(self, handler):
        """Test updating case with only custom fields (no refs)"""
        mock_update_response = APIClientResult(
            status_code=200, response_text={"id": 1, "custom_automation_ids": "AUTO-123"}, error_message=None
        )

        case_fields = {"custom_automation_ids": "AUTO-123", "template_id": 1}

        with patch.object(handler.client, "send_post", return_value=mock_update_response):

            success, error, added_refs, skipped_refs, updated_fields = handler.update_existing_case_references(
                case_id=1, junit_refs="", case_fields=case_fields, strategy="append"  # No refs
            )

            assert success is True
            assert error is None
            assert added_refs == []
            assert skipped_refs == []
            assert set(updated_fields) == {"custom_automation_ids", "template_id"}

            # Verify the API call included only custom fields
            handler.client.send_post.assert_called_once()
            call_args = handler.client.send_post.call_args
            update_data = call_args[0][1]
            assert "refs" not in update_data  # No refs in update
            assert update_data["custom_automation_ids"] == "AUTO-123"
            assert update_data["template_id"] == 1

    def test_update_case_with_only_refs_no_fields(self, handler):
        """Test updating case with only refs (backwards compatibility)"""
        mock_get_case_response = APIClientResult(
            status_code=200, response_text={"id": 1, "title": "Test Case 1", "refs": ""}, error_message=None
        )

        mock_update_response = APIClientResult(
            status_code=200, response_text={"id": 1, "refs": "REQ-1"}, error_message=None
        )

        with patch.object(handler.client, "send_get", return_value=mock_get_case_response), patch.object(
            handler.client, "send_post", return_value=mock_update_response
        ):

            success, error, added_refs, skipped_refs, updated_fields = handler.update_existing_case_references(
                case_id=1, junit_refs="REQ-1", case_fields=None, strategy="append"  # No custom fields
            )

            assert success is True
            assert error is None
            assert added_refs == ["REQ-1"]
            assert skipped_refs == []
            assert updated_fields == []

            # Verify the API call included only refs
            handler.client.send_post.assert_called_once()
            call_args = handler.client.send_post.call_args
            update_data = call_args[0][1]
            assert update_data == {"refs": "REQ-1"}

    def test_update_case_filters_internal_fields(self, handler):
        """Test that internal fields are filtered out from updates"""
        mock_update_response = APIClientResult(status_code=200, response_text={"id": 1}, error_message=None)

        case_fields = {
            "custom_preconds": "Test",
            "case_id": 999,  # Should be filtered
            "section_id": 888,  # Should be filtered
            "result": {"status": "passed"},  # Should be filtered
            "custom_automation_type": 1,
        }

        with patch.object(handler.client, "send_post", return_value=mock_update_response):

            success, error, added_refs, skipped_refs, updated_fields = handler.update_existing_case_references(
                case_id=1, junit_refs="", case_fields=case_fields, strategy="append"
            )

            assert success is True
            # Verify internal fields were filtered out
            assert set(updated_fields) == {"custom_preconds", "custom_automation_type"}

            # Verify the API call excluded internal fields
            call_args = handler.client.send_post.call_args
            update_data = call_args[0][1]
            assert "case_id" not in update_data
            assert "section_id" not in update_data
            assert "result" not in update_data
            assert update_data["custom_preconds"] == "Test"
            assert update_data["custom_automation_type"] == 1

    def test_update_case_no_changes(self, handler):
        """Test when there are no refs and no custom fields to update"""
        success, error, added_refs, skipped_refs, updated_fields = handler.update_existing_case_references(
            case_id=1, junit_refs="", case_fields=None, strategy="append"
        )

        assert success is True
        assert error is None
        assert added_refs == []
        assert skipped_refs == []
        assert updated_fields == []

        # Verify no API call was made
        handler.client.send_post.assert_not_called()

    def test_update_case_refs_append_with_fields(self, handler):
        """Test append strategy for refs with custom fields"""
        mock_get_case_response = APIClientResult(
            status_code=200, response_text={"id": 1, "title": "Test Case 1", "refs": "REQ-1,REQ-2"}, error_message=None
        )

        mock_update_response = APIClientResult(
            status_code=200, response_text={"id": 1, "refs": "REQ-1,REQ-2,REQ-3"}, error_message=None
        )

        case_fields = {"custom_preconds": "New precondition"}

        with patch.object(handler.client, "send_get", return_value=mock_get_case_response), patch.object(
            handler.client, "send_post", return_value=mock_update_response
        ):

            success, error, added_refs, skipped_refs, updated_fields = handler.update_existing_case_references(
                case_id=1, junit_refs="REQ-2,REQ-3", case_fields=case_fields, strategy="append"  # REQ-2 already exists
            )

            assert success is True
            assert added_refs == ["REQ-3"]
            assert skipped_refs == ["REQ-2"]
            assert updated_fields == ["custom_preconds"]

            # Verify refs were appended and field was added
            call_args = handler.client.send_post.call_args
            update_data = call_args[0][1]
            assert update_data["refs"] == "REQ-1,REQ-2,REQ-3"
            assert update_data["custom_preconds"] == "New precondition"

    def test_update_case_refs_replace_with_fields(self, handler):
        """Test replace strategy for refs with custom fields"""
        mock_get_case_response = APIClientResult(
            status_code=200, response_text={"id": 1, "title": "Test Case 1", "refs": "REQ-1,REQ-2"}, error_message=None
        )

        mock_update_response = APIClientResult(
            status_code=200, response_text={"id": 1, "refs": "REQ-3,REQ-4"}, error_message=None
        )

        case_fields = {"custom_automation_type": 2}

        with patch.object(handler.client, "send_get", return_value=mock_get_case_response), patch.object(
            handler.client, "send_post", return_value=mock_update_response
        ):

            success, error, added_refs, skipped_refs, updated_fields = handler.update_existing_case_references(
                case_id=1, junit_refs="REQ-3,REQ-4", case_fields=case_fields, strategy="replace"
            )

            assert success is True
            assert added_refs == ["REQ-3", "REQ-4"]
            assert skipped_refs == []
            assert updated_fields == ["custom_automation_type"]

            # Verify refs were replaced and field was added
            call_args = handler.client.send_post.call_args
            update_data = call_args[0][1]
            assert update_data["refs"] == "REQ-3,REQ-4"
            assert update_data["custom_automation_type"] == 2

    def test_update_case_no_new_refs_but_has_fields(self, handler):
        """Test when all refs are duplicates but custom fields need updating"""
        mock_get_case_response = APIClientResult(
            status_code=200, response_text={"id": 1, "title": "Test Case 1", "refs": "REQ-1,REQ-2"}, error_message=None
        )

        mock_update_response = APIClientResult(status_code=200, response_text={"id": 1}, error_message=None)

        case_fields = {"custom_preconds": "Updated"}

        with patch.object(handler.client, "send_get", return_value=mock_get_case_response), patch.object(
            handler.client, "send_post", return_value=mock_update_response
        ):

            success, error, added_refs, skipped_refs, updated_fields = handler.update_existing_case_references(
                case_id=1, junit_refs="REQ-1,REQ-2", case_fields=case_fields, strategy="append"  # All duplicates
            )

            assert success is True
            assert added_refs == []
            assert skipped_refs == ["REQ-1", "REQ-2"]
            assert updated_fields == ["custom_preconds"]

            # Verify update was still made for custom fields
            handler.client.send_post.assert_called_once()
            call_args = handler.client.send_post.call_args
            update_data = call_args[0][1]
            assert update_data["refs"] == "REQ-1,REQ-2"
            assert update_data["custom_preconds"] == "Updated"
