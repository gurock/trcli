"""
RunHandler - Handles all test run-related operations for TestRail

It manages all test run operations including:
- Creating test runs
- Updating test runs
- Managing run references
- Closing and deleting runs
"""

from beartype.typing import List, Tuple, Dict

from trcli.api.api_client import APIClient
from trcli.api.api_utils import (
    deduplicate_references,
    join_references,
    merge_references,
    parse_references,
    validate_references_length,
)
from trcli.cli import Environment
from trcli.data_providers.api_data_provider import ApiDataProvider


class RunHandler:
    """Handles all test run-related operations for TestRail"""

    MAX_RUN_REFERENCES_LENGTH = 250  # TestRail character limit for run refs field

    def __init__(
        self,
        client: APIClient,
        environment: Environment,
        data_provider: ApiDataProvider,
        get_all_tests_in_run_callback,
    ):
        """
        Initialize the RunHandler

        :param client: APIClient instance for making API calls
        :param environment: Environment configuration
        :param data_provider: Data provider for run data
        :param get_all_tests_in_run_callback: Callback to fetch all tests in a run
        """
        self.client = client
        self.environment = environment
        self.data_provider = data_provider
        self.__get_all_tests_in_run = get_all_tests_in_run_callback

    def add_run(
        self,
        project_id: int,
        run_name: str,
        milestone_id: int = None,
        start_date: str = None,
        end_date: str = None,
        plan_id: int = None,
        config_ids: List[int] = None,
        assigned_to_id: int = None,
        include_all: bool = False,
        refs: str = None,
        case_ids: List[int] = None,
    ) -> Tuple[int, str]:
        """
        Creates a new test run.

        :param project_id: project_id
        :param run_name: run name
        :param milestone_id: milestone id
        :param start_date: start date
        :param end_date: end date
        :param plan_id: plan id (if adding to plan)
        :param config_ids: configuration ids
        :param assigned_to_id: user id to assign
        :param include_all: include all cases
        :param refs: references
        :param case_ids: specific case ids
        :returns: Tuple with run id and error string.
        """
        add_run_data = self.data_provider.add_run(
            run_name,
            case_ids=case_ids,
            start_date=start_date,
            end_date=end_date,
            milestone_id=milestone_id,
            assigned_to_id=assigned_to_id,
            include_all=include_all,
            refs=refs,
        )

        # Validate that we have test cases to include in the run
        # Empty runs are not allowed unless include_all is True
        if not include_all and (not add_run_data.get("case_ids") or len(add_run_data["case_ids"]) == 0):
            error_msg = (
                "Cannot create test run: No test cases were matched.\n"
                "  - For parse_junit: Ensure tests have automation_id/test ids that matches existing cases in TestRail\n"
                "  - For parse_cucumber: Ensure features have names or @C test id tag matching the existing BDD cases"
            )
            return None, error_msg

        if not plan_id:
            response = self.client.send_post(f"add_run/{project_id}", add_run_data)
            if response.error_message:
                return None, response.error_message
            run_id = response.response_text.get("id")
        else:
            if config_ids:
                add_run_data["config_ids"] = config_ids
                entry_data = {
                    "name": add_run_data["name"],
                    "suite_id": add_run_data["suite_id"],
                    "config_ids": config_ids,
                    "runs": [add_run_data],
                }
            else:
                entry_data = add_run_data
            response = self.client.send_post(f"add_plan_entry/{plan_id}", entry_data)
            if response.error_message:
                return None, response.error_message
            run_id = response.response_text["runs"][0]["id"]
        return run_id, response.error_message

    def update_run(
        self,
        run_id: int,
        run_name: str,
        start_date: str = None,
        end_date: str = None,
        milestone_id: int = None,
        refs: str = None,
        refs_action: str = "add",
    ) -> Tuple[dict, str]:
        """
        Updates an existing run

        :param run_id: run id
        :param run_name: run name
        :param start_date: start date
        :param end_date: end date
        :param milestone_id: milestone id
        :param refs: references to manage
        :param refs_action: action to perform ('add', 'update', 'delete')
        :returns: Tuple with run and error string.
        """
        run_response = self.client.send_get(f"get_run/{run_id}")
        if run_response.error_message:
            return None, run_response.error_message

        existing_description = run_response.response_text.get("description", "")
        existing_refs = run_response.response_text.get("refs", "")

        add_run_data = self.data_provider.add_run(
            run_name, start_date=start_date, end_date=end_date, milestone_id=milestone_id
        )
        add_run_data["description"] = existing_description  # Retain the current description

        # Handle references based on action
        if refs is not None:
            updated_refs = self._manage_references(existing_refs, refs, refs_action)
            add_run_data["refs"] = updated_refs
        else:
            add_run_data["refs"] = existing_refs  # Keep existing refs if none provided

        existing_include_all = run_response.response_text.get("include_all", False)
        add_run_data["include_all"] = existing_include_all

        if not existing_include_all:
            # Only manage explicit case_ids when include_all=False
            run_tests, error_message = self.__get_all_tests_in_run(run_id)
            if error_message:
                return None, f"Failed to get tests in run: {error_message}"
            run_case_ids = [test["case_id"] for test in run_tests]
            report_case_ids = add_run_data["case_ids"]
            joint_case_ids = list(set(report_case_ids + run_case_ids))
            add_run_data["case_ids"] = joint_case_ids
        else:
            # include_all=True: TestRail includes all suite cases automatically
            # Do NOT send case_ids array (TestRail ignores it anyway)
            add_run_data.pop("case_ids", None)

        plan_id = run_response.response_text["plan_id"]
        config_ids = run_response.response_text["config_ids"]
        if not plan_id:
            update_response = self.client.send_post(f"update_run/{run_id}", add_run_data)
        elif plan_id and config_ids:
            update_response = self.client.send_post(f"update_run_in_plan_entry/{run_id}", add_run_data)
        else:
            response = self.client.send_get(f"get_plan/{plan_id}")
            entry_id = next(
                (
                    run["entry_id"]
                    for entry in response.response_text["entries"]
                    for run in entry["runs"]
                    if run["id"] == run_id
                ),
                None,
            )
            update_response = self.client.send_post(f"update_plan_entry/{plan_id}/{entry_id}", add_run_data)
        run_response = self.client.send_get(f"get_run/{run_id}")
        return run_response.response_text, update_response.error_message

    def _manage_references(self, existing_refs: str, new_refs: str, action: str) -> str:
        """
        Manage references based on the specified action.

        :param existing_refs: current references in the run
        :param new_refs: new references to process
        :param action: 'add', 'update', or 'delete'
        :returns: updated references string
        """
        # Use shared utility function for reference management
        return merge_references(existing_refs or "", new_refs, strategy=action)

    def append_run_references(self, run_id: int, references: List[str]) -> Tuple[Dict, List[str], List[str], str]:
        """
        Append references to a test run, avoiding duplicates.

        :param run_id: ID of the test run
        :param references: List of references to append
        :returns: Tuple with (run_data, added_refs, skipped_refs, error_message)
        """
        # Get current run data
        run_response = self.client.send_get(f"get_run/{run_id}")
        if run_response.error_message:
            return None, [], [], run_response.error_message

        existing_refs = run_response.response_text.get("refs", "") or ""

        # Deduplicate input references using utility function
        deduplicated_input = deduplicate_references(references)

        # Parse existing references and calculate changes
        existing_list = parse_references(existing_refs)
        added_refs = [ref for ref in deduplicated_input if ref not in existing_list]
        skipped_refs = [ref for ref in deduplicated_input if ref in existing_list]

        # If no new references to add, return current state
        if not added_refs:
            return run_response.response_text, added_refs, skipped_refs, None

        # Combine references using utility function
        combined_refs = merge_references(existing_refs, join_references(deduplicated_input), strategy="add")

        # Validate character limit
        is_valid, error_msg = validate_references_length(combined_refs, self.MAX_RUN_REFERENCES_LENGTH)
        if not is_valid:
            return None, [], [], error_msg

        update_data = {"refs": combined_refs}

        # Determine the correct API endpoint based on plan membership
        plan_id = run_response.response_text.get("plan_id")
        config_ids = run_response.response_text.get("config_ids")

        if not plan_id:
            # Standalone run
            update_response = self.client.send_post(f"update_run/{run_id}", update_data)
        elif plan_id and config_ids:
            # Run in plan with configurations
            update_response = self.client.send_post(f"update_run_in_plan_entry/{run_id}", update_data)
        else:
            # Run in plan without configurations - need to use plan entry endpoint
            plan_response = self.client.send_get(f"get_plan/{plan_id}")
            if plan_response.error_message:
                return None, [], [], f"Failed to get plan details: {plan_response.error_message}"

            # Find the entry_id for this run
            entry_id = None
            for entry in plan_response.response_text.get("entries", []):
                for run in entry.get("runs", []):
                    if run["id"] == run_id:
                        entry_id = entry["id"]
                        break
                if entry_id:
                    break

            if not entry_id:
                return None, [], [], f"Could not find plan entry for run {run_id}"

            update_response = self.client.send_post(f"update_plan_entry/{plan_id}/{entry_id}", update_data)

        if update_response.error_message:
            return None, [], [], update_response.error_message

        updated_run_response = self.client.send_get(f"get_run/{run_id}")
        return updated_run_response.response_text, added_refs, skipped_refs, updated_run_response.error_message

    def close_run(self, run_id: int) -> Tuple[dict, str]:
        """
        Closes an existing test run and archives its tests & results.

        :param run_id: run id
        :returns: Tuple with dict created resources and error string.
        """
        body = {"run_id": run_id}
        response = self.client.send_post(f"close_run/{run_id}", body)
        return response.response_text, response.error_message

    def delete_run(self, run_id: int) -> Tuple[dict, str]:
        """
        Delete run given run id

        :param run_id: run id
        :returns: Tuple with dict created resources and error string.
        """
        response = self.client.send_post(f"delete_run/{run_id}", payload={})
        return response.response_text, response.error_message
