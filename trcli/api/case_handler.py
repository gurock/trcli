"""
CaseHandler - Handles all test case-related operations for TestRail

This class was extracted from ApiRequestHandler to follow the Single Responsibility Principle.
It manages all test case operations including:
- Adding test cases
- Updating case references
- Updating case automation IDs
- Deleting test cases
- Case helper operations
"""

from concurrent.futures import ThreadPoolExecutor
from beartype.typing import List, Tuple, Dict

from trcli.api.api_client import APIClient, APIClientResult
from trcli.api.api_utils import (
    deduplicate_references,
    join_references,
    parse_references,
    validate_references_length,
)
from trcli.cli import Environment
from trcli.constants import OLD_SYSTEM_NAME_AUTOMATION_ID, UPDATED_SYSTEM_NAME_AUTOMATION_ID
from trcli.data_classes.data_parsers import MatchersParser
from trcli.data_classes.dataclass_testrail import TestRailCase
from trcli.data_providers.api_data_provider import ApiDataProvider
from trcli.settings import MAX_WORKERS_ADD_CASE


class CaseHandler:
    """Handles all test case-related operations for TestRail"""

    MAX_CASE_REFERENCES_LENGTH = 2000  # TestRail character limit for case refs field

    def __init__(
        self,
        client: APIClient,
        environment: Environment,
        data_provider: ApiDataProvider,
        handle_futures_callback,
        retrieve_results_callback,
    ):
        """
        Initialize the CaseHandler

        :param client: APIClient instance for making API calls
        :param environment: Environment configuration
        :param data_provider: Data provider for case data
        :param handle_futures_callback: Callback to handle concurrent futures
        :param retrieve_results_callback: Callback to retrieve results after cancellation
        """
        self.client = client
        self.environment = environment
        self.data_provider = data_provider
        self.handle_futures = handle_futures_callback
        self.retrieve_results_after_cancelling = retrieve_results_callback
        # Store active automation ID field (set by parent)
        self._active_automation_id_field = None

    def add_cases(self) -> Tuple[List[dict], str]:
        """
        Add cases that doesn't have ID in DataProvider.
        Runs update_data in data_provider for successfully created resources.

        :returns: Tuple with list of dict created resources and error string.
        """
        add_case_data = self.data_provider.add_cases()
        responses = []
        error_message = ""
        with self.environment.get_progress_bar(
            results_amount=len(add_case_data), prefix="Adding test cases"
        ) as progress_bar:
            with ThreadPoolExecutor(max_workers=MAX_WORKERS_ADD_CASE) as executor:
                futures = {
                    executor.submit(
                        self._add_case_and_update_data,
                        body,
                    ): body
                    for body in add_case_data
                }
                responses, error_message = self.handle_futures(
                    futures=futures, action_string="add_case", progress_bar=progress_bar
                )
            if error_message:
                # When error_message is present we cannot be sure that responses contains all added items.
                # Iterate through futures to get all responses from done tasks (not cancelled)
                responses = self.retrieve_results_after_cancelling(futures)
        returned_resources = [
            {
                "case_id": response.response_text["id"],
                "section_id": response.response_text["section_id"],
                "title": response.response_text["title"],
            }
            for response in responses
        ]
        return returned_resources, error_message

    def _add_case_and_update_data(self, case: TestRailCase) -> APIClientResult:
        """
        Helper method to add a single case and update its data

        :param case: TestRailCase object to add
        :returns: APIClientResult
        """
        case_body = case.to_dict()
        active_field = self._active_automation_id_field
        if active_field == UPDATED_SYSTEM_NAME_AUTOMATION_ID and OLD_SYSTEM_NAME_AUTOMATION_ID in case_body:
            case_body[UPDATED_SYSTEM_NAME_AUTOMATION_ID] = case_body.pop(OLD_SYSTEM_NAME_AUTOMATION_ID)
        if self.environment.case_matcher != MatchersParser.AUTO and OLD_SYSTEM_NAME_AUTOMATION_ID in case_body:
            case_body.pop(OLD_SYSTEM_NAME_AUTOMATION_ID)
        response = self.client.send_post(f"add_case/{case_body.pop('section_id')}", case_body)
        if response.status_code == 200:
            case.case_id = response.response_text["id"]
            case.result.case_id = response.response_text["id"]
            case.section_id = response.response_text["section_id"]
        return response

    def update_existing_case_references(
        self, case_id: int, junit_refs: str, strategy: str = "append"
    ) -> Tuple[bool, str, List[str], List[str]]:
        """
        Update existing case references with values from JUnit properties.

        :param case_id: ID of the test case
        :param junit_refs: References from JUnit testrail_case_field property
        :param strategy: 'append' or 'replace'
        :returns: Tuple with (success, error_message, added_refs, skipped_refs)
        """
        if not junit_refs or not junit_refs.strip():
            return True, None, [], []  # No references to process

        # Parse and deduplicate JUnit references using utility function
        junit_ref_list = deduplicate_references(parse_references(junit_refs))

        if not junit_ref_list:
            return False, "No valid references found in JUnit property", [], []

        # Get current case data
        case_response = self.client.send_get(f"get_case/{case_id}")
        if case_response.error_message:
            return False, case_response.error_message, [], []

        existing_refs = case_response.response_text.get("refs", "") or ""

        if strategy == "replace":
            # Replace strategy: use JUnit refs as-is
            new_refs = join_references(junit_ref_list)
            added_refs = junit_ref_list
            skipped_refs = []
        else:
            # Append strategy: combine with existing refs, avoiding duplicates
            existing_ref_list = parse_references(existing_refs)

            # Determine which references are new vs duplicates
            added_refs = [ref for ref in junit_ref_list if ref not in existing_ref_list]
            skipped_refs = [ref for ref in junit_ref_list if ref in existing_ref_list]

            # If no new references to add, return current state
            if not added_refs:
                return True, None, added_refs, skipped_refs

            # Combine references
            combined_list = existing_ref_list + added_refs
            new_refs = join_references(combined_list)

        # Validate 2000 character limit for test case references
        is_valid, error_msg = validate_references_length(new_refs, self.MAX_CASE_REFERENCES_LENGTH)
        if not is_valid:
            return False, error_msg, [], []

        # Update the case
        update_data = {"refs": new_refs}
        update_response = self.client.send_post(f"update_case/{case_id}", update_data)

        if update_response.error_message:
            return False, update_response.error_message, [], []

        return True, None, added_refs, skipped_refs

    def delete_cases(self, suite_id: int, added_cases: List[Dict]) -> Tuple[Dict, str]:
        """
        Delete cases given add_cases response

        :param suite_id: suite id
        :param added_cases: List of cases to delete
        :returns: Tuple with dict created resources and error string.
        """
        body = {"case_ids": [case["case_id"] for case in added_cases]}
        response = self.client.send_post(f"delete_cases/{suite_id}", payload=body)
        return response.response_text, response.error_message

    def update_case_automation_id(self, case_id: int, automation_id: str) -> Tuple[bool, str]:
        """
        Update the automation_id field of a test case

        Args:
            case_id: TestRail test case ID
            automation_id: Automation ID value to set

        Returns:
            Tuple of (success, error_message)
            - success: True if update succeeded, False otherwise
            - error_message: Empty string on success, error details on failure
        """
        self.environment.vlog(f"Setting automation_id '{automation_id}' on case {case_id}")

        update_data = {"custom_automation_id": automation_id}
        update_response = self.client.send_post(f"update_case/{case_id}", update_data)

        if update_response.status_code == 200:
            return True, ""
        else:
            error_msg = (
                update_response.error_message or f"Failed to update automation_id (HTTP {update_response.status_code})"
            )
            return False, error_msg
