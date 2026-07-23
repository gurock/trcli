"""
Handler for TestRail test operations.
Provides methods to retrieve test information.
"""

from typing import List, Tuple, Dict, Optional


class TestHandler:
    """Handles test-related API operations."""

    def __init__(self, api_client):
        """
        Initialize TestHandler.

        Args:
            api_client: APIClient instance for making API calls
        """
        self.api_client = api_client

    def get_test(self, test_id: int, with_data: Optional[str] = None) -> Tuple[Optional[Dict], str]:
        """
        Get a specific test by ID.

        Args:
            test_id: The ID of the test
            with_data: Optional parameter to get additional data (0 or 1)
                       When 1, returns test data with results and attachments

        Returns:
            Tuple of (test dictionary, error message)
            Test dict contains: id, title, assignedto_id, case_id, run_id, status_id,
            priority_id, type_id, estimate, estimate_forecast, custom fields, labels
            When with_data=1, also includes: results (list), attachments (list)
        """
        endpoint = f"get_test/{test_id}"
        if with_data:
            endpoint += f"&with_data={with_data}"

        response = self.api_client.send_get(endpoint)

        if response.error_message:
            return None, response.error_message

        response_data = response.response_text
        if not isinstance(response_data, dict):
            return None, "Invalid response format: expected test dictionary"

        # When with_data=1, TestRail wraps the test in a 'test' key and includes
        # additional 'results' and 'attachments' keys. We need to extract the test
        # and merge the additional data.
        if with_data == "1" and "test" in response_data:
            test = response_data["test"]
            # Add the additional data to the test object
            test["results"] = response_data.get("results", [])
            test["attachments"] = response_data.get("attachments", [])
            return test, ""

        return response_data, ""

    def get_tests(
        self,
        run_id: int,
        status_id: Optional[str] = None,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
        label_id: Optional[str] = None,
    ) -> Tuple[List[Dict], str]:
        """
        Get all tests for a test run with optional filters.

        Args:
            run_id: The ID of the test run
            status_id: Optional comma-separated list of status IDs to filter by
            limit: Optional limit for pagination (default: 250)
            offset: Optional offset for pagination (default: 0)
            label_id: Optional comma-separated list of label IDs to filter by

        Returns:
            Tuple of (list of test dictionaries, error message)
            Test dict contains: id, title, assignedto_id, case_id, run_id, status_id, etc.
        """
        # Build endpoint with query parameters
        params = []
        if status_id is not None:
            params.append(f"status_id={status_id}")
        if limit is not None:
            params.append(f"limit={limit}")
        if offset is not None:
            params.append(f"offset={offset}")
        if label_id is not None:
            params.append(f"label_id={label_id}")

        endpoint = f"get_tests/{run_id}"
        if params:
            endpoint += "&" + "&".join(params)

        response = self.api_client.send_get(endpoint)

        if response.error_message:
            return [], response.error_message

        response_data = response.response_text

        # Handle paginated response format (with 'tests' key) or direct list
        if isinstance(response_data, dict) and "tests" in response_data:
            tests = response_data["tests"]
        elif isinstance(response_data, list):
            tests = response_data
        else:
            return [], "Invalid response format: expected list of tests or paginated response"

        return tests, ""
