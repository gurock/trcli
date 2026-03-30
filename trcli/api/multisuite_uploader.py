"""
MultisuiteUploader - Handles cross-suite test plan creation and result uploads

This module provides functionality to upload JUnit test results across multiple
TestRail suites in a single test plan. It fetches suite information for each case,
groups cases by suite, creates a test plan with one run per suite, and uploads
results to the appropriate runs.
"""

import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from collections import defaultdict
from beartype.typing import Dict, List, Tuple, Set

from trcli.api.project_based_client import ProjectBasedClient
from trcli.cli import Environment
from trcli.constants import FAULT_MAPPING
from trcli.data_classes.dataclass_testrail import TestRailSuite, TestRailCase


class MultisuiteUploader(ProjectBasedClient):
    """
    Handles uploading test results across multiple TestRail suites.

    Creates a test plan with one run per suite and uploads results accordingly.
    Requires that all test cases have case IDs (strict validation).
    """

    def __init__(self, environment: Environment, suite: TestRailSuite):
        """
        Initialize the MultisuiteUploader

        :param environment: Environment configuration
        :param suite: TestRailSuite containing all test cases from the report
        """
        super().__init__(environment, suite)
        self.last_plan_id = None
        self.last_run_ids = {}  # {suite_id: run_id}

    def upload_results(self):
        """
        Main orchestration method for multisuite upload.

        Flow:
        1. Validate all cases have IDs
        2. Fetch suite_id for each case
        3. Validate single project
        4. Group cases by suite_id
        5. Create or update test plan
        6. Upload results per run
        7. Upload attachments
        """
        start = time.time()

        self.environment.log("Multisuite mode: Preparing cross-suite test plan...")

        # Step 1: Resolve project
        self.resolve_project()

        # Step 2: Collect all case IDs and validate they exist
        all_case_ids = self._collect_all_case_ids()
        if not all_case_ids:
            self.environment.elog("No test cases with case IDs found in the report.")
            exit(1)

        self.environment.log(f"Found {len(all_case_ids)} unique case ID(s) in report.")

        # Step 3: Fetch suite_id for each case (concurrent for performance)
        self.environment.log("Fetching suite information for all cases...")
        case_suite_mapping = self._fetch_suite_ids_for_cases(all_case_ids)

        if not case_suite_mapping:
            self.environment.elog("Failed to fetch suite information for any cases.")
            exit(1)

        # Step 4: Validate single project and filter cross-project cases
        valid_case_suite_mapping, skipped_count = self._validate_single_project(case_suite_mapping)

        if skipped_count > 0:
            self.environment.log(f"Filtered out {skipped_count} cross-project case(s).")

        if not valid_case_suite_mapping:
            self.environment.elog("No valid cases remaining after project validation.")
            exit(1)

        # Step 5: Group cases by suite
        suite_groups = self._group_cases_by_suite(valid_case_suite_mapping)
        self.environment.log(f"Grouped cases into {len(suite_groups)} suite(s).")

        # Step 6: Create or update test plan
        if self.environment.plan_id:
            # Existing plan mode - add runs to existing plan
            run_mapping, error = self._update_existing_plan(self.environment.plan_id, suite_groups)
            plan_id = self.environment.plan_id
        else:
            # New plan mode - create new plan with runs
            plan_id, run_mapping, error = self._create_test_plan(suite_groups)

        if error:
            self.environment.elog(FAULT_MAPPING["multisuite_plan_creation_failed"].format(error_message=error))
            exit(1)

        self.last_plan_id = plan_id
        self.last_run_ids = run_mapping

        self.environment.log(f"Test plan created/updated (ID: {plan_id}) with {len(run_mapping)} run(s).")

        # Step 7: Upload results per run
        total_results = self._upload_results_per_run(suite_groups, run_mapping)

        stop = time.time()
        self.environment.log(
            f"Uploaded {total_results} result(s) across {len(run_mapping)} run(s) in {stop - start:.1f} secs."
        )

    def _collect_all_case_ids(self) -> Set[int]:
        """
        Collect all unique case IDs from the test suite.
        Validates that ALL cases have case IDs (strict mode).

        :returns: Set of case IDs
        :raises: SystemExit if any case lacks a case ID
        """
        case_ids = set()
        missing_id_count = 0

        for section in self.api_request_handler.suites_data_from_provider.testsections:
            for test_case in section.testcases:
                if test_case.case_id is None or test_case.case_id == 0:
                    missing_id_count += 1
                else:
                    case_ids.add(test_case.case_id)

        if missing_id_count > 0:
            self.environment.elog(FAULT_MAPPING["multisuite_missing_case_ids"].format(count=missing_id_count))
            exit(1)

        return case_ids

    def _fetch_suite_ids_for_cases(self, case_ids: Set[int]) -> Dict[int, int]:
        """
        Fetch suite_id for each case ID using concurrent requests.

        :param case_ids: Set of case IDs to fetch
        :returns: Dictionary mapping {case_id: suite_id}
        """
        case_suite_mapping = {}
        failed_cases = []

        def fetch_case(case_id: int) -> Tuple[int, int, str]:
            """Fetch a single case and return (case_id, suite_id, error)"""
            response = self.api_request_handler.client.send_get(f"get_case/{case_id}")
            if response.error_message:
                return case_id, None, response.error_message

            suite_id = response.response_text.get("suite_id")
            if suite_id is None:
                return case_id, None, "No suite_id in response"

            return case_id, suite_id, None

        # Use ThreadPoolExecutor for concurrent fetching (max 10 threads)
        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = {executor.submit(fetch_case, cid): cid for cid in case_ids}

            for future in as_completed(futures):
                case_id, suite_id, error = future.result()

                if error:
                    failed_cases.append(case_id)
                    self.environment.vlog(
                        FAULT_MAPPING["multisuite_fetch_case_failed"].format(case_id=case_id, error_message=error)
                    )
                else:
                    case_suite_mapping[case_id] = suite_id

        if failed_cases:
            self.environment.log(f"Warning: Failed to fetch {len(failed_cases)} case(s). They will be skipped.")

        return case_suite_mapping

    def _validate_single_project(self, case_suite_mapping: Dict[int, int]) -> Tuple[Dict[int, int], int]:
        """
        Validate that all suites belong to the target project.
        Filters out cases from other projects.
        Also caches suite information for later use.

        :param case_suite_mapping: Dictionary {case_id: suite_id}
        :returns: Tuple (filtered_mapping, skipped_count)
        """
        valid_mapping = {}
        skipped_cases = []
        self.suite_info_cache = {}  # {suite_id: suite_data} - Cache for suite names

        target_project_id = self.project.project_id

        for case_id, suite_id in case_suite_mapping.items():
            # Check cache first
            if suite_id in self.suite_info_cache:
                project_id = self.suite_info_cache[suite_id].get("project_id")
            else:
                # Fetch suite info
                response = self.api_request_handler.client.send_get(f"get_suite/{suite_id}")
                if response.error_message:
                    self.environment.vlog(f"Warning: Failed to fetch suite {suite_id} info: {response.error_message}")
                    skipped_cases.append(case_id)
                    continue

                # Cache full suite data (includes project_id and name)
                self.suite_info_cache[suite_id] = response.response_text
                project_id = response.response_text.get("project_id")

            if project_id == target_project_id:
                valid_mapping[case_id] = suite_id
            else:
                skipped_cases.append(case_id)

        if skipped_cases:
            self.environment.log(
                FAULT_MAPPING["multisuite_cross_project_cases"].format(
                    count=len(skipped_cases),
                    case_ids=", ".join([f"C{cid}" for cid in skipped_cases[:10]])
                    + ("..." if len(skipped_cases) > 10 else ""),
                )
            )

        return valid_mapping, len(skipped_cases)

    def _group_cases_by_suite(self, case_suite_mapping: Dict[int, int]) -> Dict[int, List[TestRailCase]]:
        """
        Group TestRailCase objects by their suite_id.

        :param case_suite_mapping: Dictionary {case_id: suite_id}
        :returns: Dictionary {suite_id: [TestRailCase objects]}
        """
        suite_groups = defaultdict(list)

        for section in self.api_request_handler.suites_data_from_provider.testsections:
            for test_case in section.testcases:
                case_id = test_case.case_id
                if case_id in case_suite_mapping:
                    suite_id = case_suite_mapping[case_id]
                    suite_groups[suite_id].append(test_case)

        return dict(suite_groups)

    def _create_test_plan(self, suite_groups: Dict[int, List[TestRailCase]]) -> Tuple[int, Dict[int, int], str]:
        """
        Create a new test plan with one run per suite.

        :param suite_groups: Dictionary {suite_id: [TestRailCase objects]}
        :returns: Tuple (plan_id, {suite_id: run_id}, error_message)
        """
        # Build plan description with suite names and test counts
        # Use cached suite info to avoid duplicate API calls
        description_parts = []
        suite_names = {}  # Cache suite names

        for suite_id in suite_groups.keys():
            # Check if we have cached suite info
            if hasattr(self, "suite_info_cache") and suite_id in self.suite_info_cache:
                suite_name = self.suite_info_cache[suite_id].get("name", f"Suite {suite_id}")
            else:
                # Fallback: fetch suite info if not cached
                response = self.api_request_handler.client.send_get(f"get_suite/{suite_id}")
                if not response.error_message:
                    suite_name = response.response_text.get("name", f"Suite {suite_id}")
                else:
                    suite_name = f"Suite {suite_id}"

            suite_names[suite_id] = suite_name
            test_count = len(suite_groups[suite_id])
            description_parts.append(f"{suite_name} ({test_count} test(s))")

        description = ", ".join(description_parts)

        # Build entries for add_plan
        entries = []
        for suite_id, cases in suite_groups.items():
            case_ids = [case.case_id for case in cases]
            entry = {
                "suite_id": suite_id,
                "include_all": False,
                "case_ids": case_ids,
            }
            entries.append(entry)

        # Create the plan
        plan_response, error = self.api_request_handler.run_handler.add_plan(
            project_id=self.project.project_id,
            plan_name=self.environment.title,
            entries=entries,
            description=description,
            milestone_id=getattr(self.environment, "milestone_id", None),
        )

        if error:
            return None, {}, error

        # Extract run IDs from plan response
        plan_id = plan_response.get("id")
        run_mapping = {}

        for entry in plan_response.get("entries", []):
            suite_id = entry.get("suite_id")
            runs = entry.get("runs", [])
            if runs:
                run_id = runs[0].get("id")
                run_mapping[suite_id] = run_id

        return plan_id, run_mapping, None

    def _update_existing_plan(
        self, plan_id: int, suite_groups: Dict[int, List[TestRailCase]]
    ) -> Tuple[Dict[int, int], str]:
        """
        Add results to an existing test plan.
        Matches existing runs or creates new plan entries for missing suites.

        :param plan_id: Existing plan ID
        :param suite_groups: Dictionary {suite_id: [TestRailCase objects]}
        :returns: Tuple ({suite_id: run_id}, error_message)
        """
        # Fetch existing plan structure
        response = self.api_request_handler.client.send_get(f"get_plan/{plan_id}")
        if response.error_message:
            return {}, f"Failed to fetch plan {plan_id}: {response.error_message}"

        plan_data = response.response_text
        run_mapping = {}

        # Match existing entries
        for entry in plan_data.get("entries", []):
            suite_id = entry.get("suite_id")
            if suite_id in suite_groups:
                runs = entry.get("runs", [])
                if runs:
                    run_mapping[suite_id] = runs[0].get("id")

        # Create new entries for missing suites
        for suite_id in suite_groups.keys():
            if suite_id not in run_mapping:
                # Add new plan entry
                case_ids = [case.case_id for case in suite_groups[suite_id]]
                entry_data = {
                    "suite_id": suite_id,
                    "include_all": False,
                    "case_ids": case_ids,
                }

                add_entry_response = self.api_request_handler.client.send_post(f"add_plan_entry/{plan_id}", entry_data)
                if add_entry_response.error_message:
                    self.environment.elog(
                        f"Warning: Failed to add entry for suite {suite_id}: {add_entry_response.error_message}"
                    )
                    continue

                runs = add_entry_response.response_text.get("runs", [])
                if runs:
                    run_mapping[suite_id] = runs[0].get("id")

        return run_mapping, None

    def _upload_results_per_run(self, suite_groups: Dict[int, List[TestRailCase]], run_mapping: Dict[int, int]) -> int:
        """
        Upload results to each run.

        :param suite_groups: Dictionary {suite_id: [TestRailCase objects]}
        :param run_mapping: Dictionary {suite_id: run_id}
        :returns: Total number of results uploaded
        """
        total_results = 0

        # Store original testcases to restore later
        original_testsections = self.api_request_handler.suites_data_from_provider.testsections

        for suite_id, cases in suite_groups.items():
            run_id = run_mapping.get(suite_id)
            if not run_id:
                self.environment.log(f"Warning: No run ID found for suite {suite_id}, skipping.")
                continue

            # Create a temporary test section with ONLY the cases for this suite
            # This prevents contamination from other suites
            from trcli.data_classes.dataclass_testrail import TestRailSection

            temp_section = TestRailSection(name="temp", testcases=cases)

            # Temporarily replace the entire testsections list with only this suite's cases
            self.api_request_handler.suites_data_from_provider.testsections = [temp_section]

            # Upload results for this run
            responses, error, results_count = self.api_request_handler.result_handler.add_results(run_id)

            if error:
                self.environment.elog(f"Error uploading results to run {run_id}: {error}")
            else:
                total_results += results_count
                self.environment.log(f"Uploaded {results_count} result(s) to run {run_id} (suite {suite_id}).")

            # Upload attachments if any
            report_results = [
                {"case_id": case.case_id, "attachments": case.result.attachments}
                for case in cases
                if case.result.attachments
            ]

            if report_results:
                flattened_results = [result for results_list in responses for result in results_list]
                self.api_request_handler.result_handler.upload_attachments(report_results, flattened_results, run_id)

        # Restore original testsections
        self.api_request_handler.suites_data_from_provider.testsections = original_testsections

        return total_results
