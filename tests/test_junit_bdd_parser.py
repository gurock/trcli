"""
Unit tests for BDD-specific JUnit parsing functionality

Tests the --special-parser bdd mode that groups multiple scenarios
into a single TestRail BDD test case.
"""

import pytest
from unittest.mock import Mock, MagicMock, patch
from pathlib import Path

from trcli.cli import Environment
from trcli.readers.junit_xml import JunitParser
from trcli.data_classes.validation_exception import ValidationException


class TestBDDJunitParser:
    """Test BDD mode for JUnit parser"""

    @pytest.fixture
    def environment(self):
        """Create mock environment for BDD mode"""
        env = Mock(spec=Environment)
        env.case_matcher = "auto"
        env.special_parser = "bdd"
        env.suite_name = None
        env.file = None  # Required by FileParser
        env.params_from_config = {}  # Required by JunitParser for custom statuses
        env.log = Mock()
        env.elog = Mock()
        env.vlog = Mock()
        return env

    @pytest.fixture
    def mock_api_validation_success(self):
        """Mock successful API validation (case exists and is BDD)"""
        with patch("trcli.api.project_based_client.ProjectBasedClient") as mock_client_class:
            mock_client = MagicMock()
            mock_api_handler = MagicMock()
            mock_response = MagicMock()

            # Mock successful get_case response with BDD field
            mock_response.error_message = ""
            mock_response.response_text = {
                "id": 42,
                "title": "User Enrollment",
                "template_id": 4,
                "custom_testrail_bdd_scenario": '[{"content":"Scenario 1"}]',
            }

            mock_api_handler.client.send_get.return_value = mock_response
            mock_client.api_request_handler = mock_api_handler
            mock_client_class.return_value = mock_client

            yield mock_client

    def test_bdd_mode_detection(self, environment):
        """Test that BDD mode is correctly detected"""
        test_file = Path(__file__).parent / "test_data" / "XML" / "bdd_valid_testsuite_property.xml"
        environment.file = str(test_file)
        parser = JunitParser(environment)
        assert parser._is_bdd_mode() is True

    def test_standard_mode_detection(self, environment):
        """Test that standard mode is detected when not BDD"""
        test_file = Path(__file__).parent / "test_data" / "XML" / "bdd_valid_testsuite_property.xml"
        environment.file = str(test_file)
        environment.special_parser = "junit"
        parser = JunitParser(environment)
        assert parser._is_bdd_mode() is False

    def test_extract_case_id_from_testsuite_property(self, environment):
        """Test extracting case ID from testsuite property"""
        test_file = Path(__file__).parent / "test_data" / "XML" / "bdd_valid_testsuite_property.xml"
        environment.file = str(test_file)
        parser = JunitParser(environment)

        # Parse and check case ID extraction
        from junitparser import JUnitXml

        suite = JUnitXml.fromfile(test_file)
        testsuite = list(suite)[0]

        case_id = parser._extract_feature_case_id_from_property(testsuite)
        assert case_id == 42

    def test_extract_case_id_from_testcase_names(self, environment):
        """Test extracting case ID from testcase names"""
        test_file = Path(__file__).parent / "test_data" / "XML" / "bdd_valid_testcase_names.xml"
        environment.file = str(test_file)
        parser = JunitParser(environment)

        from junitparser import JUnitXml

        suite = JUnitXml.fromfile(test_file)
        testsuite = list(suite)[0]

        testcase_ids = parser._extract_case_id_from_testcases(testsuite)
        assert len(testcase_ids) == 3
        assert all(case_id == 42 for _, case_id in testcase_ids)

    def test_validate_consistent_case_ids(self, environment):
        """Test validation passes when all scenarios have same case ID"""
        test_file = Path(__file__).parent / "test_data" / "XML" / "bdd_valid_testcase_names.xml"
        environment.file = str(test_file)
        parser = JunitParser(environment)

        from junitparser import JUnitXml

        suite = JUnitXml.fromfile(test_file)
        testsuite = list(suite)[0]

        case_id, errors = parser._extract_and_validate_bdd_case_id(testsuite)
        assert case_id == 42
        assert len(errors) == 0

    def test_validate_inconsistent_case_ids_error(self, environment):
        """Test validation fails when scenarios have different case IDs"""
        test_file = Path(__file__).parent / "test_data" / "XML" / "bdd_inconsistent_case_ids.xml"
        environment.file = str(test_file)
        parser = JunitParser(environment)

        from junitparser import JUnitXml

        suite = JUnitXml.fromfile(test_file)
        testsuite = list(suite)[0]

        case_id, errors = parser._extract_and_validate_bdd_case_id(testsuite)
        assert case_id is None
        assert len(errors) == 1
        assert "Multiple different case IDs" in errors[0]
        assert "123" in errors[0] and "124" in errors[0] and "125" in errors[0]

    def test_validate_no_case_id_error(self, environment):
        """Test validation fails when no case ID found"""
        test_file = Path(__file__).parent / "test_data" / "XML" / "bdd_no_case_id.xml"
        environment.file = str(test_file)
        parser = JunitParser(environment)

        from junitparser import JUnitXml

        suite = JUnitXml.fromfile(test_file)
        testsuite = list(suite)[0]

        case_id, errors = parser._extract_and_validate_bdd_case_id(testsuite)
        assert case_id is None
        assert len(errors) == 1
        assert "No case ID found" in errors[0]

    def test_aggregate_all_pass(self, environment):
        """Test status aggregation when all scenarios pass"""
        test_file = Path(__file__).parent / "test_data" / "XML" / "bdd_all_pass.xml"
        environment.file = str(test_file)
        parser = JunitParser(environment)
        statuses = [1, 1, 1]  # All passed
        result = parser._aggregate_scenario_statuses(statuses)
        assert result == 1  # Passed

    def test_aggregate_one_fail(self, environment):
        """Test status aggregation when one scenario fails (fail-fast)"""
        test_file = Path(__file__).parent / "test_data" / "XML" / "bdd_all_pass.xml"
        environment.file = str(test_file)
        parser = JunitParser(environment)
        statuses = [1, 5, 1]  # One failed
        result = parser._aggregate_scenario_statuses(statuses)
        assert result == 5  # Failed

    def test_aggregate_all_skip(self, environment):
        """Test status aggregation when all scenarios skipped"""
        test_file = Path(__file__).parent / "test_data" / "XML" / "bdd_all_pass.xml"
        environment.file = str(test_file)
        parser = JunitParser(environment)
        statuses = [4, 4, 4]  # All skipped
        result = parser._aggregate_scenario_statuses(statuses)
        assert result == 4  # Skipped

    def test_aggregate_pass_and_skip(self, environment):
        """Test status aggregation with pass and skip (no fails)"""
        test_file = Path(__file__).parent / "test_data" / "XML" / "bdd_all_pass.xml"
        environment.file = str(test_file)
        parser = JunitParser(environment)
        statuses = [1, 4, 1]  # Mixed pass/skip
        result = parser._aggregate_scenario_statuses(statuses)
        assert result == 4  # Skipped (since some not executed)

    def test_aggregate_fail_and_skip(self, environment):
        """Test status aggregation with fail and skip"""
        test_file = Path(__file__).parent / "test_data" / "XML" / "bdd_all_pass.xml"
        environment.file = str(test_file)
        parser = JunitParser(environment)
        statuses = [5, 4, 1]  # Mixed fail/skip/pass
        result = parser._aggregate_scenario_statuses(statuses)
        assert result == 5  # Failed (failure takes precedence)

    def test_format_failure_message(self, environment):
        """Test failure message formatting"""
        test_file = Path(__file__).parent / "test_data" / "XML" / "bdd_all_pass.xml"
        environment.file = str(test_file)
        parser = JunitParser(environment)

        mock_result = Mock()
        mock_result.type = "AssertionError"
        mock_result.message = "Expected X but got Y"
        mock_result.text = "Details about failure"

        message = parser._format_failure_message("Test Scenario", mock_result)

        assert "Scenario: Test Scenario" in message
        assert "Type: AssertionError" in message
        assert "Message: Expected X but got Y" in message
        assert "Details:\n   Details about failure" in message

    def test_format_failure_message_truncation(self, environment):
        """Test failure message truncates long text"""
        test_file = Path(__file__).parent / "test_data" / "XML" / "bdd_all_pass.xml"
        environment.file = str(test_file)
        parser = JunitParser(environment)

        mock_result = Mock()
        mock_result.type = "Error"
        mock_result.message = "Error"
        mock_result.text = "A" * 600  # Long text

        message = parser._format_failure_message("Test", mock_result)
        assert "... (truncated)" in message
        assert len(message) < 700  # Should be truncated

    @patch("trcli.api.project_based_client.ProjectBasedClient")
    def test_validate_case_exists_success(self, mock_client_class, environment):
        """Test validation passes when case exists and is BDD"""
        test_file = Path(__file__).parent / "test_data" / "XML" / "bdd_all_pass.xml"
        environment.file = str(test_file)

        mock_client = MagicMock()
        mock_api_handler = MagicMock()
        mock_response = MagicMock()

        mock_response.error_message = ""
        mock_response.response_text = {
            "id": 42,
            "title": "Test Feature",
            "custom_testrail_bdd_scenario": '[{"content":"..."}]',
        }

        mock_api_handler.client.send_get.return_value = mock_response
        mock_client.api_request_handler = mock_api_handler
        mock_client_class.return_value = mock_client

        parser = JunitParser(environment)
        is_valid, error_msg, case_data = parser._validate_bdd_case_exists(42, "Test Feature")

        assert is_valid is True
        assert error_msg == ""
        assert case_data["id"] == 42

    @patch("trcli.api.project_based_client.ProjectBasedClient")
    def test_validate_case_not_exists(self, mock_client_class, environment):
        """Test validation fails when case doesn't exist"""
        test_file = Path(__file__).parent / "test_data" / "XML" / "bdd_all_pass.xml"
        environment.file = str(test_file)

        mock_client = MagicMock()
        mock_api_handler = MagicMock()
        mock_response = MagicMock()

        mock_response.error_message = "Field :case_id is not a valid test case."

        mock_api_handler.client.send_get.return_value = mock_response
        mock_client.api_request_handler = mock_api_handler
        mock_client_class.return_value = mock_client

        parser = JunitParser(environment)
        is_valid, error_msg, case_data = parser._validate_bdd_case_exists(999, "Test Feature")

        assert is_valid is False
        assert "does not exist" in error_msg
        assert "C999" in error_msg

    @patch("trcli.api.project_based_client.ProjectBasedClient")
    def test_validate_case_not_bdd(self, mock_client_class, environment):
        """Test validation fails when case is not BDD template"""
        test_file = Path(__file__).parent / "test_data" / "XML" / "bdd_all_pass.xml"
        environment.file = str(test_file)

        mock_client = MagicMock()
        mock_api_handler = MagicMock()
        mock_response = MagicMock()

        mock_response.error_message = ""
        mock_response.response_text = {
            "id": 42,
            "title": "Regular Test Case",
            "custom_testrail_bdd_scenario": None,  # Not a BDD case
        }

        mock_api_handler.client.send_get.return_value = mock_response
        mock_client.api_request_handler = mock_api_handler
        mock_client_class.return_value = mock_client

        parser = JunitParser(environment)
        is_valid, error_msg, case_data = parser._validate_bdd_case_exists(42, "Test Feature")

        assert is_valid is False
        assert "is NOT a BDD test case" in error_msg
        assert "custom_testrail_bdd_scenario" in error_msg

    def test_parse_bdd_feature_all_pass(self, environment, mock_api_validation_success):
        """Test parsing BDD feature with all scenarios passing"""
        test_file = Path(__file__).parent / "test_data" / "XML" / "bdd_all_pass.xml"
        environment.file = str(test_file)
        parser = JunitParser(environment)

        from junitparser import JUnitXml

        suite = JUnitXml.fromfile(test_file)
        testsuite = list(suite)[0]

        # Mock the case ID to match test data
        mock_api_validation_success.api_request_handler.client.send_get.return_value.response_text["id"] = 100

        test_case = parser._parse_bdd_feature_as_single_case(testsuite)

        assert test_case is not None
        assert test_case.case_id == 100
        assert test_case.result.status_id == 1  # Passed
        assert len(test_case.result.custom_step_results) == 2
        assert "Total Scenarios: 2" in test_case.result.comment
        assert "Passed: 2" in test_case.result.comment

    def test_parse_bdd_feature_mixed_results(self, environment, mock_api_validation_success):
        """Test parsing BDD feature with mixed results (pass/fail/skip)"""
        test_file = Path(__file__).parent / "test_data" / "XML" / "bdd_mixed_results.xml"
        environment.file = str(test_file)
        parser = JunitParser(environment)

        from junitparser import JUnitXml

        suite = JUnitXml.fromfile(test_file)
        testsuite = list(suite)[0]

        # Mock the case ID
        mock_api_validation_success.api_request_handler.client.send_get.return_value.response_text["id"] = 25293

        test_case = parser._parse_bdd_feature_as_single_case(testsuite)

        assert test_case is not None
        assert test_case.case_id == 25293
        assert test_case.result.status_id == 5  # Failed (fail-fast)
        assert len(test_case.result.custom_step_results) == 3

        # Check step statuses
        assert test_case.result.custom_step_results[0].status_id == 1  # Passed
        assert test_case.result.custom_step_results[1].status_id == 5  # Failed
        assert test_case.result.custom_step_results[2].status_id == 4  # Skipped

        # Check comment contains summary and failure details
        assert "Total Scenarios: 3" in test_case.result.comment
        assert "Passed: 1" in test_case.result.comment
        assert "Failed: 1" in test_case.result.comment
        assert "Skipped: 1" in test_case.result.comment
        assert "Failure Details:" in test_case.result.comment
        assert "Invalid password" in test_case.result.comment

    def test_parse_bdd_feature_no_case_id_returns_none(self, environment):
        """Test that parsing returns None when no case ID found"""
        test_file = Path(__file__).parent / "test_data" / "XML" / "bdd_no_case_id.xml"
        environment.file = str(test_file)
        parser = JunitParser(environment)

        from junitparser import JUnitXml

        suite = JUnitXml.fromfile(test_file)
        testsuite = list(suite)[0]

        test_case = parser._parse_bdd_feature_as_single_case(testsuite)

        assert test_case is None
        environment.elog.assert_called()

    def test_parse_bdd_feature_inconsistent_ids_returns_none(self, environment):
        """Test that parsing returns None when case IDs are inconsistent"""
        test_file = Path(__file__).parent / "test_data" / "XML" / "bdd_inconsistent_case_ids.xml"
        environment.file = str(test_file)
        parser = JunitParser(environment)

        from junitparser import JUnitXml

        suite = JUnitXml.fromfile(test_file)
        testsuite = list(suite)[0]

        test_case = parser._parse_bdd_feature_as_single_case(testsuite)

        assert test_case is None
        environment.elog.assert_called()

    @patch("trcli.api.project_based_client.ProjectBasedClient")
    def test_parse_bdd_feature_case_not_exists_raises_exception(self, mock_client_class, environment):
        """Test that parsing raises ValidationException when case doesn't exist"""
        test_file = Path(__file__).parent / "test_data" / "XML" / "bdd_valid_testsuite_property.xml"
        environment.file = str(test_file)

        mock_client = MagicMock()
        mock_api_handler = MagicMock()
        mock_response = MagicMock()

        mock_response.error_message = "Case not found"

        mock_api_handler.client.send_get.return_value = mock_response
        mock_client.api_request_handler = mock_api_handler
        mock_client_class.return_value = mock_client

        parser = JunitParser(environment)

        from junitparser import JUnitXml

        suite = JUnitXml.fromfile(test_file)
        testsuite = list(suite)[0]

        with pytest.raises(ValidationException) as exc_info:
            parser._parse_bdd_feature_as_single_case(testsuite)

        assert "case_id" in str(exc_info.value.field_name)
        assert "BDD Feature" in str(exc_info.value.class_name)

    def test_parse_sections_bdd_mode(self, environment, mock_api_validation_success):
        """Test that _parse_sections uses BDD mode when enabled"""
        test_file = Path(__file__).parent / "test_data" / "XML" / "bdd_valid_testsuite_property.xml"
        environment.file = str(test_file)
        parser = JunitParser(environment)

        from junitparser import JUnitXml

        suite = JUnitXml.fromfile(test_file, parse_func=parser._add_root_element_to_tree)

        sections = parser._parse_sections(suite)

        assert len(sections) == 1
        assert len(sections[0].testcases) == 1  # One BDD test case
        assert sections[0].testcases[0].case_id == 42

    def test_parse_sections_standard_mode(self, environment):
        """Test that _parse_sections uses standard mode when BDD not enabled"""
        test_file = Path(__file__).parent / "test_data" / "XML" / "bdd_valid_testcase_names.xml"
        environment.file = str(test_file)
        environment.special_parser = "junit"  # Standard mode
        parser = JunitParser(environment)

        from junitparser import JUnitXml

        suite = JUnitXml.fromfile(test_file, parse_func=parser._add_root_element_to_tree)

        sections = parser._parse_sections(suite)

        assert len(sections) == 1
        # In standard mode, should have 3 separate test cases
        assert len(sections[0].testcases) == 3

    def test_elapsed_time_calculation(self, environment, mock_api_validation_success):
        """Test that elapsed time is summed correctly from all scenarios"""
        test_file = Path(__file__).parent / "test_data" / "XML" / "bdd_mixed_results.xml"
        environment.file = str(test_file)
        parser = JunitParser(environment)

        from junitparser import JUnitXml

        suite = JUnitXml.fromfile(test_file)
        testsuite = list(suite)[0]

        mock_api_validation_success.api_request_handler.client.send_get.return_value.response_text["id"] = 25293

        test_case = parser._parse_bdd_feature_as_single_case(testsuite)

        assert test_case.result.elapsed == "2s"  # 1.0 + 1.5 + 0.0 = 2.5, rounds to 2 (banker's rounding)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
