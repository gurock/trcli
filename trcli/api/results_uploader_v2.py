import time
from typing import List

from trcli.api.project_based_client_v2 import ProjectBasedClient
from trcli.cli import Environment
from trcli.constants import PROMPT_MESSAGES, FAULT_MAPPING, SuccessMessages, ProcessingMessages, SkippingMessage, \
    ErrorMessages, ErrorMessagesRun

from trcli.data_classes.dataclass_testrail import TestRailSuite
from trcli.data_providers.api_data_provider_v2 import DataProviderException


class ResultsUploader(ProjectBasedClient):
    """
    Class to be used to upload the results to TestRail.
    Initialized with environment object and result file parser object (any parser derived from FileParser).
    """
    def __init__(self, environment: Environment, suite: TestRailSuite, skip_run: bool = False):
        super().__init__(environment, suite)
        self.skip_run = skip_run
        self._start_time = None

    def upload_results(self) -> None:
        """
        Does all the job needed to upload the results parsed from result files to TestRail.
        If needed missing items like suite/section/test case would be added to TestRail.
        Exits with result code 1 printing proper message to the user in case of a failure
        or with result code 0 if succeeds.
        """
        self._start_time = time.time()

        self.resolve_project()
        self.resolve_suite()
        self._resolve_sections_and_cases_upload()

        if self.skip_run:
            stop = time.time()
            self.environment.log(SkippingMessage.SKIP_TEST_RUN_AND_RESULTS)
            self.environment.log(SuccessMessages.COMPLETED_IN_F_ELAPSED.format(elapsed=(stop - self._start_time)))
            return

        self._resolve_run_and_results_upload()
        stop = time.time()
        self.environment.log(SuccessMessages.COMPLETED_IN_F_ELAPSED.format(elapsed=(stop - self._start_time)))

    def create_or_update_test_run(self) -> int:
        """
        Create or update a test run.
        - If run_id is provided → update the run.
        - If plan_id is provided → add the run to a plan.
        - Otherwise → create a standalone run.
        returns created or updated run ID.
        Exits with result code set to 1 in case of a failure.

        Moved this method from ancestor class to this place. It seems more logical, because
        this class is responsible for results upload and run is needed to upload results.
        """
        try:
            self._data_provider.suite_id
        except DataProviderException:
            self.resolve_suite()

        if self._data_provider.test_run_id:
            error_message = self._update_test_run()
        else:
            error_message = self._create_test_run()

        if error_message:
            self.environment.elog(error_message)
            self._rollback_and_exit()

        return self._data_provider.test_run_id

    def _resolve_sections_and_cases_upload(self) -> None:
        error_message = self._api_request_handler.sort_missing_and_existing_cases()

        if error_message:
            self.environment.elog(ErrorMessages.SORTING_TEST_CASES_F_ERROR.format(error=error_message))
            self._rollback_and_exit()

        has_missing_cases = bool(self._data_provider.missing_cases)
        should_update_cases = self.environment.update_cases

        if has_missing_cases or should_update_cases:
            self._handle_sections_upload()

        if should_update_cases:
            self._update_existing_test_cases()

        if has_missing_cases:
            self._add_missing_test_cases()

    def _handle_sections_upload(self) -> None:
        self._get_confirmation_for_sections_upload()
        self.environment.log(ProcessingMessages.ADDING_SECTIONS)
        added_sections, error_message = self._api_request_handler.add_missing_sections()
        self._data_provider.created_sections_ids = added_sections

        if error_message:
            self.environment.elog(ErrorMessages.UPLOADING_SECTIONS_F_ERROR.format(error=error_message))
            self._rollback_and_exit()
        # Update section IDs when sections are found or created.
        # if --update-cases option specified, for existing cases section or subsection id will be updated as well
        self._data_provider.update_cases_section_ids()

    def _get_confirmation_for_sections_upload(self) -> None:
        has_missing_sections, error_message = self._api_request_handler.has_missing_sections()
        if error_message:
            self.environment.elog(ErrorMessages.CHECKING_MISSING_SECTIONS_F_ERROR.format(error=error_message))
            self._rollback_and_exit()

        if not has_missing_sections:
            return

        prompt_message = PROMPT_MESSAGES["create_missing_sections"].format(project_name=self.project.name)
        fault_message = FAULT_MAPPING["no_user_agreement"].format(type="sections")

        if not self.environment.get_prompt_response_for_auto_creation(prompt_message):
            self.environment.elog(fault_message)
            self._rollback_and_exit()

    def _update_existing_test_cases(self) -> None:
        cases_to_update = self._data_provider.existing_cases
        self.environment.log(ProcessingMessages.UPDATING, new_line=False)

        if not cases_to_update:
            self.environment.log(SkippingMessage.NO_TEST_CASES_TO_UPDATE)
            return

        error_message = self._api_request_handler.update_existing_cases(cases_to_update)

        if error_message:
            self.environment.elog(ErrorMessages.CASES_UPDATE_F_ERROR.format(error=error_message))
            # not sure about roll back here

        actual_amount = len(self._data_provider.updated_cases_ids)
        success_message = (SuccessMessages.UPDATED_CASES_AMOUNT_FF_ACTUAL_EXPECTED
                          .format(actual=actual_amount,expected=len(cases_to_update)))
        self.environment.log(success_message)

    def _add_missing_test_cases(self) -> None:
        """
        Uploads missing test cases to the suite if user agrees to do so.
        Exits with result code set to 1 in case of a failure.
        """
        cases_to_add = self._data_provider.missing_cases

        prompt_message = PROMPT_MESSAGES["create_missing_test_cases"].format(
            project_name=self.environment.project
        )
        fault_message = FAULT_MAPPING["no_user_agreement"].format(type="test cases")

        if not self.environment.get_prompt_response_for_auto_creation(prompt_message):
            self.environment.elog(fault_message)
            self._rollback_and_exit()

        start_time = time.time()
        self.environment.log(ProcessingMessages.ADDING, new_line=False)
        error_message = self._api_request_handler.add_cases(cases_to_add)

        if error_message:
            self.environment.elog(ErrorMessages.ADDING_TEST_CASES_F_ERROR.format(error=error_message))
            self._rollback_and_exit()

        success_message = SuccessMessages.ADDED_CASES_FF_AMOUNT_ELAPSED.format(
            amount=len(self._data_provider.created_cases_ids),
            elapsed=(start_time - time.time())
        )
        self.environment.log(success_message)

    def _resolve_run_and_results_upload(self) -> None:
        self.create_or_update_test_run()

        start = time.time()
        results_amount, error_message = self._api_request_handler.add_results()
        if error_message:
            self.environment.elog(error_message)
            self._rollback_and_exit()

        stop = time.time()

        if results_amount:
            success_message = SuccessMessages.ADDED_RESULTS_FF_AMOUNT_ELAPSED.format(
                amount=results_amount,
                elapsed=(stop - start)
            )
            self.environment.log(success_message)

        self._close_test_run_if_required()

    def _close_test_run_if_required(self) -> None:
        """
        Closes the test run if the user requested it.
        Exits with result code set to 1 in case of a failure.
        """
        if self.environment.close_run:
            self.environment.log(ProcessingMessages.CLOSING_TEST_RUN, new_line=False)
            error_message = self._api_request_handler.close_run()
            if error_message:
                self.environment.elog(ErrorMessagesRun.CLOSING_TEST_RUN_F_ERROR.format(error=error_message))
                exit(1)
            self.environment.log(SuccessMessages.CLOSED_RUN)

    def _create_test_run(self) -> str:
        """
        Creates a new test run in TestRail.
        """
        self.environment.log(ProcessingMessages.CREATING_TEST_RUN, new_line=False)

        if self._data_provider.test_plan_id:
            run_id, error_message = self._api_request_handler.add_run_to_plan()
        else:
            run_id, error_message = self._api_request_handler.add_run()

        if error_message or (run_id is None):
            error_message = error_message or "No run ID returned."
            return ErrorMessagesRun.CREATING_TEST_RUN_F_ERROR.format(error=error_message)

        self._data_provider.update_test_run_id(run_id, is_created=True)
        self._log_run_link()
        return ""

    def _update_test_run(self) -> str:
        """
        Updates an existing test run in TestRail.

        - Retrieves the run and its cases.
        - Updates the run depending on whether it belongs to a plan (with or without configs)
          or is standalone.
        Returns an error message if any issue occurs, otherwise an empty string.
        """
        # 1: Retrieve run ---
        existing_run, error_message = self._api_request_handler.get_run()
        if error_message:
            return ErrorMessagesRun.RETRIEVING_RUN_INFO_FF_RUN_ID_ERROR.format(
                run_id=self._data_provider.test_run_id,
                error=error_message,
            )

        # 2: Retrieve cases ---
        self.environment.log(ProcessingMessages.UPDATING_TEST_RUN, new_line=False)
        run_case_ids, error_message = self._api_request_handler.get_cases_ids_in_run()
        if error_message:
            return ErrorMessagesRun.RETRIEVING_TESTS_IN_IN_RUN_F_ERROR.format(error=error_message)

        self._data_provider.merge_run_case_ids(run_case_ids)

        # 3: Update description ---
        self._data_provider.test_run.description = existing_run.get("description", "") # Retain the current description

        plan_id = existing_run.get("plan_id")
        config_ids = existing_run.get("config_ids")

        # 4: Decide update strategy ---
        if not plan_id:
            return self._update_as_standalone_run()
        if config_ids:
            return self._update_as_plan_run_with_configs()
        return self._update_as_plan_run_without_configs(plan_id)

    def _update_as_standalone_run(self) -> str:
        """Update a run that is not part of any plan."""
        self.environment.log(ProcessingMessages.CONTINUE_AS_STANDALONE_RUN, new_line=False)
        error_message = self._api_request_handler.update_run()
        if not error_message:
            self._log_run_link()
        return error_message

    def _update_as_plan_run_with_configs(self) -> str:
        """Update a run that is part of a plan with configs."""
        error_message = self._api_request_handler.update_run_in_plan_entry()
        if not error_message:
            self._log_run_link()
        return error_message

    def _update_as_plan_run_without_configs(self, plan_id: int) -> str:
        """Update a run that is part of a plan without configs, requires entry_id."""
        entry_id, error_message = self._api_request_handler.get_run_entry_id_in_plan(plan_id)
        if error_message:
            return ErrorMessagesRun.RETRIEVING_RUN_ID_IN_PLAN_F_ERROR.format(error=error_message)

        error_message = self._api_request_handler.update_plan_entry(plan_id, entry_id)
        if not error_message:
            self._log_run_link()
        return error_message

    def _log_run_link(self) -> None:
        run_id = self._data_provider.test_run_id
        link = self.environment.host.rstrip('/')
        self.environment.log(SuccessMessages.RUN_FF_LINK_RUN_ID.format(link=link, run_id=run_id))

    def _rollback_and_exit(self) -> None:
        """
        Roll back created entities and terminate the process.
        """
        logs = self._rollback_changes()
        if logs:
            self.environment.log("\n".join(logs))

        stop = time.time()
        self.environment.log(SuccessMessages.COMPLETED_IN_F_ELAPSED.format(elapsed=(stop - self._start_time)))
        exit(1)

    def _rollback_changes(self) -> List[str]:
        """
        Attempts to roll back created entities (run, cases, sections, suite).
        Returns a list of error messages for any failures.
        """
        rollback_actions = {
            "run": self._api_request_handler.delete_created_run,
            "cases": self._api_request_handler.delete_created_cases,
            "sections": self._api_request_handler.delete_created_sections,
            "suite": self._api_request_handler.delete_created_suite,
        }

        log_messages: List[str] = []
        for entity, action in rollback_actions.items():
            log_message = action()

            if log_message and log_message.strip():
                log_messages.append(log_message)
        return log_messages
