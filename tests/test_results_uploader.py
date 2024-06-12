import pytest

from tests.helpers.results_uploader_helper import (
    get_project_id_mocker,
    upload_results_inner_functions_mocker,
    api_request_handler_delete_mocker,
)
from tests.test_data.results_provider_test_data import (
    TEST_UPLOAD_RESULTS_FLOW_TEST_DATA,
    TEST_UPLOAD_RESULTS_FLOW_IDS,
    TEST_ADD_MISSING_SECTIONS_PROMPTS_USER_TEST_DATA,
    TEST_ADD_MISSING_SECTIONS_PROMPTS_USER_IDS,
    TEST_ADD_MISSING_TEST_CASES_PROMPTS_USER_TEST_DATA,
    TEST_ADD_MISSING_TEST_CASES_PROMPTS_USER_IDS,
    TEST_REVERT_FUNCTIONS_AND_EXPECTED,
    TEST_REVERT_FUNCTIONS_IDS,
    TEST_REVERT_FUNCTIONS_AND_EXPECTED_EXISTING_SUITE,
    TEST_REVERT_FUNCTIONS_IDS_EXISTING_SUITE,
)
from trcli.api.api_request_handler import ProjectData
from trcli.api.results_uploader import ResultsUploader
from trcli.constants import FAULT_MAPPING, PROMPT_MESSAGES, SuiteModes
from trcli.constants import ProjectErrors
from trcli.data_classes.data_parsers import MatchersParser
from trcli.readers.junit_xml import JunitParser


class TestResultsUploader:
    @pytest.fixture(scope="function")
    def result_uploader_data_provider(self, mocker):
        environment = mocker.patch("trcli.api.results_uploader.Environment")
        environment.host = "https://fake_host.com/"
        environment.project = "Fake project name"
        environment.project_id = 1
        environment.case_id = None
        environment.run_id = None
        environment.file = "results.xml"
        environment.case_matcher = MatchersParser.AUTO

        junit_file_parser = mocker.patch.object(JunitParser, "parse_file")
        api_request_handler = mocker.patch(
            "trcli.api.project_based_client.ApiRequestHandler"
        )
        results_uploader = ResultsUploader(
            environment=environment, suite=junit_file_parser
        )
        yield environment, api_request_handler, results_uploader

    @pytest.mark.results_uploader
    def test_project_name_missing_in_test_rail(
        self, result_uploader_data_provider, mocker
    ):
        """The purpose of this test is to check that proper message will be printed and trcli will terminate
        with proper code when project with name provided does not exist in TestRail."""
        (
            environment,
            api_request_handler,
            results_uploader,
        ) = result_uploader_data_provider
        exit_code = 1
        get_project_id_mocker(
            results_uploader=results_uploader,
            project_id=ProjectErrors.not_existing_project,
            error_message=f"{environment.project} project doesn't exist.",
            failing=True,
        )
        expected_elog_calls = [
            mocker.call(f"\n{environment.project} project doesn't exist.")
        ]

        with pytest.raises(SystemExit) as exception:
            results_uploader.upload_results()

        environment.elog.assert_has_calls(expected_elog_calls)
        assert (
            exception.type == SystemExit
        ), f"Expected SystemExit exception, but got {exception.type} instead."
        assert (
            exception.value.code == exit_code
        ), f"Expected exit code {exit_code}, but got {exception.value.code} instead."

    @pytest.mark.results_uploader
    @pytest.mark.parametrize(
        "error_type, error_message",
        [
            (ProjectErrors.other_error, "Unable to connect"),
            (
                ProjectErrors.multiple_project_same_name,
                FAULT_MAPPING["more_than_one_project"],
            ),
        ],
        ids=["Unknown error", "project name matches more than one result"],
    )
    def test_error_during_checking_of_project(
        self, error_type, error_message, result_uploader_data_provider, mocker
    ):
        """The purpose of this test is to check that proper message would be printed and trcli tool will
        terminate with proper code when errors occurs during project name check."""
        (
            environment,
            api_request_handler,
            results_uploader,
        ) = result_uploader_data_provider
        exit_code = 1
        get_project_id_mocker(
            results_uploader=results_uploader,
            project_id=error_type,
            error_message=error_message,
            failing=True,
        )
        expected_log_calls = [
            mocker.call(
                "\n"
                + FAULT_MAPPING["error_checking_project"].format(
                    error_message=error_message
                )
            )
        ]
        with pytest.raises(SystemExit) as exception:
            results_uploader.upload_results()

        environment.elog.assert_has_calls(expected_log_calls)
        assert (
            exception.type == SystemExit
        ), f"Expected SystemExit exception, but got {exception.type} instead."
        assert (
            exception.value.code == exit_code
        ), f"Expected exit code {exit_code}, but got {exception.value.code} instead."

    @pytest.mark.results_uploader
    @pytest.mark.parametrize(
        "failing_function",
        TEST_UPLOAD_RESULTS_FLOW_TEST_DATA,
        ids=TEST_UPLOAD_RESULTS_FLOW_IDS,
    )
    def test_upload_results_flow(
        self, failing_function, result_uploader_data_provider, mocker
    ):
        """The purpose of those tests is to check that proper message would be printed and trcli tool
        will terminate with proper code when one of the functions in the flow fails."""
        (
            environment,
            api_request_handler,
            results_uploader,
        ) = result_uploader_data_provider
        project_id = 10
        exit_code = 1
        environment.run_id = None
        get_project_id_mocker(
            results_uploader=results_uploader,
            project_id=project_id,
            error_message="",
            failing=True,
        )
        upload_results_inner_functions_mocker(
            results_uploader=results_uploader,
            mocker=mocker,
            failing_functions=[failing_function],
        )

        api_request_handler_delete_mocker(
            results_uploader=results_uploader,
            mocker=mocker,
            failing_functions=[],
        )

        with pytest.raises(SystemExit) as exception:
            results_uploader.upload_results()

        assert (
            exception.type == SystemExit
        ), f"Expected SystemExit exception, but got {exception.type} instead."
        assert (
            exception.value.code == exit_code
        ), f"Expected exit code {exit_code}, but got {exception.value.code} instead."

    @pytest.mark.parametrize(
        "run_id", [None, 101], ids=["No run ID provided", "Run ID provided"]
    )
    @pytest.mark.results_uploader
    def test_upload_results_successful(
        self, run_id, result_uploader_data_provider, mocker
    ):
        """The purpose of this test is to check if during successful run of upload_results proper messages
        would be printed."""
        (
            environment,
            api_request_handler,
            results_uploader,
        ) = result_uploader_data_provider
        project_id = 10
        environment.run_id = run_id
        get_project_id_mocker(
            results_uploader=results_uploader,
            project_id=project_id,
            error_message="",
            failing=True,
        )
        upload_results_inner_functions_mocker(
            results_uploader=results_uploader, mocker=mocker, failing_functions=[]
        )
        results_uploader.api_request_handler.check_automation_id_field.return_value = None
        results_uploader.api_request_handler.check_missing_test_cases_ids.return_value = ([], "")
        results_uploader.api_request_handler.delete_sections.return_value = ([], "")
        expected_log_calls = []
        if not run_id:
            calls = {
                2: mocker.call("Removing unnecessary empty sections that may have been created earlier. ", new_line=False),
                3: mocker.call("Removed 1 unused/empty section(s)."),
                4: mocker.call("Creating test run. ", new_line=False),
                5: mocker.call("Test run: https://fake_host.com/index.php?/runs/view/100"),
                6: mocker.call("Closing test run. ", new_line=False),
            }
        else:
            calls = {
                2: mocker.call("Removing unnecessary empty sections that may have been created earlier. ", new_line=False),
                3: mocker.call("Removed 1 unused/empty section(s)."),
                4: mocker.call("Updating test run. ", new_line=False),
                5: mocker.call("Test run: https://fake_host.com/index.php?/runs/view/101"),
                6: mocker.call("Closing test run. ", new_line=False),
            }

        results_uploader.upload_results()
        for index, call in calls.items():
            assert environment.log.call_args_list[index] == call

    @pytest.mark.results_uploader
    def test_add_missing_sections_no_missing_sections(
        self, result_uploader_data_provider
    ):
        """The purpose of this test is to check that add_missing_sections will return empty list
        and proper return code when there are no missing sections."""
        (
            environment,
            api_request_handler,
            results_uploader,
        ) = result_uploader_data_provider
        project_id = 1
        return_code = 1
        missing_sections = []
        results_uploader.api_request_handler.check_missing_section_ids.return_value = (
            missing_sections,
            "",
        )
        result = results_uploader.add_missing_sections(project_id)

        assert result == (
            missing_sections,
            return_code,
        ), f"Expected to get {missing_sections, return_code} as a result but got {result} instead."

    @pytest.mark.results_uploader
    @pytest.mark.parametrize(
        "user_response, missing_sections, expected_add_sections_error, expected_added_sections,"
        "expected_message, expected_result_code",
        TEST_ADD_MISSING_SECTIONS_PROMPTS_USER_TEST_DATA,
        ids=TEST_ADD_MISSING_SECTIONS_PROMPTS_USER_IDS,
    )
    def test_add_missing_sections_prompts_user(
        self,
        user_response,
        missing_sections,
        expected_add_sections_error,
        expected_added_sections,
        expected_message,
        expected_result_code,
        result_uploader_data_provider,
        mocker,
    ):
        """The purpose of this test is to check that add_missing_sections prompts user
        for adding missing sections."""
        (
            environment,
            api_request_handler,
            results_uploader,
        ) = result_uploader_data_provider
        project_id = 1
        results_uploader.api_request_handler.check_missing_section_ids.return_value = (
            missing_sections,
            "",
        )
        results_uploader.environment.get_prompt_response_for_auto_creation.return_value = (
            user_response
        )
        results_uploader.api_request_handler.data_provider.check_section_names_duplicates.return_value = (
            False
        )
        results_uploader.api_request_handler.add_sections.return_value = (
            expected_added_sections,
            expected_add_sections_error,
        )

        (
            result_added_sections,
            result_code,
        ) = results_uploader.add_missing_sections(project_id)
        expected_elog_calls = []
        expected_log_calls = []
        if "User did not agree to create" not in expected_message:
            expected_log_calls = [mocker.call(expected_message)]
        else:
            expected_elog_calls.append(mocker.call(expected_message))
        if expected_add_sections_error:
            expected_elog_calls.append(mocker.call(expected_add_sections_error))

        assert (
            result_code == expected_result_code
        ), f"Expected result_code {expected_result_code} but got {result_code} instead."
        assert (
            result_added_sections == expected_added_sections
        ), f"Expected sections to be added: {expected_added_sections} but got {result_added_sections} instead."
        environment.log.assert_has_calls(expected_log_calls)
        environment.elog.assert_has_calls(expected_elog_calls)
        environment.get_prompt_response_for_auto_creation.assert_called_with(
            PROMPT_MESSAGES["create_missing_sections"].format(
                project_name=environment.project
            )
        )

    @pytest.mark.results_uploader
    def test_add_missing_sections_error_checking(
        self, result_uploader_data_provider, mocker
    ):
        """The purpose of this test is to check that add_missing_sections will return empty list
        and -1 as a result code when check_missing_section_ids will fail. Proper message will be printed."""
        (
            environment,
            api_request_handler,
            results_uploader,
        ) = result_uploader_data_provider
        project_id = 1
        return_code = -1
        missing_sections = []
        error_message = "Connection Error."
        results_uploader.api_request_handler.check_missing_section_ids.return_value = (
            [],
            error_message,
        )
        result = results_uploader.add_missing_sections(project_id)
        expected_elog_calls = [
            mocker.call(
                FAULT_MAPPING["error_checking_missing_item"].format(
                    missing_item="missing sections", error_message=error_message
                )
            )
        ]

        environment.elog.assert_has_calls(expected_elog_calls)
        assert result == (
            missing_sections,
            return_code,
        ), f"Expected to get {missing_sections, return_code} as a result but got {result} instead."

    @pytest.mark.results_uploader
    @pytest.mark.parametrize(
        "user_response, missing_test_cases, expected_add_test_cases_error, expected_added_test_cases, "
        "expected_message, expected_result_code",
        TEST_ADD_MISSING_TEST_CASES_PROMPTS_USER_TEST_DATA,
        ids=TEST_ADD_MISSING_TEST_CASES_PROMPTS_USER_IDS,
    )
    def test_add_missing_test_cases_prompts_user(
        self,
        user_response,
        missing_test_cases,
        expected_add_test_cases_error,
        expected_added_test_cases,
        expected_message,
        expected_result_code,
        result_uploader_data_provider,
        mocker,
    ):
        """The purpose of this test is to check that add_missing_test_cases function will
        prompt the user for adding missing test cases."""
        (
            environment,
            api_request_handler,
            results_uploader,
        ) = result_uploader_data_provider
        results_uploader.api_request_handler.check_missing_test_cases_ids.return_value = (
            missing_test_cases,
            expected_message,
        )
        results_uploader.environment.get_prompt_response_for_auto_creation.return_value = (
            user_response
        )
        results_uploader.api_request_handler.add_cases.return_value = (
            expected_added_test_cases,
            expected_add_test_cases_error,
        )

        (
            result_added_test_cases,
            result_code,
        ) = results_uploader.add_missing_test_cases()

        expected_elog_calls = []
        expected_log_calls = []
        if "User did not agree to create" not in expected_message:
            expected_log_calls = [mocker.call(expected_message)]
        else:
            expected_elog_calls.append(mocker.call(expected_message))
        if expected_add_test_cases_error:
            expected_elog_calls.append(mocker.call(expected_add_test_cases_error))

        assert (
            result_code == expected_result_code
        ), f"Expected result_code {expected_result_code} but got {result_code} instead."
        assert (
            result_added_test_cases == expected_added_test_cases
        ), f"Expected test cases to be added: {expected_added_test_cases} but got {result_added_test_cases} instead."
        environment.log.assert_has_calls(expected_log_calls)
        environment.elog.assert_has_calls(expected_elog_calls)
        environment.get_prompt_response_for_auto_creation.assert_called_with(
            PROMPT_MESSAGES["create_missing_test_cases"].format(
                project_name=environment.project
            )
        )

    @pytest.mark.results_uploader
    def test_add_missing_test_cases_duplicated_case_names(
        self, result_uploader_data_provider, mocker
    ):
        """The purpose of this test is to check that proper warning will be printed when duplicated case
        names will be detected in result file."""

    def test_rollback_changes_empty_changelist(self, result_uploader_data_provider):
        """The purpose of this test is to check that rollback
        will not give unexpected results on empty changelist"""
        (
            environment,
            api_request_handler,
            results_uploader,
        ) = result_uploader_data_provider

        results_uploader.project = ProjectData(
            project_id=1,
            suite_mode=SuiteModes.single_suite,
            error_message=""
        )

        assert (
            results_uploader.rollback_changes() == []
        ), "No revert function invoked inside so revert_changes output should be empty"

    @pytest.mark.results_uploader
    @pytest.mark.parametrize(
        "failing_function, expected_result",
        TEST_REVERT_FUNCTIONS_AND_EXPECTED,
        ids=TEST_REVERT_FUNCTIONS_IDS,
    )
    def test_rollback_changes_after_error(
        self, result_uploader_data_provider, failing_function, expected_result, mocker
    ):
        """The purpose of this test is to check that if rollback behave properly
        when no permissions on deleting resources on every stage"""
        (
            environment,
            api_request_handler,
            results_uploader,
        ) = result_uploader_data_provider

        results_uploader.project = ProjectData(
            project_id=1,
            suite_mode=SuiteModes.multiple_suites,
            error_message=""
        )

        api_request_handler_delete_mocker(
            results_uploader=results_uploader,
            mocker=mocker,
            failing_functions=[failing_function],
        )

        assert (
            results_uploader.rollback_changes(1, True, [1, 2], [1, 2], 2) == expected_result
        ), "Revert process not completed as expected in test."

    @pytest.mark.results_uploader
    @pytest.mark.parametrize(
        "failing_function, expected_result",
        TEST_REVERT_FUNCTIONS_AND_EXPECTED_EXISTING_SUITE,
        ids=TEST_REVERT_FUNCTIONS_IDS_EXISTING_SUITE,
    )
    def test_rollback_changes_after_error_doesnt_delete_existing_suite(
        self, result_uploader_data_provider, failing_function, expected_result, mocker
    ):
        """The purpose of this test is to check that if rollback behave properly
        when the suite already exists and thus cannot be deleted"""
        (
            environment,
            api_request_handler,
            results_uploader,
        ) = result_uploader_data_provider

        results_uploader.project = ProjectData(
            project_id=1,
            suite_mode=SuiteModes.multiple_suites,
            error_message=""
        )

        suite_id = 1234
        results_uploader.api_request_handler.suites_data_from_provider.suite_id = (
            suite_id
        )
        results_uploader.api_request_handler.check_suite_id.return_value = (True, "")

        api_request_handler_delete_mocker(
            results_uploader=results_uploader,
            mocker=mocker,
            failing_functions=[failing_function],
        )

        assert (
            results_uploader.rollback_changes(suite_id, False, [1, 2], [1, 2], 2) == expected_result
        ), "Revert process not completed as expected in test."
