"""
LabelManager - Handles all label-related operations for TestRail

It manages all label operations including:
- Creating, retrieving, updating, and deleting labels
- Adding labels to test cases and tests
- Filtering cases and tests by labels
- Retrieving labels for specific tests
"""

from beartype.typing import List, Union, Tuple, Dict

from trcli.api.api_client import APIClient
from trcli.cli import Environment


class LabelManager:
    """Handles all label-related operations for TestRail"""

    MAX_LABELS_PER_ENTITY = 10  # TestRail limit
    MAX_LABEL_TITLE_LENGTH = 20  # TestRail limit

    def __init__(self, client: APIClient, environment: Environment):
        """
        Initialize the LabelManager

        :param client: APIClient instance for making API calls
        :param environment: Environment configuration
        """
        self.client = client
        self.environment = environment

    def add_label(self, project_id: int, title: str) -> Tuple[dict, str]:
        """
        Add a new label to the project

        :param project_id: ID of the project
        :param title: Title of the label (max 20 characters)
        :returns: Tuple with created label data and error string
        """
        payload = {"title": title}
        response = self.client.send_post(f"add_label/{project_id}", payload=payload)
        return response.response_text, response.error_message

    def update_label(self, label_id: int, project_id: int, title: str) -> Tuple[dict, str]:
        """
        Update an existing label

        :param label_id: ID of the label to update
        :param project_id: ID of the project
        :param title: New title for the label (max 20 characters)
        :returns: Tuple with updated label data and error string
        """
        payload = {"project_id": project_id, "title": title}
        response = self.client.send_post(f"update_label/{label_id}", payload=payload)
        return response.response_text, response.error_message

    def get_label(self, label_id: int) -> Tuple[dict, str]:
        """
        Get a specific label by ID

        :param label_id: ID of the label to retrieve
        :returns: Tuple with label data and error string
        """
        response = self.client.send_get(f"get_label/{label_id}")
        return response.response_text, response.error_message

    def get_labels(self, project_id: int, offset: int = 0, limit: int = 250) -> Tuple[dict, str]:
        """
        Get all labels for a project with pagination

        :param project_id: ID of the project
        :param offset: Offset for pagination
        :param limit: Limit for pagination
        :returns: Tuple with labels data (including pagination info) and error string
        """
        params = []
        if offset > 0:
            params.append(f"offset={offset}")
        if limit != 250:
            params.append(f"limit={limit}")

        url = f"get_labels/{project_id}"
        if params:
            url += "&" + "&".join(params)

        response = self.client.send_get(url)
        return response.response_text, response.error_message

    def delete_label(self, label_id: int) -> Tuple[bool, str]:
        """
        Delete a single label

        :param label_id: ID of the label to delete
        :returns: Tuple with success status and error string
        """
        response = self.client.send_post(f"delete_label/{label_id}")
        success = response.status_code == 200
        return success, response.error_message

    def delete_labels(self, label_ids: List[int]) -> Tuple[bool, str]:
        """
        Delete multiple labels

        :param label_ids: List of label IDs to delete
        :returns: Tuple with success status and error string
        """
        payload = {"label_ids": label_ids}
        response = self.client.send_post("delete_labels", payload=payload)
        success = response.status_code == 200
        return success, response.error_message

    def add_labels_to_cases(
        self,
        case_ids: List[int],
        title: str,
        project_id: int,
        suite_id: int = None,
        get_all_cases_callback=None,
    ) -> Tuple[dict, str]:
        """
        Add a label to multiple test cases

        :param case_ids: List of test case IDs
        :param title: Label title (max 20 characters)
        :param project_id: Project ID for validation
        :param suite_id: Suite ID (optional)
        :param get_all_cases_callback: Callback function to get all cases (injected dependency)
        :returns: Tuple with response data and error string
        """
        # Initialize results structure
        results = {"successful_cases": [], "failed_cases": [], "max_labels_reached": [], "case_not_found": []}

        # Check if project is multi-suite by getting all cases without suite_id
        all_cases_no_suite, error_message = get_all_cases_callback(project_id, None)
        if error_message:
            return results, error_message

        # Check if project has multiple suites
        suite_ids = set()
        for case in all_cases_no_suite:
            if "suite_id" in case and case["suite_id"]:
                suite_ids.add(case["suite_id"])

        # If project has multiple suites and no suite_id provided, require it
        if len(suite_ids) > 1 and suite_id is None:
            return results, "This project is multisuite, suite id is required"

        # Get all cases to validate that the provided case IDs exist
        all_cases, error_message = get_all_cases_callback(project_id, suite_id)
        if error_message:
            return results, error_message

        # Create a set of existing case IDs for quick lookup
        existing_case_ids = {case["id"] for case in all_cases}

        # Validate case IDs and separate valid from invalid ones
        invalid_case_ids = [case_id for case_id in case_ids if case_id not in existing_case_ids]
        valid_case_ids = [case_id for case_id in case_ids if case_id in existing_case_ids]

        # Record invalid case IDs
        for case_id in invalid_case_ids:
            results["case_not_found"].append(case_id)

        # If no valid case IDs, return early
        if not valid_case_ids:
            return results, ""

        # Check if label exists or create it
        existing_labels, error_message = self.get_labels(project_id)
        if error_message:
            return results, error_message

        # Find existing label with the same title
        label_id = None
        for label in existing_labels.get("labels", []):
            if label.get("title") == title:
                label_id = label.get("id")
                break

        # Create label if it doesn't exist
        if label_id is None:
            label_data, error_message = self.add_label(project_id, title)
            if error_message:
                return results, error_message
            label_info = label_data.get("label", label_data)
            label_id = label_info.get("id")

        # Collect case data and validate constraints
        cases_to_update = []
        for case_id in valid_case_ids:
            # Get current case to check existing labels
            case_response = self.client.send_get(f"get_case/{case_id}")
            if case_response.status_code != 200:
                results["failed_cases"].append(
                    {"case_id": case_id, "error": f"Could not retrieve case {case_id}: {case_response.error_message}"}
                )
                continue

            case_data = case_response.response_text
            current_labels = case_data.get("labels", [])

            # Check if label already exists on this case
            if any(label.get("id") == label_id for label in current_labels):
                results["successful_cases"].append(
                    {"case_id": case_id, "message": f"Label '{title}' already exists on case {case_id}"}
                )
                continue

            # Check maximum labels limit
            if len(current_labels) >= self.MAX_LABELS_PER_ENTITY:
                results["max_labels_reached"].append(case_id)
                continue

            # Prepare case for update
            existing_label_ids = [label.get("id") for label in current_labels if label.get("id")]
            updated_label_ids = existing_label_ids + [label_id]
            cases_to_update.append({"case_id": case_id, "labels": updated_label_ids})

        # Update cases using appropriate endpoint
        if len(cases_to_update) == 1:
            # Single case: use update_case/{case_id}
            case_info = cases_to_update[0]
            case_update_data = {"labels": case_info["labels"]}

            update_response = self.client.send_post(f"update_case/{case_info['case_id']}", payload=case_update_data)

            if update_response.status_code == 200:
                results["successful_cases"].append(
                    {
                        "case_id": case_info["case_id"],
                        "message": f"Successfully added label '{title}' to case {case_info['case_id']}",
                    }
                )
            else:
                results["failed_cases"].append(
                    {"case_id": case_info["case_id"], "error": update_response.error_message}
                )
        elif len(cases_to_update) > 1:
            # Multiple cases: use update_cases/{suite_id}
            # Need to determine suite_id from the cases
            case_suite_id = suite_id
            if not case_suite_id:
                # Get suite_id from the first case if not provided
                first_case = all_cases[0] if all_cases else None
                case_suite_id = first_case.get("suite_id") if first_case else None

            if not case_suite_id:
                # Fall back to individual updates if no suite_id available
                for case_info in cases_to_update:
                    case_update_data = {"labels": case_info["labels"]}
                    update_response = self.client.send_post(
                        f"update_case/{case_info['case_id']}", payload=case_update_data
                    )

                    if update_response.status_code == 200:
                        results["successful_cases"].append(
                            {
                                "case_id": case_info["case_id"],
                                "message": f"Successfully added label '{title}' to case {case_info['case_id']}",
                            }
                        )
                    else:
                        results["failed_cases"].append(
                            {"case_id": case_info["case_id"], "error": update_response.error_message}
                        )
            else:
                # Batch update using update_cases/{suite_id}
                batch_update_data = {
                    "case_ids": [case_info["case_id"] for case_info in cases_to_update],
                    "labels": cases_to_update[0]["labels"],  # Assuming same labels for all cases
                }

                batch_response = self.client.send_post(f"update_cases/{case_suite_id}", payload=batch_update_data)

                if batch_response.status_code == 200:
                    for case_info in cases_to_update:
                        results["successful_cases"].append(
                            {
                                "case_id": case_info["case_id"],
                                "message": f"Successfully added label '{title}' to case {case_info['case_id']}",
                            }
                        )
                else:
                    # If batch update fails, fall back to individual updates
                    for case_info in cases_to_update:
                        case_update_data = {"labels": case_info["labels"]}
                        update_response = self.client.send_post(
                            f"update_case/{case_info['case_id']}", payload=case_update_data
                        )

                        if update_response.status_code == 200:
                            results["successful_cases"].append(
                                {
                                    "case_id": case_info["case_id"],
                                    "message": f"Successfully added label '{title}' to case {case_info['case_id']}",
                                }
                            )
                        else:
                            results["failed_cases"].append(
                                {"case_id": case_info["case_id"], "error": update_response.error_message}
                            )

        return results, ""

    def get_cases_by_label(
        self,
        project_id: int,
        suite_id: int = None,
        label_ids: List[int] = None,
        label_title: str = None,
        get_all_cases_callback=None,
    ) -> Tuple[List[dict], str]:
        """
        Get test cases filtered by label ID or title

        :param project_id: Project ID
        :param suite_id: Suite ID (optional)
        :param label_ids: List of label IDs to filter by
        :param label_title: Label title to filter by
        :param get_all_cases_callback: Callback function to get all cases (injected dependency)
        :returns: Tuple with list of matching cases and error string
        """
        # Get all cases first
        all_cases, error_message = get_all_cases_callback(project_id, suite_id)
        if error_message:
            return [], error_message

        # If filtering by title, first get the label ID
        target_label_ids = label_ids or []
        if label_title and not target_label_ids:
            labels_data, error_message = self.get_labels(project_id)
            if error_message:
                return [], error_message

            for label in labels_data.get("labels", []):
                if label.get("title") == label_title:
                    target_label_ids.append(label.get("id"))

            if not target_label_ids:
                return [], ""  # No label found is a valid case with 0 results

        # Filter cases that have any of the target labels
        matching_cases = []
        for case in all_cases:
            case_labels = case.get("labels", [])
            case_label_ids = [label.get("id") for label in case_labels]

            # Check if any of the target label IDs are present in this case
            if any(label_id in case_label_ids for label_id in target_label_ids):
                matching_cases.append(case)

        return matching_cases, ""

    def add_labels_to_tests(
        self, test_ids: List[int], titles: Union[str, List[str]], project_id: int
    ) -> Tuple[dict, str]:
        """
        Add labels to multiple tests

        :param test_ids: List of test IDs
        :param titles: Label title(s) - can be a single string or list of strings (max 20 characters each)
        :param project_id: Project ID for validation
        :returns: Tuple with response data and error string
        """
        # Initialize results structure
        results = {"successful_tests": [], "failed_tests": [], "max_labels_reached": [], "test_not_found": []}

        # Normalize titles to a list
        if isinstance(titles, str):
            title_list = [titles]
        else:
            title_list = titles

        # At this point, title_list should already be validated by the CLI
        # Just ensure we have clean titles
        title_list = [title.strip() for title in title_list if title.strip()]

        if not title_list:
            return {}, "No valid labels provided"

        # Validate test IDs by getting run information for each test
        valid_test_ids = []
        for test_id in test_ids:
            # Get test information to validate it exists
            test_response = self.client.send_get(f"get_test/{test_id}")
            if test_response.status_code != 200:
                results["test_not_found"].append(test_id)
                continue

            test_data = test_response.response_text
            # Validate that the test belongs to the correct project
            run_id = test_data.get("run_id")
            if run_id:
                run_response = self.client.send_get(f"get_run/{run_id}")
                if run_response.status_code == 200:
                    run_data = run_response.response_text
                    if run_data.get("project_id") == project_id:
                        valid_test_ids.append(test_id)
                    else:
                        results["test_not_found"].append(test_id)
                else:
                    results["test_not_found"].append(test_id)
            else:
                results["test_not_found"].append(test_id)

        # If no valid test IDs, return early
        if not valid_test_ids:
            return results, ""

        # Check if labels exist or create them
        existing_labels, error_message = self.get_labels(project_id)
        if error_message:
            return results, error_message

        # Process each title to get/create label IDs
        label_ids = []
        label_id_to_title = {}  # Map label IDs to their titles
        for title in title_list:
            # Find existing label with the same title
            label_id = None
            for label in existing_labels.get("labels", []):
                if label.get("title") == title:
                    label_id = label.get("id")
                    break

            # Create label if it doesn't exist
            if label_id is None:
                label_data, error_message = self.add_label(project_id, title)
                if error_message:
                    return results, error_message
                label_info = label_data.get("label", label_data)
                label_id = label_info.get("id")

            if label_id:
                label_ids.append(label_id)
                label_id_to_title[label_id] = title

        # Collect test data and validate constraints
        tests_to_update = []
        for test_id in valid_test_ids:
            # Get current test to check existing labels
            test_response = self.client.send_get(f"get_test/{test_id}")
            if test_response.status_code != 200:
                results["failed_tests"].append(
                    {"test_id": test_id, "error": f"Could not retrieve test {test_id}: {test_response.error_message}"}
                )
                continue

            test_data = test_response.response_text
            current_labels = test_data.get("labels", [])
            current_label_ids = [label.get("id") for label in current_labels if label.get("id")]

            new_label_ids = []
            already_exists_titles = []

            for label_id in label_ids:
                if label_id not in current_label_ids:
                    new_label_ids.append(label_id)
                else:
                    if label_id in label_id_to_title:
                        already_exists_titles.append(label_id_to_title[label_id])

            if not new_label_ids:
                results["successful_tests"].append(
                    {
                        "test_id": test_id,
                        "message": f"All labels already exist on test {test_id}: {', '.join(already_exists_titles)}",
                    }
                )
                continue

            # Check maximum labels limit
            if len(current_label_ids) + len(new_label_ids) > self.MAX_LABELS_PER_ENTITY:
                results["max_labels_reached"].append(test_id)
                continue

            # Prepare test for update
            updated_label_ids = current_label_ids + new_label_ids

            new_label_titles = []
            for label_id in new_label_ids:
                if label_id in label_id_to_title:
                    new_label_titles.append(label_id_to_title[label_id])

            tests_to_update.append(
                {
                    "test_id": test_id,
                    "labels": updated_label_ids,
                    "new_labels": new_label_ids,
                    "new_label_titles": new_label_titles,
                }
            )

        # Update tests using appropriate endpoint
        if len(tests_to_update) == 1:
            # Single test: use update_test/{test_id}
            test_info = tests_to_update[0]
            test_update_data = {"labels": test_info["labels"]}

            update_response = self.client.send_post(f"update_test/{test_info['test_id']}", payload=test_update_data)

            if update_response.status_code == 200:
                new_label_titles = test_info.get("new_label_titles", [])
                new_label_count = len(new_label_titles)

                if new_label_count == 1:
                    message = f"Successfully added label '{new_label_titles[0]}' to test {test_info['test_id']}"
                elif new_label_count > 1:
                    message = f"Successfully added {new_label_count} labels ({', '.join(new_label_titles)}) to test {test_info['test_id']}"
                else:
                    message = f"No new labels added to test {test_info['test_id']}"

                results["successful_tests"].append({"test_id": test_info["test_id"], "message": message})
            else:
                results["failed_tests"].append(
                    {"test_id": test_info["test_id"], "error": update_response.error_message}
                )
        else:
            # Multiple tests: use individual updates to ensure each test gets its specific labels
            for test_info in tests_to_update:
                test_update_data = {"labels": test_info["labels"]}
                update_response = self.client.send_post(f"update_test/{test_info['test_id']}", payload=test_update_data)

                if update_response.status_code == 200:
                    new_label_titles = test_info.get("new_label_titles", [])
                    new_label_count = len(new_label_titles)

                    if new_label_count == 1:
                        message = f"Successfully added label '{new_label_titles[0]}' to test {test_info['test_id']}"
                    elif new_label_count > 1:
                        message = f"Successfully added {new_label_count} labels ({', '.join(new_label_titles)}) to test {test_info['test_id']}"
                    else:
                        message = f"No new labels added to test {test_info['test_id']}"

                    results["successful_tests"].append({"test_id": test_info["test_id"], "message": message})
                else:
                    results["failed_tests"].append(
                        {"test_id": test_info["test_id"], "error": update_response.error_message}
                    )

        return results, ""

    def get_tests_by_label(
        self, project_id: int, label_ids: List[int] = None, label_title: str = None, run_ids: List[int] = None
    ) -> Tuple[List[dict], str]:
        """
        Get tests filtered by label ID or title from specific runs

        :param project_id: Project ID
        :param label_ids: List of label IDs to filter by
        :param label_title: Label title to filter by
        :param run_ids: List of run IDs to filter tests from (optional, defaults to all runs)
        :returns: Tuple with list of matching tests and error string
        """
        # If filtering by title, first get the label ID
        target_label_ids = label_ids or []
        if label_title and not target_label_ids:
            labels_data, error_message = self.get_labels(project_id)
            if error_message:
                return [], error_message

            for label in labels_data.get("labels", []):
                if label.get("title") == label_title:
                    target_label_ids.append(label.get("id"))

            if not target_label_ids:
                return [], ""  # No label found is a valid case with 0 results

        # Get runs for the project (either all runs or specific run IDs)
        if run_ids:
            # Use specific run IDs - validate they exist by getting run details
            runs = []
            for run_id in run_ids:
                run_response = self.client.send_get(f"get_run/{run_id}")
                if run_response.status_code == 200:
                    runs.append(run_response.response_text)
                else:
                    return [], f"Run ID {run_id} not found or inaccessible"
        else:
            # Get all runs for the project
            runs_response = self.client.send_get(f"get_runs/{project_id}")
            if runs_response.status_code != 200:
                return [], runs_response.error_message

            runs_data = runs_response.response_text
            runs = runs_data.get("runs", []) if isinstance(runs_data, dict) else runs_data

        # Collect all tests from all runs
        matching_tests = []
        for run in runs:
            run_id = run.get("id")
            if not run_id:
                continue

            # Get tests for this run
            tests_response = self.client.send_get(f"get_tests/{run_id}")
            if tests_response.status_code != 200:
                continue  # Skip this run if we can't get tests

            tests_data = tests_response.response_text
            tests = tests_data.get("tests", []) if isinstance(tests_data, dict) else tests_data

            # Filter tests that have any of the target labels
            for test in tests:
                test_labels = test.get("labels", [])
                test_label_ids = [label.get("id") for label in test_labels]

                # Check if any of the target label IDs are present in this test
                if any(label_id in test_label_ids for label_id in target_label_ids):
                    matching_tests.append(test)

        return matching_tests, ""

    def get_test_labels(self, test_ids: List[int]) -> Tuple[List[dict], str]:
        """
        Get labels for specific tests

        :param test_ids: List of test IDs to get labels for
        :returns: Tuple with list of test label information and error string
        """
        results = []

        for test_id in test_ids:
            # Get test information
            test_response = self.client.send_get(f"get_test/{test_id}")
            if test_response.status_code != 200:
                results.append({"test_id": test_id, "error": f"Test {test_id} not found or inaccessible", "labels": []})
                continue

            test_data = test_response.response_text
            test_labels = test_data.get("labels", [])

            results.append(
                {
                    "test_id": test_id,
                    "title": test_data.get("title", "Unknown"),
                    "status_id": test_data.get("status_id"),
                    "labels": test_labels,
                    "error": None,
                }
            )

        return results, ""
