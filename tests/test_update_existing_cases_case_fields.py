"""
Unit tests for updating existing cases with case fields via --update-existing-cases yes
"""

from unittest.mock import Mock
import pytest

from trcli.api.results_uploader import ResultsUploader
from trcli.data_classes.dataclass_testrail import TestRailSuite, TestRailSection, TestRailCase, TestRailResult


class TestUpdateExistingCasesWithCaseFields:
    """Test that --update-existing-cases yes properly updates case fields"""

    def test_global_case_fields_applied_to_existing_cases(self):
        """Test that global --case-fields are applied before updating existing cases"""
        # Create suite with existing case (has case_id)
        result = TestRailResult(status_id=1)
        case = TestRailCase(title="Existing Test", case_id=1234, result=result)  # Existing case
        section = TestRailSection(name="Section")
        section.testcases = [case]
        suite = TestRailSuite(name="Suite")
        suite.testsections = [section]

        # Create environment with global case fields
        env = Mock()
        env.case_fields = {"custom_ai_type": 1, "custom_ai_model": 2}
        env.update_existing_cases = "yes"
        env.vlog = Mock()
        env.log = Mock()
        env.elog = Mock()

        # Create uploader
        api_handler = Mock()
        api_handler.suites_data_from_provider = suite
        api_handler.update_existing_case_references = Mock(
            return_value=(True, None, [], [], ["custom_ai_type", "custom_ai_model"])
        )

        uploader = ResultsUploader.__new__(ResultsUploader)
        uploader.environment = env
        uploader.api_request_handler = api_handler

        # Call update method
        update_results, failed_cases = uploader.update_existing_cases_with_junit_refs(added_test_cases=None)

        # Verify global case fields were applied
        assert case.case_fields["custom_ai_type"] == 1
        assert case.case_fields["custom_ai_model"] == 2

        # Verify update was called with the case fields
        api_handler.update_existing_case_references.assert_called_once()
        call_args = api_handler.update_existing_case_references.call_args
        assert call_args[0][0] == 1234  # case_id
        assert call_args[0][2]["custom_ai_type"] == 1  # case_fields
        assert call_args[0][2]["custom_ai_model"] == 2

        # Verify results
        assert len(update_results["updated_cases"]) == 1
        assert update_results["updated_cases"][0]["case_id"] == 1234
        assert "custom_ai_type" in update_results["updated_cases"][0]["updated_fields"]
        assert "custom_ai_model" in update_results["updated_cases"][0]["updated_fields"]

    def test_xml_case_fields_override_global(self):
        """Test that XML case fields override global CLI case fields"""
        # Create suite with existing case that has XML case fields
        result = TestRailResult(status_id=1)
        case = TestRailCase(
            title="Existing Test",
            case_id=5678,
            case_fields={"custom_ai_type": 3},  # XML specifies type=3
            result=result,
        )
        section = TestRailSection(name="Section")
        section.testcases = [case]
        suite = TestRailSuite(name="Suite")
        suite.testsections = [section]

        # Create environment with global case fields
        env = Mock()
        env.case_fields = {"custom_ai_type": 1, "custom_ai_model": 2}  # CLI specifies type=1
        env.update_existing_cases = "yes"
        env.vlog = Mock()
        env.log = Mock()
        env.elog = Mock()

        # Create uploader
        api_handler = Mock()
        api_handler.suites_data_from_provider = suite
        api_handler.update_existing_case_references = Mock(
            return_value=(True, None, [], [], ["custom_ai_type", "custom_ai_model"])
        )

        uploader = ResultsUploader.__new__(ResultsUploader)
        uploader.environment = env
        uploader.api_request_handler = api_handler

        # Call update method
        update_results, failed_cases = uploader.update_existing_cases_with_junit_refs(added_test_cases=None)

        # Verify XML value (3) takes precedence over global CLI value (1)
        assert case.case_fields["custom_ai_type"] == 3  # Should be 3 from XML, not 1 from CLI
        assert case.case_fields["custom_ai_model"] == 2  # Should be 2 from CLI (not in XML)

        # Verify update was called with merged case fields
        call_args = api_handler.update_existing_case_references.call_args
        assert call_args[0][2]["custom_ai_type"] == 3  # XML value
        assert call_args[0][2]["custom_ai_model"] == 2  # CLI value

    def test_newly_created_cases_excluded_from_update(self):
        """Test that newly created cases are excluded from update"""
        # Create suite with a newly created case
        result = TestRailResult(status_id=1)
        case = TestRailCase(title="New Test", case_id=9999, result=result)  # This case was just created
        section = TestRailSection(name="Section")
        section.testcases = [case]
        suite = TestRailSuite(name="Suite")
        suite.testsections = [section]

        # Create environment
        env = Mock()
        env.case_fields = {"custom_ai_type": 1}
        env.update_existing_cases = "yes"
        env.vlog = Mock()
        env.log = Mock()
        env.elog = Mock()

        # Create uploader
        api_handler = Mock()
        api_handler.suites_data_from_provider = suite
        api_handler.update_existing_case_references = Mock()

        uploader = ResultsUploader.__new__(ResultsUploader)
        uploader.environment = env
        uploader.api_request_handler = api_handler

        # Call update method with case 9999 in added_test_cases (newly created)
        added_test_cases = [{"case_id": 9999}]
        update_results, failed_cases = uploader.update_existing_cases_with_junit_refs(added_test_cases=added_test_cases)

        # Verify update was NOT called (case was excluded)
        api_handler.update_existing_case_references.assert_not_called()

        # Verify no cases were updated (newly created cases are silently excluded)
        assert len(update_results["updated_cases"]) == 0
        assert len(failed_cases) == 0

    def test_no_case_fields_skips_update(self):
        """Test that cases without case fields or refs are skipped"""
        # Create suite with existing case but no case fields
        result = TestRailResult(status_id=1)
        case = TestRailCase(title="Existing Test", case_id=1111, result=result)
        section = TestRailSection(name="Section")
        section.testcases = [case]
        suite = TestRailSuite(name="Suite")
        suite.testsections = [section]

        # Create environment with NO global case fields
        env = Mock()
        env.case_fields = {}  # No global case fields
        env.update_existing_cases = "yes"
        env.vlog = Mock()
        env.log = Mock()
        env.elog = Mock()

        # Create uploader
        api_handler = Mock()
        api_handler.suites_data_from_provider = suite
        api_handler.update_existing_case_references = Mock()

        uploader = ResultsUploader.__new__(ResultsUploader)
        uploader.environment = env
        uploader.api_request_handler = api_handler

        # Call update method
        update_results, failed_cases = uploader.update_existing_cases_with_junit_refs(added_test_cases=None)

        # Verify update was NOT called (no case fields to update)
        api_handler.update_existing_case_references.assert_not_called()

        # Verify no cases were updated
        assert len(update_results["updated_cases"]) == 0
        assert len(update_results["skipped_cases"]) == 0
