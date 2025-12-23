"""
ReferenceManager - Handles all reference-related operations for TestRail test cases

It manages all reference operations including:
- Adding references to test cases
- Updating references on test cases
- Deleting references from test cases
"""

from beartype.typing import List, Tuple, Optional

from trcli.api.api_client import APIClient
from trcli.api.api_utils import (
    deduplicate_references,
    join_references,
    merge_references,
    validate_references_length,
    check_response_error,
)
from trcli.cli import Environment


class ReferenceManager:
    """Handles all reference-related operations for TestRail test cases"""

    MAX_REFERENCES_LENGTH = 2000  # TestRail character limit for refs field

    def __init__(self, client: APIClient, environment: Environment):
        """
        Initialize the ReferenceManager

        :param client: APIClient instance for making API calls
        :param environment: Environment configuration
        """
        self.client = client
        self.environment = environment

    def add_case_references(self, case_id: int, references: List[str]) -> Tuple[bool, str]:
        """
        Add references to a test case (appends to existing references)

        :param case_id: ID of the test case
        :param references: List of references to add
        :returns: Tuple with success status and error string
        """
        # Get current test case to retrieve existing references
        case_response = self.client.send_get(f"get_case/{case_id}")
        if case_response.status_code != 200:
            error = check_response_error(case_response)
            return False, (
                f"Failed to retrieve test case {case_id}: {error}"
                if error
                else f"Failed to retrieve test case {case_id}"
            )

        existing_refs = case_response.response_text.get("refs", "") or ""

        # Deduplicate and merge with existing references
        deduplicated_input = deduplicate_references(references)
        new_refs_string = merge_references(existing_refs, join_references(deduplicated_input), strategy="add")

        # Validate total character limit
        is_valid, error_msg = validate_references_length(new_refs_string, self.MAX_REFERENCES_LENGTH)
        if not is_valid:
            return False, error_msg

        # Update the test case with new references
        update_response = self.client.send_post(f"update_case/{case_id}", {"refs": new_refs_string})

        if update_response.status_code == 200:
            return True, ""
        return False, update_response.error_message or "Failed to update references"

    def update_case_references(self, case_id: int, references: List[str]) -> Tuple[bool, str]:
        """
        Update references on a test case by replacing existing ones

        :param case_id: ID of the test case
        :param references: List of references to replace existing ones
        :returns: Tuple with success status and error string
        """
        # Deduplicate and join references
        deduplicated_refs = deduplicate_references(references)
        new_refs_string = join_references(deduplicated_refs)

        # Validate total character limit
        is_valid, error_msg = validate_references_length(new_refs_string, self.MAX_REFERENCES_LENGTH)
        if not is_valid:
            return False, error_msg

        # Update the test case with new references
        update_response = self.client.send_post(f"update_case/{case_id}", {"refs": new_refs_string})

        if update_response.status_code == 200:
            return True, ""
        return False, update_response.error_message or "Failed to update references"

    def delete_case_references(self, case_id: int, specific_references: Optional[List[str]] = None) -> Tuple[bool, str]:
        """
        Delete all or specific references from a test case

        :param case_id: ID of the test case
        :param specific_references: List of specific references to delete (None to delete all)
        :returns: Tuple with success status and error string
        """
        if specific_references is None:
            # Delete all references by setting refs to empty string
            new_refs_string = ""
        else:
            # Get current test case to retrieve existing references
            case_response = self.client.send_get(f"get_case/{case_id}")
            if case_response.status_code != 200:
                error = check_response_error(case_response)
                return False, (
                    f"Failed to retrieve test case {case_id}: {error}"
                    if error
                    else f"Failed to retrieve test case {case_id}"
                )

            existing_refs = case_response.response_text.get("refs", "") or ""

            if not existing_refs:
                # No references to delete
                return True, ""

            # Use utility to delete specific references
            new_refs_string = merge_references(existing_refs, join_references(specific_references), strategy="delete")

        # Update the test case
        update_response = self.client.send_post(f"update_case/{case_id}", {"refs": new_refs_string})

        if update_response.status_code == 200:
            return True, ""
        return False, update_response.error_message or "Failed to delete references"
