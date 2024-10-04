from beartype.typing import Callable, Optional, Tuple

from trcli.api.api_client import APIClient
from trcli.api.api_request_handler import ApiRequestHandler
from trcli.cli import Environment
from trcli.constants import ProjectErrors, FAULT_MAPPING, SuiteModes, PROMPT_MESSAGES
from trcli.data_classes.data_parsers import MatchersParser
from trcli.data_classes.dataclass_testrail import TestRailSuite


class ProjectBasedClient:
    """
    Class to be used to interact with the TestRail Api at a project level.
    Initialized with environment object and result file parser object (any parser derived from FileParser).
    """

    def __init__(self, environment: Environment, suite: TestRailSuite):
        self.project = None
        self.environment = environment
        self.run_name = self.environment.title
        if self.environment.suite_id:
            suite.suite_id = self.environment.suite_id
        self.api_request_handler = ApiRequestHandler(
            environment=self.environment,
            api_client=self.instantiate_api_client(),
            suites_data=suite,
            verify=self.environment.verify,
        )

    def instantiate_api_client(self) -> APIClient:
        """
        Instantiate api client with needed attributes taken from environment.
        """
        verbose_logging_function = self.environment.vlog
        logging_function = self.environment.log
        proxy = self.environment.proxy  # Will be None if --proxy is not defined
        noproxy = self.environment.noproxy  # Will be None if --noproxy is not defined
        proxy_user = self.environment.proxy_user
        if self.environment.timeout:
            api_client = APIClient(
                self.environment.host,
                verbose_logging_function=verbose_logging_function,
                logging_function=logging_function,
                timeout=self.environment.timeout,
                verify=not self.environment.insecure,
                proxy=proxy,
                proxy_user=proxy_user,
                noproxy=noproxy
            )
        else:
            api_client = APIClient(
                self.environment.host,
                logging_function=logging_function,
                verbose_logging_function=verbose_logging_function,
                verify=not self.environment.insecure,
                proxy=proxy,
                proxy_user=proxy_user,
                noproxy=noproxy
            )
        api_client.username = self.environment.username
        api_client.password = self.environment.password
        api_client.api_key = self.environment.key
        api_client.proxy = self.environment.proxy
        api_client.proxy_user = self.environment.proxy_user
        api_client.noproxy = self.environment.noproxy

        return api_client

    def resolve_project(self):
        """
        Gets and checks project settings.
        """
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

    def get_suite_id(self, suite_mode: int) -> Tuple[int, int, bool]:
        """
        Gets and checks suite ID for specified project.
        Project id should already be resolved as self.project.project_id or self.environment.project_id (as a backup).
        Depending on the entry conditions (suite ID provided or not, suite mode, project ID)
        it will:
            * check if specified suite ID exists and is correct
            * try to create missing suite ID
            * try to fetch suite ID from TestRail
        Returns the suite ID if added/found or -1 in any other case, along with a return code, and a boolean
        to identify is suite was created or not. Proper information is printed on failure.
        """
        suite_id = -1
        result_code = -1
        suite_added = False

        project_id = self._get_project_id()

        if not self.api_request_handler.suites_data_from_provider.suite_id:
            if suite_mode in [SuiteModes.multiple_suites, SuiteModes.single_suite_baselines]:
                suite_id, error_msg = self.api_request_handler.resolve_suite_id_using_name(project_id)
                if suite_id != -1:
                    self.api_request_handler.suites_data_from_provider.suite_id = suite_id
                    return suite_id, 1, False
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
                    suite_added = True
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
            suite_id = self.api_request_handler.suites_data_from_provider.suite_id
            result_code = self.check_suite_id(project_id)
        return suite_id, result_code, suite_added

    def check_suite_id(self, project_id: Optional[int]) -> int:
        """
        Checks that suite ID is correct.
        Returns suite ID is succeeds or -1 on failure. Proper information will be printed
        on failure.
        """
        result_code = -1
        if project_id is None:
            project_id = self._get_project_id()
        suite_exists, error_message = self.api_request_handler.check_suite_id(
            project_id
        )
        if suite_exists:
            result_code = 1
        else:
            self.environment.elog(error_message)
        return result_code

    def resolve_suite(self) -> Tuple[int, bool]:
        suite_id, result_code, suite_added = self.get_suite_id(suite_mode=self.project.suite_mode)
        if result_code == -1:
            exit(1)
        return suite_id, suite_added

    def create_or_update_test_run(self) -> Tuple[int, str]:
        """
        If a run_id is provided, update the test run; otherwise, add a new test run.
        """
        if not self.environment.run_id:
            self.environment.log(f"Creating test run. ", new_line=False)
            added_run, error_message = self.api_request_handler.add_run(
                project_id=self.project.project_id,
                run_name=self.run_name,
                milestone_id=self.environment.milestone_id,
                plan_id=self.environment.plan_id,
                config_ids=self.environment.config_ids,
                assigned_to_id=self.environment.run_assigned_to_id,
                include_all=bool(self.environment.run_include_all),
                refs=self.environment.run_refs,
            )
            run_id = added_run
        else:
            self.environment.log(f"Updating test run. ", new_line=False)
            run_id = self.environment.run_id
            run, error_message = self.api_request_handler.update_run(
                run_id, self.run_name, self.environment.milestone_id
            )
        if error_message:
            self.environment.elog("\n" + error_message)
        else:
            self.environment.log(f"Test run: {self.environment.host.rstrip('/')}/index.php?/runs/view/{run_id}")
        return run_id, error_message

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

    def _get_project_id(self) -> int:
        return getattr(self.project, "project_id", self.environment.project_id)
