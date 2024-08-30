import pytest

from tests.test_data.project_based_client_test_data import (
    TEST_GET_SUITE_ID_PROMPTS_USER_IDS,
    TEST_GET_SUITE_ID_PROMPTS_USER_TEST_DATA,
    TEST_GET_SUITE_ID_SINGLE_SUITE_MODE_BASELINES_TEST_DATA,
    TEST_GET_SUITE_ID_SINGLE_SUITE_MODE_BASELINES_IDS,
)
from trcli.api.project_based_client import ProjectBasedClient
from trcli.cli import Environment
from trcli.constants import FAULT_MAPPING, SuiteModes, PROMPT_MESSAGES
from trcli.data_classes.data_parsers import MatchersParser
from trcli.data_classes.dataclass_testrail import TestRailSuite, ProjectData
from trcli.readers.junit_xml import JunitParser


class TestProjectBasedClient:
    @pytest.fixture(scope="function")
    def project_based_client_data_provider(self, mocker):
        environment = mocker.patch("trcli.api.project_based_client.Environment")
        environment.host = "https://fake_host.com/"
        environment.project = "Fake project name"
        environment.project_id = 1
        environment.case_id = None
        environment.run_id = None
        environment.file = "results.xml"
        environment.case_matcher = MatchersParser.AUTO

        api_request_handler = mocker.patch(
            "trcli.api.project_based_client.ApiRequestHandler"
        )
        api_request_handler.get_project_data.return_value = ProjectData(
            project_id=environment.project_id, suite_mode=1, error_message=""
        )
        api_request_handler.check_automation_id_field.return_value = None
        project_based_client = ProjectBasedClient(
            environment=environment, suite=TestRailSuite(name=environment.suite_name, suite_id=environment.suite_id),
        )
        project_based_client.api_request_handler = api_request_handler
        yield environment, api_request_handler, project_based_client

    @pytest.mark.project_based_client
    @pytest.mark.parametrize(
        "timeout", [40, None], ids=["with_timeout", "without_timeout"]
    )
    def test_instantiate_api_client(
            self, timeout, project_based_client_data_provider, mocker
    ):
        """The purpose of this test is to check that APIClient was instantiated properly and credential fields
        were set es expected."""
        (_, api_request_handler, _) = project_based_client_data_provider
        junit_file_parser = mocker.patch.object(JunitParser, "parse_file")
        environment = Environment()
        environment.host = "https://fake_host.com"
        environment.username = "usermane@host.com"
        environment.password = "test_password"
        environment.key = "test_api_key"
        if timeout:
            environment.timeout = timeout
        timeout_expected_result = 30 if not timeout else timeout
        project_based_client = ProjectBasedClient(
            environment=environment, suite=junit_file_parser
        )

        api_client = project_based_client.instantiate_api_client()

        assert (
                api_client.username == environment.username
        ), f"Expected username to be set to: {environment.username}, but got: {api_client.username} instead."
        assert (
                api_client.password == environment.password
        ), f"Expected password  to be set to: {environment.password}, but got: {api_client.password} instead."
        assert (
                api_client.api_key == environment.key
        ), f"Expected api_key to be set to: {environment.key}, but got: {api_client.api_key} instead."
        assert (
                api_client.timeout == timeout_expected_result
        ), f"Expected timeout to be set to: {timeout_expected_result}, but got: {api_client.timeout} instead."

    def test_resolve_project(self, project_based_client_data_provider):
        """The purpose of this test is to check that a project can be resolved properly and set on the environment.
        Resolving a project includes retrieving the project data and validating the project id."""
        (
            environment,
            api_request_handler,
            project_based_client,
        ) = project_based_client_data_provider

        project_based_client.resolve_project()
        assert (
                project_based_client.project.project_id == environment.project_id
        ), (f"Expected project_based_client.project to have {environment.project_id},"
            f" but had {project_based_client.project.project_id}")

    @pytest.mark.project_based_client
    def test_get_suite_id_returns_valid_id(self, project_based_client_data_provider):
        """The purpose of this test is to check that get_suite_id function will
        return suite_id if it exists in TestRail"""
        (
            environment,
            api_request_handler,
            project_based_client,
        ) = project_based_client_data_provider
        suite_id = 1
        result_code = 1
        project_based_client.api_request_handler.suites_data_from_provider.suite_id = suite_id
        project_based_client.api_request_handler.check_suite_id.return_value = (True, "")
        (result_suite_id, result_return_code, suite_added) = project_based_client.get_suite_id(
            suite_mode=SuiteModes.single_suite
        )

        assert (
                result_suite_id == suite_id
        ), f"Expected suite_id: {suite_id} but got {result_suite_id} instead."
        assert (
                suite_added is False
        ), f"Expected suite_added: {False} but got {suite_added} instead."
        assert (
                result_return_code == result_code
        ), f"Expected suite_id: {result_code} but got {result_return_code} instead."

    @pytest.mark.project_based_client
    @pytest.mark.parametrize(
        "user_response, expected_suite_id, expected_result_code, expected_message, suite_add_error",
        TEST_GET_SUITE_ID_PROMPTS_USER_TEST_DATA,
        ids=TEST_GET_SUITE_ID_PROMPTS_USER_IDS,
    )
    def test_get_suite_id_multiple_suites_mode(
            self,
            user_response,
            expected_suite_id,
            expected_result_code,
            expected_message,
            suite_add_error,
            project_based_client_data_provider,
            mocker,
    ):
        """The purpose of this test is to check that user will be prompted to add suite is one is missing
        in TestRail. Depending on user response either information about addition of missing suite or error message
        should be printed."""
        (
            environment,
            api_request_handler,
            project_based_client,
        ) = project_based_client_data_provider
        project_id = 1
        suite_name = "Fake suite name"
        suite_mode = SuiteModes.multiple_suites
        project_based_client.api_request_handler.resolve_suite_id_using_name.return_value = (-1, "Any Error")
        if not suite_add_error:
            project_based_client.api_request_handler.add_suites.return_value = (
                [
                    {
                        "suite_id": expected_suite_id,
                        "name": suite_name,
                    }
                ],
                "",
            )
        else:
            project_based_client.api_request_handler.add_suites.return_value = (
                [{"suite_id": expected_suite_id, "name": suite_name}],
                FAULT_MAPPING["error_while_adding_suite"].format(
                    error_message="Failed to add suite."
                ),
            )
        project_based_client.api_request_handler.suites_data_from_provider.suite_id = None
        project_based_client.api_request_handler.suites_data_from_provider.name = suite_name
        environment.get_prompt_response_for_auto_creation.return_value = user_response
        result_suite_id, result_code, suite_added = project_based_client.get_suite_id(suite_mode)
        expected_elog_calls = []
        expected_log_calls = []
        if "User did not agree to create" not in expected_message:
            expected_log_calls = [mocker.call(expected_message)]
        else:
            expected_elog_calls.append(mocker.call(expected_message))

        if suite_add_error:
            expected_elog_calls.append(
                mocker.call(
                    FAULT_MAPPING["error_while_adding_suite"].format(
                        error_message="Failed to add suite."
                    )
                )
            )

        assert (
                expected_suite_id == result_suite_id
        ), f"Expected suite_id: {expected_suite_id} but got {result_suite_id} instead."
        assert (
                expected_result_code == result_code
        ), f"Expected suite_id: {expected_result_code} but got {result_code} instead."
        environment.get_prompt_response_for_auto_creation.assert_called_with(
            PROMPT_MESSAGES["create_new_suite"].format(
                suite_name=suite_name,
                project_name=environment.project,
            )
        )
        if user_response:
            project_based_client.api_request_handler.add_suites.assert_called_with(
                project_id=project_id
            )
        environment.log.assert_has_calls(expected_log_calls)
        environment.elog.assert_has_calls(expected_elog_calls)

    @pytest.mark.project_based_client
    @pytest.mark.parametrize(
        "suite_ids, error_message, expected_suite_id, expected_result_code",
        [([10], "", 10, 1), ([], "Could not get suites", -1, -1)],
        ids=["get_suite_ids succeeds", "get_suite_ids fails"],
    )
    def test_get_suite_id_single_suite_mode(
            self,
            suite_ids,
            error_message,
            expected_suite_id,
            expected_result_code,
            project_based_client_data_provider,
            mocker,
    ):
        """The purpose of this test is to check flow of get_suite_id_log_error function for single
        suite mode."""
        (
            environment,
            api_request_handler,
            project_based_client,
        ) = project_based_client_data_provider
        project_id = 1
        suite_mode = SuiteModes.single_suite
        project_based_client.api_request_handler.suites_data_from_provider.suite_id = None
        project_based_client.api_request_handler.get_suite_ids.return_value = (
            suite_ids,
            error_message,
        )
        expected_elog_calls = []
        if error_message:
            expected_elog_calls = [mocker.call(error_message)]
        result_suite_id, result_code, suite_added = project_based_client.get_suite_id(suite_mode)

        assert (
                result_suite_id == expected_suite_id
        ), f"Expected suite id: {expected_suite_id} but got {result_suite_id} instead."
        assert (
                result_code == expected_result_code
        ), f"Expected result code: {expected_result_code} but got {result_code} instead."
        if error_message:
            environment.elog.assert_has_calls(expected_elog_calls)

    @pytest.mark.project_based_client
    @pytest.mark.parametrize(
        "get_suite_ids_result, expected_suite_id, expected_result_code, expected_error_message",
        TEST_GET_SUITE_ID_SINGLE_SUITE_MODE_BASELINES_TEST_DATA,
        ids=TEST_GET_SUITE_ID_SINGLE_SUITE_MODE_BASELINES_IDS,
    )
    def test_get_suite_id_single_suite_mode_baselines(
            self,
            get_suite_ids_result,
            expected_suite_id,
            expected_result_code,
            expected_error_message,
            project_based_client_data_provider,
            mocker,
    ):
        """The purpose of this test is to check flow of get_suite_id_log_error function for single
        suite with baselines mode."""
        (
            environment,
            api_request_handler,
            project_based_client,
        ) = project_based_client_data_provider
        suite_mode = SuiteModes.single_suite_baselines
        project_based_client.api_request_handler.resolve_suite_id_using_name.return_value = (-1, "Any Error")
        project_based_client.api_request_handler.suites_data_from_provider.suite_id = None
        project_based_client.api_request_handler.get_suite_ids.return_value = (
            get_suite_ids_result
        )
        expected_elog_calls = []
        if expected_error_message:
            expected_elog_calls = [mocker.call(expected_error_message)]
        result_suite_id, result_code, suite_added = project_based_client.get_suite_id(suite_mode)

        assert (
                result_suite_id == expected_suite_id
        ), f"Expected suite id: {expected_suite_id} but got {result_suite_id} instead."
        assert (
                result_code == expected_result_code
        ), f"Expected result code: {expected_result_code} but got {result_code} instead."
        environment.elog.assert_has_calls(expected_elog_calls)

    @pytest.mark.project_based_client
    def test_get_suite_id_unknown_suite_mode(
            self, project_based_client_data_provider, mocker
    ):
        """The purpose of this test is to check that get_suite_id will return -1 and print
        proper message when unknown suite mode will be returned during execution."""
        (
            environment,
            api_request_handler,
            project_based_client,
        ) = project_based_client_data_provider
        suite_mode = 4
        expected_result_code = -1
        expected_suite_id = -1
        project_based_client.api_request_handler.suites_data_from_provider.suite_id = None
        expected_elog_calls = [
            mocker.call(
                FAULT_MAPPING["unknown_suite_mode"].format(suite_mode=suite_mode)
            )
        ]
        result_suite_id, result_code, suite_added = project_based_client.get_suite_id(suite_mode)

        assert (
                result_suite_id == expected_suite_id
        ), f"Expected suite id: {expected_suite_id} but got {result_suite_id} instead."
        assert (
                result_code == expected_result_code
        ), f"Expected result code: {expected_result_code} but got {result_code} instead."
        environment.elog.assert_has_calls(expected_elog_calls)

    @pytest.mark.project_based_client
    def test_check_suite_id_returns_id(self, project_based_client_data_provider):
        """The purpose of this test is to check that check_suite_id function will success,
        when suite ID exists under specified project."""
        (
            environment,
            api_request_handler,
            project_based_client,
        ) = project_based_client_data_provider
        expected_result_code = 1
        project_id = 2
        project_based_client.api_request_handler.check_suite_id.return_value = (True, "")

        result_code = project_based_client.check_suite_id(project_id=project_id)

        assert (
                result_code == expected_result_code
        ), f"Expected to get {result_code} as result code, but got {expected_result_code} instead."

    @pytest.mark.project_based_client
    def test_check_suite_id_prints_error_message(
            self, project_based_client_data_provider, mocker
    ):
        """The purpose of this test is to check that proper message would be printed to the user
        and program will quit when suite ID is not present in TestRail."""
        (
            environment,
            api_request_handler,
            project_based_client,
        ) = project_based_client_data_provider
        suite_id = 1
        expected_result_code = -1
        project_id = 2
        project_based_client.api_request_handler.check_suite_id.return_value = (
            False,
            FAULT_MAPPING["missing_suite"].format(suite_id=suite_id),
        )

        result_code = project_based_client.check_suite_id(project_id=project_id)
        expected_elog_calls = [
            mocker.call(FAULT_MAPPING["missing_suite"].format(suite_id=suite_id))
        ]

        environment.elog.assert_has_calls(expected_elog_calls)
        assert (
                result_code == expected_result_code
        ), f"Expected to get {expected_result_code} as result code, but got {result_code} instead."

    def test_resolve_suite_returns_valid_id(self, project_based_client_data_provider):
        """The purpose of this test is to check that resolve_suite returns a valid suite id."""
        (
            environment,
            api_request_handler,
            project_based_client,
        ) = project_based_client_data_provider
        api_request_handler.suites_data_from_provider.suite_id = 1
        api_request_handler.check_suite_id.return_value = (True, "")

        project_based_client.resolve_project()
        suite_id, suite_added = project_based_client.resolve_suite()
        assert (
                suite_id == 1
        ), f"Expected suite id 1 but got {suite_id} instead."

    def test_create_or_update_test_run_calls_add_run(self, project_based_client_data_provider):
        """The purpose of this test is to check that calling the method without a run_id in the environment causes
        the add_run method of the request handler to be called."""
        (
            environment,
            api_request_handler,
            project_based_client,
        ) = project_based_client_data_provider
        environment.run_id = None
        api_request_handler.add_run.return_value = (1, "")
        project_based_client.resolve_project()
        run_id, error_message = project_based_client.create_or_update_test_run()

        project_based_client.api_request_handler.add_run.assert_called_once()
        assert (
                run_id == 1
        ), f"Expected run_id to be 1 but got {run_id} instead."
        assert (
                error_message == ""
        ), f"Expected error message to be None but got {error_message} instead."

    def test_create_or_update_test_run_calls_update_run(self, project_based_client_data_provider):
        """The purpose of this test is to check that calling the method with a run_id in the environment causes
        the update_run method of the request handler to be called."""
        (
            environment,
            api_request_handler,
            project_based_client,
        ) = project_based_client_data_provider
        environment.run_id = 1
        api_request_handler.update_run.return_value = (1, "")
        project_based_client.resolve_project()
        run_id, error_message = project_based_client.create_or_update_test_run()

        api_request_handler.update_run.assert_called_once()
        assert (
                run_id == 1
        ), f"Expected run_id to be 1 but got {run_id} instead."
        assert (
                error_message == ""
        ), f"Expected error message to be None but got {error_message} instead."

    def test_get_project_id(self, project_based_client_data_provider):
        """The purpose of this test is to check that the _get_project_id() will fall back to the environment.project_id
        when environment.project does not contain the project_id."""
        (
            environment,
            _,
            project_based_client,
        ) = project_based_client_data_provider

        assert (
                project_based_client._get_project_id() == environment.project_id
        ), (f"Expected to get {environment.project_id} from project_based_client.get_project_id but got"
            f" {project_based_client._get_project_id()} instead.")
