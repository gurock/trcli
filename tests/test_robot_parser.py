import json
from dataclasses import asdict
from pathlib import Path
from typing import Union

import pytest
from deepdiff import DeepDiff
from robot.version import VERSION as ROBOT_VERSION

from tests.helpers.api_client_helpers import TEST_RAIL_URL, create_url
from trcli.api.api_client import APIClient
from trcli.api.api_request_handler import ApiRequestHandler
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
        parsing_result_json = self.__simplify_parent_section(parsing_result_json)
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

    def __simplify_parent_section(self, result_json: dict) -> dict:
        """Collapse each section's `parent_section` field down to just the parent's bare `name`
        (or `None` for root sections).

        `dataclasses.asdict()` (unlike serde's `to_dict()`) does not honor the `serde_skip`
        metadata used elsewhere in this codebase to keep `parent_section` in-memory-only - it
        recurses into it like any other dataclass-valued field, fully re-embedding the parent
        section's own dict (which itself embeds its own parent, etc.) inside every child. Doing
        this replacement keeps fixtures compact/human-readable while still faithfully verifying
        the produced hierarchy (which section is nested under which, by name).
        """
        for section in result_json.get("testsections", []):
            parent = section.get("parent_section")
            section["parent_section"] = parent["name"] if parent else None
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
        parsing_result_json = self.__simplify_parent_section(parsing_result_json)

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
        parsing_result_json = self.__simplify_parent_section(parsing_result_json)
        file_json = open(expected_path)
        expected_json = json.load(file_json)
        assert (
            DeepDiff(parsing_result_json, expected_json) == {}
        ), f"Result of parsing XML is different than expected \n{DeepDiff(parsing_result_json, expected_json)}"

    @pytest.mark.parse_robot
    def test_robot_xml_parser_creates_nested_sections_end_to_end(self, requests_mock):
        """End-to-end test for Section Hierarchy: parses a real multi-level Robot Framework
        suite tree (Comprehensive Suite -> Api Tests -> Authentication -> Login/Logout, etc,
        10 sections total across 4 nesting levels) and feeds it straight into
        `ApiRequestHandler.add_sections`, mocking only the HTTP layer (`add_section` POSTs).

        This verifies the full pipeline end-to-end, not just each layer in isolation:
        - Multi-level suite structures produce a correspondingly nested section tree.
        - Sections are POSTed in strict parent-before-child order, and each child's request
          body carries the real, freshly-created `parent_id` of its actual parent (verified
          live, in creation order, via the mocked POST callback below - not after the fact).
        - Section names are clean (no dotted `SuiteA.SuiteB.SuiteC` concatenation).
        """
        env = Environment()
        env.case_matcher = MatchersParser.AUTO
        env.file = Path(__file__).parent / "test_data/XML/robotframework_comprehensive_RF50.xml"
        file_reader = RobotParser(env)
        suites_data = file_reader.parse_file()[0]

        # Ground truth, read directly from the freshly-parsed, real object-linked hierarchy
        # (not from any JSON fixture) - name -> parent's name (or None for roots).
        expected_parent_by_name = {
            section.name: (section.parent_section.name if section.parent_section else None)
            for section in suites_data.testsections
        }
        assert len(expected_parent_by_name) == 10, "Comprehensive suite should yield 10 sections"
        assert any(
            parent is not None for parent in expected_parent_by_name.values()
        ), "Fixture should contain at least one nested (non-root) section"
        # No section name should contain the old dotted "Suite.SubSuite" concatenation.
        assert all(
            "." not in name for name in expected_parent_by_name
        ), "Section names must be clean suite names, not dotted concatenations"

        project_id = 42
        created_ids_by_name = {}
        id_counter = iter(range(1000, 1000 + len(expected_parent_by_name)))

        def fake_add_section(request, context):
            body = request.json()
            name = body["name"]
            parent_id = body.get("parent_id")
            expected_parent_name = expected_parent_by_name[name]
            if expected_parent_name is None:
                assert parent_id is None, f"Root section {name!r} should not have a parent_id"
            else:
                # The parent must already have been created (topological order) and this
                # child's parent_id must be exactly that real, freshly-created id.
                assert (
                    expected_parent_name in created_ids_by_name
                ), f"Section {name!r} was POSTed before its parent {expected_parent_name!r}"
                assert parent_id == created_ids_by_name[expected_parent_name], (
                    f"Section {name!r} sent parent_id={parent_id}, expected "
                    f"{created_ids_by_name[expected_parent_name]} (id of {expected_parent_name!r})"
                )
            new_id = next(id_counter)
            created_ids_by_name[name] = new_id
            context.status_code = 200
            return {"id": new_id, "suite_id": 1, "name": name, "parent_id": parent_id}

        requests_mock.post(create_url(f"add_section/{project_id}"), json=fake_add_section)

        api_client = APIClient(host_name=TEST_RAIL_URL)
        api_request_handler = ApiRequestHandler(env, api_client, suites_data, verify=False)
        resources_added, error = api_request_handler.add_sections(project_id)

        assert error == "", f"add_sections reported an unexpected error: {error}"
        assert len(resources_added) == 10
        assert set(created_ids_by_name) == set(
            expected_parent_by_name
        ), "Every section in the parsed tree should have been created exactly once"
        assert all(
            "." not in resource["name"] for resource in resources_added
        ), "Created section names must be clean suite names, not dotted concatenations"

        # The live section objects' own `parent_id` must reflect the real, resolved parent id.
        for section in suites_data.testsections:
            assert section.section_id == created_ids_by_name[section.name]
            if section.parent_section is not None:
                assert section.parent_id == created_ids_by_name[section.parent_section.name]

    @pytest.mark.parse_robot
    def test_robot_xml_parser_file_not_found(self):
        with pytest.raises(FileNotFoundError):
            env = Environment()
            env.file = Path(__file__).parent / "not_found.xml"
            RobotParser(env)

    @pytest.mark.parse_robot
    def test_robot_xml_parser_priority_tag_mapping_defaults(self):
        """Priority Tag Mapping: with no --priority-tag-mapping override, 'priority:<level>'
        tags resolve to the built-in default priority_id mapping (critical=4, high=3,
        medium=2, low=1), matched case-insensitively on both the 'priority:' prefix and the
        level value. Unrecognized tag values and tests without a priority tag at all must not
        get a priority_id. When both an explicit `- testrail_case_field: priority_id:X` doc
        directive and a priority tag are present, the explicit directive always wins. When a
        test has multiple priority tags, only the first one is used.
        """
        env = Environment()
        env.case_matcher = MatchersParser.AUTO
        env.file = Path(__file__).parent / "test_data/XML/robotframework_priority_tags_RF50.xml"
        file_reader = RobotParser(env)
        suite = file_reader.parse_file()[0]

        case_fields_by_title = {
            case.title: case.case_fields for section in suite.testsections for case in section.testcases
        }

        assert case_fields_by_title["Priority Critical Tag"] == {"priority_id": 4}
        assert case_fields_by_title["Priority High Tag Mixed Case"] == {"priority_id": 3}
        assert case_fields_by_title["Priority Medium Tag"] == {"priority_id": 2}
        assert case_fields_by_title["Priority Low Tag"] == {"priority_id": 1}
        # Unrecognized level value ("urgent") is not in the mapping -> no priority_id set.
        assert case_fields_by_title["Priority Unrecognized Tag"] == {}
        # No priority tag at all -> no priority_id set.
        assert case_fields_by_title["No Priority Tag"] == {}
        # Explicit doc directive wins over the tag-derived value (and keeps the historic
        # string-typed case_fields value, unaffected by this feature).
        assert case_fields_by_title["Explicit Case Field Overrides Priority Tag"] == {"priority_id": "1"}
        # Multiple priority tags on the same test -> only the first is honored.
        assert case_fields_by_title["Multiple Priority Tags First One Wins"] == {"priority_id": 4}

    @pytest.mark.parse_robot
    def test_robot_xml_parser_priority_tag_mapping_custom_override(self):
        """A custom --priority-tag-mapping value only overrides the level(s) specified,
        and can also add brand-new levels (e.g. 'urgent') that aren't in the built-in
        defaults - while an explicit doc directive still always wins over any tag."""
        env = Environment()
        env.case_matcher = MatchersParser.AUTO
        env.file = Path(__file__).parent / "test_data/XML/robotframework_priority_tags_RF50.xml"
        env.priority_tag_mapping = ["critical:99", "urgent:50"]
        file_reader = RobotParser(env)
        suite = file_reader.parse_file()[0]

        case_fields_by_title = {
            case.title: case.case_fields for section in suite.testsections for case in section.testcases
        }

        assert case_fields_by_title["Priority Critical Tag"] == {"priority_id": 99}
        # Unspecified levels keep their default mapping.
        assert case_fields_by_title["Priority High Tag Mixed Case"] == {"priority_id": 3}
        assert case_fields_by_title["Priority Medium Tag"] == {"priority_id": 2}
        assert case_fields_by_title["Priority Low Tag"] == {"priority_id": 1}
        # Newly-added custom level is now recognized.
        assert case_fields_by_title["Priority Unrecognized Tag"] == {"priority_id": 50}
        assert case_fields_by_title["No Priority Tag"] == {}
        # Explicit doc directive still wins over the (now-overridden) tag-derived value.
        assert case_fields_by_title["Explicit Case Field Overrides Priority Tag"] == {"priority_id": "1"}
        assert case_fields_by_title["Multiple Priority Tags First One Wins"] == {"priority_id": 99}

    @pytest.mark.parse_robot
    def test_robot_xml_parser_priority_tag_mapping_defaults_without_cli_option(self):
        """A hand-built Environment() that never went through the --priority-tag-mapping
        CLI option (env.priority_tag_mapping left as None) must still resolve priority tags
        using the built-in defaults - the feature works out of the box."""
        env = Environment()
        env.case_matcher = MatchersParser.AUTO
        env.file = Path(__file__).parent / "test_data/XML/robotframework_priority_tags_RF50.xml"
        assert env.priority_tag_mapping is None
        file_reader = RobotParser(env)
        suite = file_reader.parse_file()[0]

        case_fields_by_title = {
            case.title: case.case_fields for section in suite.testsections for case in section.testcases
        }
        assert case_fields_by_title["Priority Critical Tag"] == {"priority_id": 4}
