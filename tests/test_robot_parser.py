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
            )
        ],
        ids=["Case Matcher Auto", "Case Matcher Name", "Case Matcher Auto", "Case Matcher Name"]
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
        read_junit = file_reader.parse_file()[0]
        parsing_result_json = asdict(read_junit)
        file_json = open(expected_path)
        expected_json = json.load(file_json)
        assert DeepDiff(parsing_result_json, expected_json) == {}, \
            f"Result of parsing XML is different than expected \n{DeepDiff(parsing_result_json, expected_json)}"

    @pytest.mark.parse_robot
    def test_robot_xml_parser_file_not_found(self):
        with pytest.raises(FileNotFoundError):
            env = Environment()
            env.file = Path(__file__).parent / "not_found.xml"
            RobotParser(env)
