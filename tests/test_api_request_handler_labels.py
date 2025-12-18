import pytest
from unittest.mock import Mock, patch, MagicMock, call
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
            status_code=200, response_text={"id": 1, "title": "Test Label"}, error_message=None
        )

        with patch.object(labels_handler.client, "send_post", return_value=mock_response):
            result, error = labels_handler.add_label(project_id=1, title="Test Label")

            assert error is None
            assert result["id"] == 1
            assert result["title"] == "Test Label"

            # Verify the API call was made with correct parameters
            labels_handler.client.send_post.assert_called_once_with("add_label/1", payload={"title": "Test Label"})

    def test_add_label_api_error(self, labels_handler):
        """Test label addition with API error"""
        mock_response = APIClientResult(status_code=400, response_text=None, error_message="Label title already exists")

        with patch.object(labels_handler.client, "send_post", return_value=mock_response):
            result, error = labels_handler.add_label(project_id=1, title="Duplicate Label")

            assert error == "Label title already exists"
            assert result is None

    def test_add_label_json_format(self, labels_handler):
        """Test label addition uses JSON format"""
        mock_response = APIClientResult(
            status_code=200, response_text={"id": 1, "title": "Test Label"}, error_message=None
        )

        with patch.object(labels_handler.client, "send_post", return_value=mock_response):
            result, error = labels_handler.add_label(project_id=1, title="Test Label")

            assert error is None
            # Verify JSON format is used
            call_args = labels_handler.client.send_post.call_args
            assert call_args[1]["payload"] == {"title": "Test Label"}

    def test_update_label_success(self, labels_handler):
        """Test successful label update"""
        mock_response = APIClientResult(
            status_code=200, response_text={"id": 1, "title": "Updated Label"}, error_message=None
        )

        with patch.object(labels_handler.client, "send_post", return_value=mock_response):
            result, error = labels_handler.update_label(label_id=1, project_id=1, title="Updated Label")

            assert error is None
            assert result["id"] == 1
            assert result["title"] == "Updated Label"

            # Verify the API call was made with correct parameters
            labels_handler.client.send_post.assert_called_once_with(
                "update_label/1", payload={"project_id": 1, "title": "Updated Label"}
            )

    def test_update_label_api_error(self, labels_handler):
        """Test label update with API error"""
        mock_response = APIClientResult(status_code=403, response_text=None, error_message="No access to the project")

        with patch.object(labels_handler.client, "send_post", return_value=mock_response):
            result, error = labels_handler.update_label(label_id=1, project_id=1, title="Updated Label")

            assert error == "No access to the project"
            assert result is None

    def test_get_label_success(self, labels_handler):
        """Test successful single label retrieval"""
        mock_response = APIClientResult(
            status_code=200,
            response_text={"id": 1, "title": "Test Label", "created_by": "2", "created_on": "1234567890"},
            error_message=None,
        )

        with patch.object(labels_handler.client, "send_get", return_value=mock_response):
            result, error = labels_handler.get_label(label_id=1)

            assert error is None
            assert result["id"] == 1
            assert result["title"] == "Test Label"
            assert result["created_by"] == "2"

            # Verify the API call was made with correct parameters
            labels_handler.client.send_get.assert_called_once_with("get_label/1")

    def test_get_label_not_found(self, labels_handler):
        """Test single label retrieval when label not found"""
        mock_response = APIClientResult(status_code=400, response_text=None, error_message="Label not found")

        with patch.object(labels_handler.client, "send_get", return_value=mock_response):
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
                    {"id": 2, "title": "Label 2", "created_by": "3", "created_on": "1234567891"},
                ],
            },
            error_message=None,
        )

        with patch.object(labels_handler.client, "send_get", return_value=mock_response):
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
            response_text={"offset": 10, "limit": 5, "size": 0, "_links": {"next": None, "prev": None}, "labels": []},
            error_message=None,
        )

        with patch.object(labels_handler.client, "send_get", return_value=mock_response):
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
            response_text={"offset": 0, "limit": 250, "size": 1, "labels": [{"id": 1, "title": "Label 1"}]},
            error_message=None,
        )

        with patch.object(labels_handler.client, "send_get", return_value=mock_response):
            result, error = labels_handler.get_labels(project_id=1, offset=0, limit=250)

            assert error is None
            # Should call without pagination parameters since they're defaults
            labels_handler.client.send_get.assert_called_once_with("get_labels/1")

    def test_get_labels_api_error(self, labels_handler):
        """Test labels listing with API error"""
        mock_response = APIClientResult(status_code=403, response_text=None, error_message="No access to the project")

        with patch.object(labels_handler.client, "send_get", return_value=mock_response):
            result, error = labels_handler.get_labels(project_id=1)

            assert error == "No access to the project"
            assert result is None

    def test_delete_labels_success(self, labels_handler):
        """Test successful label deletion"""
        mock_response = APIClientResult(status_code=200, response_text="Success", error_message=None)

        with patch.object(labels_handler.client, "send_post", return_value=mock_response):
            success, error = labels_handler.delete_labels(label_ids=[1, 2, 3])

            assert success is True
            assert error is None

            # Verify the API call was made with correct parameters
            labels_handler.client.send_post.assert_called_once_with("delete_labels", payload={"label_ids": [1, 2, 3]})

    def test_delete_label_single_id(self, labels_handler):
        """Test single label deletion"""
        mock_response = APIClientResult(status_code=200, response_text="Success", error_message=None)

        with patch.object(labels_handler.client, "send_post", return_value=mock_response):
            success, error = labels_handler.delete_label(label_id=1)

            assert success is True
            assert error is None

            labels_handler.client.send_post.assert_called_once_with("delete_label/1")

    def test_delete_labels_batch(self, labels_handler):
        """Test batch label deletion with multiple IDs"""
        mock_response = APIClientResult(status_code=200, response_text="Success", error_message=None)

        with patch.object(labels_handler.client, "send_post", return_value=mock_response):
            success, error = labels_handler.delete_labels(label_ids=[1, 2, 3])

            assert success is True
            assert error is None

            labels_handler.client.send_post.assert_called_once_with("delete_labels", payload={"label_ids": [1, 2, 3]})

    def test_delete_labels_api_error(self, labels_handler):
        """Test label deletion with API error"""
        mock_response = APIClientResult(
            status_code=400, response_text=None, error_message="One or more labels not found"
        )

        with patch.object(labels_handler.client, "send_post", return_value=mock_response):
            success, error = labels_handler.delete_labels(label_ids=[999, 1000])

            assert success is False
            assert error == "One or more labels not found"

    def test_delete_labels_forbidden(self, labels_handler):
        """Test label deletion with forbidden access"""
        mock_response = APIClientResult(status_code=403, response_text=None, error_message="No access to the project")

        with patch.object(labels_handler.client, "send_post", return_value=mock_response):
            success, error = labels_handler.delete_labels(label_ids=[1])

            assert success is False
            assert error == "No access to the project"


class TestApiRequestHandlerLabelsCases:
    """Test cases for test case label operations"""

    def setup_method(self):
        """Set up test fixtures"""
        # Create proper objects like the existing fixture
        api_client = APIClient(host_name="http://test.com")
        environment = Environment()
        environment.project = "Test Project"
        environment.batch_size = 10

        # Create a minimal TestRailSuite for testing
        from trcli.data_classes.dataclass_testrail import TestRailSuite

        test_suite = TestRailSuite(name="Test Suite")

        self.labels_handler = ApiRequestHandler(environment, api_client, test_suite, verify=False)

    def test_add_labels_to_cases_success(self):
        """Test successful addition of labels to test cases"""
        with patch.object(self.labels_handler, "_ApiRequestHandler__get_all_cases") as mock_get_cases, patch.object(
            self.labels_handler, "get_labels"
        ) as mock_get_labels, patch.object(self.labels_handler, "add_label") as mock_add_label, patch.object(
            self.labels_handler.client, "send_get"
        ) as mock_send_get, patch.object(
            self.labels_handler.client, "send_post"
        ) as mock_send_post:

            # Mock __get_all_cases response (cases exist)
            mock_get_cases.return_value = (
                [{"id": 1, "title": "Case 1", "suite_id": 1}, {"id": 2, "title": "Case 2", "suite_id": 1}],
                "",
            )

            # Mock get_labels response (label doesn't exist)
            mock_get_labels.return_value = ({"labels": []}, "")

            # Mock add_label response (create new label)
            mock_add_label.return_value = ({"label": {"id": 5, "title": "test-label"}}, "")

            # Mock get_case responses
            mock_send_get.side_effect = [
                MagicMock(status_code=200, response_text={"labels": [], "suite_id": 1, "title": "Case 1"}),  # Case 1
                MagicMock(status_code=200, response_text={"labels": [], "suite_id": 1, "title": "Case 2"}),  # Case 2
            ]

            # Mock update_cases batch response (for multiple cases)
            mock_send_post.return_value = MagicMock(status_code=200)

            # Test the method
            results, error_message = self.labels_handler.add_labels_to_cases(
                case_ids=[1, 2], title="test-label", project_id=1
            )

            # Verify no error
            assert error_message == ""

            # Verify results
            assert len(results["successful_cases"]) == 2
            assert len(results["failed_cases"]) == 0
            assert len(results["max_labels_reached"]) == 0
            assert len(results["case_not_found"]) == 0

            # Verify API calls - should be called twice: once for multi-suite detection, once for case validation
            assert mock_get_cases.call_count == 2
            mock_get_cases.assert_has_calls([call(1, None), call(1, None)])  # Multi-suite detection  # Case validation
            mock_get_labels.assert_called_once_with(1)
            mock_add_label.assert_called_once_with(1, "test-label")
            assert mock_send_get.call_count == 2
            # Should call update_cases/{suite_id} once for batch update
            mock_send_post.assert_called_once_with("update_cases/1", payload={"case_ids": [1, 2], "labels": [5]})

    def test_add_labels_to_cases_single_case(self):
        """Test adding labels to a single test case using update_case endpoint"""
        with patch.object(self.labels_handler, "_ApiRequestHandler__get_all_cases") as mock_get_cases, patch.object(
            self.labels_handler, "get_labels"
        ) as mock_get_labels, patch.object(self.labels_handler, "add_label") as mock_add_label, patch.object(
            self.labels_handler.client, "send_get"
        ) as mock_send_get, patch.object(
            self.labels_handler.client, "send_post"
        ) as mock_send_post:

            # Mock __get_all_cases response (case exists)
            mock_get_cases.return_value = ([{"id": 1, "title": "Case 1"}], "")

            # Mock get_labels response (label doesn't exist)
            mock_get_labels.return_value = ({"labels": []}, "")

            # Mock add_label response (create new label)
            mock_add_label.return_value = ({"label": {"id": 5, "title": "test-label"}}, "")

            # Mock get_case response
            mock_send_get.return_value = MagicMock(
                status_code=200, response_text={"labels": [], "suite_id": 1, "title": "Case 1"}
            )

            # Mock update_case response (for single case)
            mock_send_post.return_value = MagicMock(status_code=200)

            # Test the method with single case
            results, error_message = self.labels_handler.add_labels_to_cases(
                case_ids=[1], title="test-label", project_id=1
            )

            # Verify no error
            assert error_message == ""

            # Verify results
            assert len(results["successful_cases"]) == 1
            assert len(results["failed_cases"]) == 0
            assert len(results["max_labels_reached"]) == 0
            assert len(results["case_not_found"]) == 0

            # Verify API calls
            assert mock_get_cases.call_count == 2
            mock_get_labels.assert_called_once_with(1)
            mock_add_label.assert_called_once_with(1, "test-label")
            assert mock_send_get.call_count == 1
            # Should call update_case/{case_id} once for single case
            mock_send_post.assert_called_once_with("update_case/1", payload={"labels": [5]})

    def test_add_labels_to_cases_existing_label(self):
        """Test adding labels when label already exists"""
        with patch.object(self.labels_handler, "_ApiRequestHandler__get_all_cases") as mock_get_cases, patch.object(
            self.labels_handler, "get_labels"
        ) as mock_get_labels, patch.object(self.labels_handler, "add_label") as mock_add_label, patch.object(
            self.labels_handler.client, "send_get"
        ) as mock_send_get, patch.object(
            self.labels_handler.client, "send_post"
        ) as mock_send_post:

            # Mock __get_all_cases response (case exists)
            mock_get_cases.return_value = ([{"id": 1, "title": "Case 1"}], "")

            # Mock get_labels response (label exists)
            mock_get_labels.return_value = ({"labels": [{"id": 5, "title": "test-label"}]}, "")

            # Mock get_case response
            mock_send_get.return_value = MagicMock(
                status_code=200, response_text={"labels": [], "section_id": 1, "title": "Case 1"}
            )

            # Mock add_label_to_case response
            mock_send_post.return_value = MagicMock(status_code=200)

            # Test the method
            results, error_message = self.labels_handler.add_labels_to_cases(
                case_ids=[1], title="test-label", project_id=1
            )

            # Verify no error
            assert error_message == ""

            # Verify results
            assert len(results["successful_cases"]) == 1
            assert len(results["case_not_found"]) == 0

            # Verify add_label was not called (label already exists)
            mock_add_label.assert_not_called()

    def test_add_labels_to_cases_max_labels_reached(self):
        """Test handling of maximum labels limit (10)"""
        with patch.object(self.labels_handler, "_ApiRequestHandler__get_all_cases") as mock_get_cases, patch.object(
            self.labels_handler, "get_labels"
        ) as mock_get_labels, patch.object(self.labels_handler.client, "send_get") as mock_send_get:

            # Mock __get_all_cases response (case exists)
            mock_get_cases.return_value = ([{"id": 1, "title": "Case 1"}], "")

            # Mock get_labels response
            mock_get_labels.return_value = ({"labels": [{"id": 15, "title": "test-label"}]}, "")

            # Mock get_case response with 10 existing labels (different from test-label)
            existing_labels = [{"id": i, "title": f"label-{i}"} for i in range(1, 11)]
            mock_send_get.return_value = MagicMock(status_code=200, response_text={"labels": existing_labels})

            # Test the method
            results, error_message = self.labels_handler.add_labels_to_cases(
                case_ids=[1], title="test-label", project_id=1
            )

            # Verify no error
            assert error_message == ""

            # Verify results
            assert len(results["successful_cases"]) == 0
            assert len(results["failed_cases"]) == 0
            assert len(results["max_labels_reached"]) == 1
            assert len(results["case_not_found"]) == 0
            assert results["max_labels_reached"][0] == 1

    def test_add_labels_to_cases_label_already_on_case(self):
        """Test handling when label already exists on case"""
        with patch.object(self.labels_handler, "_ApiRequestHandler__get_all_cases") as mock_get_cases, patch.object(
            self.labels_handler, "get_labels"
        ) as mock_get_labels, patch.object(self.labels_handler.client, "send_get") as mock_send_get:

            # Mock __get_all_cases response (case exists)
            mock_get_cases.return_value = ([{"id": 1, "title": "Case 1"}], "")

            # Mock get_labels response
            mock_get_labels.return_value = ({"labels": [{"id": 5, "title": "test-label"}]}, "")

            # Mock get_case response with the label already present
            mock_send_get.return_value = MagicMock(
                status_code=200, response_text={"labels": [{"id": 5, "title": "test-label"}]}
            )

            # Test the method
            results, error_message = self.labels_handler.add_labels_to_cases(
                case_ids=[1], title="test-label", project_id=1
            )

            # Verify no error
            assert error_message == ""

            # Verify results
            assert len(results["successful_cases"]) == 1
            assert len(results["case_not_found"]) == 0
            assert "already exists" in results["successful_cases"][0]["message"]

    def test_add_labels_to_cases_case_not_found(self):
        """Test handling when case IDs don't exist"""
        with patch.object(self.labels_handler, "_ApiRequestHandler__get_all_cases") as mock_get_cases:

            # Mock __get_all_cases response (no cases exist)
            mock_get_cases.return_value = ([], "")

            # Test the method with case IDs that don't exist
            results, error_message = self.labels_handler.add_labels_to_cases(
                case_ids=[999, 1000, 1001], title="test-label", project_id=1
            )

            # Verify no error
            assert error_message == ""

            # Verify results - all cases should be in case_not_found
            assert len(results["case_not_found"]) == 3
            assert 999 in results["case_not_found"]
            assert 1000 in results["case_not_found"]
            assert 1001 in results["case_not_found"]

            # Verify that no other processing happened since no valid cases
            assert len(results["successful_cases"]) == 0
            assert len(results["failed_cases"]) == 0
            assert len(results["max_labels_reached"]) == 0

    def test_get_cases_by_label_with_label_ids(self):
        """Test getting cases by label IDs"""
        with patch.object(self.labels_handler, "_ApiRequestHandler__get_all_cases") as mock_get_cases:

            # Mock cases response
            mock_cases = [
                {"id": 1, "title": "Test Case 1", "labels": [{"id": 5, "title": "label1"}]},
                {"id": 2, "title": "Test Case 2", "labels": [{"id": 6, "title": "label2"}]},
                {"id": 3, "title": "Test Case 3", "labels": [{"id": 5, "title": "label1"}]},
            ]
            mock_get_cases.return_value = (mock_cases, "")

            # Test the method
            matching_cases, error_message = self.labels_handler.get_cases_by_label(
                project_id=1, suite_id=None, label_ids=[5]
            )

            # Verify no error
            assert error_message == ""

            # Verify results (should return cases 1 and 3)
            assert len(matching_cases) == 2
            assert matching_cases[0]["id"] == 1
            assert matching_cases[1]["id"] == 3

    def test_get_cases_by_label_with_title(self):
        """Test getting cases by label title"""
        with patch.object(self.labels_handler, "_ApiRequestHandler__get_all_cases") as mock_get_cases, patch.object(
            self.labels_handler, "get_labels"
        ) as mock_get_labels:

            # Mock labels response
            mock_get_labels.return_value = ({"labels": [{"id": 5, "title": "test-label"}]}, "")

            # Mock cases response
            mock_cases = [
                {"id": 1, "title": "Test Case 1", "labels": [{"id": 5, "title": "test-label"}]},
                {"id": 2, "title": "Test Case 2", "labels": [{"id": 6, "title": "other-label"}]},
            ]
            mock_get_cases.return_value = (mock_cases, "")

            # Test the method
            matching_cases, error_message = self.labels_handler.get_cases_by_label(
                project_id=1, suite_id=None, label_title="test-label"
            )

            # Verify no error
            assert error_message == ""

            # Verify results (should return case 1)
            assert len(matching_cases) == 1
            assert matching_cases[0]["id"] == 1

    def test_get_cases_by_label_title_not_found(self):
        """Test getting cases by non-existent label title"""
        with patch.object(self.labels_handler, "_ApiRequestHandler__get_all_cases") as mock_get_cases, patch.object(
            self.labels_handler, "get_labels"
        ) as mock_get_labels:

            # Mock labels response (no matching label)
            mock_get_labels.return_value = ({"labels": []}, "")

            # Mock get_all_cases to return empty (not called due to early return)
            mock_get_cases.return_value = ([], "")

            # Test the method
            matching_cases, error_message = self.labels_handler.get_cases_by_label(
                project_id=1, suite_id=None, label_title="non-existent-label"
            )

            # Verify error
            assert error_message == ""
            assert matching_cases == []

    def test_get_cases_by_label_no_matching_cases(self):
        """Test getting cases when no cases have the specified label"""
        with patch.object(self.labels_handler, "_ApiRequestHandler__get_all_cases") as mock_get_cases:

            # Mock cases response (no cases with target label)
            mock_cases = [
                {"id": 1, "title": "Test Case 1", "labels": [{"id": 6, "title": "other-label"}]},
                {"id": 2, "title": "Test Case 2", "labels": []},
            ]
            mock_get_cases.return_value = (mock_cases, "")

            # Test the method
            matching_cases, error_message = self.labels_handler.get_cases_by_label(
                project_id=1, suite_id=None, label_ids=[5]
            )

            # Verify no error but no results
            assert error_message == ""
            assert len(matching_cases) == 0


class TestApiRequestHandlerTestLabels:
    """Test class for test label management API methods"""

    def test_add_labels_to_tests_success_single(self, labels_handler):
        """Test successful label addition to a single test"""
        # Mock test validation
        mock_test_response = APIClientResult(
            status_code=200, response_text={"id": 1, "title": "Test 1", "run_id": 1, "labels": []}, error_message=None
        )

        # Mock run validation
        mock_run_response = APIClientResult(
            status_code=200, response_text={"id": 1, "project_id": 1}, error_message=None
        )

        # Mock existing labels
        mock_labels_response = APIClientResult(status_code=200, response_text={"labels": []}, error_message=None)

        # Mock label creation
        mock_add_label_response = APIClientResult(
            status_code=200, response_text={"id": 5, "title": "Test Label"}, error_message=None
        )

        # Mock test update
        mock_update_response = APIClientResult(
            status_code=200, response_text={"id": 1, "labels": [{"id": 5, "title": "Test Label"}]}, error_message=None
        )

        with patch.object(labels_handler.client, "send_get") as mock_get, patch.object(
            labels_handler.client, "send_post"
        ) as mock_post:

            # Setup get responses for validation and label retrieval
            mock_get.side_effect = [
                mock_test_response,  # get_test/{test_id}
                mock_run_response,  # get_run/{run_id}
                mock_labels_response,  # get_labels
                mock_test_response,  # get_test/{test_id} again for labels check
            ]

            # Setup post responses for label creation and test update
            mock_post.side_effect = [mock_add_label_response, mock_update_response]  # add_label  # update_test

            result, error = labels_handler.add_labels_to_tests(test_ids=[1], titles="Test Label", project_id=1)

            assert error == ""
            assert len(result["successful_tests"]) == 1
            assert len(result["failed_tests"]) == 0
            assert len(result["test_not_found"]) == 0
            assert len(result["max_labels_reached"]) == 0

    def test_add_labels_to_tests_test_not_found(self, labels_handler):
        """Test handling of non-existent test IDs"""
        # Mock test not found
        mock_test_response = APIClientResult(status_code=404, response_text=None, error_message="Test not found")

        with patch.object(labels_handler.client, "send_get", return_value=mock_test_response):
            result, error = labels_handler.add_labels_to_tests(test_ids=[999], titles="Test Label", project_id=1)

            assert error == ""
            assert len(result["test_not_found"]) == 1
            assert 999 in result["test_not_found"]

    def test_add_labels_to_tests_max_labels_reached(self, labels_handler):
        """Test handling of tests that already have maximum labels"""
        # Create 10 existing labels
        existing_labels = [{"id": i, "title": f"Label {i}"} for i in range(1, 11)]

        # Mock test with max labels
        mock_test_response = APIClientResult(
            status_code=200,
            response_text={"id": 1, "title": "Test 1", "run_id": 1, "labels": existing_labels},
            error_message=None,
        )

        # Mock run validation
        mock_run_response = APIClientResult(
            status_code=200, response_text={"id": 1, "project_id": 1}, error_message=None
        )

        # Mock existing labels
        mock_labels_response = APIClientResult(status_code=200, response_text={"labels": []}, error_message=None)

        # Mock label creation
        mock_add_label_response = APIClientResult(
            status_code=200, response_text={"id": 11, "title": "New Label"}, error_message=None
        )

        with patch.object(labels_handler.client, "send_get") as mock_get, patch.object(
            labels_handler.client, "send_post"
        ) as mock_post:

            mock_get.side_effect = [
                mock_test_response,  # get_test/{test_id}
                mock_run_response,  # get_run/{run_id}
                mock_labels_response,  # get_labels
                mock_test_response,  # get_test/{test_id} again for labels check
            ]

            mock_post.return_value = mock_add_label_response

            result, error = labels_handler.add_labels_to_tests(test_ids=[1], titles="New Label", project_id=1)

            assert error == ""
            assert len(result["max_labels_reached"]) == 1
            assert 1 in result["max_labels_reached"]

    def test_get_tests_by_label_success(self, labels_handler):
        """Test successful retrieval of tests by label"""
        # Mock runs response
        mock_runs_response = APIClientResult(
            status_code=200, response_text={"runs": [{"id": 1}, {"id": 2}]}, error_message=None
        )

        # Mock tests responses for each run
        mock_tests_response_run1 = APIClientResult(
            status_code=200,
            response_text={
                "tests": [
                    {"id": 1, "title": "Test 1", "labels": [{"id": 5, "title": "Test Label"}]},
                    {"id": 2, "title": "Test 2", "labels": []},
                ]
            },
            error_message=None,
        )

        mock_tests_response_run2 = APIClientResult(
            status_code=200,
            response_text={"tests": [{"id": 3, "title": "Test 3", "labels": [{"id": 5, "title": "Test Label"}]}]},
            error_message=None,
        )

        with patch.object(labels_handler.client, "send_get") as mock_get:
            mock_get.side_effect = [
                mock_runs_response,  # get_runs/{project_id}
                mock_tests_response_run1,  # get_tests/{run_id} for run 1
                mock_tests_response_run2,  # get_tests/{run_id} for run 2
            ]

            result, error = labels_handler.get_tests_by_label(project_id=1, label_ids=[5])

            assert error == ""
            assert len(result) == 2
            assert result[0]["id"] == 1
            assert result[1]["id"] == 3

    def test_get_tests_by_label_with_run_ids(self, labels_handler):
        """Test retrieval of tests by label filtered by specific run IDs"""
        # Mock run responses for specific run IDs
        mock_run_response_1 = APIClientResult(
            status_code=200, response_text={"id": 1, "name": "Test Run 1"}, error_message=None
        )

        mock_run_response_2 = APIClientResult(
            status_code=200, response_text={"id": 2, "name": "Test Run 2"}, error_message=None
        )

        # Mock tests responses for each run
        mock_tests_response_run1 = APIClientResult(
            status_code=200,
            response_text={"tests": [{"id": 1, "title": "Test 1", "labels": [{"id": 5, "title": "Test Label"}]}]},
            error_message=None,
        )

        mock_tests_response_run2 = APIClientResult(
            status_code=200,
            response_text={"tests": [{"id": 2, "title": "Test 2", "labels": [{"id": 5, "title": "Test Label"}]}]},
            error_message=None,
        )

        with patch.object(labels_handler.client, "send_get") as mock_get:
            mock_get.side_effect = [
                mock_run_response_1,  # get_run/1
                mock_run_response_2,  # get_run/2
                mock_tests_response_run1,  # get_tests/1
                mock_tests_response_run2,  # get_tests/2
            ]

            result, error = labels_handler.get_tests_by_label(project_id=1, label_ids=[5], run_ids=[1, 2])

            assert error == ""
            assert len(result) == 2
            assert result[0]["id"] == 1
            assert result[1]["id"] == 2

    def test_get_test_labels_success(self, labels_handler):
        """Test successful retrieval of test labels"""
        # Mock test responses
        mock_test_response1 = APIClientResult(
            status_code=200,
            response_text={"id": 1, "title": "Test 1", "status_id": 1, "labels": [{"id": 5, "title": "Test Label"}]},
            error_message=None,
        )

        mock_test_response2 = APIClientResult(
            status_code=200,
            response_text={"id": 2, "title": "Test 2", "status_id": 2, "labels": []},
            error_message=None,
        )

        with patch.object(labels_handler.client, "send_get") as mock_get:
            mock_get.side_effect = [mock_test_response1, mock_test_response2]

            result, error = labels_handler.get_test_labels([1, 2])

            assert error == ""
            assert len(result) == 2

            # Check first test
            assert result[0]["test_id"] == 1
            assert result[0]["title"] == "Test 1"
            assert result[0]["status_id"] == 1
            assert len(result[0]["labels"]) == 1
            assert result[0]["labels"][0]["title"] == "Test Label"
            assert result[0]["error"] is None

            # Check second test
            assert result[1]["test_id"] == 2
            assert result[1]["title"] == "Test 2"
            assert result[1]["status_id"] == 2
            assert len(result[1]["labels"]) == 0
            assert result[1]["error"] is None

    def test_get_test_labels_test_not_found(self, labels_handler):
        """Test handling of non-existent test IDs in get_test_labels"""
        # Mock test not found
        mock_test_response = APIClientResult(status_code=404, response_text=None, error_message="Test not found")

        with patch.object(labels_handler.client, "send_get", return_value=mock_test_response):
            result, error = labels_handler.get_test_labels([999])

            assert error == ""
            assert len(result) == 1
            assert result[0]["test_id"] == 999
            assert result[0]["error"] == "Test 999 not found or inaccessible"
            assert result[0]["labels"] == []

    def test_add_labels_to_tests_batch_update(self, labels_handler):
        """Test batch update of multiple tests"""
        # Mock test validation for multiple tests
        mock_test_response1 = APIClientResult(
            status_code=200, response_text={"id": 1, "title": "Test 1", "run_id": 1, "labels": []}, error_message=None
        )

        mock_test_response2 = APIClientResult(
            status_code=200, response_text={"id": 2, "title": "Test 2", "run_id": 1, "labels": []}, error_message=None
        )

        # Mock run validation
        mock_run_response = APIClientResult(
            status_code=200, response_text={"id": 1, "project_id": 1}, error_message=None
        )

        # Mock existing labels
        mock_labels_response = APIClientResult(
            status_code=200, response_text={"labels": [{"id": 5, "title": "Test Label"}]}, error_message=None
        )

        # Mock batch update
        mock_batch_response = APIClientResult(status_code=200, response_text={"updated": 2}, error_message=None)

        with patch.object(labels_handler.client, "send_get") as mock_get, patch.object(
            labels_handler.client, "send_post"
        ) as mock_post:

            # Setup get responses
            mock_get.side_effect = [
                mock_test_response1,  # get_test/1
                mock_run_response,  # get_run/1
                mock_test_response2,  # get_test/2
                mock_run_response,  # get_run/1
                mock_labels_response,  # get_labels
                mock_test_response1,  # get_test/1 for labels check
                mock_test_response2,  # get_test/2 for labels check
            ]

            # Setup batch update response
            mock_post.return_value = mock_batch_response

            result, error = labels_handler.add_labels_to_tests(test_ids=[1, 2], titles="Test Label", project_id=1)

            assert error == ""
            assert len(result["successful_tests"]) == 2
