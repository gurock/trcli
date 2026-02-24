"""
CaseMatcherFactory - Strategy pattern implementation for TestRail case matching

Matching Strategies:
- AutomationIdMatcher: Matches cases by automation_id field
- NameMatcher: Matches cases by name (requires case_id in test data)
- PropertyMatcher: Matches cases by custom property (requires case_id in test data)
"""

import html
from abc import ABC, abstractmethod
from beartype.typing import Tuple, List, Dict, Set

from trcli.cli import Environment
from trcli.constants import OLD_SYSTEM_NAME_AUTOMATION_ID, UPDATED_SYSTEM_NAME_AUTOMATION_ID
from trcli.data_classes.data_parsers import MatchersParser
from trcli.data_classes.dataclass_testrail import TestRailSuite
from trcli.data_providers.api_data_provider import ApiDataProvider


class CaseMatcher(ABC):
    """Abstract base class for case matching strategies"""

    def __init__(self, environment: Environment, data_provider: ApiDataProvider):
        """
        Initialize the case matcher

        :param environment: Environment configuration
        :param data_provider: Data provider for accessing test case data
        """
        self.environment = environment
        self.data_provider = data_provider

    @abstractmethod
    def check_missing_cases(
        self,
        project_id: int,
        suite_id: int,
        suites_data: TestRailSuite,
        get_all_cases_callback,
        validate_case_ids_callback,
    ) -> Tuple[bool, str]:
        """
        Check for missing test cases using the specific matching strategy

        :param project_id: TestRail project ID
        :param suite_id: TestRail suite ID
        :param suites_data: Test suite data from provider
        :param get_all_cases_callback: Callback to fetch all cases from TestRail
        :param validate_case_ids_callback: Callback to validate case IDs exist
        :returns: Tuple (has_missing_cases, error_message)
        """
        pass


class AutomationIdMatcher(CaseMatcher):
    """Matches test cases by automation_id field"""

    @staticmethod
    def _strip_froala_paragraph_tags(value: str) -> str:
        """
        Strip Froala HTML paragraph tags from automation_id values.

        :param value: Automation ID value from TestRail
        :returns: Value with leading <p> and trailing </p> tags removed
        """
        if not value:
            return value

        # Strip whitespace first
        value = value.strip()

        # Remove leading <p> tag (case-insensitive)
        if value.lower().startswith("<p>"):
            value = value[3:]

        # Remove trailing </p> tag (case-insensitive)
        if value.lower().endswith("</p>"):
            value = value[:-4]

        # Strip any remaining whitespace after tag removal
        return value.strip()

    def check_missing_cases(
        self,
        project_id: int,
        suite_id: int,
        suites_data: TestRailSuite,
        get_all_cases_callback,
        validate_case_ids_callback,
    ) -> Tuple[bool, str]:
        """
        Match cases using automation_id field

        :param project_id: TestRail project ID
        :param suite_id: TestRail suite ID
        :param suites_data: Test suite data from provider
        :param get_all_cases_callback: Callback to fetch all cases from TestRail
        :param validate_case_ids_callback: Callback to validate case IDs exist
        :returns: Tuple (has_missing_cases, error_message)
        """
        missing_cases_number = 0

        # Fetch all cases from TestRail
        returned_cases, error_message = get_all_cases_callback(project_id, suite_id)
        if error_message:
            return False, error_message

        # Build lookup dictionary: automation_id -> case data
        test_cases_by_aut_id = {}
        for case in returned_cases:
            aut_case_id = case.get(OLD_SYSTEM_NAME_AUTOMATION_ID) or case.get(UPDATED_SYSTEM_NAME_AUTOMATION_ID)
            if aut_case_id:
                aut_case_id = html.unescape(aut_case_id)
                aut_case_id = self._strip_froala_paragraph_tags(aut_case_id)
                test_cases_by_aut_id[aut_case_id] = case

        # Match test cases from report with TestRail cases
        test_case_data = []
        for section in suites_data.testsections:
            for test_case in section.testcases:
                aut_id = test_case.custom_automation_id
                if aut_id in test_cases_by_aut_id.keys():
                    case = test_cases_by_aut_id[aut_id]
                    test_case_data.append(
                        {
                            "case_id": case["id"],
                            "section_id": case["section_id"],
                            "title": case["title"],
                            OLD_SYSTEM_NAME_AUTOMATION_ID: aut_id,
                        }
                    )
                else:
                    missing_cases_number += 1

        # Update data provider with matched cases
        self.data_provider.update_data(case_data=test_case_data)

        if missing_cases_number:
            self.environment.log(f"Found {missing_cases_number} test cases not matching any TestRail case.")

        return missing_cases_number > 0, ""


class IdBasedMatcher(CaseMatcher):
    """Base class for matchers that rely on case_id being present in test data (NAME, PROPERTY)"""

    def check_missing_cases(
        self,
        project_id: int,
        suite_id: int,
        suites_data: TestRailSuite,
        get_all_cases_callback,
        validate_case_ids_callback,
    ) -> Tuple[bool, str]:
        """
        Validate that case IDs exist in TestRail

        For NAME/PROPERTY matchers, the test data must already contain case_id.
        This method validates those IDs exist in TestRail.

        :param project_id: TestRail project ID
        :param suite_id: TestRail suite ID
        :param suites_data: Test suite data from provider
        :param get_all_cases_callback: Callback to fetch all cases from TestRail
        :param validate_case_ids_callback: Callback to validate case IDs exist
        :returns: Tuple (has_missing_cases, error_message)
        """
        missing_cases_number = 0
        nonexistent_ids = []
        case_ids_to_validate = set()

        # Collect all unique case IDs that need validation
        for section in suites_data.testsections:
            for test_case in section.testcases:
                if not test_case.case_id:
                    missing_cases_number += 1
                else:
                    case_ids_to_validate.add(int(test_case.case_id))

        total_tests_in_report = missing_cases_number + len(case_ids_to_validate)

        if missing_cases_number:
            self.environment.log(f"Found {missing_cases_number} test cases without case ID in the report file.")

        # Smart validation strategy based on report size
        # Threshold: 1000 cases (same as skip validation threshold for consistency)
        if case_ids_to_validate:
            # Skip validation for large reports with all IDs (most efficient)
            if missing_cases_number == 0 and total_tests_in_report >= 1000:
                # All tests have IDs and report is large: Skip validation (trust IDs)
                self.environment.log(
                    f"Skipping validation of {len(case_ids_to_validate)} case IDs "
                    f"(all tests have IDs, trusting they exist). "
                    f"If you encounter errors, ensure all case IDs in your test report exist in TestRail."
                )
                nonexistent_ids = []

            # Fetch all for large reports with missing IDs
            elif total_tests_in_report >= 1000:
                # Large report (>=1000 cases) with some missing IDs: Fetch all cases and validate locally
                # This is more efficient than individual validation for large batches
                self.environment.log(
                    f"Large report detected ({total_tests_in_report} cases). "
                    f"Fetching all cases from TestRail for efficient validation..."
                )
                returned_cases, error_message = get_all_cases_callback(project_id, suite_id)
                if error_message:
                    return False, error_message

                # Build lookup dictionary from fetched cases
                all_case_ids = {case["id"] for case in returned_cases}

                # Validate locally (O(1) lookup)
                nonexistent_ids = [cid for cid in case_ids_to_validate if cid not in all_case_ids]

                if nonexistent_ids:
                    self.environment.elog(
                        f"Nonexistent case IDs found in the report file: {nonexistent_ids[:20]}"
                        f"{' ...' if len(nonexistent_ids) > 20 else ''}"
                    )
                    return False, "Case IDs not in TestRail project or suite were detected in the report file."

            # Individual validation for small reports
            else:
                # Small report (<1000 cases): Use individual validation
                # This is more efficient for small batches
                self.environment.log(f"Validating {len(case_ids_to_validate)} case IDs exist in TestRail...")
                validated_ids = validate_case_ids_callback(suite_id, list(case_ids_to_validate))
                nonexistent_ids = [cid for cid in case_ids_to_validate if cid not in validated_ids]

                if nonexistent_ids:
                    self.environment.elog(f"Nonexistent case IDs found in the report file: {nonexistent_ids}")
                    return False, "Case IDs not in TestRail project or suite were detected in the report file."

        return missing_cases_number > 0, ""


class NameMatcher(IdBasedMatcher):
    """Matches test cases by name (case_id must be present in test data)"""

    pass


class PropertyMatcher(IdBasedMatcher):
    """Matches test cases by custom property (case_id must be present in test data)"""

    pass


class CaseMatcherFactory:
    """Factory for creating appropriate case matcher based on configuration"""

    @staticmethod
    def create_matcher(
        matcher_type: MatchersParser, environment: Environment, data_provider: ApiDataProvider
    ) -> CaseMatcher:
        """
        Create the appropriate case matcher based on the matcher type

        :param matcher_type: Type of matcher to create (AUTO, NAME, PROPERTY). If None, defaults to AUTO.
        :param environment: Environment configuration
        :param data_provider: Data provider for accessing test case data
        :returns: Concrete CaseMatcher instance
        :raises ValueError: If matcher_type is not recognized
        """
        # Default to AUTO if matcher_type is None (e.g., for parse_openapi command)
        if matcher_type is None or matcher_type == MatchersParser.AUTO:
            return AutomationIdMatcher(environment, data_provider)
        elif matcher_type == MatchersParser.NAME:
            return NameMatcher(environment, data_provider)
        elif matcher_type == MatchersParser.PROPERTY:
            return PropertyMatcher(environment, data_provider)
        else:
            raise ValueError(f"Unknown matcher type: {matcher_type}")
