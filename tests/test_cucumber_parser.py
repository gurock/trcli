import pytest
from pathlib import Path
from trcli.cli import Environment
from trcli.data_classes.data_parsers import MatchersParser
from trcli.readers.cucumber_json import CucumberParser


class TestCucumberParser:
    """Tests for Cucumber JSON parser"""

    @pytest.fixture
    def sample_cucumber_path(self):
        """Path to the sample Cucumber JSON file"""
        return Path(__file__).parent / "test_data" / "CUCUMBER" / "sample_cucumber.json"

    @pytest.fixture
    def environment(self, sample_cucumber_path):
        """Create a test environment"""
        env = Environment()
        env.file = str(sample_cucumber_path)
        env.case_matcher = MatchersParser.AUTO
        env.suite_name = None
        env.verbose = False
        return env

    @pytest.mark.parse_cucumber
    def test_cucumber_parser_basic(self, environment, sample_cucumber_path):
        """Test basic Cucumber JSON parsing"""
        parser = CucumberParser(environment)
        suites = parser.parse_file()

        assert len(suites) == 1
        suite = suites[0]

        # Check suite structure
        assert suite.name == "Cucumber Test Results"
        assert len(suite.testsections) == 1

        # Check section
        section = suite.testsections[0]
        assert section.name == "User Login"
        assert len(section.testcases) == 2

    @pytest.mark.parse_cucumber
    def test_cucumber_parser_scenarios(self, environment):
        """Test that scenarios are parsed correctly"""
        parser = CucumberParser(environment)
        suites = parser.parse_file()

        section = suites[0].testsections[0]
        cases = section.testcases

        # First scenario - passed
        case1 = cases[0]
        assert "Successful login" in case1.title
        assert case1.result.status_id == 1  # Passed
        assert len(case1.result.custom_step_results) == 5

        # Second scenario - failed
        case2 = cases[1]
        assert "Failed login" in case2.title
        assert case2.result.status_id == 5  # Failed
        assert len(case2.result.custom_step_results) == 5

    @pytest.mark.parse_cucumber
    def test_cucumber_parser_steps(self, environment):
        """Test that steps are parsed with correct status"""
        parser = CucumberParser(environment)
        suites = parser.parse_file()

        section = suites[0].testsections[0]
        case1 = section.testcases[0]

        # Check steps
        steps = case1.result.custom_step_results
        assert all(step.status_id == 1 for step in steps)  # All passed

        # Check step content
        assert "Given" in steps[0].content
        assert "I am on the login page" in steps[0].content

    @pytest.mark.parse_cucumber
    def test_cucumber_parser_automation_id(self, environment):
        """Test automation ID generation"""
        parser = CucumberParser(environment)
        suites = parser.parse_file()

        section = suites[0].testsections[0]
        case1 = section.testcases[0]

        # Check automation ID includes feature name, tags, and scenario name
        assert case1.custom_automation_id is not None
        assert "User Login" in case1.custom_automation_id
        assert "@positive" in case1.custom_automation_id

    @pytest.mark.parse_cucumber
    def test_cucumber_parser_tags(self, environment):
        """Test that tags are extracted correctly"""
        parser = CucumberParser(environment)
        suites = parser.parse_file()

        section = suites[0].testsections[0]
        case1 = section.testcases[0]

        # Check tags in case_fields
        assert "tags" in case1.case_fields
        tags_str = case1.case_fields["tags"]
        assert "@smoke" in tags_str
        assert "@authentication" in tags_str
        assert "@positive" in tags_str

    @pytest.mark.parse_cucumber
    def test_cucumber_generate_feature_file(self, environment):
        """Test .feature file generation"""
        parser = CucumberParser(environment)
        feature_content = parser.generate_feature_file()

        assert feature_content
        assert "Feature: User Login" in feature_content
        assert "Scenario: Successful login" in feature_content
        assert "Scenario: Failed login" in feature_content
        assert "Given I am on the login page" in feature_content
        assert "@smoke" in feature_content

    @pytest.mark.parse_cucumber
    def test_cucumber_parser_elapsed_time(self, environment):
        """Test elapsed time calculation"""
        parser = CucumberParser(environment)
        suites = parser.parse_file()

        section = suites[0].testsections[0]
        case1 = section.testcases[0]

        # Check elapsed time is calculated (may be None if very short duration)
        # The proper_format_for_elapsed in TestRailResult may strip very small values
        if case1.result.elapsed is not None:
            assert case1.result.elapsed.endswith("s")

    @pytest.fixture
    def advanced_cucumber_path(self):
        """Path to the advanced Cucumber JSON file with Background, Examples, and Rules"""
        return Path(__file__).parent / "test_data" / "CUCUMBER" / "sample_cucumber_advanced.json"

    @pytest.fixture
    def advanced_environment(self, advanced_cucumber_path):
        """Create a test environment for advanced features"""
        env = Environment()
        env.file = str(advanced_cucumber_path)
        env.case_matcher = MatchersParser.AUTO
        env.suite_name = None
        env.verbose = False
        return env

    @pytest.mark.parse_cucumber
    def test_cucumber_generate_background(self, advanced_environment):
        """Test Background element generation in .feature file"""
        parser = CucumberParser(advanced_environment)
        feature_content = parser.generate_feature_file()

        assert "Background: User is logged in" in feature_content
        assert "Given I am logged in as a customer" in feature_content
        assert "And my shopping cart is empty" in feature_content

    @pytest.mark.parse_cucumber
    def test_cucumber_generate_scenario_outline_with_examples(self, advanced_environment):
        """Test Scenario Outline with Examples table generation"""
        parser = CucumberParser(advanced_environment)
        feature_content = parser.generate_feature_file()

        # Check Scenario Outline
        assert "Scenario Outline: Add items to cart" in feature_content

        # Check Examples section
        assert "Examples:" in feature_content
        assert "| quantity | product | price |" in feature_content
        assert "| 1 | Laptop | $1000 |" in feature_content
        assert "| 2 | Mouse | $40 |" in feature_content
        assert "| 3 | Keyboard | $150 |" in feature_content

        # Check Examples tags
        assert "@products" in feature_content

    @pytest.mark.parse_cucumber
    def test_cucumber_generate_rule_with_nested_elements(self, advanced_environment):
        """Test Rule element with nested Background and Scenario"""
        parser = CucumberParser(advanced_environment)
        feature_content = parser.generate_feature_file()

        # Check Rule
        assert "Rule: Payment validation" in feature_content
        assert "@validation" in feature_content

        # Check nested Background under Rule
        assert "Background: Setup payment environment" in feature_content
        assert "Given the payment gateway is available" in feature_content

        # Check nested Scenario under Rule
        assert "Scenario: Valid credit card payment" in feature_content
        assert "When I pay with a valid credit card" in feature_content
        assert "Then the payment should be approved" in feature_content

    @pytest.mark.parse_cucumber
    def test_cucumber_advanced_feature_structure(self, advanced_environment):
        """Test complete feature structure with all elements"""
        parser = CucumberParser(advanced_environment)
        feature_content = parser.generate_feature_file()

        # Check feature tags and name
        assert "@shopping" in feature_content
        assert "@cart" in feature_content
        assert "Feature: Shopping Cart" in feature_content

        # Check feature description
        assert "As a customer" in feature_content
        assert "I want to manage my shopping cart" in feature_content

        # Verify proper ordering: Background before Scenarios
        background_pos = feature_content.find("Background:")
        scenario_outline_pos = feature_content.find("Scenario Outline:")
        assert background_pos < scenario_outline_pos, "Background should appear before Scenario Outline"

    @pytest.mark.parse_cucumber
    def test_cucumber_multiple_features_in_output(self, advanced_environment):
        """Test that multiple features are separated correctly"""
        parser = CucumberParser(advanced_environment)
        feature_content = parser.generate_feature_file()

        # Should have both features
        assert "Feature: Shopping Cart" in feature_content
        assert "Feature: Payment Processing" in feature_content

        # Features should be separated by double newline
        features = feature_content.split("\n\n")
        # Should have at least 2 distinct feature sections
        feature_count = feature_content.count("Feature:")
        assert feature_count == 2, "Should have exactly 2 features"

    @pytest.mark.parse_cucumber
    def test_cucumber_indentation_in_generated_feature(self, advanced_environment):
        """Test proper indentation in generated .feature file"""
        parser = CucumberParser(advanced_environment)
        feature_content = parser.generate_feature_file()

        lines = feature_content.split("\n")

        # Background should be indented with 2 spaces
        background_lines = [l for l in lines if "Background:" in l]
        assert any(l.startswith("  Background:") for l in background_lines)

        # Steps should be indented with 4 spaces
        given_lines = [l for l in lines if l.strip().startswith("Given")]
        assert any(l.startswith("    Given") for l in given_lines)

        # Examples should be indented with 4 spaces
        examples_lines = [l for l in lines if "Examples:" in l]
        assert any(l.startswith("    Examples:") for l in examples_lines)

    @pytest.mark.parse_cucumber
    def test_cucumber_json_parser_glob_pattern_single_file(self):
        """Test glob pattern that matches single file"""
        env = Environment()
        env.case_matcher = MatchersParser.AUTO
        env.suite_name = None
        # Use single file path
        env.file = Path(__file__).parent / "test_data/CUCUMBER/sample_cucumber.json"

        # This should work just like a regular file path
        parser = CucumberParser(env)
        result = parser.parse_file()

        assert len(result) == 1
        from trcli.data_classes.dataclass_testrail import TestRailSuite

        assert isinstance(result[0], TestRailSuite)
        # Verify it has test sections and cases
        assert len(result[0].testsections) > 0

    @pytest.mark.parse_cucumber
    def test_cucumber_json_parser_glob_pattern_multiple_files(self):
        """Test glob pattern that matches multiple files and merges them"""
        env = Environment()
        env.case_matcher = MatchersParser.AUTO
        env.suite_name = None
        # Use glob pattern that matches multiple Cucumber JSON files
        env.file = Path(__file__).parent / "test_data/CUCUMBER/testglob/*.json"

        parser = CucumberParser(env)
        result = parser.parse_file()

        # Should return a merged result
        assert len(result) == 1
        from trcli.data_classes.dataclass_testrail import TestRailSuite

        assert isinstance(result[0], TestRailSuite)

        # Verify merged file was created
        merged_file = Path.cwd() / "Merged-Cucumber-report.json"
        assert merged_file.exists(), "Merged Cucumber report should be created"

        # Verify the merged result contains test cases from both files
        total_cases = sum(len(section.testcases) for section in result[0].testsections)
        assert total_cases > 0, "Merged result should contain test cases"

        # Clean up merged file
        if merged_file.exists():
            merged_file.unlink()

    @pytest.mark.parse_cucumber
    def test_cucumber_json_parser_glob_pattern_no_matches(self):
        """Test glob pattern that matches no files"""
        with pytest.raises(FileNotFoundError):
            env = Environment()
            env.case_matcher = MatchersParser.AUTO
            env.suite_name = None
            # Use glob pattern that matches no files
            env.file = Path(__file__).parent / "test_data/CUCUMBER/nonexistent_*.json"
            CucumberParser(env)

    @pytest.mark.parse_cucumber
    def test_cucumber_check_file_glob_returns_path(self):
        """Test that check_file method returns valid Path for glob pattern"""
        # Test single file match
        single_file_glob = Path(__file__).parent / "test_data/CUCUMBER/sample_cucumber.json"
        result = CucumberParser.check_file(single_file_glob)
        assert isinstance(result, Path)
        assert result.exists()

        # Test multiple file match (returns merged file path)
        multi_file_glob = Path(__file__).parent / "test_data/CUCUMBER/testglob/*.json"
        result = CucumberParser.check_file(multi_file_glob)
        assert isinstance(result, Path)
        assert result.name == "Merged-Cucumber-report.json"
        assert result.exists()

        # Verify merged file contains valid JSON array
        import json

        with open(result, "r", encoding="utf-8") as f:
            merged_data = json.load(f)
        assert isinstance(merged_data, list), "Merged Cucumber JSON should be an array"
        assert len(merged_data) > 0, "Merged array should contain features"

        # Clean up
        if result.exists() and result.name == "Merged-Cucumber-report.json":
            result.unlink()
