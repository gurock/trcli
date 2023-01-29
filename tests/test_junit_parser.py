import pytest
import json
from pathlib import Path
from xml.etree.ElementTree import ParseError

from deepdiff import DeepDiff
from junitparser import JUnitXmlError
from trcli.readers.junit_saucectl_xml import JunitSaucectlParser

from trcli.cli import Environment
from trcli.data_classes.matchers import Matchers
from trcli.readers.junit_xml import JunitParser
from typing import Union
from dataclasses import asdict
from trcli.data_classes.dataclass_testrail import TestRailSuite
from trcli.data_classes.validation_exception import ValidationException


class TestJunitParser:
    @pytest.mark.parse_junit
    @pytest.mark.parametrize(
        "input_xml_path, expected_path",
        [
            (
                Path(__file__).parent / "test_data/XML/no_root.xml",
                Path(__file__).parent / "test_data/json/no_root.json",
            ),
            (
                Path(__file__).parent / "test_data/XML/root.xml",
                Path(__file__).parent / "test_data/json/root.json",
            ),
            (
                Path(__file__).parent / "test_data/XML/required_only.xml",
                Path(__file__).parent / "test_data/json/required_only.json",
            )
        ],
        ids=[
            "XML without testsuites root",
            "XML with testsuites root",
            "XML with no data",
        ],
    )
    @pytest.mark.parse_junit
    def test_junit_xml_parser_valid_files(
        self, input_xml_path: Union[str, Path], expected_path: str, freezer
    ):
        freezer.move_to("2020-05-20 01:00:00")
        env = Environment()
        env.case_matcher = Matchers.AUTO
        env.file = input_xml_path
        file_reader = JunitParser(env)
        read_junit = self.__clear_unparsable_junit_elements(file_reader.parse_file()[0])
        parsing_result_json = asdict(read_junit)
        file_json = open(expected_path)
        expected_json = json.load(file_json)
        assert DeepDiff(parsing_result_json, expected_json) == {}, \
            f"Result of parsing Junit XML is different than expected \n{DeepDiff(parsing_result_json, expected_json)}"

    @pytest.mark.parse_junit
    def test_junit_xml_parser_sauce(self, freezer):
        def _compare(junit_output, expected_path):
            read_junit = self.__clear_unparsable_junit_elements(junit_output)
            parsing_result_json = asdict(read_junit)
            file_json = open(expected_path)
            expected_json = json.load(file_json)
            assert DeepDiff(parsing_result_json, expected_json) == {}, \
                f"Result of parsing Junit XML is different than expected \n{DeepDiff(parsing_result_json, expected_json)}"
        freezer.move_to("2020-05-20 01:00:00")
        env = Environment()
        env.case_matcher = Matchers.AUTO
        env.file = Path(__file__).parent / "test_data/XML/sauce.xml"
        file_reader = JunitSaucectlParser(env)
        junit_outputs = file_reader.parse_file()
        _compare(junit_outputs[0], Path(__file__).parent / "test_data/json/sauce1.json",)
        _compare(junit_outputs[1], Path(__file__).parent / "test_data/json/sauce2.json", )

    @pytest.mark.parse_junit
    @pytest.mark.parametrize(
        "matcher, input_xml_path, expected_path",
        [
            (
                Matchers.NAME,
                Path(__file__).parent / "test_data/XML/root_id_in_name.xml",
                Path(__file__).parent / "test_data/json/root_id_in_name.json",
            ),
            (
                Matchers.PROPERTY,
                Path(__file__).parent / "test_data/XML/root_id_in_property.xml",
                Path(__file__).parent / "test_data/json/root_id_in_property.json",
            )
        ],
        ids=["Case Matcher Name", "Case Matcher Property"],
    )
    @pytest.mark.parse_junit
    def test_junit_xml_parser_id_matcher_name(
            self, matcher: str, input_xml_path: Union[str, Path], expected_path: str, freezer
    ):
        freezer.move_to("2020-05-20 01:00:00")
        env = Environment()
        env.case_matcher = matcher
        env.file = input_xml_path
        file_reader = JunitParser(env)
        read_junit = self.__clear_unparsable_junit_elements(file_reader.parse_file()[0])
        parsing_result_json = asdict(read_junit)
        file_json = open(expected_path)
        expected_json = json.load(file_json)
        assert DeepDiff(parsing_result_json, expected_json) == {}, \
            f"Result of parsing Junit XML is different than expected \n{DeepDiff(parsing_result_json, expected_json)}"

    @pytest.mark.parse_junit
    def test_junit_xml_parser_invalid_file(self):
        env = Environment()
        env.file = Path(__file__).parent / "test_data/XML/invalid.xml"
        file_reader = JunitParser(env)
        with pytest.raises(JUnitXmlError):
            file_reader.parse_file()

    @pytest.mark.parse_junit
    def test_junit_xml_parser_invalid_empty_file(self):
        env = Environment()
        env.file = Path(__file__).parent / "test_data/XML/invalid_empty.xml"
        file_reader = JunitParser(env)
        with pytest.raises(ParseError):
            file_reader.parse_file()

    @pytest.mark.parse_junit
    def test_junit_xml_parser_file_not_found(self):
        with pytest.raises(FileNotFoundError):
            env = Environment()
            env.file = Path(__file__).parent / "not_found.xml"
            JunitParser(env)

    @pytest.mark.parse_junit
    def test_junit_xml_parser_validation_error(self):
        env = Environment()
        env.file = Path(__file__).parent / "test_data/XML/empty.xml"
        file_reader = JunitParser(env)
        with pytest.raises(ValidationException):
            file_reader.parse_file()

    def __clear_unparsable_junit_elements(
        self, test_rail_suite: TestRailSuite
    ) -> TestRailSuite:
        """helper method to delete junit_result_unparsed field,
        which asdict() method of dataclass can't handle"""
        for section in test_rail_suite.testsections:
            for case in section.testcases:
                case.result.junit_result_unparsed = []
        return test_rail_suite
