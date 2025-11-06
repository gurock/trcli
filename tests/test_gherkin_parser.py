import pytest
from pathlib import Path
from trcli.cli import Environment
from trcli.data_classes.data_parsers import MatchersParser
from trcli.readers.gherkin_parser import GherkinParser


class TestGherkinParser:
    """Tests for Gherkin .feature file parser"""

    @pytest.fixture
    def sample_feature_path(self):
        """Path to the sample login feature file"""
        return Path(__file__).parent / "test_data" / "FEATURE" / "sample_login.feature"

    @pytest.fixture
    def environment(self, sample_feature_path):
        """Create a test environment"""
        env = Environment()
        env.file = str(sample_feature_path)
        env.case_matcher = MatchersParser.AUTO
        env.suite_name = None
        env.verbose = False
        return env

    @pytest.mark.parse_gherkin
    def test_gherkin_parser_sample_file(self, environment, sample_feature_path):
        """Test parsing of sample_login.feature"""
        # Ensure file exists
        assert sample_feature_path.exists(), f"Sample file not found: {sample_feature_path}"

        # Create parser and parse
        parser = GherkinParser(environment)
        suites = parser.parse_file()

        # Verify structure
        assert suites is not None
        assert len(suites) == 1, "Should parse into exactly one suite"

        suite = suites[0]
        assert suite.name == "User Login"
        assert suite.source == "sample_login.feature"

        # Check sections
        assert len(suite.testsections) == 1
        section = suite.testsections[0]
        assert section.name == "User Login"

        # Check background stored as property
        assert section.properties is not None
        assert len(section.properties) > 0
        background_prop = section.properties[0]
        assert background_prop.name == "background"
        assert "the application is running" in background_prop.value

        # Check test cases (should have expanded scenario outline)
        # Expected: 2 regular scenarios + 4 scenario outline examples = 6 total
        assert len(section.testcases) >= 2, "Should have at least 2 test cases"

        # Verify first test case structure
        first_case = section.testcases[0]
        assert first_case.title is not None
        assert first_case.custom_automation_id is not None
        assert first_case.result is not None
        assert len(first_case.result.custom_step_results) > 0

    @pytest.mark.parse_gherkin
    def test_gherkin_parser_scenario_parsing(self, environment, sample_feature_path):
        """Test that scenarios are correctly parsed with steps"""
        parser = GherkinParser(environment)
        suites = parser.parse_file()

        suite = suites[0]
        section = suite.testsections[0]
        test_cases = section.testcases

        # Find the "Successful login" scenario
        successful_login_case = None
        for case in test_cases:
            if "Successful login" in case.title:
                successful_login_case = case
                break

        assert successful_login_case is not None, "Should find 'Successful login' test case"

        # Verify steps
        steps = successful_login_case.result.custom_step_results
        assert len(steps) == 6, "Successful login scenario should have 6 steps"

        # Check first step
        first_step = steps[0]
        assert "Given" in first_step.content
        assert "valid username" in first_step.content

    @pytest.mark.parse_gherkin
    def test_gherkin_parser_tags_in_automation_id(self, environment, sample_feature_path):
        """Test that tags are included in automation ID"""
        parser = GherkinParser(environment)
        suites = parser.parse_file()

        suite = suites[0]
        section = suite.testsections[0]
        test_cases = section.testcases

        # Find a case with tags
        tagged_case = None
        for case in test_cases:
            if "@smoke" in case.custom_automation_id or "@authentication" in case.custom_automation_id:
                tagged_case = case
                break

        assert tagged_case is not None, "Should find a test case with tags in automation_id"
        assert "@" in tagged_case.custom_automation_id, "Automation ID should contain tags"

    @pytest.mark.parse_gherkin
    def test_gherkin_parser_scenario_outline_expansion(self, environment, sample_feature_path):
        """Test that Scenario Outlines are expanded into multiple test cases"""
        parser = GherkinParser(environment)
        suites = parser.parse_file()

        suite = suites[0]
        section = suite.testsections[0]
        test_cases = section.testcases

        # Find scenario outline examples
        outline_examples = [case for case in test_cases if "Example" in case.title]

        assert len(outline_examples) >= 4, "Should have at least 4 example cases from Scenario Outline"

        # Verify example case has parameters
        example_case = outline_examples[0]
        assert "example_params" in example_case.case_fields
        assert example_case.result is not None

    @pytest.mark.parse_gherkin
    def test_gherkin_parser_with_custom_suite_name(self, environment, sample_feature_path):
        """Test parser with custom suite name"""
        environment.suite_name = "Custom Suite Name"

        parser = GherkinParser(environment)
        suites = parser.parse_file()

        assert suites[0].name == "Custom Suite Name"

    @pytest.mark.parse_gherkin
    def test_gherkin_parser_case_matcher_name(self, environment, sample_feature_path):
        """Test parser with NAME case matcher"""
        environment.case_matcher = MatchersParser.NAME

        parser = GherkinParser(environment)
        suites = parser.parse_file()

        # Should parse without errors
        assert suites is not None
        assert len(suites) == 1

    @pytest.mark.parse_gherkin
    def test_gherkin_parser_missing_file(self):
        """Test parser with non-existent file"""
        env = Environment()
        env.file = "nonexistent.feature"
        env.case_matcher = MatchersParser.AUTO

        with pytest.raises(FileNotFoundError):
            parser = GherkinParser(env)

    @pytest.mark.parse_gherkin
    def test_gherkin_parser_all_steps_untested(self, environment, sample_feature_path):
        """Test that all steps are marked as untested by default"""
        parser = GherkinParser(environment)
        suites = parser.parse_file()

        suite = suites[0]
        section = suite.testsections[0]

        for test_case in section.testcases:
            assert test_case.result.status_id == 3, "Result status should be 3 (Untested)"
            for step in test_case.result.custom_step_results:
                assert step.status_id == 3, "All steps should be untested (status_id=3)"
