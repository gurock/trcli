import time
from typing import Tuple, Callable, List

from trcli.api.api_client import APIClient
from trcli.api.api_request_handler import ApiRequestHandler
from trcli.cli import Environment
from trcli.constants import PROMPT_MESSAGES, FAULT_MAPPING, SuiteModes
from trcli.constants import ProjectErrors, RevertMessages
from trcli.data_classes.dataclass_testrail import TestRailSuite
from trcli.data_classes.data_parsers import MatchersParser


class ResultsUploader:
    """
    Class to be used to upload the results to TestRail.
    Initialized with environment object and result file parser object (any parser derived from FileParser).
    """

    def __init__(self, environment: Environment, suite: TestRailSuite):
        self.project = None
        self.environment = environment
        self.parsed_data = suite
        self.run_name = self.environment.title
        if self.environment.special_parser == "saucectl":
            self.run_name += f" ({self.parsed_data.name})"
        if self.environment.suite_id:
            self.parsed_data.suite_id = self.environment.suite_id
        self.api_request_handler = ApiRequestHandler(
            api_client=self.instantiate_api_client(),
            environment=self.environment,
            suites_data=self.parsed_data,
            verify=self.environment.verify,
        )
        if self.environment.suite_id:
            self.api_request_handler.data_provider.update_data(
                [{"suite_id": self.environment.suite_id}]
            )

    def upload_results(self):
        """
        Does all the job needed to upload the results parsed from result files to TestRail.
        If needed missing items like suite/section/test case would be added to TestRail.
        Exits with result code 1 printing proper message to the user in case of a failure
        or with result code 0 if succeeds.
        """
        start = time.time()
        results_amount = None

        # Validate project settings
        self.environment.log("Checking project. ", new_line=False)
        self.project = self.api_request_handler.get_project_data(
            self.environment.project, self.environment.project_id
        )
        self._validate_project_id()
        if self.environment.auto_creation_response:
            if self.environment.case_matcher == MatchersParser.AUTO:
                automation_id_error = self.api_request_handler.check_automation_id_field(self.project.project_id)
                if automation_id_error:
                    self.environment.elog(automation_id_error)
                    exit(1)
        self.environment.log("Done.")

        # Resolve test suite
        added_suite_id, result_code = self.get_suite_id(
            project_id=self.project.project_id, suite_mode=self.project.suite_mode
        )
        if result_code == -1:
            exit(1)

        # Resolve missing test cases and sections
        missing_test_cases, error_message = self.api_request_handler.check_missing_test_cases_ids(
            self.project.project_id
        )
        if error_message:
            self.environment.elog(
                FAULT_MAPPING["error_checking_missing_item"].format(
                    missing_item="missing test cases", error_message=error_message
                )
            )
        added_sections = None
        added_test_cases = None
        if self.environment.auto_creation_response:
            added_sections, result_code = self.add_missing_sections(
                self.project.project_id
            )
            if result_code == -1:
                revert_logs = self.rollback_changes(
                    added_suite_id=added_suite_id, added_sections=added_sections
                )
                self.environment.log("\n".join(revert_logs))
                exit(1)

            if missing_test_cases:
                added_test_cases, result_code = self.add_missing_test_cases()
            else:
                result_code = 1
            if result_code == -1:
                revert_logs = self.rollback_changes(
                    added_suite_id=added_suite_id,
                    added_sections=added_sections,
                    added_test_cases=added_test_cases,
                )
                self.environment.log("\n".join(revert_logs))
                exit(1)

        # Create/update test run
        if not self.environment.run_id:
            self.environment.log(f"Creating test run. ", new_line=False)
            added_run, error_message = self.api_request_handler.add_run(
                self.project.project_id, self.run_name, self.environment.milestone_id
            )
            if error_message:
                self.environment.elog("\n" + error_message)
                revert_logs = self.rollback_changes(
                    added_suite_id=added_suite_id,
                    added_sections=added_sections,
                    added_test_cases=added_test_cases,
                )
                self.environment.log("\n".join(revert_logs))
                exit(1)
            run_id = added_run
            self.environment.log(f"Run created: {self.environment.host.rstrip('/')}/index.php?/runs/view/{run_id}")
        else:
            run_id = self.environment.run_id
            self.environment.log(f"Updating run: {self.environment.host.rstrip('/')}/index.php?/runs/view/{run_id}")
        added_results, error_message, results_amount = self.api_request_handler.add_results(run_id)
        if error_message:
            self.environment.elog(error_message)
            revert_logs = self.rollback_changes(
                added_suite_id=added_suite_id,
                added_sections=added_sections,
                added_test_cases=added_test_cases,
                run_id=0 if run_id == self.environment.run_id else run_id,
            )
            self.environment.log("\n".join(revert_logs))
            exit(1)
        if self.environment.close_run:
            self.environment.log("Closing test run. ", new_line=False)
            response, error_message = self.api_request_handler.close_run(run_id)
        if error_message:
            self.environment.elog("\n" + error_message)
            exit(1)

        # Terminate upload
        stop = time.time()
        if results_amount:
            self.environment.log(f"Submitted {results_amount} test results in {stop - start:.1f} secs.")

    def get_suite_id(self, project_id: int, suite_mode: int) -> Tuple[int, int]:
        """
        Gets and checks suite ID for specified project_id.
        Depending on the entry conditions (suite ID provided or not, suite mode, project ID)
        it will:
            * check if specified suite ID exists and is correct
            * try to create missing suite ID
            * try to fetch suite ID from TestRail
        Returns new suite ID if added or -1 in any other case. Proper information is printed
        on failure.
        """
        suite_id = -1
        result_code = -1

        if not self.api_request_handler.suites_data_from_provider.suite_id:
            if suite_mode in [SuiteModes.multiple_suites, SuiteModes.single_suite_baselines]:
                suite_id, error_msg = self.api_request_handler.resolve_suite_id_using_name(project_id)
                if suite_id != -1:
                    self.api_request_handler.suites_data_from_provider.suite_id = suite_id
            if suite_mode == SuiteModes.multiple_suites:
                prompt_message = PROMPT_MESSAGES["create_new_suite"].format(
                    suite_name=self.api_request_handler.suites_data_from_provider.name,
                    project_name=self.environment.project,
                )
                adding_message = (
                    f"Adding missing suites to project {self.environment.project}."
                )
                fault_message = FAULT_MAPPING["no_user_agreement"].format(type="suite")
                added_suites, result_code = self.prompt_user_and_add_items(
                    prompt_message=prompt_message,
                    adding_message=adding_message,
                    fault_message=fault_message,
                    add_function=self.api_request_handler.add_suites,
                    project_id=project_id,
                )
                if added_suites:
                    suite_id = added_suites[0]["suite_id"]
            elif suite_mode == SuiteModes.single_suite_baselines:
                suite_ids, error_message = self.api_request_handler.get_suite_ids(
                    project_id=project_id
                )
                if error_message:
                    self.environment.elog(error_message)
                else:
                    if len(suite_ids) > 1:
                        self.environment.elog(
                            FAULT_MAPPING[
                                "not_unique_suite_id_single_suite_baselines"
                            ].format(project_name=self.environment.project)
                        )
                    else:
                        result_code = 1
            elif suite_mode == SuiteModes.single_suite:
                suite_ids, error_message = self.api_request_handler.get_suite_ids(
                    project_id=project_id
                )
                if error_message:
                    self.environment.elog(error_message)
                else:
                    suite_id = suite_ids[0]
                    result_code = 1
            else:
                self.environment.elog(
                    FAULT_MAPPING["unknown_suite_mode"].format(suite_mode=suite_mode)
                )
        else:
            result_code = self.check_suite_id(project_id)
        return suite_id, result_code

    def check_suite_id(self, project_id: int) -> int:
        """
        Checks that suite ID is correct.
        Returns suite ID is succeeds or -1 on failure. Proper information will be printed
        on failure.
        """
        result_code = -1
        suite_exists, error_message = self.api_request_handler.check_suite_id(
            project_id
        )
        if suite_exists:
            result_code = 1
        else:
            self.environment.elog(error_message)
        return result_code

    def add_missing_sections(self, project_id: int) -> Tuple[list, int]:
        """
        Checks for missing sections in specified project. Add missing sections if user agrees to
        do so. Returns list of added section IDs if succeeds or empty list with result_code set to
        -1.
        """
        result_code = -1
        added_sections = []
        (
            missing_sections,
            error_message,
        ) = self.api_request_handler.check_missing_section_ids(project_id)
        if missing_sections:
            if self.api_request_handler.data_provider.check_section_names_duplicates():
                self.environment.elog(
                    f"Error: Section duplicates detected in {self.environment.file}. "
                    f"This will result to failure to upload all cases."
                )
                return added_sections, result_code
            prompt_message = PROMPT_MESSAGES["create_missing_sections"].format(
                project_name=self.environment.project
            )
            adding_message = "Adding missing sections to the suite."
            fault_message = FAULT_MAPPING["no_user_agreement"].format(type="sections")
            added_sections, result_code = self.prompt_user_and_add_items(
                prompt_message=prompt_message,
                adding_message=adding_message,
                fault_message=fault_message,
                add_function=self.api_request_handler.add_sections,
                project_id=project_id,
            )
        else:
            if error_message:
                self.environment.elog(
                    FAULT_MAPPING["error_checking_missing_item"].format(
                        missing_item="missing sections", error_message=error_message
                    )
                )
            else:
                result_code = 1
        return added_sections, result_code

    def add_missing_test_cases(self) -> Tuple[list, int]:
        """
        Checks for missing test cases in specified project. Add missing test cases if user agrees to
        do so. Returns list of added test case IDs if succeeds or empty list with result_code set to
        -1.
        """
        prompt_message = PROMPT_MESSAGES["create_missing_test_cases"].format(
            project_name=self.environment.project
        )
        adding_message = "Adding missing test cases to the suite."
        fault_message = FAULT_MAPPING["no_user_agreement"].format(type="test cases")
        added_cases, result_code = self.prompt_user_and_add_items(
            prompt_message=prompt_message,
            adding_message=adding_message,
            fault_message=fault_message,
            add_function=self.api_request_handler.add_cases,
        )

        return added_cases, result_code

    def prompt_user_and_add_items(
        self,
        prompt_message,
        adding_message,
        fault_message,
        add_function: Callable,
        project_id: int = None,
    ):
        added_items = []
        result_code = -1
        if self.environment.get_prompt_response_for_auto_creation(prompt_message):
            self.environment.log(adding_message)
            if project_id:
                added_items, error_message = add_function(project_id=project_id)
            else:
                added_items, error_message = add_function()
            if error_message:
                self.environment.elog(error_message)
            else:
                result_code = 1
        else:
            self.environment.elog(fault_message)
        return added_items, result_code

    def instantiate_api_client(self) -> APIClient:
        """
        Instantiate api client with needed attributes taken from environment.
        """
        verbose_logging_function = self.environment.vlog
        logging_function = self.environment.log
        if self.environment.timeout:
            api_client = APIClient(
                self.environment.host,
                verbose_logging_function=verbose_logging_function,
                logging_function=logging_function,
                timeout=self.environment.timeout,
                verify=not self.environment.insecure,
            )
        else:
            api_client = APIClient(
                self.environment.host,
                logging_function=logging_function,
                verbose_logging_function=verbose_logging_function,
                verify=not self.environment.insecure,
            )
        api_client.username = self.environment.username
        api_client.password = self.environment.password
        api_client.api_key = self.environment.key
        return api_client

    def rollback_changes(
        self, added_suite_id=0, added_sections=None, added_test_cases=None, run_id=0
    ) -> List[str]:
        """
        Flow for rollback changes that was uploaded before error or user prompt.
        Method priority: runs, cases, sections, suite.
        Depending on user privileges delete might be successful or not on various stages.
        Method returns list of deletion results as string.
        """
        if added_test_cases is None:
            added_test_cases = []
        if added_sections is None:
            added_sections = []
        returned_log = []
        if run_id:
            _, error = self.api_request_handler.delete_run(run_id)
            if error:
                returned_log.append(RevertMessages.run_not_deleted.format(error=error))
            else:
                returned_log.append(RevertMessages.run_deleted)
        if len(added_test_cases) > 0:
            _, error = self.api_request_handler.delete_cases(
                added_suite_id, added_test_cases
            )
            if error:
                returned_log.append(
                    RevertMessages.test_cases_not_deleted.format(error=error)
                )
            else:
                returned_log.append(RevertMessages.test_cases_deleted)
        if len(added_sections) > 0:
            _, error = self.api_request_handler.delete_sections(added_sections)
            if error:
                returned_log.append(
                    RevertMessages.section_not_deleted.format(error=error)
                )
            else:
                returned_log.append(RevertMessages.section_deleted)
        if self.project.suite_mode != SuiteModes.single_suite and added_suite_id > 0:
            _, error = self.api_request_handler.delete_suite(added_suite_id)
            if error:
                returned_log.append(
                    RevertMessages.suite_not_deleted.format(error=error)
                )
            else:
                returned_log.append(RevertMessages.suite_deleted)
        return returned_log


    def _validate_project_id(self):
        if self.project.project_id == ProjectErrors.not_existing_project:
            self.environment.elog("\n" + self.project.error_message)
            exit(1)
        elif self.project.project_id == ProjectErrors.other_error:
            self.environment.elog(
                "\n"
                + FAULT_MAPPING["error_checking_project"].format(
                    error_message=self.project.error_message
                )
            )
            exit(1)
        elif self.project.project_id == ProjectErrors.multiple_project_same_name:
            self.environment.elog(
                "\n"
                + FAULT_MAPPING["error_checking_project"].format(
                    error_message=self.project.error_message
                )
            )
            exit(1)
