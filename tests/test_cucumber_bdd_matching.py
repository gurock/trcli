import pytest
import json
from unittest import mock
from unittest.mock import MagicMock, patch, call
from pathlib import Path

from trcli.cli import Environment
from trcli.readers.cucumber_json import CucumberParser
from trcli.data_classes.dataclass_testrail import TestRailSeparatedStep


class TestCucumberBDDMatching:
    """Test class for BDD matching mode functionality in CucumberParser"""

    def setup_method(self):
        """Set up test environment"""
        self.environment = Environment(cmd="parse_cucumber")
        self.environment.host = "https://test.testrail.com"
        self.environment.username = "test@example.com"
        self.environment.password = "password"
        self.environment.project = "Test Project"
        self.environment.project_id = 1
        self.environment.suite_id = 2

        # Create a temporary test file for CucumberParser initialization
        import tempfile

        self.temp_file = tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False)
        self.temp_file.write("[]")
        self.temp_file.close()
        self.environment.file = self.temp_file.name

        # Sample Cucumber JSON feature
        self.sample_feature = {
            "name": "User Login",
            "tags": [{"name": "@smoke"}],
            "elements": [
                {
                    "type": "scenario",
                    "name": "Successful login",
                    "tags": [],
                    "steps": [
                        {
                            "keyword": "Given",
                            "name": "user is on login page",
                            "result": {"status": "passed", "duration": 1000000000},
                        },
                        {
                            "keyword": "When",
                            "name": "user enters valid credentials",
                            "result": {"status": "passed", "duration": 2000000000},
                        },
                        {
                            "keyword": "Then",
                            "name": "user is logged in",
                            "result": {"status": "passed", "duration": 500000000},
                        },
                    ],
                },
                {
                    "type": "scenario",
                    "name": "Failed login",
                    "tags": [],
                    "steps": [
                        {
                            "keyword": "Given",
                            "name": "user is on login page",
                            "result": {"status": "passed", "duration": 1000000000},
                        },
                        {
                            "keyword": "When",
                            "name": "user enters invalid credentials",
                            "result": {"status": "passed", "duration": 2000000000},
                        },
                        {
                            "keyword": "Then",
                            "name": "error message is shown",
                            "result": {
                                "status": "failed",
                                "duration": 500000000,
                                "error_message": "Expected error not found",
                            },
                        },
                    ],
                },
            ],
        }

    def teardown_method(self):
        """Clean up temporary files"""
        import os

        if hasattr(self, "temp_file") and os.path.exists(self.temp_file.name):
            os.unlink(self.temp_file.name)

    @pytest.mark.cucumber_bdd_matching
    def test_normalize_title_basic(self):
        """Test title normalization removes special characters and normalizes case"""
        parser = CucumberParser(self.environment)

        assert parser._normalize_title("User Login") == "user login"
        assert parser._normalize_title("User-Login") == "user login"
        assert parser._normalize_title("User_Login!") == "user login"
        assert parser._normalize_title("  User  Login  ") == "user login"
        assert parser._normalize_title("User@#$%Login") == "user login"

    @pytest.mark.cucumber_bdd_matching
    def test_normalize_title_complex(self):
        """Test title normalization with complex cases"""
        parser = CucumberParser(self.environment)

        assert parser._normalize_title("E-commerce: Product Checkout") == "e commerce product checkout"
        assert parser._normalize_title("API (v2) Authentication") == "api v2 authentication"
        assert parser._normalize_title("Test-Case #123") == "test case 123"

    @pytest.mark.cucumber_bdd_matching
    def test_extract_case_id_from_feature_tags(self):
        """Test case ID extraction from feature-level tags"""
        parser = CucumberParser(self.environment)

        feature_tags = ["@smoke", "@C123", "@regression"]
        scenario_tags = ["@C456"]

        # Feature-level tag should take priority
        case_id = parser._extract_case_id_from_tags(feature_tags, scenario_tags)
        assert case_id == 123

    @pytest.mark.cucumber_bdd_matching
    def test_extract_case_id_from_scenario_tags(self):
        """Test case ID extraction from scenario-level tags (fallback)"""
        parser = CucumberParser(self.environment)

        feature_tags = ["@smoke"]
        scenario_tags = ["@C456", "@regression"]

        # Should use scenario-level tag when no feature-level tag
        case_id = parser._extract_case_id_from_tags(feature_tags, scenario_tags)
        assert case_id == 456

    @pytest.mark.cucumber_bdd_matching
    def test_extract_case_id_no_tags(self):
        """Test case ID extraction returns None when no @C tags"""
        parser = CucumberParser(self.environment)

        feature_tags = ["@smoke", "@regression"]
        scenario_tags = ["@fast"]

        case_id = parser._extract_case_id_from_tags(feature_tags, scenario_tags)
        assert case_id is None

    @pytest.mark.cucumber_bdd_matching
    def test_extract_case_id_lowercase(self):
        """Test case ID extraction with lowercase @c tag"""
        parser = CucumberParser(self.environment)

        feature_tags = ["@c789"]
        scenario_tags = []

        case_id = parser._extract_case_id_from_tags(feature_tags, scenario_tags)
        assert case_id == 789

    @pytest.mark.cucumber_bdd_matching
    def test_extract_case_id_invalid_format(self):
        """Test case ID extraction handles invalid formats gracefully"""
        parser = CucumberParser(self.environment)

        feature_tags = ["@C", "@Cabc", "@C123abc"]
        scenario_tags = []

        # Should return None for invalid formats
        case_id = parser._extract_case_id_from_tags(feature_tags, scenario_tags)
        assert case_id is None

    @pytest.mark.cucumber_bdd_matching
    def test_find_case_by_title_found(self):
        """Test finding case by title using cached lookup"""
        parser = CucumberParser(self.environment)

        # Mock API handler
        mock_api_handler = MagicMock()
        parser._api_handler = mock_api_handler

        # Mock find_bdd_case_by_name to return case ID 101
        mock_api_handler.find_bdd_case_by_name.return_value = (101, None, [])

        case_id = parser._find_case_by_title("User Login", project_id=1, suite_id=2)
        assert case_id == 101

        # Verify API handler was called correctly
        mock_api_handler.find_bdd_case_by_name.assert_called_once_with(
            feature_name="User Login", project_id=1, suite_id=2
        )

    @pytest.mark.cucumber_bdd_matching
    def test_find_case_by_title_not_found(self):
        """Test finding case by title returns None when not in cache"""
        parser = CucumberParser(self.environment)

        # Mock API handler
        mock_api_handler = MagicMock()
        parser._api_handler = mock_api_handler

        # Mock find_bdd_case_by_name to return -1 (not found)
        mock_api_handler.find_bdd_case_by_name.return_value = (-1, None, [])

        case_id = parser._find_case_by_title("Nonexistent Feature", project_id=1, suite_id=2)
        assert case_id is None

    @pytest.mark.cucumber_bdd_matching
    def test_find_case_by_title_normalization(self):
        """Test case matching with different formatting (normalization happens in API handler)"""
        parser = CucumberParser(self.environment)

        # Mock API handler
        mock_api_handler = MagicMock()
        parser._api_handler = mock_api_handler

        # Mock find_bdd_case_by_name to always return case ID 101
        # (normalization is tested in API handler tests)
        mock_api_handler.find_bdd_case_by_name.return_value = (101, None, [])

        # Should call API handler with each variation
        assert parser._find_case_by_title("User Login", 1, 2) == 101
        assert parser._find_case_by_title("User-Login", 1, 2) == 101
        assert parser._find_case_by_title("user_login", 1, 2) == 101
        assert parser._find_case_by_title("USER LOGIN", 1, 2) == 101

        # Verify API handler was called 4 times
        assert mock_api_handler.find_bdd_case_by_name.call_count == 4

    @pytest.mark.cucumber_bdd_matching
    def test_api_handler_builds_cache_correctly(self):
        """Test API handler builds BDD cases cache correctly (integration test)"""
        from trcli.api.api_request_handler import ApiRequestHandler
        from trcli.api.api_client import APIClient

        # Create mock environment and client
        mock_env = MagicMock()
        mock_env.vlog = MagicMock()
        mock_client = MagicMock(spec=APIClient)
        mock_client.VERSION = "v2"

        # Create API handler with mock suite data
        from trcli.data_classes.dataclass_testrail import TestRailSuite

        mock_suite = TestRailSuite(name="test", suite_id=2)

        api_handler = ApiRequestHandler(
            environment=mock_env, api_client=mock_client, suites_data=mock_suite, verify=False
        )

        # Mock __get_all_cases to return BDD and non-BDD cases
        mock_cases = [
            {"id": 101, "title": "User Login", "custom_testrail_bdd_scenario": "Scenario: Login"},
            {"id": 102, "title": "Product Search", "custom_testrail_bdd_scenario": None},  # Not BDD
            {"id": 103, "title": "Checkout Process", "custom_testrail_bdd_scenario": "Scenario: Checkout"},
        ]

        with patch.object(api_handler, "_ApiRequestHandler__get_all_cases", return_value=(mock_cases, None)):
            # Call find_bdd_case_by_name which triggers cache build
            case_id, error, duplicates = api_handler.find_bdd_case_by_name("User Login", 1, 2)

            # Should find case 101
            assert case_id == 101
            assert error is None
            assert duplicates == []

    @pytest.mark.cucumber_bdd_matching
    def test_api_handler_caching_behavior(self):
        """Test API handler cache is only built once per project/suite"""
        from trcli.api.api_request_handler import ApiRequestHandler
        from trcli.api.api_client import APIClient
        from trcli.data_classes.dataclass_testrail import TestRailSuite

        # Create mock environment and client
        mock_env = MagicMock()
        mock_env.vlog = MagicMock()
        mock_client = MagicMock(spec=APIClient)
        mock_client.VERSION = "v2"

        mock_suite = TestRailSuite(name="test", suite_id=2)
        api_handler = ApiRequestHandler(
            environment=mock_env, api_client=mock_client, suites_data=mock_suite, verify=False
        )

        mock_cases = [{"id": 101, "title": "User Login", "custom_testrail_bdd_scenario": "Scenario: Login"}]

        with patch.object(
            api_handler, "_ApiRequestHandler__get_all_cases", return_value=(mock_cases, None)
        ) as mock_get_cases:
            # First call - should build cache
            case_id1, _, _ = api_handler.find_bdd_case_by_name("User Login", 1, 2)
            assert mock_get_cases.call_count == 1

            # Second call with same project/suite - should use cache
            case_id2, _, _ = api_handler.find_bdd_case_by_name("User Login", 1, 2)
            assert mock_get_cases.call_count == 1  # No additional call

            # Both calls should find the same case
            assert case_id1 == case_id2 == 101

    @pytest.mark.cucumber_bdd_matching
    def test_api_handler_handles_api_error(self):
        """Test API handler handles API errors gracefully"""
        from trcli.api.api_request_handler import ApiRequestHandler
        from trcli.api.api_client import APIClient
        from trcli.data_classes.dataclass_testrail import TestRailSuite

        # Create mock environment and client
        mock_env = MagicMock()
        mock_env.vlog = MagicMock()
        mock_client = MagicMock(spec=APIClient)
        mock_client.VERSION = "v2"

        mock_suite = TestRailSuite(name="test", suite_id=2)
        api_handler = ApiRequestHandler(
            environment=mock_env, api_client=mock_client, suites_data=mock_suite, verify=False
        )

        # Mock API error
        with patch.object(api_handler, "_ApiRequestHandler__get_all_cases", return_value=([], "API Error")):
            case_id, error, duplicates = api_handler.find_bdd_case_by_name("User Login", 1, 2)

            # Should return None with error message
            assert case_id is None
            assert "API Error" in error
            assert duplicates == []

    @pytest.mark.cucumber_bdd_matching
    def test_validate_bdd_case_exists_valid(self):
        """Test validation succeeds for valid BDD case"""
        parser = CucumberParser(self.environment)

        mock_api_handler = MagicMock()
        parser._api_handler = mock_api_handler

        # Mock valid BDD case - mock send_get response
        mock_response = MagicMock()
        mock_response.error_message = None
        mock_response.response_text = {
            "id": 101,
            "title": "User Login",
            "custom_testrail_bdd_scenario": "Scenario: Login",
        }
        mock_api_handler.client.send_get.return_value = mock_response

        is_valid, error_message = parser._validate_bdd_case_exists(101)

        assert is_valid is True
        assert error_message is None

    @pytest.mark.cucumber_bdd_matching
    def test_validate_bdd_case_not_found(self):
        """Test validation fails when case not found"""
        parser = CucumberParser(self.environment)

        mock_api_handler = MagicMock()
        parser._api_handler = mock_api_handler

        # Mock case not found - mock send_get response
        mock_response = MagicMock()
        mock_response.error_message = "Case not found"
        mock_response.response_text = None
        mock_api_handler.client.send_get.return_value = mock_response

        is_valid, error_message = parser._validate_bdd_case_exists(999)

        assert is_valid is False
        assert "not found" in error_message.lower()

    @pytest.mark.cucumber_bdd_matching
    def test_validate_bdd_case_not_bdd_template(self):
        """Test validation fails when case is not BDD template"""
        parser = CucumberParser(self.environment)

        mock_api_handler = MagicMock()
        parser._api_handler = mock_api_handler

        # Mock non-BDD case - mock send_get response
        mock_response = MagicMock()
        mock_response.error_message = None
        mock_response.response_text = {"id": 102, "title": "Regular Test", "custom_testrail_bdd_scenario": None}
        mock_api_handler.client.send_get.return_value = mock_response

        is_valid, error_message = parser._validate_bdd_case_exists(102)

        assert is_valid is False
        assert "not a bdd template" in error_message.lower()

    @pytest.mark.cucumber_bdd_matching
    def test_parse_feature_as_bdd_case_with_tag(self):
        """Test parsing feature as BDD case using @C tag"""
        parser = CucumberParser(self.environment)

        mock_api_handler = MagicMock()
        parser._api_handler = mock_api_handler

        # Mock validation - mock send_get response
        mock_response = MagicMock()
        mock_response.error_message = None
        mock_response.response_text = {"id": 123, "custom_testrail_bdd_scenario": "Scenario: Test"}
        mock_api_handler.client.send_get.return_value = mock_response

        # Add @C tag to feature
        feature_with_tag = self.sample_feature.copy()
        feature_with_tag["tags"] = [{"name": "@C123"}]

        test_case = parser._parse_feature_as_bdd_case(feature_with_tag, project_id=1, suite_id=2)

        assert test_case is not None
        assert test_case.case_id == 123
        assert test_case.result.case_id == 123
        assert len(test_case.result.custom_testrail_bdd_scenario_results) == 2  # Two scenarios
        assert test_case.result.status_id == 5  # Failed (one scenario failed)

    @pytest.mark.cucumber_bdd_matching
    @patch("trcli.readers.cucumber_json.CucumberParser._find_case_by_title")
    def test_parse_feature_as_bdd_case_by_title(self, mock_find):
        """Test parsing feature as BDD case using title matching"""
        parser = CucumberParser(self.environment)

        mock_api_handler = MagicMock()
        parser._api_handler = mock_api_handler

        # Mock title matching
        mock_find.return_value = 456

        # Mock validation - mock send_get response
        mock_response = MagicMock()
        mock_response.error_message = None
        mock_response.response_text = {"id": 456, "custom_testrail_bdd_scenario": "Scenario: Test"}
        mock_api_handler.client.send_get.return_value = mock_response

        test_case = parser._parse_feature_as_bdd_case(self.sample_feature, project_id=1, suite_id=2)

        assert test_case is not None
        assert test_case.case_id == 456
        mock_find.assert_called_once_with("User Login", 1, 2)

    @pytest.mark.cucumber_bdd_matching
    def test_parse_feature_as_bdd_case_scenario_statuses(self):
        """Test BDD scenario results have correct statuses"""
        parser = CucumberParser(self.environment)

        mock_api_handler = MagicMock()
        parser._api_handler = mock_api_handler

        # Mock validation - mock send_get response
        mock_response = MagicMock()
        mock_response.error_message = None
        mock_response.response_text = {"id": 123, "custom_testrail_bdd_scenario": "Scenario: Test"}
        mock_api_handler.client.send_get.return_value = mock_response

        feature_with_tag = self.sample_feature.copy()
        feature_with_tag["tags"] = [{"name": "@C123"}]

        test_case = parser._parse_feature_as_bdd_case(feature_with_tag, project_id=1, suite_id=2)

        scenarios = test_case.result.custom_testrail_bdd_scenario_results

        # First scenario: passed
        assert scenarios[0].content == "Successful login"
        assert scenarios[0].status_id == 1

        # Second scenario: failed
        assert scenarios[1].content == "Failed login"
        assert scenarios[1].status_id == 5

    @pytest.mark.cucumber_bdd_matching
    def test_parse_feature_as_bdd_case_elapsed_time(self):
        """Test elapsed time calculation for BDD case"""
        parser = CucumberParser(self.environment)

        mock_api_handler = MagicMock()
        parser._api_handler = mock_api_handler

        # Mock validation - mock send_get response
        mock_response = MagicMock()
        mock_response.error_message = None
        mock_response.response_text = {"id": 123, "custom_testrail_bdd_scenario": "Scenario: Test"}
        mock_api_handler.client.send_get.return_value = mock_response

        feature_with_tag = self.sample_feature.copy()
        feature_with_tag["tags"] = [{"name": "@C123"}]

        test_case = parser._parse_feature_as_bdd_case(feature_with_tag, project_id=1, suite_id=2)

        # Total duration: (1+2+0.5) + (1+2+0.5) = 7 seconds
        assert test_case.result.elapsed == "7s"

    @pytest.mark.cucumber_bdd_matching
    def test_parse_feature_as_bdd_case_not_found(self):
        """Test parsing returns None when case not found"""
        parser = CucumberParser(self.environment)

        mock_api_handler = MagicMock()
        parser._api_handler = mock_api_handler

        # Mock no case found (no tag, no title match)
        with patch.object(parser, "_find_case_by_title", return_value=None):
            test_case = parser._parse_feature_as_bdd_case(self.sample_feature, project_id=1, suite_id=2)

        assert test_case is None

    @pytest.mark.cucumber_bdd_matching
    def test_parse_feature_as_bdd_case_validation_fails(self):
        """Test parsing returns None when validation fails"""
        parser = CucumberParser(self.environment)

        mock_api_handler = MagicMock()
        parser._api_handler = mock_api_handler

        # Mock validation failure (not BDD template) - mock send_get response
        mock_response = MagicMock()
        mock_response.error_message = None
        mock_response.response_text = {"id": 123, "custom_testrail_bdd_scenario": None}
        mock_api_handler.client.send_get.return_value = mock_response

        feature_with_tag = self.sample_feature.copy()
        feature_with_tag["tags"] = [{"name": "@C123"}]

        test_case = parser._parse_feature_as_bdd_case(feature_with_tag, project_id=1, suite_id=2)

        assert test_case is None

    @pytest.mark.cucumber_bdd_matching
    def test_parse_feature_branching_bdd_mode(self):
        """Test _parse_feature branches correctly to BDD matching mode"""
        parser = CucumberParser(self.environment)

        mock_api_handler = MagicMock()
        parser._api_handler = mock_api_handler

        # Mock validation - mock send_get response
        mock_response = MagicMock()
        mock_response.error_message = None
        mock_response.response_text = {"id": 123, "custom_testrail_bdd_scenario": "Scenario: Test"}
        mock_api_handler.client.send_get.return_value = mock_response

        feature_with_tag = self.sample_feature.copy()
        feature_with_tag["tags"] = [{"name": "@C123"}]

        # Call with BDD matching mode enabled
        sections = parser._parse_feature(feature_with_tag, bdd_matching_mode=True, project_id=1, suite_id=2)

        assert len(sections) == 1
        assert len(sections[0].testcases) == 1  # One BDD case (not 2 separate scenarios)
        assert sections[0].testcases[0].case_id == 123

    @pytest.mark.cucumber_bdd_matching
    def test_parse_feature_branching_standard_mode(self):
        """Test _parse_feature uses standard mode when bdd_matching_mode=False"""
        parser = CucumberParser(self.environment)

        # Call with standard mode
        sections = parser._parse_feature(self.sample_feature, bdd_matching_mode=False, project_id=None, suite_id=None)

        assert len(sections) == 1
        assert len(sections[0].testcases) == 2  # Two separate test cases (one per scenario)
