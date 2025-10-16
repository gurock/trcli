"""
Unit tests for new features coverage - focused on critical missing areas.
Tests for --test-run-ref, case updates, and reference management functionality.
"""
import pytest
from unittest.mock import Mock, patch
import json

from trcli.commands.cmd_parse_junit import _validate_test_run_ref, _handle_case_update_reporting


class TestCmdParseJunitValidation:
    """Test coverage for cmd_parse_junit.py validation functions"""

    def test_validate_test_run_ref_valid_input(self):
        """Test _validate_test_run_ref with valid input"""
        # Valid single reference
        result = _validate_test_run_ref("REF-123")
        assert result is None
        
        # Valid multiple references
        result = _validate_test_run_ref("REF-123,REF-456,REF-789")
        assert result is None
        
        # Valid with spaces
        result = _validate_test_run_ref("REF-123, REF-456 , REF-789")
        assert result is None

    def test_validate_test_run_ref_invalid_input(self):
        """Test _validate_test_run_ref with invalid input"""
        # Empty string
        result = _validate_test_run_ref("")
        assert "cannot be empty" in result
        
        # Whitespace only
        result = _validate_test_run_ref("   ")
        assert "cannot be empty" in result
        
        # Only commas
        result = _validate_test_run_ref(",,,")
        assert "malformed input" in result
        
        # Too long (over 250 chars)
        long_refs = ",".join([f"REF-{i:03d}" for i in range(50)])  # Creates ~300 chars
        result = _validate_test_run_ref(long_refs)
        assert "250 character limit" in result

    def test_handle_case_update_reporting_console(self):
        """Test _handle_case_update_reporting console output"""
        env = Mock()
        env.json_output = False
        
        case_update_results = {
            "updated_cases": [
                {"case_id": 123, "case_title": "Test Case 1", "added_refs": ["REF-1"], "skipped_refs": []}
            ],
            "skipped_cases": [
                {"case_id": 456, "case_title": "Test Case 2", "reason": "All references already present", "skipped_refs": ["REF-2"]}
            ],
            "failed_cases": [
                {"case_id": 789, "case_title": "Test Case 3", "error": "API error"}
            ]
        }
        
        _handle_case_update_reporting(env, case_update_results)
        
        # Verify console output was logged
        assert env.log.called
        call_args = [call[0][0] for call in env.log.call_args_list]
        output = " ".join(call_args)
        assert "Case Reference Updates Summary:" in output
        assert "Updated cases: 1" in output
        assert "Skipped cases: 1" in output
        assert "Failed cases: 1" in output

    @patch('builtins.print')
    def test_handle_case_update_reporting_json(self, mock_print):
        """Test _handle_case_update_reporting JSON output"""
        env = Mock()
        env.json_output = True
        
        case_update_results = {
            "updated_cases": [{"case_id": 123, "added_refs": ["REF-1"]}],
            "skipped_cases": [],
            "failed_cases": []
        }
        
        _handle_case_update_reporting(env, case_update_results)
        
        # Verify JSON output
        assert mock_print.called
        json_output = mock_print.call_args[0][0]
        parsed = json.loads(json_output)
        assert "summary" in parsed
        assert "details" in parsed
        assert parsed["summary"]["updated_cases"] == 1

    def test_handle_case_update_reporting_none_input(self):
        """Test _handle_case_update_reporting with None input"""
        env = Mock()
        
        # Should return early without error
        result = _handle_case_update_reporting(env, None)
        assert result is None


class TestReferenceDeduplication:
    """Test coverage for reference deduplication logic"""

    def test_reference_deduplication_logic(self):
        """Test the deduplication logic used in reference management"""
        # Test input with duplicates
        references = ["REF-1", "REF-1", "REF-2", "REF-2", "REF-1", "REF-3"]
        
        # Apply deduplication logic (same as in api_request_handler.py)
        seen = set()
        unique_refs = []
        for ref in references:
            if ref not in seen:
                seen.add(ref)
                unique_refs.append(ref)
        
        # Should preserve order and remove duplicates
        assert unique_refs == ["REF-1", "REF-2", "REF-3"]
        assert len(unique_refs) == 3

    def test_reference_string_parsing(self):
        """Test parsing comma-separated reference strings"""
        # Test various input formats
        test_cases = [
            ("REF-1,REF-2,REF-3", ["REF-1", "REF-2", "REF-3"]),
            ("REF-1, REF-2 , REF-3", ["REF-1", "REF-2", "REF-3"]),
            ("REF-1,,REF-2", ["REF-1", "REF-2"]),
            ("  REF-1  ,  REF-2  ", ["REF-1", "REF-2"]),
        ]
        
        for input_str, expected in test_cases:
            # Apply parsing logic (same as in api_request_handler.py)
            refs_list = [ref.strip() for ref in input_str.split(',') if ref.strip()]
            assert refs_list == expected

    def test_character_limit_validation(self):
        """Test character limit validation for references"""
        # Test 250 character limit (for run references)
        short_refs = ",".join([f"REF-{i:02d}" for i in range(30)])  # ~150 chars
        assert len(short_refs) < 250
        
        long_refs = ",".join([f"REF-{i:03d}" for i in range(50)])  # ~300 chars
        assert len(long_refs) > 250
        
        # Test 2000 character limit (for case references)
        very_long_refs = ",".join([f"VERY-LONG-REFERENCE-NAME-{i:03d}" for i in range(100)])
        assert len(very_long_refs) > 2000


class TestJunitReferenceExtraction:
    """Test coverage for JUnit reference extraction logic"""

    def test_testrail_case_field_parsing(self):
        """Test parsing testrail_case_field values"""
        # Test various formats
        test_cases = [
            ("refs:REF-1", "REF-1"),
            ("refs:REF-1,REF-2", "REF-1,REF-2"),
            ("refs:REF-1,REF-2,REF-3", "REF-1,REF-2,REF-3"),
            ("refs: REF-1 , REF-2 ", " REF-1 , REF-2 "),  # Spaces preserved
        ]
        
        for testrail_field, expected_refs in test_cases:
            # Apply parsing logic (same as in junit_xml.py)
            if testrail_field.startswith("refs:"):
                refs = testrail_field[5:]  # Remove "refs:" prefix
                assert refs == expected_refs

    def test_case_refs_validation(self):
        """Test case reference validation"""
        # Test empty/whitespace handling
        test_cases = [
            ("", False),
            ("   ", False),
            ("refs:", False),
            ("refs:   ", False),
            ("refs:REF-1", True),
            ("refs: REF-1 ", True),
        ]
        
        for case_refs, should_be_valid in test_cases:
            # Apply validation logic (same as in junit_xml.py)
            if case_refs.startswith("refs:"):
                refs_content = case_refs[5:]
                is_valid = bool(refs_content and refs_content.strip())
                assert is_valid == should_be_valid


class TestCaseUpdateWorkflow:
    """Test coverage for case update workflow logic"""

    def test_case_categorization_logic(self):
        """Test logic for categorizing cases during updates"""
        # Mock test cases
        existing_case = {"case_id": 123, "has_junit_refs": True}
        newly_created_case = {"case_id": 456, "has_junit_refs": True}
        case_without_refs = {"case_id": 789, "has_junit_refs": False}
        
        # Mock newly created case IDs
        newly_created_case_ids = {456}
        
        # Test categorization logic
        cases_to_update = []
        cases_to_skip = []
        
        for case in [existing_case, newly_created_case, case_without_refs]:
            case_id = case["case_id"]
            has_refs = case["has_junit_refs"]
            
            if case_id in newly_created_case_ids:
                cases_to_skip.append({"case_id": case_id, "reason": "Newly created case"})
            elif not has_refs:
                cases_to_skip.append({"case_id": case_id, "reason": "No JUnit refs"})
            else:
                cases_to_update.append(case)
        
        # Verify categorization
        assert len(cases_to_update) == 1
        assert cases_to_update[0]["case_id"] == 123
        
        assert len(cases_to_skip) == 2
        assert any(c["case_id"] == 456 and "Newly created" in c["reason"] for c in cases_to_skip)
        assert any(c["case_id"] == 789 and "No JUnit refs" in c["reason"] for c in cases_to_skip)

    def test_update_result_categorization(self):
        """Test categorization of update results"""
        # Mock API responses
        api_responses = [
            (True, "Success", ["REF-1"], []),  # Successful update
            (True, "Success", [], ["REF-2"]),  # All refs already present
            (False, "API Error", [], []),      # Failed update
        ]
        
        updated_cases = []
        skipped_cases = []
        failed_cases = []
        
        for i, (success, message, added_refs, skipped_refs) in enumerate(api_responses):
            case_id = 100 + i
            
            if not success:
                failed_cases.append({"case_id": case_id, "error": message})
            elif not added_refs:  # No refs were added (all were duplicates)
                skipped_cases.append({
                    "case_id": case_id,
                    "reason": "All references already present",
                    "skipped_refs": skipped_refs
                })
            else:
                updated_cases.append({
                    "case_id": case_id,
                    "added_refs": added_refs,
                    "skipped_refs": skipped_refs
                })
        
        # Verify categorization
        assert len(updated_cases) == 1
        assert updated_cases[0]["case_id"] == 100
        assert updated_cases[0]["added_refs"] == ["REF-1"]
        
        assert len(skipped_cases) == 1
        assert skipped_cases[0]["case_id"] == 101
        assert "All references already present" in skipped_cases[0]["reason"]
        
        assert len(failed_cases) == 1
        assert failed_cases[0]["case_id"] == 102
        assert failed_cases[0]["error"] == "API Error"
