import json
from pathlib import Path
from types import SimpleNamespace

import pytest
from deepdiff import DeepDiff

from trcli.cli import Environment
from trcli.data_classes.data_parsers import MatchersParser
from trcli.data_classes.dataclass_testrail import TestRailSeparatedStep
from trcli.readers.robot_xml import RobotParser

_XML_DIR = Path(__file__).parent / "test_data/XML"
_JSON_DIR = Path(__file__).parent / "test_data/json"


def _kw(kwname="Keyword", args=None, status="PASS", messages=None, type_="KEYWORD", body=None):
    """Lightweight stand-in for a robot.result.model Keyword/Message item, exposing
    only the attributes ``_extract_steps``/``_build_step`` actually read (``type``,
    ``kwname``, ``args``, ``status``, ``messages``, ``body``). Using SimpleNamespace
    lets these whitebox tests exercise the recursion/formatting logic in complete
    isolation, without needing a full Robot Framework XML fixture for every edge case."""
    return SimpleNamespace(
        type=type_,
        kwname=kwname,
        args=args or [],
        status=status,
        messages=messages or [],
        body=body or [],
    )


def _msg(message, level="INFO"):
    return SimpleNamespace(message=message, level=level)


def _container(type_, body):
    """Stand-in for a transparent control-flow container (FOR/IF/ELSE/ITERATION/etc.):
    has a ``body`` to recurse into, but no keyword-call ``type``."""
    return SimpleNamespace(type=type_, body=body)


@pytest.fixture
def parser() -> RobotParser:
    """A real RobotParser instance (needs a real, existing file for FileParser.check_file,
    but the file's contents are irrelevant to the whitebox tests below, which call
    ``_extract_steps``/``_build_step`` directly against synthetic SimpleNamespace items)."""
    env = Environment()
    env.case_matcher = MatchersParser.AUTO
    env.file = _XML_DIR / "robotframework_nested_keywords_RF70.xml"
    return RobotParser(env)


class TestExtractStepsWhitebox:
    """Unit tests for ``RobotParser._extract_steps``/``_build_step`` in isolation."""

    def test_single_top_level_keyword_no_args_no_messages(self, parser):
        steps = parser._extract_steps([_kw(kwname="No Operation")])
        assert len(steps) == 1
        assert steps[0].content == "No Operation()"
        assert steps[0].status_id == 1
        assert steps[0].actual is None

    def test_args_joined_with_comma_space(self, parser):
        steps = parser._extract_steps([_kw(kwname="Log", args=["hello", "level=INFO"])])
        assert steps[0].content == "Log(hello, level=INFO)"

    def test_nested_keyword_indented_two_spaces(self, parser):
        inner = _kw(kwname="Inner")
        outer = _kw(kwname="Outer", body=[inner])
        steps = parser._extract_steps([outer])
        assert [s.content for s in steps] == ["Outer()", "  Inner()"]

    def test_triple_nested_keyword_indented_by_level(self, parser):
        innermost = _kw(kwname="Innermost")
        middle = _kw(kwname="Middle", body=[innermost])
        outer = _kw(kwname="Outer", body=[middle])
        steps = parser._extract_steps([outer])
        assert [s.content for s in steps] == ["Outer()", "  Middle()", "    Innermost()"]

    @pytest.mark.parametrize(
        "status, expected_status_id",
        [
            ("PASS", 1),
            ("pass", 1),
            ("FAIL", 5),
            ("Fail", 5),
            ("SKIP", 4),
            ("NOT RUN", 3),
        ],
    )
    def test_status_mapping_is_case_insensitive(self, parser, status, expected_status_id):
        steps = parser._extract_steps([_kw(status=status)])
        assert steps[0].status_id == expected_status_id

    @pytest.mark.parametrize("level", ["INFO", "WARN", "ERROR"])
    def test_logged_message_levels_included_in_actual(self, parser, level):
        steps = parser._extract_steps([_kw(messages=[_msg("hello", level=level)])])
        assert steps[0].actual == f"{level}: hello"

    @pytest.mark.parametrize("level", ["FAIL", "SKIP", "DEBUG", "TRACE"])
    def test_non_logged_message_levels_excluded_from_actual(self, parser, level):
        steps = parser._extract_steps([_kw(messages=[_msg("hello", level=level)])])
        assert steps[0].actual is None

    def test_multiple_messages_joined_by_newline_in_order(self, parser):
        steps = parser._extract_steps([_kw(messages=[_msg("first"), _msg("second", level="WARN")])])
        assert steps[0].actual == "INFO: first\nWARN: second"

    def test_mixed_logged_and_non_logged_messages_are_filtered(self, parser):
        steps = parser._extract_steps(
            [
                _kw(
                    messages=[
                        _msg("keep1", level="INFO"),
                        _msg("drop-fail", level="FAIL"),
                        _msg("keep2", level="ERROR"),
                        _msg("drop-debug", level="DEBUG"),
                    ]
                )
            ]
        )
        assert steps[0].actual == "INFO: keep1\nERROR: keep2"

    def test_no_messages_leaves_actual_none(self, parser):
        steps = parser._extract_steps([_kw(messages=[])])
        assert steps[0].actual is None

    @pytest.mark.parametrize("kw_type", ["SETUP", "TEARDOWN"])
    def test_setup_and_teardown_types_are_keyword_calls(self, parser, kw_type):
        steps = parser._extract_steps([_kw(kwname="MySetup", type_=kw_type)])
        assert len(steps) == 1
        assert steps[0].content == "MySetup()"

    def test_for_container_produces_no_step_of_its_own(self, parser):
        for_container = _container("FOR", body=[_kw(kwname="Inner")])
        steps = parser._extract_steps([for_container])
        assert len(steps) == 1
        assert steps[0].content == "Inner()"

    def test_for_container_does_not_add_a_nesting_level(self, parser):
        for_container = _container("FOR", body=[_kw(kwname="Inner")])
        outer = _kw(kwname="Outer", body=[for_container])
        steps = parser._extract_steps([outer])
        # "Inner" is called *inside* Outer's FOR loop; the loop itself must not add
        # an extra indentation level beyond the one from being nested under Outer.
        assert [s.content for s in steps] == ["Outer()", "  Inner()"]

    def test_if_else_root_and_branches_are_transparent(self, parser):
        if_branch = _container("IF", body=[_kw(kwname="OnTrue")])
        if_root = _container("IF/ELSE ROOT", body=[if_branch])
        steps = parser._extract_steps([if_root])
        assert len(steps) == 1
        assert steps[0].content == "OnTrue()"

    def test_iteration_container_is_transparent(self, parser):
        iteration = _container("ITERATION", body=[_kw(kwname="Inner")])
        for_container = _container("FOR", body=[iteration])
        steps = parser._extract_steps([for_container])
        assert len(steps) == 1
        assert steps[0].content == "Inner()"

    def test_bare_message_item_produces_no_step_and_does_not_raise(self, parser):
        # A genuine Message item has no `body` attribute at all; must be safely
        # skipped (not mistaken for a keyword call, and not recursed into).
        message_item = SimpleNamespace(type="MESSAGE")
        steps = parser._extract_steps([message_item])
        assert steps == []

    def test_empty_container_body_produces_no_steps(self, parser):
        steps = parser._extract_steps([_container("FOR", body=[])])
        assert steps == []

    def test_depth_first_order_preserved_across_sibling_keywords(self, parser):
        kw_a = _kw(kwname="KeywordA", body=[_kw(kwname="ChildA")])
        kw_b = _kw(kwname="KeywordB", body=[_kw(kwname="ChildB")])
        steps = parser._extract_steps([kw_a, kw_b])
        assert [s.content for s in steps] == [
            "KeywordA()",
            "  ChildA()",
            "KeywordB()",
            "  ChildB()",
        ]

    def test_extreme_nesting_depth_is_stack_safe(self, parser):
        # A synthetic chain of 500 nested keyword calls - far beyond any realistic
        # Robot Framework suite - proves the recursive traversal has no artificial
        # depth limit of its own (bounded only by Python's own recursion limit).
        depth = 500
        current = _kw(kwname=f"Level{depth}")
        for level in range(depth - 1, 0, -1):
            current = _kw(kwname=f"Level{level}", body=[current])
        steps = parser._extract_steps([current])
        assert len(steps) == depth
        assert steps[0].content == "Level1()"
        assert steps[-1].content == ("  " * (depth - 1)) + f"Level{depth}()"

    def test_build_step_returns_testrailseparatedstep_instance(self, parser):
        step = parser._build_step(_kw(kwname="Anything"), level=0)
        assert isinstance(step, TestRailSeparatedStep)


class TestExtractStepsIntegrationNestedKeywordsFixture:
    """Blackbox/integration tests: parse the real
    ``robotframework_nested_keywords_RF60.xml``/``RF70.xml`` fixtures (generated by
    genuine ``robot`` runs of ``tests/test_data/robot_source/nested_suite/nested_keywords.robot``,
    RF 6.0.2 and RF 7.4.2 respectively) end-to-end through ``RobotParser.parse_file()``,
    and verify the resulting ``custom_step_results`` for every one of the 8 test cases
    exactly match ground truth captured from a real Robot Framework execution-result
    tree, stored in ``test_data/json/robotframework_nested_keywords_steps.json``.
    RF 6.0.2 and RF 7.4.2 are asserted to produce byte-identical step output."""

    @staticmethod
    def _parse(xml_filename: str):
        env = Environment()
        env.case_matcher = MatchersParser.AUTO
        env.file = _XML_DIR / xml_filename
        reader = RobotParser(env)
        suite = reader.parse_file()[0]
        cases = {}
        for section in suite.testsections:
            for case in section.testcases:
                cases[case.title] = case.result.custom_step_results or []
        return cases

    @staticmethod
    def _as_dicts(steps):
        return [{"content": s.content, "status_id": s.status_id, "actual": s.actual} for s in steps]

    @pytest.fixture(scope="class")
    def expected(self):
        with open(_JSON_DIR / "robotframework_nested_keywords_steps.json") as f:
            return json.load(f)

    @pytest.mark.parse_robot
    @pytest.mark.parametrize(
        "xml_filename",
        ["robotframework_nested_keywords_RF60.xml", "robotframework_nested_keywords_RF70.xml"],
        ids=["RF 6.0", "RF 7.0"],
    )
    @pytest.mark.parametrize(
        "case_title",
        [
            "Deep Recursive Nesting",
            "For Loop With If Else Branches",
            "Argument Type Variety",
            "Keyword With No Args And No Messages",
            "Keyword With Only Messages No Nested Call",
            "Keyword With Special Characters In Arguments",
            "Fifty Plus Keyword Calls",
            "Test With Setup And Teardown Around Nesting",
        ],
    )
    def test_case_steps_match_ground_truth(self, xml_filename, case_title, expected):
        cases = self._parse(xml_filename)
        actual_steps = self._as_dicts(cases[case_title])
        diff = DeepDiff(actual_steps, expected[case_title])
        assert diff == {}, f"Steps for '{case_title}' in {xml_filename} differ from ground truth:\n{diff}"

    @pytest.mark.parse_robot
    @pytest.mark.parametrize(
        "xml_filename",
        ["robotframework_nested_keywords_RF60.xml", "robotframework_nested_keywords_RF70.xml"],
        ids=["RF 6.0", "RF 7.0"],
    )
    def test_deep_recursive_nesting_terminal_step_has_actual_and_rest_not_run(self, xml_filename):
        steps = self._parse(xml_filename)["Deep Recursive Nesting"]
        assert len(steps) == 40
        # The 13th (final, base-case) recursion level: the "Reached the bottom" Log
        # actually executes (unlike every shallower level, where that branch is the
        # one NOT taken) and its INFO message is captured in `actual`...
        assert steps[37].content == "                          Log(Reached the bottom, level=INFO)"
        assert steps[37].status_id == 1
        assert steps[37].actual == "INFO: Reached the bottom"
        # ...while everything past the point of no return (the ELSE branch's log,
        # and the one-recursion-too-far call) is correctly marked NOT RUN.
        assert steps[38].status_id == 3
        assert steps[39].status_id == 3

    @pytest.mark.parse_robot
    @pytest.mark.parametrize(
        "xml_filename",
        ["robotframework_nested_keywords_RF60.xml", "robotframework_nested_keywords_RF70.xml"],
        ids=["RF 6.0", "RF 7.0"],
    )
    def test_for_loop_if_else_branches_alternate_even_odd_per_iteration(self, xml_filename):
        steps = self._parse(xml_filename)["For Loop With If Else Branches"]
        assert len(steps) == 17
        assert steps[0].content == "Iterate And Branch(4)"
        # Iteration 0 (even): "Log Even Branch" executes, "Log Odd Branch" does not.
        assert steps[2].content == "  Log Even Branch(${i})"
        assert steps[2].status_id == 1
        assert steps[4].content == "  Log Odd Branch(${i})"
        assert steps[4].status_id == 3
        # Iteration 1 (odd): the reverse.
        assert steps[6].content == "  Log Even Branch(${i})"
        assert steps[6].status_id == 3
        assert steps[7].content == "  Log Odd Branch(${i})"
        assert steps[7].status_id == 1

    @pytest.mark.parse_robot
    @pytest.mark.parametrize(
        "xml_filename",
        ["robotframework_nested_keywords_RF60.xml", "robotframework_nested_keywords_RF70.xml"],
        ids=["RF 6.0", "RF 7.0"],
    )
    def test_argument_type_variety_captures_string_bool_list_and_named_args(self, xml_filename):
        steps = self._parse(xml_filename)["Argument Type Variety"]
        assert len(steps) == 2
        assert steps[0].content == "Accept Many Argument Types(hello, ${TRUE}, a, b, c, key=value)"
        assert steps[0].status_id == 1

    @pytest.mark.parse_robot
    @pytest.mark.parametrize(
        "xml_filename",
        ["robotframework_nested_keywords_RF60.xml", "robotframework_nested_keywords_RF70.xml"],
        ids=["RF 6.0", "RF 7.0"],
    )
    def test_keyword_with_no_args_and_no_messages_has_empty_parens_and_no_actual(self, xml_filename):
        steps = self._parse(xml_filename)["Keyword With No Args And No Messages"]
        assert [s.content for s in steps] == ["No Op Keyword()", "  No Operation()"]
        assert all(s.actual is None for s in steps)

    @pytest.mark.parse_robot
    @pytest.mark.parametrize(
        "xml_filename",
        ["robotframework_nested_keywords_RF60.xml", "robotframework_nested_keywords_RF70.xml"],
        ids=["RF 6.0", "RF 7.0"],
    )
    def test_keyword_with_only_messages_no_nested_call(self, xml_filename):
        steps = self._parse(xml_filename)["Keyword With Only Messages No Nested Call"]
        assert len(steps) == 2
        assert steps[1].content == "  Log(Only a log line, no nested keyword call, level=INFO)"
        assert steps[1].actual == "INFO: Only a log line, no nested keyword call"

    @pytest.mark.parse_robot
    @pytest.mark.parametrize(
        "xml_filename",
        ["robotframework_nested_keywords_RF60.xml", "robotframework_nested_keywords_RF70.xml"],
        ids=["RF 6.0", "RF 7.0"],
    )
    def test_special_characters_in_arguments_are_preserved_verbatim(self, xml_filename):
        steps = self._parse(xml_filename)["Keyword With Special Characters In Arguments"]
        assert len(steps) == 2
        assert steps[0].content == ('Special Characters Keyword(Line with "quotes", a comma, and Ünïcödé ☺ <tag>)')
        assert steps[1].actual == ('INFO: Special: Line with "quotes", a comma, and Ünïcödé ☺ <tag>')

    @pytest.mark.parse_robot
    @pytest.mark.parametrize(
        "xml_filename",
        ["robotframework_nested_keywords_RF60.xml", "robotframework_nested_keywords_RF70.xml"],
        ids=["RF 6.0", "RF 7.0"],
    )
    def test_fifty_plus_keyword_calls_extracts_every_call(self, xml_filename):
        steps = self._parse(xml_filename)["Fifty Plus Keyword Calls"]
        assert len(steps) == 56
        assert steps[0].content == "Call Many Keywords(55)"
        assert all(s.content == "  No Operation()" for s in steps[1:])
        assert all(s.status_id == 1 for s in steps)

    @pytest.mark.parse_robot
    @pytest.mark.parametrize(
        "xml_filename",
        ["robotframework_nested_keywords_RF60.xml", "robotframework_nested_keywords_RF70.xml"],
        ids=["RF 6.0", "RF 7.0"],
    )
    def test_setup_and_teardown_are_both_extracted_at_top_level_around_body(self, xml_filename):
        steps = self._parse(xml_filename)["Test With Setup And Teardown Around Nesting"]
        assert len(steps) == 21
        # [Setup] keyword call starts the list, unindented, like a normal top-level call.
        assert steps[0].content == "Recurse To Depth(${2})"
        # The test body's own Log call is sandwiched between setup (indices 0-9) and
        # teardown (indices 11-20), also unindented (it is a top-level body item).
        assert steps[10].content == "Log(Body executes, level=INFO)"
        assert steps[10].actual == "INFO: Body executes"
        # [Teardown] keyword call repeats the same recursive structure as [Setup].
        assert steps[11].content == "Recurse To Depth(${2})"
        assert [s.content for s in steps[11:]] == [s.content for s in steps[0:10]]

    @pytest.mark.parse_robot
    def test_rf60_and_rf70_produce_byte_identical_step_output(self):
        rf60_cases = self._parse("robotframework_nested_keywords_RF60.xml")
        rf70_cases = self._parse("robotframework_nested_keywords_RF70.xml")
        assert rf60_cases.keys() == rf70_cases.keys()
        for title in rf60_cases:
            diff = DeepDiff(self._as_dicts(rf60_cases[title]), self._as_dicts(rf70_cases[title]))
            assert diff == {}, f"RF 6.0 vs RF 7.0 step mismatch for '{title}':\n{diff}"
