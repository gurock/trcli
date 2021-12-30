from typing import List
from trcli.api.api_request_handler import ProjectData
from trcli.api.results_uploader import ResultsUploader


def upload_results_inner_functions_mocker(
    results_uploader: ResultsUploader, mocker, failing_functions: List[str]
):
    mocker_functions = [
        get_suite_id_mocker,
        check_for_missing_sections_and_add_mocker,
        check_for_missing_test_cases_and_add_mocker,
        add_run_mocker,
        add_results_mocker,
        close_run_mocker,
    ]

    for mocker_function in mocker_functions:
        failing = (
            True
            if mocker_function.__name__.replace("_mocker", "") in failing_functions
            else False
        )
        mocker_function(results_uploader, mocker, failing=failing)


def get_project_id_mocker(
    results_uploader: ResultsUploader, project_id, error_message: str, failing=False
):
    if failing:
        results_uploader.api_request_handler.get_project_id.return_value = ProjectData(
            project_id=project_id, suite_mode=-1, error_message=error_message
        )
    else:
        results_uploader.api_request_handler.get_project_id.return_value = ProjectData(
            project_id=project_id, suite_mode=1, error_message=""
        )


def get_suite_id_mocker(results_uploader: ResultsUploader, mocker, failing=False):
    suite_id = 10
    results_uploader._ResultsUploader__get_suite_id = mocker.Mock()
    if failing:
        results_uploader._ResultsUploader__get_suite_id.return_value = (suite_id, -1)
    else:
        results_uploader._ResultsUploader__get_suite_id.return_value = (suite_id, 1)


def check_for_missing_sections_and_add_mocker(
    results_uploader: ResultsUploader, mocker, failing=False
):
    results_uploader._ResultsUploader__add_missing_sections = mocker.Mock()
    if failing:
        results_uploader._ResultsUploader__add_missing_sections.return_value = (
            [10],
            -1,
        )
    else:
        results_uploader._ResultsUploader__add_missing_sections.return_value = (
            [10],
            1,
        )


def check_for_missing_test_cases_and_add_mocker(
    results_uploader: ResultsUploader, mocker, failing=False
):
    results_uploader._ResultsUploader__add_missing_test_cases = mocker.Mock()
    if failing:
        results_uploader._ResultsUploader__add_missing_test_cases.return_value = (
            [20, 30],
            -1,
        )
    else:
        results_uploader._ResultsUploader__add_missing_test_cases.return_value = (
            [20, 30],
            1,
        )


def add_run_mocker(results_uploader: ResultsUploader, mocker=None, failing=False):
    if failing:
        results_uploader.api_request_handler.add_run.return_value = (
            [],
            "Failed to add run.",
        )
    else:
        results_uploader.api_request_handler.add_run.return_value = ([100], "")


def add_results_mocker(results_uploader: ResultsUploader, mocker=None, failing=False):
    if failing:
        results_uploader.api_request_handler.add_results.return_value = (
            [],
            "Failed to add results.",
        )
    else:
        results_uploader.api_request_handler.add_results.return_value = ([1, 2, 3], "")


def close_run_mocker(results_uploader: ResultsUploader, mocker=None, failing=False):
    if failing:
        results_uploader.api_request_handler.close_run.return_value = (
            [],
            "Failed to close run.",
        )
    else:
        results_uploader.api_request_handler.close_run.return_value = ([100], "")
