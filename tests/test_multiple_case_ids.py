"""
Unit tests for multiple case ID feature (GitHub #343)

Tests the ability to map a single JUnit test to multiple TestRail case IDs
using comma-separated values in the test_id property.
"""

import pytest
from trcli.readers.junit_xml import JunitParser


class TestParseMultipleCaseIds:
    """Test cases for JunitParser._parse_multiple_case_ids static method"""

    @pytest.mark.parametrize(
        "input_value, expected_output",
        [
            # Single case ID (backwards compatibility)
            ("C123", 123),
            ("c123", 123),
            ("123", 123),
            (" C123 ", 123),
            ("  123  ", 123),
            # Multiple case IDs
            ("C123, C456, C789", [123, 456, 789]),
            ("C123,C456,C789", [123, 456, 789]),
            ("123, 456, 789", [123, 456, 789]),
            ("123,456,789", [123, 456, 789]),
            # Mixed case
            ("c123, C456, c789", [123, 456, 789]),
            # Whitespace variations
            ("C123 , C456 , C789", [123, 456, 789]),
            (" C123 , C456 , C789 ", [123, 456, 789]),
            ("C123  ,  C456  ,  C789", [123, 456, 789]),
            # Deduplication
            ("C123, C123", 123),  # Returns single int when deduplicated to one
            ("C123, C456, C123", [123, 456]),
            ("C100, C200, C100, C300, C200", [100, 200, 300]),
            # Invalid inputs (should be ignored)
            ("C123, invalid, C456", [123, 456]),
            ("C123, , C456", [123, 456]),  # Empty part
            ("C123, C, C456", [123, 456]),  # C without number
            ("C123, abc, C456", [123, 456]),
            ("invalid", None),
            ("", None),
            ("   ", None),
            (",,,", None),
            # Edge cases
            ("C1", 1),
            ("C999999", 999999),
            ("C1, C2, C3", [1, 2, 3]),
            ("1,2,3,4,5", [1, 2, 3, 4, 5]),
        ],
    )
    def test_parse_multiple_case_ids(self, input_value, expected_output):
        """Test parsing of single and multiple case IDs"""
        result = JunitParser._parse_multiple_case_ids(input_value)
        assert result == expected_output, f"Failed for input: '{input_value}'"

    def test_parse_multiple_case_ids_none_input(self):
        """Test handling of None input"""
        result = JunitParser._parse_multiple_case_ids(None)
        assert result is None

    def test_parse_multiple_case_ids_very_long_list(self):
        """Test handling of very long lists (100+ case IDs)"""
        # Create a list of 150 case IDs
        case_ids = [f"C{i}" for i in range(1, 151)]
        input_value = ", ".join(case_ids)

        result = JunitParser._parse_multiple_case_ids(input_value)

        assert isinstance(result, list)
        assert len(result) == 150
        assert result[0] == 1
        assert result[-1] == 150

    def test_parse_multiple_case_ids_preserves_order(self):
        """Test that order is preserved when parsing multiple IDs"""
        result = JunitParser._parse_multiple_case_ids("C789, C123, C456")
        assert result == [789, 123, 456], "Order should be preserved"

    def test_parse_multiple_case_ids_mixed_valid_invalid(self):
        """Test handling of mixed valid and invalid case IDs"""
        # Should extract only valid IDs and ignore invalid ones
        result = JunitParser._parse_multiple_case_ids("C123, invalid, C456, abc, C789, xyz")
        assert result == [123, 456, 789]

    def test_parse_multiple_case_ids_special_characters(self):
        """Test that special characters are handled correctly"""
        # These should not be parsed as valid case IDs
        assert JunitParser._parse_multiple_case_ids("C123!, C456#") is None
        assert JunitParser._parse_multiple_case_ids("C-123, C+456") is None

    def test_backwards_compatibility_single_id(self):
        """Ensure single case ID returns integer (not list) for backwards compatibility"""
        # Single IDs should return int, not list
        assert JunitParser._parse_multiple_case_ids("C123") == 123
        assert not isinstance(JunitParser._parse_multiple_case_ids("C123"), list)

        # Single ID after deduplication should also return int
        assert JunitParser._parse_multiple_case_ids("C123, C123, C123") == 123
        assert not isinstance(JunitParser._parse_multiple_case_ids("C123, C123, C123"), list)


class TestMultipleCaseIdsIntegration:
    """Integration tests for multiple case ID feature with JUnit XML parsing"""

    @pytest.fixture
    def mock_environment(self, mocker, tmp_path):
        """Create a mock environment for testing"""
        # Create a dummy XML file
        xml_file = tmp_path / "test.xml"
        xml_file.write_text(
            '<testsuites><testsuite name="test"><testcase name="test" classname="Test"/></testsuite></testsuites>'
        )

        env = mocker.Mock()
        env.case_matcher = "property"
        env.special_parser = None
        env.params_from_config = {}
        env.file = str(xml_file)
        return env

    def test_extract_single_case_id_property(self, mock_environment, mocker):
        """Test extraction of single case ID from property (backwards compatibility)"""
        parser = JunitParser(mock_environment)

        # Mock a testcase with single test_id property
        mock_case = mocker.Mock()
        mock_case.name = "test_example"

        mock_prop = mocker.Mock()
        mock_prop.name = "test_id"
        mock_prop.value = "C123"

        mock_props = mocker.Mock()
        mock_props.iterchildren.return_value = [mock_prop]

        mock_case.iterchildren.return_value = [mock_props]

        case_id, case_name = parser._extract_case_id_and_name(mock_case)

        assert case_id == 123
        assert case_name == "test_example"

    def test_extract_multiple_case_ids_property(self, mock_environment, mocker):
        """Test extraction of multiple case IDs from property"""
        parser = JunitParser(mock_environment)

        # Mock a testcase with multiple test_ids
        mock_case = mocker.Mock()
        mock_case.name = "test_combined_scenario"

        mock_prop = mocker.Mock()
        mock_prop.name = "test_id"
        mock_prop.value = "C123, C456, C789"

        mock_props = mocker.Mock()
        mock_props.iterchildren.return_value = [mock_prop]

        mock_case.iterchildren.return_value = [mock_props]

        case_id, case_name = parser._extract_case_id_and_name(mock_case)

        assert case_id == [123, 456, 789]
        assert case_name == "test_combined_scenario"

    def test_multiple_case_ids_ignored_for_name_matcher(self, mock_environment, mocker):
        """Test that multiple case IDs in property are ignored when using name matcher"""
        mock_environment.case_matcher = "name"
        parser = JunitParser(mock_environment)

        # When using name matcher, we parse from the name, not the property
        mock_case = mocker.Mock()
        mock_case.name = "test_C100_example"
        mock_case.iterchildren.return_value = []

        # Mock the MatchersParser.parse_name_with_id
        with mocker.patch(
            "trcli.readers.junit_xml.MatchersParser.parse_name_with_id", return_value=(100, "test_example")
        ):
            case_id, case_name = parser._extract_case_id_and_name(mock_case)

        # With name matcher, it should extract from name (not property)
        assert case_id == 100
        assert case_name == "test_example"


class TestMultipleCaseIdsEndToEnd:
    """End-to-end tests for multiple case ID feature with real JUnit XML"""

    @pytest.fixture
    def mock_environment(self, mocker):
        """Create a mock environment for end-to-end testing"""
        env = mocker.Mock()
        env.case_matcher = "property"
        env.special_parser = None
        env.params_from_config = {}
        env.file = "tests/test_data/XML/multiple_case_ids_in_property.xml"
        env.suite_name = None
        return env

    def test_parse_junit_xml_with_multiple_case_ids(self, mock_environment):
        """Test end-to-end parsing of JUnit XML with multiple case IDs"""
        parser = JunitParser(mock_environment)
        suites = parser.parse_file()

        assert suites is not None
        assert len(suites) > 0

        # Get all test cases across all suites and sections
        all_test_cases = []
        for suite in suites:
            for section in suite.testsections:
                all_test_cases.extend(section.testcases)

        # We should have 8 test cases total:
        # - Test 1: 1 case (C1050381)
        # - Test 2: 3 cases (C1050382, C1050383, C1050384)
        # - Test 3: 4 cases (C1050385, C1050386, C1050387, C1050388)
        assert len(all_test_cases) == 8

        # Find test cases by case_id
        case_ids = [tc.case_id for tc in all_test_cases]
        assert 1050381 in case_ids  # Single case ID

        # Multiple case IDs from test 2
        assert 1050382 in case_ids
        assert 1050383 in case_ids
        assert 1050384 in case_ids

        # Multiple case IDs from test 3
        assert 1050385 in case_ids
        assert 1050386 in case_ids
        assert 1050387 in case_ids
        assert 1050388 in case_ids

        # Verify that test cases with same source test have same title
        combined_test_cases = [tc for tc in all_test_cases if tc.case_id in [1050382, 1050383, 1050384]]
        assert len(combined_test_cases) == 3
        assert combined_test_cases[0].title == combined_test_cases[1].title == combined_test_cases[2].title

        # Verify all combined test cases have the same result status
        assert combined_test_cases[0].result.status_id == combined_test_cases[1].result.status_id
        assert combined_test_cases[1].result.status_id == combined_test_cases[2].result.status_id

        # Verify comment is preserved across all cases
        if combined_test_cases[0].result.comment:
            assert "Combined test covering multiple scenarios" in combined_test_cases[0].result.comment
            assert combined_test_cases[0].result.comment == combined_test_cases[1].result.comment

    def test_multiple_case_ids_all_get_same_result(self, mock_environment):
        """Verify that all case IDs from one test get the same result data"""
        parser = JunitParser(mock_environment)
        suites = parser.parse_file()

        # Get test cases for C1050382, C1050383, C1050384 (from the same JUnit test)
        all_test_cases = []
        for suite in suites:
            for section in suite.testsections:
                all_test_cases.extend(section.testcases)

        combined_cases = [tc for tc in all_test_cases if tc.case_id in [1050382, 1050383, 1050384]]
        assert len(combined_cases) == 3

        # All should have same status
        statuses = [tc.result.status_id for tc in combined_cases]
        assert len(set(statuses)) == 1, "All cases should have the same status"

        # All should have same elapsed time
        elapsed_times = [tc.result.elapsed for tc in combined_cases]
        assert len(set(elapsed_times)) == 1, "All cases should have the same elapsed time"

        # All should have same automation_id
        automation_ids = [tc.custom_automation_id for tc in combined_cases]
        assert len(set(automation_ids)) == 1, "All cases should have the same automation_id"

    def test_multiple_case_ids_attachments_duplicated(self, mock_environment):
        """Verify that attachments are duplicated for each case ID"""
        mock_environment.file = "tests/test_data/XML/multiple_case_ids_with_attachments.xml"
        parser = JunitParser(mock_environment)
        suites = parser.parse_file()

        # Get test cases for C1050400, C1050401, C1050402 (test with attachments)
        all_test_cases = []
        for suite in suites:
            for section in suite.testsections:
                all_test_cases.extend(section.testcases)

        attachment_cases = [tc for tc in all_test_cases if tc.case_id in [1050400, 1050401, 1050402]]
        assert len(attachment_cases) == 3, "Should have 3 test cases with attachments"

        # Verify all cases have the same attachments
        for case in attachment_cases:
            assert len(case.result.attachments) == 3, f"Case {case.case_id} should have 3 attachments"
            assert "/path/to/screenshot.png" in case.result.attachments
            assert "/path/to/log.txt" in case.result.attachments
            assert "/path/to/video.mp4" in case.result.attachments

        # Verify attachment lists are independent (different list objects)
        assert attachment_cases[0].result.attachments is not attachment_cases[1].result.attachments
        assert attachment_cases[0].result.attachments is not attachment_cases[2].result.attachments
        assert attachment_cases[1].result.attachments is not attachment_cases[2].result.attachments

    def test_multiple_case_ids_result_fields_duplicated(self, mock_environment):
        """Verify that result fields are duplicated for each case ID"""
        mock_environment.file = "tests/test_data/XML/multiple_case_ids_with_attachments.xml"
        parser = JunitParser(mock_environment)
        suites = parser.parse_file()

        # Get test cases for C1050410, C1050411, C1050412 (test with result fields)
        all_test_cases = []
        for suite in suites:
            for section in suite.testsections:
                all_test_cases.extend(section.testcases)

        result_field_cases = [tc for tc in all_test_cases if tc.case_id in [1050410, 1050411, 1050412]]
        assert len(result_field_cases) == 3, "Should have 3 test cases with result fields"

        # Verify all cases have the same result fields
        for case in result_field_cases:
            assert "version" in case.result.result_fields
            assert case.result.result_fields["version"] == "1.2.3"
            assert "environment" in case.result.result_fields
            assert case.result.result_fields["environment"] == "staging"
            assert "browser" in case.result.result_fields
            assert case.result.result_fields["browser"] == "chrome"

        # Verify result_fields dicts are independent (different dict objects)
        assert result_field_cases[0].result.result_fields is not result_field_cases[1].result.result_fields
        assert result_field_cases[0].result.result_fields is not result_field_cases[2].result.result_fields
        assert result_field_cases[1].result.result_fields is not result_field_cases[2].result.result_fields

    def test_multiple_case_ids_case_fields_duplicated(self, mock_environment):
        """Verify that case fields are duplicated for each case ID"""
        mock_environment.file = "tests/test_data/XML/multiple_case_ids_with_attachments.xml"
        parser = JunitParser(mock_environment)
        suites = parser.parse_file()

        # Get test cases for C1050420, C1050421 (test with case fields)
        all_test_cases = []
        for suite in suites:
            for section in suite.testsections:
                all_test_cases.extend(section.testcases)

        case_field_cases = [tc for tc in all_test_cases if tc.case_id in [1050420, 1050421]]
        assert len(case_field_cases) == 2, "Should have 2 test cases with case fields"

        # Verify all cases have the same case fields
        for case in case_field_cases:
            assert "custom_preconds" in case.case_fields
            assert case.case_fields["custom_preconds"] == "Setup database and test users"
            assert "custom_automation_type" in case.case_fields
            assert case.case_fields["custom_automation_type"] == "e2e"
            assert "custom_steps" in case.case_fields
            assert "1. Login to application" in case.case_fields["custom_steps"]
            assert "2. Navigate to dashboard" in case.case_fields["custom_steps"]

        # Verify case_fields dicts are independent (different dict objects)
        assert case_field_cases[0].case_fields is not case_field_cases[1].case_fields

    def test_multiple_case_ids_step_results_duplicated(self, mock_environment):
        """Verify that step results are duplicated for each case ID"""
        mock_environment.file = "tests/test_data/XML/multiple_case_ids_with_attachments.xml"
        parser = JunitParser(mock_environment)
        suites = parser.parse_file()

        # Get test cases for C1050430, C1050431, C1050432, C1050433 (test with step results)
        all_test_cases = []
        for suite in suites:
            for section in suite.testsections:
                all_test_cases.extend(section.testcases)

        step_result_cases = [tc for tc in all_test_cases if tc.case_id in [1050430, 1050431, 1050432, 1050433]]
        assert len(step_result_cases) == 4, "Should have 4 test cases with step results"

        # Verify all cases have the same step results
        for case in step_result_cases:
            assert len(case.result.custom_step_results) == 3, f"Case {case.case_id} should have 3 step results"

            # Verify step content and statuses
            assert case.result.custom_step_results[0].content == "Login successful"
            assert case.result.custom_step_results[0].status_id == 1  # passed

            assert case.result.custom_step_results[1].content == "Navigate to checkout"
            assert case.result.custom_step_results[1].status_id == 1  # passed

            assert case.result.custom_step_results[2].content == "Payment processing failed"
            assert case.result.custom_step_results[2].status_id == 5  # failed

        # Verify step result lists are independent (different list objects)
        assert step_result_cases[0].result.custom_step_results is not step_result_cases[1].result.custom_step_results
        assert step_result_cases[0].result.custom_step_results is not step_result_cases[2].result.custom_step_results

    def test_multiple_case_ids_all_features_combined_passing(self, mock_environment):
        """Verify all features work together for passing tests"""
        mock_environment.file = "tests/test_data/XML/multiple_case_ids_with_attachments.xml"
        parser = JunitParser(mock_environment)
        suites = parser.parse_file()

        # Get test cases for C1050440, C1050441, C1050442 (kitchen sink passing test)
        all_test_cases = []
        for suite in suites:
            for section in suite.testsections:
                all_test_cases.extend(section.testcases)

        kitchen_sink_cases = [tc for tc in all_test_cases if tc.case_id in [1050440, 1050441, 1050442]]
        assert len(kitchen_sink_cases) == 3, "Should have 3 test cases for kitchen sink test"

        for case in kitchen_sink_cases:
            # Verify status
            assert case.result.status_id == 1, f"Case {case.case_id} should be passed"

            # Verify attachments
            assert len(case.result.attachments) == 2
            assert "/evidence/test_screenshot.png" in case.result.attachments
            assert "/evidence/debug.log" in case.result.attachments

            # Verify result fields
            assert case.result.result_fields["version"] == "2.0.0"
            assert case.result.result_fields["browser"] == "firefox"

            # Verify case fields
            assert case.case_fields["custom_automation_type"] == "integration"

            # Verify comment
            assert "Full integration test executed successfully" in case.result.comment

            # Verify step results
            assert len(case.result.custom_step_results) == 2
            assert case.result.custom_step_results[0].content == "Setup complete"
            assert case.result.custom_step_results[0].status_id == 1

    def test_multiple_case_ids_all_features_combined_failing(self, mock_environment):
        """Verify all features work together for failing tests (failure info + attachments)"""
        mock_environment.file = "tests/test_data/XML/multiple_case_ids_with_attachments.xml"
        parser = JunitParser(mock_environment)
        suites = parser.parse_file()

        # Get test cases for C1050450, C1050451 (kitchen sink failing test)
        all_test_cases = []
        for suite in suites:
            for section in suite.testsections:
                all_test_cases.extend(section.testcases)

        failing_cases = [tc for tc in all_test_cases if tc.case_id in [1050450, 1050451]]
        assert len(failing_cases) == 2, "Should have 2 test cases for failing kitchen sink test"

        for case in failing_cases:
            # Verify status
            assert case.result.status_id == 5, f"Case {case.case_id} should be failed"

            # Verify failure information in comment
            assert "Type: AssertionError" in case.result.comment
            assert "Message: Payment gateway returned error" in case.result.comment
            assert "Payment failed with error code 500" in case.result.comment

            # Verify attachments (should be present alongside failure info)
            assert len(case.result.attachments) == 2
            assert "/failure/error_screenshot.png" in case.result.attachments
            assert "/failure/stack_trace.txt" in case.result.attachments

            # Verify result fields
            assert case.result.result_fields["version"] == "2.0.0"
            assert case.result.result_fields["environment"] == "production"

            # Verify case fields
            assert case.case_fields["custom_preconds"] == "User must be logged in"

            # Verify prepended comment
            assert "Test failed during checkout" in case.result.comment

            # Verify step results
            assert len(case.result.custom_step_results) == 2
            assert case.result.custom_step_results[1].content == "Checkout failed"
            assert case.result.custom_step_results[1].status_id == 5  # failed

    def test_multiple_case_ids_data_independence_mutation(self, mock_environment):
        """Verify that modifying one case's data doesn't affect other cases"""
        mock_environment.file = "tests/test_data/XML/multiple_case_ids_with_attachments.xml"
        parser = JunitParser(mock_environment)
        suites = parser.parse_file()

        # Get test cases for C1050400, C1050401, C1050402 (test with attachments)
        all_test_cases = []
        for suite in suites:
            for section in suite.testsections:
                all_test_cases.extend(section.testcases)

        test_cases = [tc for tc in all_test_cases if tc.case_id in [1050400, 1050401, 1050402]]
        assert len(test_cases) == 3

        # Store original attachment counts
        original_counts = [len(tc.result.attachments) for tc in test_cases]

        # Mutate first case's attachments
        test_cases[0].result.attachments.append("/mutated/new_file.txt")

        # Verify other cases are unchanged
        assert (
            len(test_cases[0].result.attachments) == original_counts[0] + 1
        ), "First case should have one more attachment"
        assert len(test_cases[1].result.attachments) == original_counts[1], "Second case should be unchanged"
        assert len(test_cases[2].result.attachments) == original_counts[2], "Third case should be unchanged"

        # Verify the mutated attachment is only in first case
        assert "/mutated/new_file.txt" in test_cases[0].result.attachments
        assert "/mutated/new_file.txt" not in test_cases[1].result.attachments
        assert "/mutated/new_file.txt" not in test_cases[2].result.attachments

        # Test result_fields independence
        result_field_cases = [tc for tc in all_test_cases if tc.case_id in [1050410, 1050411, 1050412]]
        if len(result_field_cases) == 3:
            # Mutate first case's result fields
            result_field_cases[0].result.result_fields["new_field"] = "mutated_value"

            # Verify other cases don't have the new field
            assert "new_field" in result_field_cases[0].result.result_fields
            assert "new_field" not in result_field_cases[1].result.result_fields
            assert "new_field" not in result_field_cases[2].result.result_fields
