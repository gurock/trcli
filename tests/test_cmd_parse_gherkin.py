import pytest
import json
from unittest import mock
from unittest.mock import MagicMock, patch, mock_open
from click.testing import CliRunner
from pathlib import Path

from trcli.cli import Environment
from trcli.commands import cmd_parse_gherkin
from trcli.readers.gherkin_parser import GherkinParser


class TestCmdParseGherkin:
    """Test class for parse_gherkin command functionality"""

    def setup_method(self):
        """Set up test environment and runner"""
        self.runner = CliRunner()
        self.test_feature_path = str(Path(__file__).parent / "test_data" / "FEATURE" / "sample_login.feature")

    @pytest.mark.cmd_parse_gherkin
    def test_parse_gherkin_success_stdout(self):
        """Test successful parsing with output to stdout"""
        result = self.runner.invoke(cmd_parse_gherkin.cli, ["--file", self.test_feature_path])

        assert result.exit_code == 0
        # Output contains logging messages + JSON, extract JSON (starts with '{')
        json_start = result.output.find("{")
        assert json_start >= 0, "No JSON found in output"
        json_str = result.output[json_start:]
        output_data = json.loads(json_str)
        assert "suites" in output_data
        assert "summary" in output_data
        assert output_data["summary"]["total_suites"] >= 1

    @pytest.mark.cmd_parse_gherkin
    def test_parse_gherkin_success_with_output_file(self):
        """Test successful parsing with output to file"""
        with self.runner.isolated_filesystem():
            output_file = "parsed_output.json"
            result = self.runner.invoke(
                cmd_parse_gherkin.cli, ["--file", self.test_feature_path, "--output", output_file]
            )

            assert result.exit_code == 0
            assert "parsed results saved to" in result.output.lower()

            # Verify file was created
            with open(output_file, "r") as f:
                output_data = json.load(f)
                assert "suites" in output_data
                assert "summary" in output_data

    @pytest.mark.cmd_parse_gherkin
    def test_parse_gherkin_pretty_print(self):
        """Test parsing with pretty print formatting"""
        result = self.runner.invoke(cmd_parse_gherkin.cli, ["--file", self.test_feature_path, "--pretty"])

        assert result.exit_code == 0
        # Extract JSON from output
        json_start = result.output.find("{")
        json_str = result.output[json_start:]
        output_data = json.loads(json_str)
        assert "suites" in output_data
        # Check that JSON portion contains newlines and indentation (pretty format)
        assert "\n" in json_str
        assert "  " in json_str  # Indentation

    @pytest.mark.cmd_parse_gherkin
    def test_parse_gherkin_custom_suite_name(self):
        """Test parsing with custom suite name"""
        custom_suite_name = "My Custom Suite"
        result = self.runner.invoke(
            cmd_parse_gherkin.cli, ["--file", self.test_feature_path, "--suite-name", custom_suite_name]
        )

        assert result.exit_code == 0
        json_start = result.output.find("{")
        output_data = json.loads(result.output[json_start:])
        assert output_data["suites"][0]["name"] == custom_suite_name

    @pytest.mark.cmd_parse_gherkin
    def test_parse_gherkin_case_matcher_name(self):
        """Test parsing with NAME case matcher"""
        result = self.runner.invoke(cmd_parse_gherkin.cli, ["--file", self.test_feature_path, "--case-matcher", "name"])

        assert result.exit_code == 0
        json_start = result.output.find("{")
        output_data = json.loads(result.output[json_start:])
        assert "suites" in output_data

    @pytest.mark.cmd_parse_gherkin
    def test_parse_gherkin_case_matcher_property(self):
        """Test parsing with PROPERTY case matcher"""
        result = self.runner.invoke(
            cmd_parse_gherkin.cli, ["--file", self.test_feature_path, "--case-matcher", "property"]
        )

        assert result.exit_code == 0
        json_start = result.output.find("{")
        output_data = json.loads(result.output[json_start:])
        assert "suites" in output_data

    @pytest.mark.cmd_parse_gherkin
    def test_parse_gherkin_verbose_logging(self):
        """Test parsing with verbose logging enabled"""
        result = self.runner.invoke(cmd_parse_gherkin.cli, ["--file", self.test_feature_path, "--verbose"])

        assert result.exit_code == 0
        # Extract JSON from output (may have verbose logs before and after)
        json_start = result.output.find("{")
        json_end = result.output.rfind("}") + 1  # Find last closing brace
        json_str = result.output[json_start:json_end]
        output_data = json.loads(json_str)
        assert "suites" in output_data

    @pytest.mark.cmd_parse_gherkin
    def test_parse_gherkin_missing_file(self):
        """Test parsing with non-existent file"""
        result = self.runner.invoke(cmd_parse_gherkin.cli, ["--file", "/nonexistent/file.feature"])

        # Click returns exit code 2 for invalid parameter (file doesn't exist)
        assert result.exit_code in [1, 2]  # Either our error handling or Click's

    @pytest.mark.cmd_parse_gherkin
    def test_parse_gherkin_invalid_feature_file(self):
        """Test parsing with invalid Gherkin syntax"""
        with self.runner.isolated_filesystem():
            # Create invalid feature file
            invalid_file = "invalid.feature"
            with open(invalid_file, "w") as f:
                f.write("This is not valid Gherkin syntax at all!!!")

            result = self.runner.invoke(cmd_parse_gherkin.cli, ["--file", invalid_file])

            assert result.exit_code == 1

    @pytest.mark.cmd_parse_gherkin
    def test_parse_gherkin_required_file_parameter(self):
        """Test that --file parameter is required"""
        result = self.runner.invoke(cmd_parse_gherkin.cli, [])

        assert result.exit_code == 2  # Click returns 2 for missing required params
        assert "Missing option" in result.output or "required" in result.output.lower()

    @pytest.mark.cmd_parse_gherkin
    def test_parse_gherkin_output_structure(self):
        """Test that output has correct structure"""
        result = self.runner.invoke(cmd_parse_gherkin.cli, ["--file", self.test_feature_path])

        assert result.exit_code == 0
        json_start = result.output.find("{")
        output_data = json.loads(result.output[json_start:])

        # Verify top-level structure
        assert "suites" in output_data
        assert "summary" in output_data

        # Verify summary structure
        summary = output_data["summary"]
        assert "total_suites" in summary
        assert "total_sections" in summary
        assert "total_cases" in summary
        assert "source_file" in summary

        # Verify suites structure
        if output_data["suites"]:
            suite = output_data["suites"][0]
            assert "name" in suite
            assert "source" in suite
            assert "testsections" in suite

            if suite["testsections"]:
                section = suite["testsections"][0]
                assert "name" in section
                assert "testcases" in section

    @pytest.mark.cmd_parse_gherkin
    def test_parse_gherkin_empty_file(self):
        """Test parsing with empty feature file"""
        with self.runner.isolated_filesystem():
            empty_file = "empty.feature"
            with open(empty_file, "w") as f:
                f.write("")

            result = self.runner.invoke(cmd_parse_gherkin.cli, ["--file", empty_file])

            # Should fail with parsing error
            assert result.exit_code == 1
