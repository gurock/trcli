import json
from dataclasses import asdict
from pathlib import Path
from typing import Union

import pytest
from deepdiff import DeepDiff

from trcli.cli import Environment
from trcli.data_classes.data_parsers import MatchersParser
from trcli.data_classes.dataclass_testrail import TestRailSuite
from trcli.readers.robot_xml import RobotParser


class TestRobotParser:

    @pytest.mark.parse_robot
    @pytest.mark.parametrize(
        "matcher, input_xml_path, expected_path",
        [
            # RF 5.0 format
            (
                MatchersParser.AUTO,
                Path(__file__).parent / "test_data/XML/robotframework_simple_RF50.xml",
                Path(__file__).parent / "test_data/json/robotframework_simple_RF50.json",
            ),
            (
                MatchersParser.NAME,
                Path(__file__).parent / "test_data/XML/robotframework_id_in_name_RF50.xml",
                Path(__file__).parent / "test_data/json/robotframework_id_in_name_RF50.json",
            ),
            # RF 7.0 format
            (
                MatchersParser.AUTO,
                Path(__file__).parent / "test_data/XML/robotframework_simple_RF70.xml",
                Path(__file__).parent / "test_data/json/robotframework_simple_RF70.json",
            ),
            (
                MatchersParser.NAME,
                Path(__file__).parent / "test_data/XML/robotframework_id_in_name_RF70.xml",
                Path(__file__).parent / "test_data/json/robotframework_id_in_name_RF70.json",
            ),
        ],
        ids=["Case Matcher Auto", "Case Matcher Name", "Case Matcher Auto", "Case Matcher Name"],
    )
    @pytest.mark.parse_robot
    def test_robot_xml_parser_id_matcher_name(
        self, matcher: str, input_xml_path: Union[str, Path], expected_path: str, freezer
    ):
        freezer.move_to("2020-05-20 01:00:00")
        env = Environment()
        env.case_matcher = matcher
        env.file = input_xml_path
        file_reader = RobotParser(env)
        read_junit = self.__clear_unparsable_junit_elements(file_reader.parse_file()[0])
        parsing_result_json = asdict(read_junit)
        file_json = open(expected_path)
        expected_json = json.load(file_json)
        assert (
            DeepDiff(parsing_result_json, expected_json) == {}
        ), f"Result of parsing XML is different than expected \n{DeepDiff(parsing_result_json, expected_json)}"

    def __clear_unparsable_junit_elements(self, test_rail_suite: TestRailSuite) -> TestRailSuite:
        """helper method to delete temporary junit_case_refs attribute,
        which asdict() method of dataclass can't handle"""
        for section in test_rail_suite.testsections:
            for case in section.testcases:
                # Remove temporary junit_case_refs attribute if it exists
                if hasattr(case, "_junit_case_refs"):
                    delattr(case, "_junit_case_refs")
        return test_rail_suite

    @pytest.mark.parse_robot
    def test_robot_xml_parser_file_not_found(self):
        with pytest.raises(FileNotFoundError):
            env = Environment()
            env.file = Path(__file__).parent / "not_found.xml"
            RobotParser(env)

    @pytest.mark.parse_robot
    def test_robot_xml_parser_glob_pattern_single_file(self):
        """Test glob pattern that matches single file"""
        env = Environment()
        env.case_matcher = MatchersParser.AUTO
        # Use glob pattern that matches only one file
        env.file = Path(__file__).parent / "test_data/XML/robotframework_simple_RF50.xml"

        # This should work just like a regular file path
        file_reader = RobotParser(env)
        result = file_reader.parse_file()

        assert len(result) == 1
        assert isinstance(result[0], TestRailSuite)
        # Verify it has test sections and cases
        assert len(result[0].testsections) > 0

    @pytest.mark.parse_robot
    def test_robot_xml_parser_glob_pattern_multiple_files(self):
        """Test glob pattern that matches multiple files and merges them"""
        env = Environment()
        env.case_matcher = MatchersParser.AUTO
        # Use glob pattern that matches multiple Robot XML files
        env.file = Path(__file__).parent / "test_data/XML/testglob_robot/*.xml"

        file_reader = RobotParser(env)
        result = file_reader.parse_file()

        # Should return a merged result
        assert len(result) == 1
        assert isinstance(result[0], TestRailSuite)

        # Verify merged file was created
        merged_file = Path.cwd() / "Merged-Robot-report.xml"
        assert merged_file.exists(), "Merged Robot report should be created"

        # Verify the merged result contains test cases from both files
        total_cases = sum(len(section.testcases) for section in result[0].testsections)
        assert total_cases > 0, "Merged result should contain test cases"

        # Clean up merged file
        if merged_file.exists():
            merged_file.unlink()

    @pytest.mark.parse_robot
    def test_robot_xml_parser_glob_pattern_no_matches(self):
        """Test glob pattern that matches no files"""
        with pytest.raises(FileNotFoundError):
            env = Environment()
            env.case_matcher = MatchersParser.AUTO
            # Use glob pattern that matches no files
            env.file = Path(__file__).parent / "test_data/XML/nonexistent_*.xml"
            RobotParser(env)

    @pytest.mark.parse_robot
    def test_robot_check_file_glob_returns_path(self):
        """Test that check_file method returns valid Path for glob pattern"""
        # Test single file match
        single_file_glob = Path(__file__).parent / "test_data/XML/robotframework_simple_RF50.xml"
        result = RobotParser.check_file(single_file_glob)
        assert isinstance(result, Path)
        assert result.exists()

        # Test multiple file match (returns merged file path)
        multi_file_glob = Path(__file__).parent / "test_data/XML/testglob_robot/*.xml"
        result = RobotParser.check_file(multi_file_glob)
        assert isinstance(result, Path)
        assert result.name == "Merged-Robot-report.xml"
        assert result.exists()

        # Clean up
        if result.exists() and result.name == "Merged-Robot-report.xml":
            result.unlink()
