"""
PlanHandler - Handles all plan-related operations for TestRail

It manages all plan operations including:
- Retrieving individual plans
- Listing plans with pagination
- Creating new plans
- Validating dynamic filters in plan entries
"""

from beartype.typing import Tuple, Optional, Dict, Any, List

from trcli.api.api_client import APIClient
from trcli.cli import Environment
from trcli.api.dynamic_filters_utils import load_dynamic_filters_from_file, validate_dynamic_filters_structure


class PlanHandler:
    """Handles all plan-related operations for TestRail"""

    def __init__(
        self,
        client: APIClient,
        environment: Environment,
    ):
        """
        Initialize the PlanHandler

        :param client: APIClient instance for making API calls
        :param environment: Environment configuration
        """
        self.client = client
        self.environment = environment

    def get_plan(self, plan_id: int) -> Tuple[dict, str]:
        """
        Retrieve a single test plan by ID

        :param plan_id: TestRail plan ID
        :returns: Tuple with (plan_data_dict, error_message)
        """
        response = self.client.send_get(f"get_plan/{plan_id}")
        if response.error_message:
            return {}, response.error_message
        return response.response_text, ""

    def get_plans(
        self,
        project_id: int,
        limit: int = 250,
        offset: int = 0,
    ) -> Tuple[dict, str]:
        """
        Retrieve test plans for a project with pagination

        :param project_id: TestRail project ID
        :param limit: Maximum number of plans to return (default: 250)
        :param offset: Offset for pagination (default: 0)
        :returns: Tuple with (paginated_response_dict, error_message)
                  Response dict contains: plans, offset, limit, size, _links
        """
        # Build query parameters
        params = []
        if limit != 250:
            params.append(f"limit={limit}")
        if offset > 0:
            params.append(f"offset={offset}")

        # Build URL
        query_string = "&".join(params) if params else ""
        url = f"get_plans/{project_id}"
        if query_string:
            url = f"{url}&{query_string}"

        response = self.client.send_get(url)
        if response.error_message:
            return {}, response.error_message
        return response.response_text, ""

    def add_plan(
        self,
        project_id: int,
        name: str,
        description: Optional[str] = None,
        milestone_id: Optional[int] = None,
        entries: Optional[list] = None,
        start_on: Optional[int] = None,
        due_on: Optional[int] = None,
    ) -> Tuple[Dict[str, Any], str]:
        """
        Create a new test plan

        TestRail's add_plan API doesn't support dynamic_filters in entries during plan creation.
        If entries contain dynamic_filters, we:
        1. Create the plan without those entries
        2. Add each entry with dynamic_filters using add_plan_entry endpoint

        :param project_id: TestRail project ID
        :param name: Name of the test plan (required)
        :param description: Description of the test plan
        :param milestone_id: ID of the milestone to link to the plan
        :param entries: Array of test run entries (see add_plan API documentation)
        :param start_on: Start date as UNIX timestamp
        :param due_on: Due date as UNIX timestamp
        :returns: Tuple with (created_plan_dict, error_message)
        """
        # Separate entries with dynamic_filters from regular entries
        regular_entries = []
        dynamic_entries = []

        if entries:
            for entry in entries:
                # Flat format: dynamic_filters directly on the entry (no "runs" array)
                has_dynamic_filters = "dynamic_filters" in entry
                if not has_dynamic_filters and "runs" in entry:
                    for run in entry["runs"]:
                        if "dynamic_filters" in run:
                            has_dynamic_filters = True
                            break

                if has_dynamic_filters:
                    dynamic_entries.append(entry)
                else:
                    regular_entries.append(entry)

        # Create plan with regular entries only
        payload = {"name": name}

        if description is not None:
            payload["description"] = description
        if milestone_id is not None:
            payload["milestone_id"] = milestone_id
        if regular_entries:
            payload["entries"] = regular_entries
        if start_on is not None:
            payload["start_on"] = start_on
        if due_on is not None:
            payload["due_on"] = due_on

        response = self.client.send_post(f"add_plan/{project_id}", payload)
        if response.error_message:
            return {}, response.error_message

        plan_data = response.response_text
        plan_id = plan_data.get("id")

        # Add entries with dynamic_filters using add_plan_entry
        if dynamic_entries and plan_id:
            for entry in dynamic_entries:
                # Check if entry or any run has config_ids (multi-config format)
                has_config_ids = "config_ids" in entry and entry["config_ids"]
                if not has_config_ids and "runs" in entry:
                    # Check if any run has config_ids
                    for run in entry["runs"]:
                        if "config_ids" in run and run["config_ids"]:
                            has_config_ids = True
                            break

                # For entries with runs array but no config_ids, flatten to single run format
                if "runs" in entry and not has_config_ids and len(entry["runs"]) == 1:
                    # Single run without configs - use flat format like add_run does (line 127 in run_handler.py)
                    run = entry["runs"][0]
                    entry_payload = {
                        "suite_id": entry["suite_id"],
                        "name": entry.get("name", "Test Run"),
                    }
                    # Copy run fields to entry level
                    if "dynamic_filters" in run:
                        entry_payload["dynamic_filters"] = run["dynamic_filters"]
                        # add_plan_entry requires include_all field even with dynamic_filters
                        entry_payload["include_all"] = False
                    if "description" in entry:
                        entry_payload["description"] = entry["description"]
                else:
                    # Multi-config format or multiple runs - use runs array
                    # According to TestRail API docs, dynamic_filters should be at ENTRY level, not in runs array
                    if "runs" in entry and len(entry["runs"]) == 1:
                        run = entry["runs"][0]
                        if "config_ids" in run:
                            # Move config_ids and dynamic_filters to entry level (per TestRail API spec)
                            entry_payload = {
                                "suite_id": entry["suite_id"],
                                "name": entry.get("name", "Test Run"),
                                "config_ids": run["config_ids"],
                                "include_all": False,
                            }
                            # Move dynamic_filters to entry level (not in runs array)
                            if "dynamic_filters" in run:
                                entry_payload["dynamic_filters"] = run["dynamic_filters"]
                            if "description" in entry:
                                entry_payload["description"] = entry["description"]

                            # Create runs array
                            entry_payload["runs"] = [{"config_ids": run["config_ids"]}]
                        else:
                            entry_payload = entry
                            # For runs array format without config_ids, ensure include_all is set in runs
                            if "runs" in entry_payload:
                                for r in entry_payload["runs"]:
                                    if "dynamic_filters" in r and "include_all" not in r:
                                        r["include_all"] = False
                    else:
                        entry_payload = entry
                        # For runs array format without config_ids, ensure include_all is set in runs
                        if "runs" in entry_payload:
                            for run in entry_payload["runs"]:
                                if "dynamic_filters" in run and "include_all" not in run:
                                    run["include_all"] = False

                entry_response = self.client.send_post(f"add_plan_entry/{plan_id}", entry_payload)
                if entry_response.error_message:
                    # Provide more helpful error message for common issues
                    error_msg = entry_response.error_message
                    if "case_ids needs to include at least one test case" in error_msg:
                        entry_name = entry.get("name", "Unnamed entry")
                        return {}, (
                            f"Plan created (ID: {plan_id}) but failed to add entry '{entry_name}': "
                            f"Dynamic filters matched zero test cases. "
                            f"Please verify that:\n"
                            f"  - The suite contains test cases\n"
                            f"  - The filter criteria matches at least one test case\n"
                            f"  - All field names exist in the suite (e.g., 'cases:is_automated')\n"
                            f"Original error: {error_msg}"
                        )
                    return {}, f"Plan created (ID: {plan_id}) but failed to add entry with dynamic_filters: {error_msg}"

                # Add the created entry to plan_data for return
                if "entries" not in plan_data:
                    plan_data["entries"] = []
                plan_data["entries"].append(entry_response.response_text)

        return plan_data, ""

    def validate_and_process_plan_entries(
        self, entries: List[Dict[str, Any]], cli_mode: Optional[str] = None
    ) -> Tuple[List[Dict[str, Any]], str]:
        """
        Validate and process plan entries with dynamic filters support.

        This method:
        1. Validates dynamic_filters structure in each run or entry
        2. Checks mutual exclusivity (filters vs case_ids/include_all)
        3. Auto-wraps simplified filter format
        4. Removes internal _mode_from_json flag
        5. Applies CLI mode override if specified (CLI > JSON precedence)
        6. Ensures default mode "1" is added when not specified
        7. Supports flat entry format (dynamic_filters at entry level without runs array)

        :param entries: List of plan entry dictionaries
        :param cli_mode: Optional CLI mode parameter ("1" or "2") to override JSON mode for all runs
        :returns: Tuple with (processed_entries, error_message)
        """
        if not entries:
            return entries, ""

        processed_entries = []

        for entry_idx, entry in enumerate(entries):
            entry_name = entry.get("name", f"Entry {entry_idx + 1}")

            if "dynamic_filters" in entry:
                entry_label = f"Entry '{entry_name}'"
                dynamic_filters = entry["dynamic_filters"]

                if "case_ids" in entry and entry["case_ids"]:
                    return (
                        [],
                        f"{entry_label}: dynamic_filters and case_ids cannot be used together. Choose one case selection method.",
                    )

                # Validation: Mutual exclusivity with include_all=true
                if entry.get("include_all") is True:
                    return (
                        [],
                        f"{entry_label}: dynamic_filters and include_all=true cannot be used together. Set include_all=false or omit it when using dynamic filters.",
                    )

                # Track if mode was explicitly provided in the JSON
                mode_was_in_json = "mode" in dynamic_filters

                if "filters" not in dynamic_filters:
                    dynamic_filters = {"mode": "1", "filters": dynamic_filters}
                    mode_was_in_json = False

                if cli_mode and not mode_was_in_json:
                    dynamic_filters["mode"] = cli_mode
                elif "mode" not in dynamic_filters:
                    # Ensure default mode "1" is set if not specified anywhere
                    dynamic_filters["mode"] = "1"

                is_valid, error = validate_dynamic_filters_structure(dynamic_filters)
                if not is_valid:
                    return [], f"{entry_label}: {error}"

                if "_mode_from_json" in dynamic_filters:
                    del dynamic_filters["_mode_from_json"]

                entry["dynamic_filters"] = dynamic_filters

                if "include_all" not in entry:
                    entry["include_all"] = False

                processed_entries.append(entry)
                continue

            runs = entry.get("runs", [])

            if not runs:
                # No runs and no entry-level dynamic_filters, just pass through
                processed_entries.append(entry)
                continue

            processed_runs = []

            for run_idx, run in enumerate(runs):
                run_label = f"Entry '{entry_name}', Run {run_idx + 1}"

                # Check if run has dynamic_filters
                if "dynamic_filters" in run:
                    dynamic_filters = run["dynamic_filters"]

                    # Validation: Mutual exclusivity with case_ids
                    if "case_ids" in run and run["case_ids"]:
                        return (
                            [],
                            f"{run_label}: dynamic_filters and case_ids cannot be used together. Choose one case selection method.",
                        )

                    # Validation: Mutual exclusivity with include_all=true
                    if run.get("include_all") is True:
                        return (
                            [],
                            f"{run_label}: dynamic_filters and include_all=true cannot be used together. Set include_all=false or omit it when using dynamic filters.",
                        )

                    # Track if mode was explicitly provided in the JSON
                    mode_was_in_json = "mode" in dynamic_filters

                    # Normalize: if simplified format (no "filters" wrapper), wrap it
                    if "filters" not in dynamic_filters:
                        dynamic_filters = {"mode": "1", "filters": dynamic_filters}
                        # Simplified format means no mode in JSON
                        mode_was_in_json = False

                    # Apply CLI mode override if specified (CLI > JSON precedence)
                    # Only override if mode was NOT explicitly set in JSON
                    if cli_mode and not mode_was_in_json:
                        # No explicit mode in JSON, apply CLI mode
                        dynamic_filters["mode"] = cli_mode
                    elif "mode" not in dynamic_filters:
                        # Ensure default mode "1" is set if not specified anywhere
                        dynamic_filters["mode"] = "1"

                    # Validate filter structure
                    is_valid, error = validate_dynamic_filters_structure(dynamic_filters)
                    if not is_valid:
                        return [], f"{run_label}: {error}"

                    # Remove internal flag if present
                    if "_mode_from_json" in dynamic_filters:
                        del dynamic_filters["_mode_from_json"]

                    # Update run with processed filters
                    run["dynamic_filters"] = dynamic_filters

                    # Ensure include_all is false when using dynamic_filters (required by add_plan_entry API)
                    if "include_all" not in run:
                        run["include_all"] = False

                processed_runs.append(run)

            # Update entry with processed runs
            entry["runs"] = processed_runs
            processed_entries.append(entry)

        return processed_entries, ""
