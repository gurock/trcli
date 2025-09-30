import time
from beartype.typing import Tuple, Callable, List

from trcli.api.project_based_client import ProjectBasedClient
from trcli.cli import Environment
from trcli.constants import PROMPT_MESSAGES, FAULT_MAPPING, SuiteModes
from trcli.constants import RevertMessages
from trcli.data_classes.dataclass_testrail import TestRailSuite


class ResultsUploader(ProjectBasedClient):
    """
    Class to be used to upload the results to TestRail.
    Initialized with environment object and result file parser object (any parser derived from FileParser).
    """

    def __init__(self, environment: Environment, suite: TestRailSuite, skip_run: bool = False):
        super().__init__(environment, suite)
        self.skip_run = skip_run
        if hasattr(self.environment, 'special_parser') and self.environment.special_parser == "saucectl":
            self.run_name += f" ({suite.name})"

    def upload_results(self):
        """
        Does all the job needed to upload the results parsed from result files to TestRail.
        If needed missing items like suite/section/test case would be added to TestRail.
        Exits with result code 1 printing proper message to the user in case of a failure
        or with result code 0 if succeeds.
        """
        start = time.time()
        results_amount = None

        # Validate user emails early if --assign is specified
        try:
            assign_value = getattr(self.environment, 'assign_failed_to', None)
            if assign_value is not None and str(assign_value).strip():
                self._validate_and_store_user_ids()
        except (AttributeError, TypeError):
            # Skip validation if there are any issues with the assign_failed_to attribute
            pass

        self.resolve_project()
        suite_id, suite_added = self.resolve_suite()

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
                    suite_id=suite_id, suite_added=suite_added, added_sections=added_sections
                )
                self.environment.log("\n".join(revert_logs))
                exit(1)

            if missing_test_cases:
                added_test_cases, result_code = self.add_missing_test_cases()
            else:
                result_code = 1
            if result_code == -1:
                revert_logs = self.rollback_changes(
                    suite_id=suite_id,
                    suite_added=suite_added,
                    added_sections=added_sections,
                    added_test_cases=added_test_cases,
                )
                self.environment.log("\n".join(revert_logs))
                exit(1)

        if self.skip_run:
            stop = time.time()
            if added_test_cases:
                self.environment.log(f"Submitted {len(added_test_cases)} test cases in {stop - start:.1f} secs.")
            return
        
        # remove empty, unused sections created earlier, based on the sections actually used by the new test cases
        #  - iterate on added_sections and remove those that are not used by the new test cases
        empty_sections = None
        if added_sections:
            if not added_test_cases:
                empty_sections = added_sections
            else:
                empty_sections = [section for section in added_sections if section['section_id'] not in [case['section_id'] for case in added_test_cases]]
            if len(empty_sections) > 0:
                self.environment.log("Removing unnecessary empty sections that may have been created earlier. ", new_line=False)
                _, error = self.api_request_handler.delete_sections(empty_sections)
                if error:
                    self.environment.elog("\n" + error)
                    exit(1)
                else:
                    self.environment.log(f"Removed {len(empty_sections)} unused/empty section(s).")

        # Create/update test run
        run_id, error_message = self.create_or_update_test_run()
        if error_message:
            revert_logs = self.rollback_changes(
                suite_id=suite_id,
                suite_added=suite_added,
                added_sections=added_sections,
                added_test_cases=added_test_cases,
            )
            self.environment.log("\n".join(revert_logs))
            exit(1)

        added_results, error_message, results_amount = self.api_request_handler.add_results(run_id)
        if error_message:
            self.environment.elog(error_message)
            revert_logs = self.rollback_changes(
                suite_id=suite_id,
                suite_added=suite_added,
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
        
        # Exit with error if there were invalid users (after processing valid ones)
        try:
            has_invalid = getattr(self.environment, '_has_invalid_users', False)
            if has_invalid is True:  # Explicitly check for True to avoid mock object issues
                exit(1)
        except (AttributeError, TypeError):
            # Skip exit if there are any issues with the attribute
            pass

    def _validate_and_store_user_ids(self):
        """
        Validates user emails from --assign option and stores valid user IDs.
        For mixed valid/invalid users, warns about invalid ones but continues with valid ones.
        Exits only if NO valid users are found.
        """
        try:
            assign_value = getattr(self.environment, 'assign_failed_to', None)
            if assign_value is None or not str(assign_value).strip():
                return
        except (AttributeError, TypeError):
            return
        
        # Check for empty or whitespace-only values  
        assign_str = str(assign_value)
        if not assign_str.strip():
            self.environment.elog("Error: --assign option requires at least one user email")
            exit(1)
        
        emails = [email.strip() for email in assign_str.split(',') if email.strip()]
        
        if not emails:
            self.environment.elog("Error: --assign option requires at least one user email")
            exit(1)
        
        valid_user_ids = []
        invalid_users = []
        
        for email in emails:
            user_id, error_msg = self.api_request_handler.get_user_by_email(email)
            if user_id is None:
                invalid_users.append(email)
                if "User not found" not in error_msg:
                    # If it's not a "user not found" error, it might be an API issue
                    self.environment.elog(f"Error: {error_msg}")
                    exit(1)
            else:
                valid_user_ids.append(user_id)
        
        # Handle invalid users
        if invalid_users:
            for invalid_user in invalid_users:
                self.environment.elog(f"Error: User not found: {invalid_user}")
            
            # Store valid user IDs for processing, but mark that we should exit with error later
            self.environment._has_invalid_users = True
            
            # If ALL users are invalid, exit immediately
            if not valid_user_ids:
                exit(1)
        
        # Store valid user IDs for later use
        self.environment._validated_user_ids = valid_user_ids


    def add_missing_sections(self, project_id: int) -> Tuple[List, int]:
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

    def rollback_changes(
        self, suite_id=0, suite_added=False, added_sections=None, added_test_cases=None, run_id=0
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
                suite_id, added_test_cases
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
        if self.project.suite_mode != SuiteModes.single_suite and suite_added > 0:
            _, error = self.api_request_handler.delete_suite(suite_id)
            if error:
                returned_log.append(
                    RevertMessages.suite_not_deleted.format(error=error)
                )
            else:
                returned_log.append(RevertMessages.suite_deleted)
        return returned_log
