from typing import Optional, Tuple

from trcli.api.api_client import APIClient
from trcli.api.api_request_handler_v2 import ApiRequestHandler
from trcli.cli import Environment
from trcli.constants import ProjectErrors, FAULT_MAPPING, SuiteModes, PROMPT_MESSAGES, ProcessingMessages, \
    SuccessMessages, ErrorMessages, ErrorMessagesSuites
from trcli.data_classes.data_parsers import MatchersParser
from trcli.data_classes.dataclass_testrail import TestRailSuite, ProjectData
from trcli.data_providers.api_data_provider_v2 import ApiDataProvider


class ProjectBasedClient:
    """
    Class to be used to interact with the TestRail Api at a project level.
    Initialized with environment object and result file parser object (any parser derived from FileParser).
    """

    def __init__(self, environment: Environment, suite: TestRailSuite):
        self.project: Optional[ProjectData] = None
        self.environment = environment
        self._data_provider = ApiDataProvider(suite, self.environment)
        self._api_request_handler = ApiRequestHandler(
            environment=self.environment,
            api_client=self._instantiate_api_client(),
            provider=self._data_provider,
        )

    def _instantiate_api_client(self) -> APIClient:
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

    def resolve_project(self) -> None:
        """
        Gets and checks project settings.
        """
        self.environment.log(ProcessingMessages.CHECKING_PROJECT, new_line=False)
        self.project = self._api_request_handler.get_project_data(
            self.environment.project, self.environment.project_id
        )
        self._validate_project_id()
        self._data_provider.project_id = self.project.project_id

        # Removed conformation check environment.auto_creation_response from previous implementation
        # Probably was here by mistake, following code creates nothing...
        if self.environment.case_matcher == MatchersParser.AUTO:
            automation_id_name = self._api_request_handler.define_automation_id_field(self.project.project_id)
            if not automation_id_name:
                self._exit_with_error(ErrorMessages.FAILED_TO_DEFINE_AUTOMATION_ID_FIELD)

            self._data_provider.update_custom_automation_id_system_name(automation_id_name)

        self.environment.log(SuccessMessages.DONE)

    def resolve_suite(self) -> None:
        if not self.project:
            self.resolve_project()
        if self.environment.suite_id:
            self._handle_suite_by_id()
        else:
            self._handle_suite_by_name()

    def _validate_project_id(self) -> None:
        error_messages = {
            ProjectErrors.not_existing_project: self.project.error_message,
            ProjectErrors.other_error: FAULT_MAPPING["error_checking_project"].format(
                error_message=self.project.error_message
            ),
            ProjectErrors.multiple_project_same_name: FAULT_MAPPING["error_checking_project"].format(
                error_message=self.project.error_message
            ),
        }

        if self.project.project_id in error_messages:
            self._exit_with_error(self.project.error_message)

    def _handle_suite_by_id(self) -> None:
        """Handles suite selection when suite ID is provided."""
        self._data_provider.update_suite_id(self.environment.suite_id)
        existing, error_message = self._api_request_handler.check_suite_id()

        if error_message:
            self._exit_with_error(ErrorMessagesSuites.CAN_NOT_RESOLVE_SUITE_F_ERROR.format(error=error_message))

        if not existing:
            self._exit_with_error(
                ErrorMessagesSuites.NOT_EXISTING_F_SUITE_ID.format(suite_id=self.environment.suite_id))

    def _handle_suite_by_name(self) -> None:
        """Handles suite selection when suite name is provided."""
        suite_mode = self.project.suite_mode
        project_id = self.project.project_id

        if suite_mode not in (
                SuiteModes.multiple_suites,
                SuiteModes.single_suite_baselines,
                SuiteModes.single_suite,
        ):
            self._exit_with_error(ErrorMessagesSuites.UNKNOWN_SUITE_MODE_F_MODE.format(mode=suite_mode))

        if suite_mode == SuiteModes.single_suite:
            self._handle_single_suite()
            return

        if suite_mode == SuiteModes.single_suite_baselines:
            self._handle_single_suite_baselines()
            return

        if suite_mode == SuiteModes.multiple_suites:
            self._handle_multiple_suites(project_id)
            return

    def _handle_single_suite(self) -> None:
        suite_ids, error_message = self._api_request_handler.get_suites_ids()
        if error_message:
            self._exit_with_error(
                ErrorMessagesSuites.CAN_NOT_RESOLVE_SUITE_F_ERROR.format(error=error_message)
            )
        if not suite_ids:
            self._exit_with_error(ErrorMessagesSuites.NO_SUITES_IN_SINGLE_SUITE_MODE)

        self._data_provider.update_suite_id(suite_ids[0])

    def _handle_single_suite_baselines(self) -> None:
        suite_ids, error_message = self._api_request_handler.get_suites_ids()
        if error_message:
            self._exit_with_error(
                ErrorMessagesSuites.CAN_NOT_RESOLVE_SUITE_F_ERROR.format(error=error_message)
            )
        if len(suite_ids) > 1:
            self._exit_with_error(ErrorMessagesSuites.ONE_OR_MORE_BASE_LINE_CREATED)

        self._data_provider.update_suite_id(suite_ids[0])

    def _handle_multiple_suites(self, project_id: int) -> None:
        # First try resolving by name
        suite_id, error_message = self._api_request_handler.resolve_suite_id_using_name()
        if error_message:
            self._exit_with_error(
                ErrorMessagesSuites.CAN_NOT_RESOLVE_SUITE_F_ERROR.format(error=error_message)
            )
        if suite_id:
            self._data_provider.update_suite_id(suite_id)
            return

        # Otherwise, prompt user to add a suite
        suite_id, error_message = self._prompt_user_and_add_suite()
        if error_message:
            self._exit_with_error(
                ErrorMessagesSuites.CAN_NOT_ADD_SUITE_F_ERROR.format(error=error_message)
            )
        self._data_provider.update_suite_id(suite_id, is_created=True)

    def _prompt_user_and_add_suite(self) -> Tuple[Optional[int], str]:
        prompt_message = PROMPT_MESSAGES["create_new_suite"].format(
            suite_name=self._data_provider.suites_input.name,
            project_name=self.project.name,
        )
        adding_message = ProcessingMessages.ADDING_SUITE_F_PROJECT_NAME.format(project_name=self.project.name)
        fault_message = FAULT_MAPPING["no_user_agreement"].format(type="suite")

        if not self.environment.get_prompt_response_for_auto_creation(prompt_message):
            self._exit_with_error(fault_message)

        self.environment.log(adding_message)
        return self._api_request_handler.add_suite()

    def _exit_with_error(self, message: str) -> None:
        """Logs error and exits."""
        self.environment.elog(message)
        exit(1)
