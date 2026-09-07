from beartype.typing import List, Union
from pathlib import Path
from xml.etree import ElementTree
import glob

from robot.api import ExecutionResult

from trcli.backports import removeprefix
from trcli.cli import Environment
from trcli.data_classes.data_parsers import (
    MatchersParser,
    FieldsParser,
    TestRailCaseFieldsOptimizer,
    QualityRatingParser,
)
from trcli.data_classes.dataclass_testrail import (
    TestRailCase,
    TestRailSuite,
    TestRailSection,
    TestRailResult,
    TestRailSeparatedStep,
)
from trcli.readers.file_parser import FileParser

# robot.result item ``type`` values that represent an actual keyword call (as opposed
# to a Message, or a control-flow container like For/If/While/Try/Group/Var/Return/
# Break/Continue). ``test.setup``/``test.teardown`` are Keyword instances too, just
# distinguished by their ``type`` being SETUP/TEARDOWN instead of KEYWORD.
_KEYWORD_LIKE_TYPES = {"KEYWORD", "SETUP", "TEARDOWN"}

# Message levels that get surfaced in a step's "actual" (runtime output) field.
# FAIL/SKIP are intentionally excluded here: those pseudo-messages duplicate
# information already conveyed by the keyword's own status_id/failure handling.
_LOGGED_MESSAGE_LEVELS = {"INFO", "WARN", "ERROR"}


class RobotParser(FileParser):

    def __init__(self, environment: Environment):
        super().__init__(environment)
        self.case_matcher = environment.case_matcher
        self._case_result_statuses = {"pass": 1, "not run": 3, "skip": 4, "fail": 5}
        self._update_with_custom_statuses()
        self.invalid_quality_ratings_found = False  # Track if any quality ratings were invalid

    @staticmethod
    def check_file(filepath: Union[str, Path]) -> Path:
        """Check and process file path, supporting glob patterns.

        If the filepath contains glob patterns (*, ?, []), expand them:
        - Single file match: Return that file path
        - Multiple file matches: Merge the files and return merged file path
        - No matches: Raise FileNotFoundError
        """
        filepath = Path(filepath)

        # Check if this is a glob pattern (contains wildcards)
        filepath_str = str(filepath)
        if any(char in filepath_str for char in ["*", "?", "["]):
            # Expand glob pattern
            files = glob.glob(filepath_str, recursive=True)

            if not files:
                raise FileNotFoundError(f"File not found: {filepath}")
            elif len(files) == 1:
                # Single file match - return it directly
                return Path().cwd().joinpath(files[0])
            else:
                # Multiple files - merge them
                merged_root = ElementTree.Element("robot", generator="Robot 7.0 (merged)")

                for file_path in files:
                    tree = ElementTree.parse(file_path)
                    root = tree.getroot()

                    # Merge all <suite> elements from each file
                    for suite in root.findall("suite"):
                        merged_root.append(suite)

                # Write merged XML to a file
                merged_tree = ElementTree.ElementTree(merged_root)
                merged_file_path = Path.cwd() / "Merged-Robot-report.xml"

                # Use UTF-8 encoding explicitly
                merged_tree.write(merged_file_path, encoding="utf-8", xml_declaration=True)

                return merged_file_path
        else:
            # Not a glob pattern - use parent class behavior
            if not filepath.is_file():
                raise FileNotFoundError(f"File not found: {filepath}")
            return filepath

    def parse_file(self) -> List[TestRailSuite]:
        self.env.log(f"Parsing Robot Framework report.")
        sections_list = []
        # Enumerate top-level <suite> elements the same way as before (this correctly
        # handles both a single genuine RF output.xml - which always has exactly one
        # top-level <suite> - and the synthetic "<robot><suite/><suite/>...</robot>"
        # produced by check_file() when merging multiple glob-matched files).
        root = ElementTree.parse(self.filepath).getroot()
        suite_elements = root.findall("suite")
        if len(suite_elements) == 1:
            # Common case (a genuine, non-merged RF output.xml)
            result_suite = ExecutionResult(self.filepath).suite
            self._find_suites(result_suite, sections_list)
        else:
            # Merged-glob case (multiple sibling top-level <suite> elements)
            for suite_element in suite_elements:
                wrapper = ElementTree.Element("robot", generator="trcli-isolated-suite")
                wrapper.append(suite_element)
                suite_xml = ElementTree.tostring(wrapper, encoding="utf-8")
                result_suite = ExecutionResult(suite_xml).suite
                self._find_suites(result_suite, sections_list)
        cases_count = sum(len(section.testcases) for section in sections_list)
        self.env.log(f"Processed {cases_count} test cases in {len(sections_list)} sections.")
        testrail_suites = [
            TestRailSuite(
                self.env.suite_name if self.env.suite_name else self.filepath.stem,
                testsections=sections_list,
                source=self.filename,
            )
        ]

        return testrail_suites

    def _find_suites(self, suite, sections_list: List, namespace=""):
        name = suite.name
        namespace += f".{name}" if namespace else name
        tests = suite.tests
        if tests:
            # Check if section with this namespace already exists (for merged files with duplicate suites)
            section = next((s for s in sections_list if s.name == namespace), None)
            if section is None:
                # Create new section if it doesn't exist
                section = TestRailSection(namespace)
                sections_list.append(section)
            # else: reuse existing section and add tests to it

            for test in tests:
                case_id = None
                case_name = test.name
                attachments = []
                result_fields = []
                case_fields = []
                comments = []
                quality_rating = None
                documentation = test.doc
                if self.case_matcher == MatchersParser.NAME:
                    case_id, case_name = MatchersParser.parse_name_with_id(case_name)
                if documentation:
                    lines = [line.strip() for line in documentation.splitlines()]
                    for line in lines:
                        if (
                            line.lower().startswith("- testrail_case_id:")
                            and self.case_matcher == MatchersParser.PROPERTY
                        ):
                            case_id = int(self._remove_tr_prefix(line, "- testrail_case_id:").lower().replace("c", ""))
                        if line.lower().startswith("- quality_rating:"):
                            quality_rating_str = self._remove_tr_prefix(line, "- quality_rating:")
                            parsed_rating, error = QualityRatingParser.parse_quality_rating(quality_rating_str)
                            if error:
                                self.env.elog(f"Quality rating validation failed for test '{case_name}': {error}")
                                # Mark that we found invalid quality ratings
                                self.invalid_quality_ratings_found = True
                            else:
                                quality_rating = parsed_rating
                        if line.lower().startswith("- testrail_attachment:"):
                            attachments.append(self._remove_tr_prefix(line, "- testrail_attachment:"))
                        if line.lower().startswith("- testrail_result_field"):
                            result_fields.append(self._remove_tr_prefix(line, "- testrail_result_field:"))
                        if line.lower().startswith("- testrail_result_comment"):
                            comments.append(self._remove_tr_prefix(line, "- testrail_result_comment:"))
                        if line.lower().startswith("- testrail_case_field"):
                            case_fields.append(self._remove_tr_prefix(line, "- testrail_case_field:"))

                status_id = self._case_result_statuses[test.status.lower()]
                # Prefer elapsed_time (timedelta, microsecond precision) when available;
                # it was only added to the result model in RF 7.x. Fall back to elapsedtime
                # (int milliseconds - available across the full supported range, RF 6.0+)
                # for older versions.
                if hasattr(test, "elapsed_time"):
                    elapsed_time_seconds = test.elapsed_time.total_seconds()
                else:
                    elapsed_time_seconds = test.elapsedtime / 1000.0
                # test.message is "" (not None) when a test has no message/failure text;
                # normalize back to None so it is skipped from the result payload exactly
                # like the historic (possibly-absent) <status> element text used to be.
                error_msg = test.message if test.message else None
                # Build the ordered top-level item list exactly as Robot Framework
                # executed it: [Setup] (if any), each top-level test-body item, then
                # [Teardown] (if any). _extract_steps() recurses fully from here,
                # including into FOR/IF/WHILE/TRY/GROUP blocks nested anywhere below.
                top_level_items = []
                if test.has_setup:
                    top_level_items.append(test.setup)
                top_level_items.extend(test.body)
                if test.has_teardown:
                    top_level_items.append(test.teardown)
                step_keywords = self._extract_steps(top_level_items)

                result_fields_dict, error = FieldsParser.resolve_fields(result_fields)
                if error:
                    self.env.elog(error)
                    raise Exception(error)
                case_fields_dict, error = FieldsParser.resolve_fields(case_fields)
                if error:
                    self.env.elog(error)
                    raise Exception(error)
                result = TestRailResult(
                    case_id,
                    elapsed=f"{elapsed_time_seconds}",
                    status_id=status_id,
                    comment=error_msg,
                    attachments=attachments,
                    result_fields=result_fields_dict,
                    custom_step_results=step_keywords,
                    quality_rating=quality_rating,
                )
                for comment in reversed(comments):
                    result.prepend_comment(comment)
                tr_test = TestRailCase(
                    title=TestRailCaseFieldsOptimizer.extract_last_words(
                        case_name, TestRailCaseFieldsOptimizer.MAX_TESTCASE_TITLE_LENGTH
                    ),
                    case_id=case_id,
                    result=result,
                    custom_automation_id=(
                        f"{namespace}.{case_name}"
                        if not hasattr(test, "custom_case_automation_id")
                        else test.custom_case_automation_id
                    ),
                    case_fields=case_fields_dict,
                )
                section.testcases.append(tr_test)

        for sub_suite in suite.suites:
            self._find_suites(sub_suite, sections_list, namespace=namespace)

    def _extract_steps(self, body_items, level: int = 0) -> List[TestRailSeparatedStep]:
        """Recursively extract every keyword call in ``body_items`` as a flat,
        depth-first list of TestRail steps, in exact Robot Framework execution order.

        Each real keyword call (``KEYWORD``/``SETUP``/``TEARDOWN`` type items) becomes
        its own step, formatted as ``"<2-space-indent><name>(<args>)"`` where the
        indent depth reflects how many keyword calls it is nested beneath (recursing
        into ``kw.body`` at ``level + 1``). Control-flow containers - FOR, IF/ELSE,
        WHILE, TRY/EXCEPT, GROUP, and their iteration/branch sub-items - are NOT
        themselves rendered as a step (they are not keyword calls), but are walked
        transparently at the *same* level so that keywords called from inside a loop
        or conditional branch are still captured, at their true keyword-call depth.
        Message items have no ``body`` to recurse into and are skipped here; their
        content is instead surfaced via each keyword's own ``actual`` field below.

        This is a finite, single-pass traversal of Robot's own (already-finite,
        acyclic) execution-result tree - one recursive call per body item, each
        strictly narrowing to that item's direct children - so it cannot loop
        infinitely, and recursion depth is bounded by the real keyword-call nesting
        depth of the test (Python's default recursion limit comfortably covers any
        realistic Robot Framework suite).
        """
        steps = []
        for item in body_items:
            item_type = getattr(item, "type", None)
            nested_body = getattr(item, "body", None)
            if item_type in _KEYWORD_LIKE_TYPES:
                steps.append(self._build_step(item, level))
                if nested_body:
                    steps.extend(self._extract_steps(nested_body, level + 1))
            elif nested_body:
                # Transparent control-flow container (FOR/IF/WHILE/TRY/GROUP and their
                # ITERATION/branch sub-items): no step of its own, same nesting level.
                steps.extend(self._extract_steps(nested_body, level))
        return steps

    def _build_step(self, kw, level: int) -> TestRailSeparatedStep:
        """Build a single TestRailSeparatedStep for one keyword call."""
        indent = "  " * level
        # Use kwname (the unqualified keyword name), not name: under RF 6.0.x,
        # Keyword.name is fully qualified as "LibraryName.Keyword Name", while
        # under RF 7.x it already returns the unqualified name. kwname returns
        # the unqualified name consistently across both, matching the historic
        # xml.etree-based behavior (which read the plain <kw name="..."> attribute).
        args_str = ", ".join(kw.args)
        step = TestRailSeparatedStep(f"{indent}{kw.kwname}({args_str})")
        step.status_id = self._case_result_statuses[kw.status.lower()]
        messages = [f"{msg.level}: {msg.message}" for msg in kw.messages if msg.level in _LOGGED_MESSAGE_LEVELS]
        if messages:
            step.actual = "\n".join(messages)
        return step

    @staticmethod
    def _remove_tr_prefix(text: str, tr_prefix: str) -> str:
        return removeprefix(text, tr_prefix).strip()
