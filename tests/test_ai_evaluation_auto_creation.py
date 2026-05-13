"""
Unit tests for AI Evaluation Template auto-creation feature

Tests verify that when using -y flag (auto-creation mode), TRCLI automatically:
1. Detects AI Evaluation indicators (quality_rating, AI case fields)
2. Validates AI Evaluation template exists in project
3. Applies template_id=5 to auto-created test cases
"""

from pathlib import Path
from unittest.mock import Mock, MagicMock
import pytest

from trcli.data_classes.dataclass_testrail import TestRailSuite, TestRailSection, TestRailCase, TestRailResult
from trcli.data_classes.data_parsers import FieldsParser


class TestFieldsParserIntegerConversion:
    """Test that FieldsParser converts numeric strings to integers"""

    def test_convert_ai_dropdown_fields_to_int(self):
        """Test that AI dropdown fields are converted to integers"""
        fields = ["custom_ai_type:1", "custom_ai_model:2"]

        result, error = FieldsParser.resolve_fields(fields)

        assert error is None
        assert result["custom_ai_type"] == 1  # Should be integer, not string
        assert result["custom_ai_model"] == 2
        assert isinstance(result["custom_ai_type"], int)
        assert isinstance(result["custom_ai_model"], int)

    def test_keep_non_ai_numeric_strings_as_strings(self):
        """Test that non-AI numeric strings remain as strings"""
        fields = ["custom_automation_id:1234", "custom_steps:5"]

        result, error = FieldsParser.resolve_fields(fields)

        assert error is None
        assert result["custom_automation_id"] == "1234"  # Should remain string
        assert result["custom_steps"] == "5"  # Should remain string
        assert isinstance(result["custom_automation_id"], str)
        assert isinstance(result["custom_steps"], str)

    def test_mixed_ai_and_regular_fields(self):
        """Test that AI fields are converted but regular fields remain strings"""
        fields = ["custom_ai_type:3", "custom_preconds:AI setup", "custom_ai_model:1", "custom_automation_id:999"]

        result, error = FieldsParser.resolve_fields(fields)

        assert error is None
        assert result["custom_ai_type"] == 3  # AI field -> integer
        assert isinstance(result["custom_ai_type"], int)
        assert result["custom_preconds"] == "AI setup"  # Text field -> string
        assert isinstance(result["custom_preconds"], str)
        assert result["custom_ai_model"] == 1  # AI field -> integer
        assert isinstance(result["custom_ai_model"], int)
        assert result["custom_automation_id"] == "999"  # Regular numeric field -> string
        assert isinstance(result["custom_automation_id"], str)

    def test_list_values_remain_lists(self):
        """Test that list values (using ast.literal_eval) are preserved"""
        fields = ["custom_steps:[1, 2, 3]", 'custom_tags:["ai", "evaluation"]']

        result, error = FieldsParser.resolve_fields(fields)

        assert error is None
        assert result["custom_steps"] == [1, 2, 3]
        assert isinstance(result["custom_steps"], list)
        assert result["custom_tags"] == ["ai", "evaluation"]


class TestAIEvaluationFieldParsing:
    """Test parsing of AI case fields - integration tests are in test_junit_quality_rating.py"""

    def test_fields_parser_handles_ai_case_fields(self):
        """Test that FieldsParser correctly processes AI case fields"""
        # This test validates the core parsing logic that powers XML/Robot parsing
        case_fields_list = ["custom_ai_type:1", "custom_ai_model:2", "custom_preconds:Setup AI environment"]

        result, error = FieldsParser.resolve_fields(case_fields_list)

        assert error is None
        assert result["custom_ai_type"] == 1  # Integer conversion
        assert isinstance(result["custom_ai_type"], int)
        assert result["custom_ai_model"] == 2  # Integer conversion
        assert isinstance(result["custom_ai_model"], int)
        assert result["custom_preconds"] == "Setup AI environment"  # String preserved
        assert isinstance(result["custom_preconds"], str)


class TestAIEvaluationDetection:
    """Test _should_use_ai_evaluation_template() detection logic"""

    def test_detect_quality_rating_in_results(self):
        """Test detection when quality_rating is present"""
        from trcli.api.results_uploader import ResultsUploader

        # Create suite with quality_rating
        result = TestRailResult(status_id=1, quality_rating={"factual_accuracy": 5})
        case = TestRailCase(title="Test", result=result)
        section = TestRailSection(name="Section")
        section.testcases = [case]
        suite = TestRailSuite(name="Suite")
        suite.testsections = [section]

        # Create uploader with mock env and api_request_handler
        env = Mock()
        env.case_fields = {}
        env.vlog = Mock()

        api_handler = Mock()
        api_handler.suites_data_from_provider = suite

        uploader = ResultsUploader.__new__(ResultsUploader)
        uploader.environment = env
        uploader.api_request_handler = api_handler

        result = uploader._should_use_ai_evaluation_template()

        assert result is True
        env.vlog.assert_called_with("Detected quality_rating in test results - will use AI Evaluation template")

    def test_detect_ai_case_fields_in_cli(self):
        """Test detection when AI case fields are in CLI --case-fields"""
        from trcli.api.results_uploader import ResultsUploader

        # Create suite without quality_rating
        result = TestRailResult(status_id=1)
        case = TestRailCase(title="Test", result=result)
        section = TestRailSection(name="Section")
        section.testcases = [case]
        suite = TestRailSuite(name="Suite")
        suite.testsections = [section]

        # Create uploader with AI case fields in CLI
        env = Mock()
        env.case_fields = {"custom_ai_type": 1, "custom_ai_model": 2}
        env.vlog = Mock()

        api_handler = Mock()
        api_handler.suites_data_from_provider = suite

        uploader = ResultsUploader.__new__(ResultsUploader)
        uploader.environment = env
        uploader.api_request_handler = api_handler

        result = uploader._should_use_ai_evaluation_template()

        assert result is True
        env.vlog.assert_called_with("Detected AI case fields in --case-fields - will use AI Evaluation template")

    def test_detect_ai_case_fields_in_xml(self):
        """Test detection when AI case fields are in XML properties"""
        from trcli.api.results_uploader import ResultsUploader

        # Create suite with AI case fields in test case
        result = TestRailResult(status_id=1)
        case = TestRailCase(title="Test", case_fields={"custom_ai_type": 1, "custom_ai_model": 2}, result=result)
        section = TestRailSection(name="Section")
        section.testcases = [case]
        suite = TestRailSuite(name="Suite")
        suite.testsections = [section]

        # Create uploader
        env = Mock()
        env.case_fields = {}
        env.vlog = Mock()

        api_handler = Mock()
        api_handler.suites_data_from_provider = suite

        uploader = ResultsUploader.__new__(ResultsUploader)
        uploader.environment = env
        uploader.api_request_handler = api_handler

        result = uploader._should_use_ai_evaluation_template()

        assert result is True
        env.vlog.assert_called_with("Detected AI case fields in XML properties - will use AI Evaluation template")

    def test_no_detection_without_indicators(self):
        """Test no detection when no AI indicators present"""
        from trcli.api.results_uploader import ResultsUploader

        # Create suite without any AI indicators
        result = TestRailResult(status_id=1)
        case = TestRailCase(title="Test", result=result)
        section = TestRailSection(name="Section")
        section.testcases = [case]
        suite = TestRailSuite(name="Suite")
        suite.testsections = [section]

        # Create uploader
        env = Mock()
        env.case_fields = {}
        env.vlog = Mock()

        api_handler = Mock()
        api_handler.suites_data_from_provider = suite

        uploader = ResultsUploader.__new__(ResultsUploader)
        uploader.environment = env
        uploader.api_request_handler = api_handler

        result = uploader._should_use_ai_evaluation_template()

        assert result is False


class TestSelectiveTemplateApplication:
    """Test that AI Evaluation template is applied selectively per test case"""

    def test_apply_template_only_to_cases_with_quality_rating(self):
        """Test that only cases with quality_rating get AI template"""
        from trcli.api.results_uploader import ResultsUploader

        # Create suite with mixed cases
        result_with_rating = TestRailResult(status_id=1, quality_rating={"factual_accuracy": 5})
        result_without_rating = TestRailResult(status_id=1)

        case_with_rating = TestRailCase(title="AI Test", result=result_with_rating)
        case_without_rating = TestRailCase(title="Regular Test", result=result_without_rating)

        section = TestRailSection(name="Section")
        section.testcases = [case_with_rating, case_without_rating]
        suite = TestRailSuite(name="Suite")
        suite.testsections = [section]

        # Create uploader
        env = Mock()
        env.case_fields = {}
        env.vlog = Mock()
        env.log = Mock()

        api_handler = Mock()
        api_handler.suites_data_from_provider = suite

        uploader = ResultsUploader.__new__(ResultsUploader)
        uploader.environment = env
        uploader.api_request_handler = api_handler

        # Test per-case logic
        assert uploader._test_case_needs_ai_template(case_with_rating) is True
        assert uploader._test_case_needs_ai_template(case_without_rating) is False

    def test_ai_case_fields_do_not_require_ai_template(self):
        """Test that AI case fields do NOT require AI template - they work with any template"""
        from trcli.api.results_uploader import ResultsUploader

        # Create suite with AI case fields but NO quality_rating in result
        result = TestRailResult(status_id=1)  # No quality_rating

        case_with_ai_fields = TestRailCase(
            title="AI Test", case_fields={"custom_ai_type": 1, "custom_ai_model": 2}, result=result
        )

        section = TestRailSection(name="Section")
        section.testcases = [case_with_ai_fields]
        suite = TestRailSuite(name="Suite")
        suite.testsections = [section]

        # Create uploader
        env = Mock()
        env.case_fields = {}
        env.vlog = Mock()

        api_handler = Mock()
        api_handler.suites_data_from_provider = suite

        uploader = ResultsUploader.__new__(ResultsUploader)
        uploader.environment = env
        uploader.api_request_handler = api_handler

        # AI case fields are just metadata - they do NOT require AI template
        # Only quality_rating requires AI Evaluation template
        assert uploader._test_case_needs_ai_template(case_with_ai_fields) is False

    def test_ai_case_fields_with_quality_rating_gets_template(self):
        """Test that cases with BOTH AI case fields AND quality_rating get AI template"""
        from trcli.api.results_uploader import ResultsUploader

        # Create case with both AI case fields AND quality_rating
        result_with_rating = TestRailResult(status_id=1, quality_rating={"factual_accuracy": 5})
        case_with_both = TestRailCase(
            title="AI Test", case_fields={"custom_ai_type": 1, "custom_ai_model": 2}, result=result_with_rating
        )

        section = TestRailSection(name="Section")
        section.testcases = [case_with_both]
        suite = TestRailSuite(name="Suite")
        suite.testsections = [section]

        # Create uploader
        env = Mock()
        env.case_fields = {}
        env.vlog = Mock()

        api_handler = Mock()
        api_handler.suites_data_from_provider = suite

        uploader = ResultsUploader.__new__(ResultsUploader)
        uploader.environment = env
        uploader.api_request_handler = api_handler

        # Should need AI template due to quality_rating
        assert uploader._test_case_needs_ai_template(case_with_both) is True

    def test_mixed_report_selective_template_application(self):
        """Test full workflow: mixed report with selective template application"""
        from trcli.api.results_uploader import ResultsUploader

        # Create suite with 3 cases: 2 with quality_rating, 1 without
        result1 = TestRailResult(status_id=1, quality_rating={"factual_accuracy": 5})
        result2 = TestRailResult(status_id=1, quality_rating={"coherence": 4})
        result3 = TestRailResult(status_id=1)  # No quality_rating

        case1 = TestRailCase(title="AI Test 1", result=result1)
        case2 = TestRailCase(title="AI Test 2", result=result2)
        case3 = TestRailCase(title="Regular Test", result=result3)

        section = TestRailSection(name="Section")
        section.testcases = [case1, case2, case3]
        suite = TestRailSuite(name="Suite")
        suite.testsections = [section]

        # Create uploader and mock project
        env = Mock()
        env.case_fields = {}
        env.vlog = Mock()
        env.log = Mock()

        api_handler = Mock()
        api_handler.suites_data_from_provider = suite
        api_handler.validate_ai_evaluation_template = Mock(return_value=(True, "", 10))

        uploader = ResultsUploader.__new__(ResultsUploader)
        uploader.environment = env
        uploader.api_request_handler = api_handler
        uploader.project = Mock()
        uploader.project.project_id = 1

        # Apply template
        uploader._apply_ai_evaluation_template()

        # Verify: cases 1 and 2 should have template_id=10, case 3 should not
        assert case1.template_id == 10
        assert case2.template_id == 10
        assert case3.template_id is None  # No template set

        # Verify log message
        env.log.assert_any_call(
            "Using AI Evaluation template (ID: 10) for 2 test case(s), 1 test case(s) will use default template"
        )


class TestValidateAIEvaluationTemplate:
    """Test validate_ai_evaluation_template API method"""

    def test_validate_template_exists_by_id(self):
        """Test validation succeeds when template ID 5 exists"""
        from trcli.api.api_request_handler import ApiRequestHandler

        mock_client = Mock()
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.error_message = None
        mock_response.response_text = [
            {"id": 1, "name": "Test Case (Text)"},
            {"id": 5, "name": "AI Evaluation", "i18n_custom_id": "templates_ai_evaluation"},
            {"id": 2, "name": "Test Case (Steps)"},
        ]
        mock_client.send_get.return_value = mock_response

        # Create handler using __new__ to bypass __init__
        handler = ApiRequestHandler.__new__(ApiRequestHandler)
        handler.client = mock_client
        handler.environment = Mock()
        handler.environment.vlog = Mock()

        exists, error, template_id = handler.validate_ai_evaluation_template(project_id=1)

        assert exists is True
        assert error == ""
        assert template_id == 5
        mock_client.send_get.assert_called_once_with("get_templates/1")

    def test_validate_template_exists_by_i18n(self):
        """Test validation succeeds when template has i18n_custom_id with non-standard ID"""
        from trcli.api.api_request_handler import ApiRequestHandler

        mock_client = Mock()
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.error_message = None
        mock_response.response_text = [
            {"id": 10, "name": "AI Evaluation Custom", "i18n_custom_id": "templates_ai_evaluation"}
        ]
        mock_client.send_get.return_value = mock_response

        handler = ApiRequestHandler.__new__(ApiRequestHandler)
        handler.client = mock_client
        handler.environment = Mock()
        handler.environment.vlog = Mock()

        exists, error, template_id = handler.validate_ai_evaluation_template(project_id=1)

        assert exists is True
        assert error == ""
        assert template_id == 10  # Returns actual ID, not hardcoded 5

    def test_validate_template_not_found(self):
        """Test validation fails when template doesn't exist"""
        from trcli.api.api_request_handler import ApiRequestHandler

        mock_client = Mock()
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.error_message = None
        mock_response.response_text = [{"id": 1, "name": "Test Case (Text)"}, {"id": 2, "name": "Test Case (Steps)"}]
        mock_client.send_get.return_value = mock_response

        handler = ApiRequestHandler.__new__(ApiRequestHandler)
        handler.client = mock_client
        handler.environment = Mock()
        handler.environment.vlog = Mock()

        exists, error, template_id = handler.validate_ai_evaluation_template(project_id=1)

        assert exists is False
        assert "AI Evaluation template" in error
        assert "not enabled" in error
        assert "To enable AI Evaluation template" in error
        assert template_id == 0  # Returns 0 when not found

    def test_validate_template_api_error(self):
        """Test validation handles API errors gracefully"""
        from trcli.api.api_request_handler import ApiRequestHandler

        mock_client = Mock()
        mock_response = Mock()
        mock_response.status_code = 403
        mock_response.error_message = "Insufficient permissions"
        mock_response.response_text = None
        mock_client.send_get.return_value = mock_response

        handler = ApiRequestHandler.__new__(ApiRequestHandler)
        handler.client = mock_client
        handler.environment = Mock()
        handler.environment.vlog = Mock()

        exists, error, template_id = handler.validate_ai_evaluation_template(project_id=1)

        assert exists is False
        assert "Insufficient permissions" in error
        assert template_id == 0  # Returns 0 on API error
