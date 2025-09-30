import pytest
from trcli.data_classes.data_parsers import MatchersParser


class TestMatchersParser:
    """Test cases for MatchersParser.parse_name_with_id method"""

    @pytest.mark.parametrize(
        "test_input, expected_id, expected_name",
        [
            # Basic patterns (existing functionality)
            ("C123 my test case", 123, "my test case"),
            ("my test case C123", 123, "my test case"),
            ("C123_my_test_case", 123, "my_test_case"),
            ("my_test_case_C123", 123, "my_test_case"),
            ("module_1_C123_my_test_case", 123, "module_1_my_test_case"),
            ("[C123] my test case", 123, "my test case"),
            ("my test case [C123]", 123, "my test case"),
            ("module 1 [C123] my test case", 123, "module 1 my test case"),
            
            # JUnit 5 patterns with parentheses (new functionality)
            ("test_name_C120013()", 120013, "test_name"),
            ("testMethod_C123()", 123, "testMethod"),
            ("my_test_C456()", 456, "my_test"),
            ("C789_test_name()", 789, "test_name()"),
            ("C100 test_name()", 100, "test_name()"),
            
            # JUnit 5 patterns with parameters
            ("test_name_C120013(TestParam)", 120013, "test_name"),
            ("test_C456(param1, param2)", 456, "test"),
            ("complexTest_C999(String param, int value)", 999, "complexTest"),
            
            # Edge cases with parentheses
            ("myTest_C789()", 789, "myTest"),
            ("C200_method()", 200, "method()"),
            ("[C300] test_case()", 300, "test_case()"),
            ("test [C400] method()", 400, "test method()"),
            
            # Cases that should not match
            ("test_name_C()", None, "test_name_C()"),
            ("test_name_123()", None, "test_name_123()"),
            ("test_name", None, "test_name"),
            ("C_test_name", None, "C_test_name"),
            ("test_Cabc_name", None, "test_Cabc_name"),
            
            # Case sensitivity
            ("c123_test_name", 123, "test_name"),
            ("test_name_c456", 456, "test_name"),
            ("[c789] test_name", 789, "test_name"),
        ]
    )
    def test_parse_name_with_id_patterns(self, test_input, expected_id, expected_name):
        """Test various patterns of test name parsing including JUnit 5 parentheses support"""
        case_id, case_name = MatchersParser.parse_name_with_id(test_input)
        assert case_id == expected_id, f"Expected ID {expected_id}, got {case_id} for input '{test_input}'"
        assert case_name == expected_name, f"Expected name '{expected_name}', got '{case_name}' for input '{test_input}'"

    def test_parse_name_with_id_junit5_specific(self):
        """Specific test cases for JUnit 5 parentheses issue reported by user"""
        # The exact examples from the user's issue
        junit5_cases = [
            ("test_name_C120013()", 120013, "test_name"),  # Should work now
            ("test_name_C120013", 120013, "test_name"),    # Should still work
            ("C120013_test_name()", 120013, "test_name()"), # Should work
        ]
        
        for test_case, expected_id, expected_name in junit5_cases:
            case_id, case_name = MatchersParser.parse_name_with_id(test_case)
            assert case_id == expected_id, f"JUnit 5 case failed: {test_case}"
            assert case_name == expected_name, f"JUnit 5 name failed: {test_case}"

    def test_parse_name_with_id_regression(self):
        """Ensure existing functionality still works (regression test)"""
        # Test all the patterns mentioned in the docstring
        existing_patterns = [
            ("C123 my test case", 123, "my test case"),
            ("my test case C123", 123, "my test case"),  
            ("C123_my_test_case", 123, "my_test_case"),
            ("my_test_case_C123", 123, "my_test_case"),
            ("module_1_C123_my_test_case", 123, "module_1_my_test_case"),
            ("[C123] my test case", 123, "my test case"),
            ("my test case [C123]", 123, "my test case"),
            ("module 1 [C123] my test case", 123, "module 1 my test case"),
        ]
        
        for test_case, expected_id, expected_name in existing_patterns:
            case_id, case_name = MatchersParser.parse_name_with_id(test_case)
            assert case_id == expected_id, f"Regression failed for: {test_case}"
            assert case_name == expected_name, f"Regression name failed for: {test_case}"

    def test_parse_name_with_id_empty_and_none(self):
        """Test edge cases with empty or None inputs"""
        # Empty string
        case_id, case_name = MatchersParser.parse_name_with_id("")
        assert case_id is None
        assert case_name == ""
        
        # String with just spaces
        case_id, case_name = MatchersParser.parse_name_with_id("   ")
        assert case_id is None
        assert case_name == "   "
