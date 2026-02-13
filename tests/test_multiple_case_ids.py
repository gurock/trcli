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
