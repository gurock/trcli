import glob
from pathlib import Path
from beartype.typing import Union, List
from unittest import TestCase, TestSuite
from xml.etree import ElementTree as etree

from junitparser import JUnitXml, JUnitXmlError, Element, Attr, TestSuite as JUnitTestSuite, TestCase as JUnitTestCase

from trcli.cli import Environment
from trcli.constants import OLD_SYSTEM_NAME_AUTOMATION_ID
from trcli.data_classes.data_parsers import MatchersParser, FieldsParser, TestRailCaseFieldsOptimizer
from trcli.data_classes.dataclass_testrail import (
    TestRailCase,
    TestRailSuite,
    TestRailSection,
    TestRailProperty,
    TestRailResult,
    TestRailSeparatedStep,
)
from trcli.readers.file_parser import FileParser

STEP_STATUSES = {"passed": 1, "untested": 3, "skipped": 4, "failed": 5}

TestCase.id = Attr("id")
TestSuite.id = Attr("id")
JUnitXml.id = Attr("id")


class Properties(Element):
    _tag = "properties"


class Property(Element):
    _tag = "property"
    name = Attr()
    value = Attr()


class JunitParser(FileParser):

    def __init__(self, environment: Environment):
        super().__init__(environment)
        self._case_matcher = environment.case_matcher
        self._special = environment.special_parser
        self._case_result_statuses = {"passed": 1, "skipped": 4, "error": 5, "failure": 5}
        self._update_with_custom_statuses()

    @classmethod
    def _add_root_element_to_tree(cls, filepath: Union[str, Path]) -> etree:
        """
        Because some of junits have XML root as testsuites and some not.
        This way make sure that we always have testsuites root.
        """
        tree = etree.parse(filepath)
        root_elem = tree.getroot()
        if root_elem.tag == "testsuites":
            return tree
        elif root_elem.tag == "testsuite":
            new_root = etree.Element("testsuites")
            new_root.insert(0, root_elem)
            return etree.ElementTree(new_root)
        else:
            raise JUnitXmlError("Invalid format.")

    @staticmethod
    def check_file(filepath: Union[str, Path]) -> Path:
        filepath = Path(filepath)
        files = glob.glob(str(filepath))
        if not files:
            raise FileNotFoundError(f"File not found: {filepath}")
        elif len(files) == 1:
            return Path().cwd().joinpath(files[0])
        sub_suites = []
        for file in files:
            suite = JUnitXml.fromfile(file)
            sub_suites.append(suite)
        suite = sub_suites.pop(0)
        for sub_suite in sub_suites:
            suite += sub_suite
        merged_report_path = Path().cwd().joinpath("Merged-JUnit-report.xml")
        suite.write(merged_report_path)
        return merged_report_path

    @staticmethod
    def _extract_section_properties(section, processed_props) -> List[TestRailProperty]:
        properties = []
        for prop in section.properties():
            if prop.name not in processed_props:
                properties.append(TestRailProperty(prop.name, prop.value))
                processed_props.append(prop.name)

        return properties

    def _update_with_custom_statuses(self):
        custom_statuses = self.env.params_from_config.get("case_result_statuses", None)
        if custom_statuses:
            self._case_result_statuses.update(custom_statuses)

    def _extract_case_id_and_name(self, case) -> tuple:
        case_name = case.name
        case_id = None

        if self._case_matcher == MatchersParser.NAME:
            return MatchersParser.parse_name_with_id(case_name)

        if self._case_matcher == MatchersParser.PROPERTY:
            for case_props in case.iterchildren(Properties):
                for prop in case_props.iterchildren(Property):
                    if prop.name == "test_id":
                        case_id = self._parse_multiple_case_ids(prop.value)
                        return case_id, case_name

        return case_id, case_name

    @staticmethod
    def _parse_multiple_case_ids(test_id_value: str) -> Union[int, List[int], None]:
        """
        Parse single or multiple case IDs from a test_id property value.

        Supports comma-separated case IDs for mapping multiple TestRail cases to one JUnit test.

        Examples:
          - "C123" -> 123 (int)
          - "C123, C456, C789" -> [123, 456, 789] (list)
          - "123, 456, 789" -> [123, 456, 789] (list)
          - " C123 , C456 " -> [123, 456] (list)
          - "C123, C123" -> 123 (int, deduplicated)

        :param test_id_value: Value of the test_id property
        :return: Single case ID (int), multiple case IDs (List[int]), or None if invalid
        """
        if not test_id_value or not isinstance(test_id_value, str):
            return None

        test_id_value = test_id_value.strip()
        if not test_id_value:
            return None

        # Check if comma-separated (multiple IDs)
        if "," in test_id_value:
            case_ids = []
            parts = [part.strip() for part in test_id_value.split(",")]

            for part in parts:
                if not part:
                    continue

                # Remove 'C' or 'c' prefix if present
                cleaned = part.lower().replace("c", "", 1).strip()

                # Check if it's a valid numeric ID
                if cleaned.isdigit():
                    case_id = int(cleaned)
                    # Deduplicate
                    if case_id not in case_ids:
                        case_ids.append(case_id)

            # Return None if no valid IDs found
            if not case_ids:
                return None
            # Return int for single ID (backwards compatibility after deduplication)
            elif len(case_ids) == 1:
                return case_ids[0]
            # Return list for multiple IDs
            else:
                return case_ids
        else:
            # Single case ID (original behavior)
            cleaned = test_id_value.lower().replace("c", "", 1).strip()
            if cleaned.isdigit():
                return int(cleaned)
            return None

    def _get_status_id_for_case_result(self, case: JUnitTestCase) -> Union[int, None]:
        if case.is_passed:
            status = "passed"
        elif case.is_skipped:
            status = "skipped"
        else:
            status = case.result[0]._tag.lower()
        return self._case_result_statuses.get(status)

    @staticmethod
    def _get_comment_for_case_result(case: JUnitTestCase) -> str:
        if case.is_passed:
            return ""
        result = case.result[0]
        parts = [
            f"Type: {result.type}" if result.type else "",
            f"Message: {result.message}" if result.message else "",
            f"Text: {result.text}" if result.text else "",
        ]
        return "\n".join(part for part in parts if part).strip()

    @staticmethod
    def _parse_case_properties(case):
        result_steps = []
        attachments = []
        result_fields = []
        comments = []
        case_fields = []
        case_refs = None
        sauce_session = None

        for case_props in case.iterchildren(Properties):
            for prop in case_props.iterchildren(Property):
                name, value = prop.name, prop.value
                if not name:
                    continue

                elif name.startswith("testrail_result_step"):
                    status, step = value.split(":", maxsplit=1)
                    step_obj = TestRailSeparatedStep(step.strip())
                    step_obj.status_id = STEP_STATUSES[status.lower().strip()]
                    result_steps.append(step_obj)
                elif name.startswith("testrail_attachment"):
                    attachments.append(value)
                elif name.startswith("testrail_result_field"):
                    result_fields.append(value)
                elif name.startswith("testrail_result_comment"):
                    comments.append(value)
                elif name.startswith("testrail_case_field"):
                    text = prop._elem.text.strip() if prop._elem.text else None
                    field_value = text or value
                    case_fields.append(field_value)

                    # Extract refs for case updates
                    if field_value and field_value.startswith("refs:"):
                        case_refs = field_value[5:].strip()  # Remove "refs:" prefix
                elif name.startswith("testrail_sauce_session"):
                    sauce_session = value

        return result_steps, attachments, result_fields, comments, case_fields, case_refs, sauce_session

    def _resolve_case_fields(self, result_fields, case_fields):
        result_fields_dict, error = FieldsParser.resolve_fields(result_fields)
        if error:
            self.env.elog(error)
            raise Exception(error)

        case_fields_dict, error = FieldsParser.resolve_fields(case_fields)
        if error:
            self.env.elog(error)
            raise Exception(error)

        return result_fields_dict, case_fields_dict

    def _parse_test_cases(self, section) -> List[TestRailCase]:
        test_cases = []

        for case in section:
            """
            TODO: use section.iterchildren(JUnitTestCase) to get only testcases belonging to the section
            required for nested suites
            """
            automation_id = f"{case.classname}.{case.name}"
            case_id, case_name = self._extract_case_id_and_name(case)
            result_steps, attachments, result_fields, comments, case_fields, case_refs, sauce_session = (
                self._parse_case_properties(case)
            )
            result_fields_dict, case_fields_dict = self._resolve_case_fields(result_fields, case_fields)
            status_id = self._get_status_id_for_case_result(case)
            comment = self._get_comment_for_case_result(case)

            # Prepare data that will be shared across all case IDs (if multiple)
            base_automation_id = case_fields_dict.pop(OLD_SYSTEM_NAME_AUTOMATION_ID, None) or case._elem.get(
                OLD_SYSTEM_NAME_AUTOMATION_ID, automation_id
            )
            base_title = TestRailCaseFieldsOptimizer.extract_last_words(
                case_name, TestRailCaseFieldsOptimizer.MAX_TESTCASE_TITLE_LENGTH
            )

            # Check if case_id is a list (multiple IDs) or single value
            if isinstance(case_id, list):
                # Multiple case IDs: create a TestRailCase for each ID with same result data
                for individual_case_id in case_id:
                    # Create a new result object for each case (avoid sharing references)
                    result = TestRailResult(
                        case_id=individual_case_id,
                        elapsed=case.time,
                        attachments=attachments.copy() if attachments else [],
                        result_fields=result_fields_dict.copy(),
                        custom_step_results=result_steps.copy() if result_steps else [],
                        status_id=status_id,
                        comment=comment,
                    )

                    # Apply comment prepending
                    for comment_text in reversed(comments):
                        result.prepend_comment(comment_text)
                    if sauce_session:
                        result.prepend_comment(f"SauceLabs session: {sauce_session}")

                    # Create TestRailCase kwargs
                    case_kwargs = {
                        "title": base_title,
                        "case_id": individual_case_id,
                        "result": result,
                        "custom_automation_id": base_automation_id,
                        "case_fields": case_fields_dict.copy(),
                    }

                    # Only set refs field if case_refs has actual content
                    if case_refs and case_refs.strip():
                        case_kwargs["refs"] = case_refs

                    test_case = TestRailCase(**case_kwargs)

                    # Store JUnit references as a temporary attribute for case updates (not serialized)
                    if case_refs and case_refs.strip():
                        test_case._junit_case_refs = case_refs

                    test_cases.append(test_case)
            else:
                # Single case ID: existing behavior (backwards compatibility)
                result = TestRailResult(
                    case_id=case_id,
                    elapsed=case.time,
                    attachments=attachments,
                    result_fields=result_fields_dict,
                    custom_step_results=result_steps,
                    status_id=status_id,
                    comment=comment,
                )

                for comment_text in reversed(comments):
                    result.prepend_comment(comment_text)
                if sauce_session:
                    result.prepend_comment(f"SauceLabs session: {sauce_session}")

                # Create TestRailCase kwargs
                case_kwargs = {
                    "title": base_title,
                    "case_id": case_id,
                    "result": result,
                    "custom_automation_id": base_automation_id,
                    "case_fields": case_fields_dict,
                }

                # Only set refs field if case_refs has actual content
                if case_refs and case_refs.strip():
                    case_kwargs["refs"] = case_refs

                test_case = TestRailCase(**case_kwargs)

                # Store JUnit references as a temporary attribute for case updates (not serialized)
                if case_refs and case_refs.strip():
                    test_case._junit_case_refs = case_refs

                test_cases.append(test_case)

        return test_cases

    def _get_suite_name(self, suite):
        if self.env.suite_name:
            return self.env.suite_name
        elif suite.name:
            return suite.name
        raise ValueError("Suite name is not defined in environment or JUnit report.")

    def _parse_sections(self, suite) -> List[TestRailSection]:
        sections = []
        processed_props = []

        for section in suite:
            if isinstance(section, JUnitTestSuite):
                if not len(section):
                    continue
                """
                TODO: Handle nested suites if needed (add sub_sections to data class TestRailSection)
                inner_suites = section.testsuites()
                sub_sections = self._parse_sections(inner_suites)
                then sub_sections=sub_sections
                """
                properties = self._extract_section_properties(section, processed_props)

                # BDD MODE: Group all scenarios under one test case
                if self._is_bdd_mode():
                    test_case = self._parse_bdd_feature_as_single_case(section)
                    test_cases = [test_case] if test_case else []
                # STANDARD MODE: One test case per JUnit testcase
                else:
                    test_cases = self._parse_test_cases(section)

                self.env.log(f"Processed {len(test_cases)} test cases in section {section.name}.")
                sections.append(
                    TestRailSection(
                        section.name,
                        testcases=test_cases,
                        properties=properties,
                    )
                )

        return sections

    def _is_bdd_mode(self) -> bool:
        """Check if BDD grouping mode is enabled

        Returns:
            True if special parser is 'bdd', False otherwise
        """
        return self._special == "bdd"

    def _extract_feature_case_id_from_property(self, testsuite) -> Union[int, None]:
        """Extract case ID from testsuite-level properties

        Looks for properties: testrail_case_id, test_id, bdd_case_id

        Args:
            testsuite: JUnit testsuite element

        Returns:
            Case ID as integer or None if not found
        """
        for prop in testsuite.properties():
            if prop.name in ["testrail_case_id", "test_id", "bdd_case_id"]:
                case_id_str = prop.value.lower().replace("c", "")
                if case_id_str.isnumeric():
                    self.env.vlog(f"BDD: Found case ID C{case_id_str} in testsuite property '{prop.name}'")
                    return int(case_id_str)
        return None

    def _extract_case_id_from_testcases(self, testsuite) -> List[tuple]:
        """Extract case IDs from testcase properties and names

        Args:
            testsuite: JUnit testsuite element

        Returns:
            List of tuples (testcase_name, case_id)
        """
        testcase_case_ids = []

        for testcase in testsuite:
            tc_case_id = None

            # Check testcase properties first
            for case_props in testcase.iterchildren(Properties):
                for prop in case_props.iterchildren(Property):
                    if prop.name == "test_id":
                        tc_case_id_str = prop.value.lower().replace("c", "")
                        if tc_case_id_str.isnumeric():
                            tc_case_id = int(tc_case_id_str)
                            break

            # Check testcase name if property not found
            if not tc_case_id:
                tc_case_id, _ = MatchersParser.parse_name_with_id(testcase.name)

            if tc_case_id:
                testcase_case_ids.append((testcase.name, tc_case_id))

        return testcase_case_ids

    def _extract_and_validate_bdd_case_id(self, testsuite) -> tuple:
        """Extract case ID from various sources and validate consistency

        In BDD mode, all scenarios in a feature MUST share the same case ID.

        Priority order:
        1. Testsuite-level property (testrail_case_id, test_id, bdd_case_id)
        2. Testcase properties (all must be same)
        3. Testcase names (all must be same)
        4. Testsuite name pattern [C123]

        Args:
            testsuite: JUnit testsuite element

        Returns:
            Tuple of (case_id: int or None, validation_errors: List[str])
        """
        validation_errors = []

        # Priority 1: Testsuite-level property
        case_id = self._extract_feature_case_id_from_property(testsuite)
        if case_id:
            return case_id, []

        # Priority 2 & 3: Check testcase properties and names
        testcase_case_ids = self._extract_case_id_from_testcases(testsuite)

        if not testcase_case_ids:
            validation_errors.append(
                f"BDD Error: No case ID found for feature '{testsuite.name}'.\n"
                f"  Add case ID using one of:\n"
                f"  - Testsuite property: <property name='testrail_case_id' value='C42'/>\n"
                f"  - Testcase names: 'Scenario name C42'\n"
                f"  - Testcase property: <property name='test_id' value='C42'/>"
            )
            return None, validation_errors

        # Check consistency - all must be the same
        unique_case_ids = set(cid for _, cid in testcase_case_ids)

        if len(unique_case_ids) > 1:
            validation_errors.append(
                f"BDD Error: Multiple different case IDs found in feature '{testsuite.name}'.\n"
                f"  In BDD mode, all scenarios must map to the SAME TestRail case.\n"
                f"  Found case IDs: {sorted(unique_case_ids)}\n"
                f"  Scenarios:\n"
                + "\n".join(f"    - '{name}' → C{cid}" for name, cid in testcase_case_ids)
                + f"\n\n  If these should be separate test cases, remove --special-parser bdd flag."
            )
            return None, validation_errors

        case_id = testcase_case_ids[0][1]
        self.env.vlog(
            f"BDD: Found consistent case ID C{case_id} across {len(testcase_case_ids)} scenario(s) "
            f"in feature '{testsuite.name}'"
        )

        # Priority 4: Check testsuite name if no testcase IDs found
        if not case_id and self._case_matcher == MatchersParser.NAME:
            case_id, _ = MatchersParser.parse_name_with_id(testsuite.name)
            if case_id:
                self.env.vlog(f"BDD: Found case ID C{case_id} in testsuite name")

        return case_id, []

    def _validate_bdd_case_exists(self, case_id: int, feature_name: str) -> tuple:
        """Validate that case exists in TestRail AND is a BDD test case

        A valid BDD test case MUST have:
        - Exist in TestRail (case ID is valid)
        - Have custom_testrail_bdd_scenario field with content

        Args:
            case_id: TestRail case ID to validate
            feature_name: Feature/testsuite name for error context

        Returns:
            Tuple of (is_valid: bool, error_message: str, case_data: dict)
        """
        try:
            # Import here to avoid circular dependency
            from trcli.api.api_request_handler import ApiRequestHandler
            from trcli.api.project_based_client import ProjectBasedClient
            from trcli.data_classes.dataclass_testrail import TestRailSuite

            # Get API client
            temp_suite = TestRailSuite(name="temp", suite_id=1)
            project_client = ProjectBasedClient(environment=self.env, suite=temp_suite)
            api_handler = project_client.api_request_handler

            # Step 1: Get case from TestRail
            response = api_handler.client.send_get(f"get_case/{case_id}")

            if response.error_message:
                return (
                    False,
                    (
                        f"BDD Validation Error: Case C{case_id} does not exist in TestRail.\n"
                        f"Feature: '{feature_name}'\n"
                        f"API Error: {response.error_message}\n\n"
                        f"Action Required:\n"
                        f"  1. Verify case C{case_id} exists in TestRail\n"
                        f"  2. Ensure you have permission to access this case\n"
                        f"  3. Create the BDD test case if it doesn't exist:\n"
                        f"     trcli import_gherkin -f {feature_name}.feature --section-id <ID>"
                    ),
                    {},
                )

            case_data = response.response_text

            # Step 2: Validate it's a BDD test case
            # Resolve BDD case field name dynamically
            bdd_field_name = api_handler.get_bdd_case_field_name()
            bdd_scenario_field = case_data.get(bdd_field_name)

            if not bdd_scenario_field:
                return (
                    False,
                    (
                        f"BDD Validation Error: Case C{case_id} is NOT a BDD test case.\n"
                        f"Feature: '{feature_name}'\n"
                        f"Case Title: '{case_data.get('title', 'Unknown')}'\n\n"
                        f"Reason: The '{bdd_field_name}' field is empty or null.\n"
                        f"This indicates the case is using a regular template, not the BDD template.\n\n"
                        f"Action Required:\n"
                        f"  Option 1: Upload this case using standard mode (remove --special-parser bdd)\n"
                        f"  Option 2: Create a proper BDD test case with:\n"
                        f"     trcli import_gherkin -f {feature_name}.feature --section-id <ID>\n"
                        f"  Option 3: Convert existing case to BDD template in TestRail UI"
                    ),
                    case_data,
                )

            # Success!
            self.env.vlog(
                f"BDD: Validated case C{case_id} is a valid BDD test case\n"
                f"  - Title: '{case_data.get('title')}'\n"
                f"  - Template ID: {case_data.get('template_id')}\n"
                f"  - Has BDD scenarios: Yes"
            )

            return True, "", case_data

        except Exception as e:
            return (
                False,
                (
                    f"BDD Validation Error: Unable to validate case C{case_id}.\n"
                    f"Feature: '{feature_name}'\n"
                    f"Error: {str(e)}\n\n"
                    f"Action Required: Verify your TestRail connection and case access permissions."
                ),
                {},
            )

    def _aggregate_scenario_statuses(self, scenario_statuses: List[int]) -> int:
        """Aggregate scenario statuses using fail-fast logic

        Fail-fast logic:
        - If ANY scenario is Failed (5) → Feature is Failed (5)
        - Else if ANY scenario is Skipped (4) → Feature is Skipped (4)
        - Else if ALL scenarios Passed (1) → Feature is Passed (1)

        Args:
            scenario_statuses: List of TestRail status IDs

        Returns:
            Aggregated status ID
        """
        if 5 in scenario_statuses:  # Any failure
            return 5
        elif 4 in scenario_statuses:  # Any skipped (no failures)
            return 4
        else:  # All passed
            return 1

    def _format_failure_message(self, scenario_name: str, result_obj) -> str:
        """Format failure details for comment

        Args:
            scenario_name: Clean scenario name
            result_obj: JUnit result object (failure/error element)

        Returns:
            Formatted failure message
        """
        lines = [f"Scenario: {scenario_name}"]

        if result_obj.type:
            lines.append(f"   Type: {result_obj.type}")

        if result_obj.message:
            lines.append(f"   Message: {result_obj.message}")

        if result_obj.text:
            # Truncate if too long
            text = result_obj.text.strip()
            if len(text) > 500:
                text = text[:500] + "\n   ... (truncated)"
            lines.append(f"   Details:\n   {text}")

        return "\n".join(lines)

    def _parse_bdd_feature_as_single_case(self, testsuite) -> Union[TestRailCase, None]:
        """Parse all scenarios in a testsuite as a single BDD test case

        Enhanced validation:
        1. Case ID exists
        2. All scenarios have same case ID
        3. Case exists in TestRail
        4. Case is actually a BDD test case (has custom_testrail_bdd_scenario)

        Args:
            testsuite: JUnit testsuite containing multiple scenarios

        Returns:
            Single TestRailCase with aggregated scenario results, or None if validation fails
        """
        feature_name = testsuite.name

        # Step 1: Extract and validate case ID consistency
        case_id, validation_errors = self._extract_and_validate_bdd_case_id(testsuite)

        if validation_errors:
            for error in validation_errors:
                self.env.elog(error)
            return None

        if not case_id:
            self.env.elog(f"BDD Error: No valid case ID found for feature '{feature_name}'. " f"Skipping this feature.")
            return None

        # Step 2: Validate case exists AND is a BDD case
        is_valid, error_message, case_data = self._validate_bdd_case_exists(case_id, feature_name)

        if not is_valid:
            self.env.elog(error_message)
            # Raise exception to stop processing
            from trcli.data_classes.validation_exception import ValidationException

            raise ValidationException(
                field_name="case_id",
                class_name="BDD Feature",
                reason=f"Case C{case_id} validation failed. See error above for details.",
            )

        self.env.log(f"BDD: Case C{case_id} validated as BDD test case for feature '{feature_name}'")

        # Step 3: Parse all scenarios
        bdd_scenario_results = []
        scenario_statuses = []
        total_time = 0
        failure_messages = []

        for idx, testcase in enumerate(testsuite, 1):
            scenario_name = testcase.name
            # Clean case ID from name
            _, clean_scenario_name = MatchersParser.parse_name_with_id(scenario_name)
            if not clean_scenario_name:
                clean_scenario_name = scenario_name

            scenario_time = float(testcase.time or 0)
            total_time += scenario_time

            # Determine scenario status
            if testcase.is_passed:
                scenario_status = 1
                scenario_status_label = "PASSED"
            elif testcase.is_skipped:
                scenario_status = 4
                scenario_status_label = "SKIPPED"
            else:  # Failed
                scenario_status = 5
                scenario_status_label = "FAILED"

                # Capture failure details
                if testcase.result:
                    result_obj = testcase.result[0]
                    error_msg = self._format_failure_message(clean_scenario_name, result_obj)
                    failure_messages.append(error_msg)

            # Track status for aggregation
            scenario_statuses.append(scenario_status)

            # Create BDD scenario result (matches Cucumber parser format)
            step = TestRailSeparatedStep(content=clean_scenario_name)
            step.status_id = scenario_status
            bdd_scenario_results.append(step)

            self.env.vlog(f"  - Scenario {idx}: {clean_scenario_name} → {scenario_status_label} " f"({scenario_time}s)")

        # Step 4: Aggregate statuses
        overall_status = self._aggregate_scenario_statuses(scenario_statuses)

        status_labels = {1: "PASSED", 4: "SKIPPED", 5: "FAILED"}
        overall_status_label = status_labels.get(overall_status, "UNKNOWN")

        # Step 5: Create comment with summary
        passed_count = scenario_statuses.count(1)
        failed_count = scenario_statuses.count(5)
        skipped_count = scenario_statuses.count(4)
        total_count = len(scenario_statuses)

        summary = (
            f"Feature Summary:\n"
            f"  Total Scenarios: {total_count}\n"
            f"  Passed: {passed_count}\n"
            f"  Failed: {failed_count}\n"
            f"  Skipped: {skipped_count}\n"
        )

        if failure_messages:
            comment = f"{summary}\n{'='*50}\nFailure Details:\n\n" + "\n\n".join(failure_messages)
        else:
            comment = summary

        # Step 6: Create aggregated result
        # Get API handler to resolve BDD result field name
        from trcli.api.project_based_client import ProjectBasedClient
        from trcli.data_classes.dataclass_testrail import TestRailSuite as TRSuite

        temp_suite = TRSuite(name="temp", suite_id=1)
        project_client = ProjectBasedClient(environment=self.env, suite=temp_suite)
        bdd_result_field_name = project_client.api_request_handler.get_bdd_result_field_name()

        result = TestRailResult(
            case_id=case_id,
            status_id=overall_status,
            elapsed=total_time if total_time > 0 else None,  # Pass numeric value, not formatted string
            comment=comment,
        )

        # Add BDD scenario results to result_fields dict (for serialization)
        # Convert TestRailSeparatedStep objects to dicts for API
        result.result_fields[bdd_result_field_name] = [
            {"content": step.content, "status_id": step.status_id} for step in bdd_scenario_results
        ]

        # Step 7: Create test case
        test_case = TestRailCase(
            title=feature_name,
            case_id=case_id,
            result=result,
        )

        self.env.log(
            f"BDD: Grouped {total_count} scenario(s) under case C{case_id} "
            f"'{feature_name}' → {overall_status_label}"
        )
        self.env.log(f"     Breakdown: {passed_count} passed, {failed_count} failed, " f"{skipped_count} skipped")

        return test_case

    def parse_file(self) -> List[TestRailSuite]:
        self.env.log("Parsing JUnit report.")
        suite = JUnitXml.fromfile(self.filepath, parse_func=self._add_root_element_to_tree)

        suites = self._split_sauce_report(suite) if self._special == "saucectl" else [suite]
        testrail_suites = []

        for suite in suites:
            if suite.name:
                self.env.log(f"Processing JUnit suite - {suite.name}")

            testrail_sections = self._parse_sections(suite)
            suite_name = self.env.suite_name if self.env.suite_name else suite.name

            testrail_suites.append(
                TestRailSuite(
                    suite_name,
                    testsections=testrail_sections,
                    source=self.filename,
                )
            )

        return testrail_suites

    def _split_sauce_report(self, suite) -> List[JUnitXml]:
        self.env.log(f"Processing SauceLabs report.")
        subsuites = {}
        for section in suite:
            if not len(section):
                continue
            divider_index = section.name.find("-")
            subsuite_name = section.name[:divider_index].strip()
            section.name = section.name[divider_index + 1 :].strip()
            new_xml = JUnitXml(subsuite_name)
            if subsuite_name not in subsuites.keys():
                subsuites[subsuite_name] = new_xml
            subsuites[subsuite_name].add_testsuite(section)

        for suite_name, suite in subsuites.items():
            for section in suite:
                if not len(section):
                    continue
                session_url = None
                session_prop = None
                for section_prop in section.properties():
                    if section_prop.name == "url":
                        session_prop = section_prop
                        session_url = section_prop.value
                if session_prop:
                    section.remove_property(session_prop)
                for case in section:
                    case_props = case.child(Properties)
                    if not case_props:
                        case_props = Properties()
                        case.append(case_props)
                    case_prop = Property()
                    case_prop.name = "testrail_sauce_session"
                    case_prop.value = session_url
                    case_props.append(case_prop)

        self.env.log(f"Found {len(subsuites)} SauceLabs suites.")

        return [v for k, v in subsuites.items()]


if __name__ == "__main__":
    pass
