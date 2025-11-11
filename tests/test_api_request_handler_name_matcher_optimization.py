"""
Unit tests for NAME matcher optimization that skips fetching all cases.

Tests the performance optimization introduced to avoid downloading 165k+ cases
when using NAME or PROPERTY matcher, which only need to validate specific case IDs.
"""

import pytest
from unittest.mock import patch, MagicMock, call
from pathlib import Path
import json
from serde.json import from_json

from tests.helpers.api_client_helpers import TEST_RAIL_URL, create_url
from trcli.cli import Environment
from trcli.api.api_request_handler import ApiRequestHandler
from trcli.api.api_client import APIClient, APIClientResult
from trcli.data_classes.dataclass_testrail import TestRailSuite, TestRailSection, TestRailCase, TestRailResult
from trcli.data_classes.data_parsers import MatchersParser


@pytest.fixture
def environment():
    """Create test environment"""
    env = Environment()
    env.project = "Test Project"
    env.batch_size = 10
    return env


@pytest.fixture
def api_client():
    """Create test API client"""
    return APIClient(host_name=TEST_RAIL_URL)


def create_test_suite_with_case_ids(num_cases=10):
    """Helper to create test suite with specified number of cases with case IDs"""
    test_cases = []
    for i in range(1, num_cases + 1):
        test_case = TestRailCase(
            case_id=i,
            title=f"Test case {i}",
            section_id=1,
            result=TestRailResult(case_id=i, comment=f"Test result {i}", elapsed="1s", status_id=1),
        )
        test_cases.append(test_case)

    section = TestRailSection(name="Test Section", section_id=1, suite_id=1, testcases=test_cases)

    return TestRailSuite(name="Test Suite", suite_id=1, testsections=[section])


def create_test_suite_with_missing_case_ids(total_cases=10, missing_count=3):
    """Helper to create test suite with some cases missing IDs"""
    test_cases = []
    for i in range(1, total_cases + 1):
        # First `missing_count` cases don't have case_id
        case_id = None if i <= missing_count else i
        test_case = TestRailCase(
            case_id=case_id,
            title=f"Test case {i}",
            section_id=1,
            result=TestRailResult(case_id=case_id, comment=f"Test result {i}", elapsed="1s", status_id=1),
        )
        test_cases.append(test_case)

    section = TestRailSection(name="Test Section", section_id=1, suite_id=1, testcases=test_cases)

    return TestRailSuite(name="Test Suite", suite_id=1, testsections=[section])


class TestNameMatcherOptimization:
    """Test suite for NAME matcher performance optimizations"""

    @pytest.mark.api_handler
    def test_name_matcher_skips_bulk_case_fetch(self, environment, api_client, mocker):
        """
        Test that NAME matcher does NOT fetch all cases from TestRail.
        This is the key optimization - we should skip the expensive get_all_cases call.
        """
        # Setup: NAME matcher with 100 test cases
        environment.case_matcher = MatchersParser.NAME
        test_suite = create_test_suite_with_case_ids(num_cases=100)
        api_request_handler = ApiRequestHandler(environment, api_client, test_suite)

        # Mock the get_all_cases method to track if it's called
        mock_get_all_cases = mocker.patch.object(
            api_request_handler, "_ApiRequestHandler__get_all_cases", return_value=([], None)
        )

        # Mock validation to return all IDs as valid (skip actual validation)
        mocker.patch.object(
            api_request_handler, "_ApiRequestHandler__validate_case_ids_exist", return_value=set(range(1, 101))
        )

        # Execute
        project_id = 1
        missing_ids, error = api_request_handler.check_missing_test_cases_ids(project_id)

        # Assert: get_all_cases should NOT have been called for NAME matcher
        mock_get_all_cases.assert_not_called()
        assert not missing_ids, "Should not have missing IDs"
        assert error == "", "Should not have errors"

    @pytest.mark.api_handler
    def test_auto_matcher_still_fetches_all_cases(self, environment, api_client, mocker):
        """
        Test that AUTO matcher STILL fetches all cases (required for automation ID lookup).
        This ensures we didn't break the AUTO matcher functionality.
        """
        # Setup: AUTO matcher
        environment.case_matcher = MatchersParser.AUTO
        test_suite = create_test_suite_with_case_ids(num_cases=10)
        api_request_handler = ApiRequestHandler(environment, api_client, test_suite)

        # Mock get_all_cases to return some cases
        mock_cases = [
            {"id": i, "custom_automation_id": f"test{i}", "title": f"Test {i}", "section_id": 1} for i in range(1, 11)
        ]
        mock_get_all_cases = mocker.patch.object(
            api_request_handler, "_ApiRequestHandler__get_all_cases", return_value=(mock_cases, None)
        )

        mocker.patch.object(api_request_handler.data_provider, "update_data")

        # Execute
        project_id = 1
        api_request_handler.check_missing_test_cases_ids(project_id)

        # Assert: get_all_cases SHOULD be called for AUTO matcher
        mock_get_all_cases.assert_called_once_with(project_id, 1)

    @pytest.mark.api_handler
    def test_name_matcher_skips_validation_for_large_batches(self, environment, api_client, mocker):
        """
        Test that validation is SKIPPED when:
        - Using NAME matcher
        - All tests have case IDs (no missing)
        - More than 1000 case IDs (large batch)
        """
        # Setup: NAME matcher with 2000 test cases (> 1000 threshold)
        environment.case_matcher = MatchersParser.NAME
        test_suite = create_test_suite_with_case_ids(num_cases=2000)
        api_request_handler = ApiRequestHandler(environment, api_client, test_suite)

        # Mock validation method to track if it's called
        mock_validate = mocker.patch.object(
            api_request_handler, "_ApiRequestHandler__validate_case_ids_exist", return_value=set(range(1, 2001))
        )

        mock_log = mocker.patch.object(environment, "log")

        # Execute
        project_id = 1
        missing_ids, error = api_request_handler.check_missing_test_cases_ids(project_id)

        # Assert: Validation should be SKIPPED for large batches
        mock_validate.assert_not_called()

        # Should log that validation was skipped
        skip_log_calls = [call for call in mock_log.call_args_list if "Skipping validation" in str(call)]
        assert len(skip_log_calls) > 0, "Should log that validation was skipped"

        assert not missing_ids, "Should not have missing IDs"
        assert error == "", "Should not have errors"

    @pytest.mark.api_handler
    def test_name_matcher_validates_small_batches(self, environment, api_client, mocker):
        """
        Test that validation RUNS when:
        - Using NAME matcher
        - Less than 1000 case IDs (small batch)
        """
        # Setup: NAME matcher with 500 test cases (< 1000 threshold)
        environment.case_matcher = MatchersParser.NAME
        test_suite = create_test_suite_with_case_ids(num_cases=500)
        api_request_handler = ApiRequestHandler(environment, api_client, test_suite)

        # Mock validation method to track if it's called
        mock_validate = mocker.patch.object(
            api_request_handler, "_ApiRequestHandler__validate_case_ids_exist", return_value=set(range(1, 501))
        )

        # Execute
        project_id = 1
        missing_ids, error = api_request_handler.check_missing_test_cases_ids(project_id)

        # Assert: Validation SHOULD run for small batches
        mock_validate.assert_called_once()
        assert not missing_ids, "Should not have missing IDs"
        assert error == "", "Should not have errors"

    @pytest.mark.api_handler
    def test_name_matcher_validates_when_missing_case_ids(self, environment, api_client, mocker):
        """
        Test that validation RUNS when:
        - Using NAME matcher
        - Some tests are missing case IDs (even if total > 1000)
        This is important because missing IDs might indicate extraction errors.
        """
        # Setup: 1500 total cases, 3 missing IDs
        environment.case_matcher = MatchersParser.NAME
        test_suite = create_test_suite_with_missing_case_ids(total_cases=1500, missing_count=3)
        api_request_handler = ApiRequestHandler(environment, api_client, test_suite)

        # Mock validation
        mock_validate = mocker.patch.object(
            api_request_handler,
            "_ApiRequestHandler__validate_case_ids_exist",
            return_value=set(range(4, 1501)),  # Exclude the 3 missing
        )

        mock_log = mocker.patch.object(environment, "log")

        # Execute
        project_id = 1
        missing_ids, error = api_request_handler.check_missing_test_cases_ids(project_id)

        # Assert: Validation SHOULD run because there are missing case IDs
        mock_validate.assert_called_once()

        # Should log that missing cases were found
        missing_log_calls = [call for call in mock_log.call_args_list if "without case ID" in str(call)]
        assert len(missing_log_calls) > 0, "Should log missing case IDs"

        assert missing_ids, "Should have missing IDs"
        assert error == "", "Should not have errors"

    @pytest.mark.api_handler
    def test_name_matcher_detects_nonexistent_case_ids(self, environment, api_client, mocker):
        """
        Test that NAME matcher correctly detects case IDs that don't exist in TestRail.
        """
        # Setup: Test suite with case IDs 1-10
        environment.case_matcher = MatchersParser.NAME
        test_suite = create_test_suite_with_case_ids(num_cases=10)
        api_request_handler = ApiRequestHandler(environment, api_client, test_suite)

        # Mock validation: Only IDs 1-5 exist, 6-10 don't exist
        mock_validate = mocker.patch.object(
            api_request_handler,
            "_ApiRequestHandler__validate_case_ids_exist",
            return_value=set(range(1, 6)),  # Only 1-5 exist
        )

        mock_elog = mocker.patch.object(environment, "elog")

        # Execute
        project_id = 1
        missing_ids, error = api_request_handler.check_missing_test_cases_ids(project_id)

        # Assert: Should detect nonexistent IDs
        mock_validate.assert_called_once()
        mock_elog.assert_called_once()

        # Check error message contains nonexistent IDs
        error_call = mock_elog.call_args[0][0]
        assert "Nonexistent case IDs" in error_call
        assert "6" in error_call or "7" in error_call  # At least some of the missing IDs

        assert not missing_ids, "missing_ids refers to tests without IDs in report"
        assert error != "", "Should have error about nonexistent IDs"


class TestValidateCaseIdsExist:
    """Test the __validate_case_ids_exist helper method"""

    @pytest.mark.api_handler
    def test_validate_empty_list(self, environment, api_client):
        """Test that empty list returns empty set"""
        test_suite = create_test_suite_with_case_ids(num_cases=1)
        api_request_handler = ApiRequestHandler(environment, api_client, test_suite)

        result = api_request_handler._ApiRequestHandler__validate_case_ids_exist(suite_id=1, case_ids=[])

        assert result == set(), "Empty list should return empty set"

    @pytest.mark.api_handler
    def test_validate_small_batch_sequential(self, environment, api_client, requests_mock):
        """
        Test validation of small batch (<=50 cases) uses sequential validation.
        """
        test_suite = create_test_suite_with_case_ids(num_cases=1)
        api_request_handler = ApiRequestHandler(environment, api_client, test_suite)

        # Mock get_case responses for IDs 1-10
        for i in range(1, 11):
            requests_mock.get(create_url(f"get_case/{i}"), json={"id": i, "suite_id": 1, "title": f"Case {i}"})

        # Add one non-existent case (returns 404)
        requests_mock.get(create_url("get_case/999"), status_code=404, json={"error": "Not found"})

        result = api_request_handler._ApiRequestHandler__validate_case_ids_exist(
            suite_id=1, case_ids=[1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 999]
        )

        # Should return 1-10 (11 total requested, 1 doesn't exist)
        assert result == set(range(1, 11)), "Should validate existing cases"
        assert 999 not in result, "Non-existent case should not be in result"

    @pytest.mark.api_handler
    def test_validate_large_batch_concurrent(self, environment, api_client, requests_mock):
        """
        Test validation of large batch (>50 cases) uses concurrent validation.
        """
        test_suite = create_test_suite_with_case_ids(num_cases=1)
        api_request_handler = ApiRequestHandler(environment, api_client, test_suite)

        # Mock 100 case responses
        for i in range(1, 101):
            requests_mock.get(create_url(f"get_case/{i}"), json={"id": i, "suite_id": 1, "title": f"Case {i}"})

        result = api_request_handler._ApiRequestHandler__validate_case_ids_exist(
            suite_id=1, case_ids=list(range(1, 101))
        )

        # Should validate all 100 cases concurrently
        assert result == set(range(1, 101)), "Should validate all cases"
        assert len(result) == 100

    @pytest.mark.api_handler
    def test_validate_filters_wrong_suite(self, environment, api_client, requests_mock):
        """
        Test that validation filters out cases belonging to different suite.
        """
        test_suite = create_test_suite_with_case_ids(num_cases=1)
        api_request_handler = ApiRequestHandler(environment, api_client, test_suite)

        # Case 1 belongs to suite 1 (correct)
        requests_mock.get(create_url("get_case/1"), json={"id": 1, "suite_id": 1, "title": "Case 1"})

        # Case 2 belongs to suite 2 (wrong suite)
        requests_mock.get(create_url("get_case/2"), json={"id": 2, "suite_id": 2, "title": "Case 2"})

        # Case 3 belongs to suite 1 (correct)
        requests_mock.get(create_url("get_case/3"), json={"id": 3, "suite_id": 1, "title": "Case 3"})

        result = api_request_handler._ApiRequestHandler__validate_case_ids_exist(suite_id=1, case_ids=[1, 2, 3])

        # Should only return cases from suite 1
        assert result == {1, 3}, "Should filter out case from wrong suite"
        assert 2 not in result, "Case from wrong suite should be excluded"

    @pytest.mark.api_handler
    def test_validate_handles_api_errors(self, environment, api_client, requests_mock):
        """
        Test that validation gracefully handles API errors (404, 500, etc).
        """
        test_suite = create_test_suite_with_case_ids(num_cases=1)
        api_request_handler = ApiRequestHandler(environment, api_client, test_suite)

        # Case 1: Success
        requests_mock.get(create_url("get_case/1"), json={"id": 1, "suite_id": 1, "title": "Case 1"})

        # Case 2: 404 Not Found
        requests_mock.get(create_url("get_case/2"), status_code=404, json={"error": "Not found"})

        # Case 3: 500 Server Error
        requests_mock.get(create_url("get_case/3"), status_code=500, json={"error": "Internal error"})

        # Case 4: Success
        requests_mock.get(create_url("get_case/4"), json={"id": 4, "suite_id": 1, "title": "Case 4"})

        result = api_request_handler._ApiRequestHandler__validate_case_ids_exist(suite_id=1, case_ids=[1, 2, 3, 4])

        # Should return only successful cases
        assert result == {1, 4}, "Should only return successfully validated cases"


class TestPerformanceComparison:
    """Tests demonstrating the performance improvement"""

    @pytest.mark.api_handler
    def test_performance_auto_vs_name_matcher(self, environment, api_client, mocker):
        """
        Demonstrate that NAME matcher makes fewer API calls than AUTO matcher.
        This is a documentation test showing the optimization benefit.
        """
        test_suite = create_test_suite_with_case_ids(num_cases=2000)

        # Test AUTO matcher (old way)
        environment.case_matcher = MatchersParser.AUTO
        api_request_handler_auto = ApiRequestHandler(environment, api_client, test_suite)

        mock_get_all_cases_auto = mocker.patch.object(
            api_request_handler_auto,
            "_ApiRequestHandler__get_all_cases",
            return_value=([{"id": i, "custom_automation_id": f"test{i}"} for i in range(1, 2001)], None),
        )
        mocker.patch.object(api_request_handler_auto.data_provider, "update_data")

        api_request_handler_auto.check_missing_test_cases_ids(project_id=1)

        # AUTO matcher should call get_all_cases
        assert mock_get_all_cases_auto.call_count == 1, "AUTO matcher fetches all cases"

        # Test NAME matcher (new optimized way)
        environment.case_matcher = MatchersParser.NAME
        test_suite_name = create_test_suite_with_case_ids(num_cases=2000)
        api_request_handler_name = ApiRequestHandler(environment, api_client, test_suite_name)

        mock_get_all_cases_name = mocker.patch.object(
            api_request_handler_name, "_ApiRequestHandler__get_all_cases", return_value=([], None)
        )

        # Mock validation to skip it (large batch)
        mocker.patch.object(environment, "log")

        api_request_handler_name.check_missing_test_cases_ids(project_id=1)

        # NAME matcher should NOT call get_all_cases
        mock_get_all_cases_name.assert_not_called()

        print("\n" + "=" * 60)
        print("PERFORMANCE COMPARISON")
        print("=" * 60)
        print(f"AUTO matcher: {mock_get_all_cases_auto.call_count} get_all_cases calls")
        print(f"NAME matcher: {mock_get_all_cases_name.call_count} get_all_cases calls")
        print(f"Improvement: {mock_get_all_cases_auto.call_count - mock_get_all_cases_name.call_count} fewer calls")
        print("=" * 60)


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
