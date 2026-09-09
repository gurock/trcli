import json
from dataclasses import asdict
from pathlib import Path
from typing import Union

import pytest
from deepdiff import DeepDiff
from robot.version import VERSION as ROBOT_VERSION

from trcli.cli import Environment
from trcli.data_classes.data_parsers import MatchersParser
from trcli.data_classes.dataclass_testrail import TestRailSuite
from trcli.readers.robot_xml import RobotParser

# Robot Framework result-XML schemaversion 5 (elapsed="X" attribute on <status>,
# used by our "RF70"-suffixed fixtures) was only introduced in RF 7.0. RF 6.0.x's
# ExecutionResult XML reader predates that schema and cannot read the elapsed="X"
# attribute at all, so elapsed time is silently read back as 0 -> None. This is an
# inherent limitation of the installed robot library itself, not a trcli bug, and it
# can only be observed in this artificial scenario (RF7.0-schema XML fed to an RF
# 6.0.x reader) that never happens with genuine RF 6.0.x output (which never emits
# schema 5). See tox.ini's `robotframework-60` env, which pins robotframework==6.0.*
# specifically to exercise this cross-version boundary.
_ROBOT_MAJOR_VERSION = int(ROBOT_VERSION.split(".")[0])
_RF70_SCHEMA_XFAIL = pytest.mark.xfail(
    _ROBOT_MAJOR_VERSION < 7,
    reason=(
        'Installed robotframework<7.0 cannot read the elapsed="X" attribute '
        "introduced in result-XML schemaversion 5 (RF 7.0+); elapsed time is read "
        "back as 0/None instead of the expected value. Inherent robot library "
        "limitation, not reproducible with genuine RF<7.0 output."
    ),
    strict=True,
)


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
            pytest.param(
                MatchersParser.AUTO,
                Path(__file__).parent / "test_data/XML/robotframework_simple_RF70.xml",
                Path(__file__).parent / "test_data/json/robotframework_simple_RF70.json",
                marks=_RF70_SCHEMA_XFAIL,
            ),
            pytest.param(
                MatchersParser.NAME,
                Path(__file__).parent / "test_data/XML/robotframework_id_in_name_RF70.xml",
                Path(__file__).parent / "test_data/json/robotframework_id_in_name_RF70.json",
                marks=_RF70_SCHEMA_XFAIL,
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
        parsing_result_json = self.__remove_none_quality_ratings(parsing_result_json)
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

    def __remove_none_quality_ratings(self, result_json: dict) -> dict:
        """Remove quality_rating fields that are None for backward compatibility with existing tests"""
        for section in result_json.get("testsections", []):
            for testcase in section.get("testcases", []):
                if testcase.get("result", {}).get("quality_rating") is None:
                    testcase["result"].pop("quality_rating", None)
        return result_json

    @pytest.mark.parse_robot
    @pytest.mark.parametrize(
        "input_xml_path, expected_path",
        [
            # RF 5.0 format with quality ratings
            (
                Path(__file__).parent / "test_data/XML/robotframework_quality_rating_RF50.xml",
                Path(__file__).parent / "test_data/json/robotframework_quality_rating_RF50.json",
            ),
            # RF 7.0 format with quality ratings
            pytest.param(
                Path(__file__).parent / "test_data/XML/robotframework_quality_rating_RF70.xml",
                Path(__file__).parent / "test_data/json/robotframework_quality_rating_RF70.json",
                marks=_RF70_SCHEMA_XFAIL,
            ),
        ],
        ids=["RF 5.0 Quality Rating", "RF 7.0 Quality Rating"],
    )
    def test_robot_xml_parser_quality_ratings(self, input_xml_path: Union[str, Path], expected_path: str, freezer):
        """Test that Robot Framework parser correctly parses quality ratings from test documentation"""
        freezer.move_to("2020-05-20 01:00:00")
        env = Environment()
        env.case_matcher = MatchersParser.PROPERTY
        env.file = input_xml_path
        file_reader = RobotParser(env)
        read_junit = self.__clear_unparsable_junit_elements(file_reader.parse_file()[0])
        parsing_result_json = asdict(read_junit)

        # Don't remove quality_rating for this test - we want to verify it's present
        file_json = open(expected_path)
        expected_json = json.load(file_json)

        diff = DeepDiff(parsing_result_json, expected_json)
        assert diff == {}, f"Result of parsing Robot XML is different than expected \n{diff}"

    @pytest.mark.parse_robot
    @pytest.mark.parametrize(
        "input_xml_path, expected_path",
        [
            (
                Path(__file__).parent / "test_data/XML/robotframework_comprehensive_RF50.xml",
                Path(__file__).parent / "test_data/json/robotframework_comprehensive_RF50.json",
            ),
            pytest.param(
                Path(__file__).parent / "test_data/XML/robotframework_comprehensive_RF70.xml",
                Path(__file__).parent / "test_data/json/robotframework_comprehensive_RF70.json",
                marks=_RF70_SCHEMA_XFAIL,
            ),
        ],
        ids=["RF 5.0 Comprehensive", "RF 7.0 Comprehensive"],
    )
    def test_robot_xml_parser_comprehensive_regression_baseline(
        self, input_xml_path: Union[str, Path], expected_path: str, freezer
    ):
        """Regression-baseline test for the current (pre-ExecutionResult-refactor) parser.

        Fixtures are genuinely generated by real `robot` runs (RF 5.0.1 and RF 7.4.2) against
        tests/test_data/robot_source/comprehensive_suite, covering: nested keywords (4 levels deep),
        multiple keyword argument styles, all Log levels, tags, and diverse failure scenarios
        (direct failure, nested-keyword failure, test setup/teardown failure, suite setup failure,
        skip). This locks in the CURRENT parser's behavior (flat top-level-only keyword capture, no
        tag/arg extraction) so that the upcoming ExecutionResult-based refactor can be verified to
        not silently change this baseline before new capabilities are layered on.
        """
        freezer.move_to("2020-05-20 01:00:00")
        env = Environment()
        env.case_matcher = MatchersParser.AUTO
        env.file = input_xml_path
        file_reader = RobotParser(env)
        read_junit = self.__clear_unparsable_junit_elements(file_reader.parse_file()[0])
        parsing_result_json = asdict(read_junit)
        parsing_result_json = self.__remove_none_quality_ratings(parsing_result_json)
        file_json = open(expected_path)
        expected_json = json.load(file_json)
        assert (
            DeepDiff(parsing_result_json, expected_json) == {}
        ), f"Result of parsing XML is different than expected \n{DeepDiff(parsing_result_json, expected_json)}"

    @pytest.mark.parse_robot
    @pytest.mark.parametrize(
        "input_xml_path, expected_path",
        [
            (
                Path(__file__).parent / "test_data/XML/robotframework_references_login_flow_RF60.xml",
                Path(__file__).parent / "test_data/json/robotframework_references_login_flow_RF60.json",
            ),
            pytest.param(
                Path(__file__).parent / "test_data/XML/robotframework_references_login_flow_RF70.xml",
                Path(__file__).parent / "test_data/json/robotframework_references_login_flow_RF70.json",
                marks=_RF70_SCHEMA_XFAIL,
            ),
        ],
        ids=["RF 6.0 Realworld Login Flow", "RF 7.0 Realworld Login Flow"],
    )
    def test_robot_xml_parser_realworld_login_flow(self, input_xml_path: Union[str, Path], expected_path: str, freezer):
        """Regression test based on a genuinely-generated, real-world-style page-object suite
        (``tests/test_data/robot_source/realworld_suite/login_dashboard.robot``), modeled after
        an anonymized customer output.xml sample. Exercises several patterns not covered by the
        other, more synthetic fixtures: a suite-level [Setup]/[Teardown] (which the parser
        correctly does NOT surface as part of the test's own custom_step_results, since those
        keywords are never part of any individual test's body/setup/teardown items), a keyword
        that returns a value via RETURN and has that value captured in a `${var} = value` INFO
        message, and a tag using the real-world "refs:<ID>" convention, which the parser
        extracts into the case's ``refs`` field via ``extract_jira_references()``.
        """
        freezer.move_to("2020-05-20 01:00:00")
        env = Environment()
        env.case_matcher = MatchersParser.AUTO
        env.file = input_xml_path
        file_reader = RobotParser(env)
        read_junit = self.__clear_unparsable_junit_elements(file_reader.parse_file()[0])
        parsing_result_json = asdict(read_junit)
        parsing_result_json = self.__remove_none_quality_ratings(parsing_result_json)
        file_json = open(expected_path)
        expected_json = json.load(file_json)
        assert (
            DeepDiff(parsing_result_json, expected_json) == {}
        ), f"Result of parsing XML is different than expected \n{DeepDiff(parsing_result_json, expected_json)}"

    @pytest.mark.parse_robot
    def test_robot_xml_parser_file_not_found(self):
        with pytest.raises(FileNotFoundError):
            env = Environment()
            env.file = Path(__file__).parent / "not_found.xml"
            RobotParser(env)
