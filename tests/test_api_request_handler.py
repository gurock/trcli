import json
from unittest.mock import patch, mock_open, call

import requests
import pytest
from pathlib import Path
from serde.json import from_json
from tests.helpers.api_client_helpers import TEST_RAIL_URL, create_url
from trcli.cli import Environment
from trcli.api.api_request_handler import ApiRequestHandler, ProjectData
from trcli.api.api_client import APIClient
from trcli.data_classes.dataclass_testrail import TestRailSuite
from trcli.constants import ProjectErrors, FAULT_MAPPING
from trcli.data_classes.data_parsers import MatchersParser


@pytest.fixture(scope="function")
def handler_maker():
    def _make_handler(verify=False, custom_json=None):
        api_client = APIClient(host_name=TEST_RAIL_URL)
        environment = Environment()
        environment.project = "Test Project"
        environment.batch_size = 10
        environment.case_matcher = MatchersParser.AUTO
        if custom_json is None:
            json_path = Path(__file__).parent / "test_data/json/api_request_handler.json"
        else:
            json_path = custom_json
        file_json = open(json_path)
        json_string = json.dumps(json.load(file_json))
        test_input = from_json(TestRailSuite, json_string)
        api_request = ApiRequestHandler(environment, api_client, test_input, verify)
        return api_request

    return _make_handler


@pytest.fixture(scope="function")
def api_request_handler(handler_maker):
    yield handler_maker()


@pytest.fixture(scope="function")
def api_request_handler_verify(handler_maker):
    yield handler_maker(verify=True)


@pytest.fixture(scope="function")
def api_request_handler_update_case_json(handler_maker):
    json_path = Path(__file__).parent / "test_data/json/update_case_result_single_with_id.json"
    yield handler_maker(custom_json=json_path, verify=False)


class TestApiRequestHandler:
    @pytest.mark.api_handler
    def test_return_project(self, api_request_handler: ApiRequestHandler, requests_mock):
        mocked_response = {
            "offset": 0,
            "limit": 250,
            "size": 2,
            "_links": {
                "next": None,
                "prev": None,
            },
            "projects": [
                {"id": 1, "name": "DataHub", "suite_mode": 1},
                {"id": 2, "name": "Test Project", "suite_mode": 1},
                {"id": 3, "name": "DataHub", "suite_mode": 1},
            ],
        }
        requests_mock.get(create_url("get_projects"), json=mocked_response)
        assert api_request_handler.get_project_data("Test Project") == ProjectData(
            project_id=2, suite_mode=1, error_message=""
        ), "Get project should return proper project data object"
        assert api_request_handler.get_project_data("DataHub") == ProjectData(
            project_id=ProjectErrors.multiple_project_same_name,
            suite_mode=-1,
            error_message="Given project name matches more than one result."
            "Please specify which should be used using the --project-id argument",
        ), "Get project should return proper project data object"
        assert api_request_handler.get_project_data("DataHub", 2) == ProjectData(
            project_id=ProjectErrors.multiple_project_same_name,
            suite_mode=-1,
            error_message="Given project name matches more than one result."
            "Please specify which should be used using the --project-id argument",
        ), (
            "Get project should return proper project data object when passing"
            "project_id and project_id doesn't match the response"
        )
        assert api_request_handler.get_project_data("DataHub", 3) == ProjectData(
            project_id=3, suite_mode=1, error_message=""
        ), (
            "Get project should return proper project data object when passing"
            "project_id and project_id matches response"
        )

        assert api_request_handler.get_project_data("Some project") == ProjectData(
            project_id=ProjectErrors.not_existing_project,
            suite_mode=-1,
            error_message="Please specify a valid project name using the --project argument",
        ), "Get project should return proper project data object"

    @pytest.mark.api_handler
    def test_return_project_legacy_response(self, api_request_handler: ApiRequestHandler, requests_mock):
        mocked_response = [
            {"id": 1, "name": "DataHub", "suite_mode": 1},
            {"id": 2, "name": "Test Project", "suite_mode": 1},
            {"id": 3, "name": "DataHub", "suite_mode": 1},
        ]

        requests_mock.get(create_url("get_projects"), json=mocked_response)
        assert api_request_handler.get_project_data("Test Project") == ProjectData(
            project_id=2, suite_mode=1, error_message=""
        ), "Get project should return proper project data object"

    @pytest.mark.api_handler
    def test_return_project_legacy_response_with_buggy_authentication_prefix(
        self, api_request_handler: ApiRequestHandler, requests_mock
    ):
        mocked_response = [
            {"id": 1, "name": "DataHub", "suite_mode": 1},
            {"id": 2, "name": "Test Project", "suite_mode": 1},
            {"id": 3, "name": "DataHub", "suite_mode": 1},
        ]

        requests_mock.get(
            create_url("get_projects"), text=f"USER AUTHENTICATION SUCCESSFUL!\n" + json.dumps(mocked_response)
        )
        assert api_request_handler.get_project_data("Test Project") == ProjectData(
            project_id=2, suite_mode=1, error_message=""
        ), "Get project should return proper project data object"

    @pytest.mark.api_handler
    def test_check_suite_exists(self, api_request_handler: ApiRequestHandler, requests_mock):
        project_id = 3
        mocked_response = [
            {"id": 4, "name": "Suite1", "description": "Test1", "project_id": 3},
            {"id": 5, "name": "Suite2", "description": "Test2", "project_id": 3},
        ]
        requests_mock.get(create_url(f"get_suites/{project_id}"), json=mocked_response)
        assert api_request_handler.check_suite_id(project_id) == (
            True,
            "",
        ), "Suite id in test data should exist in mocked response."
        api_request_handler.suites_data_from_provider.suite_id = 6
        assert api_request_handler.check_suite_id(project_id) == (
            False,
            FAULT_MAPPING["missing_suite"].format(suite_id=6),
        ), "Given suite id should NOT exist in mocked response."

    @pytest.mark.api_handler
    def test_check_suite_exists_with_pagination(self, api_request_handler: ApiRequestHandler, requests_mock):
        project_id = 3
        mocked_response = {
            "offset": 0,
            "limit": 250,
            "size": 2,
            "_links": {"next": None, "prev": None},
            "suites": [
                {"id": 4, "name": "Suite1", "description": "Test1", "project_id": 3},
                {"id": 5, "name": "Suite2", "description": "Test2", "project_id": 3},
            ],
        }
        requests_mock.get(create_url(f"get_suites/{project_id}"), json=mocked_response)

        api_request_handler.suites_data_from_provider.suite_id = 4
        assert api_request_handler.check_suite_id(project_id) == (
            True,
            "",
        ), "Suite id in test data should exist in mocked response."

        api_request_handler.suites_data_from_provider.suite_id = 6
        assert api_request_handler.check_suite_id(project_id) == (
            False,
            FAULT_MAPPING["missing_suite"].format(suite_id=6),
        ), "Given suite id should NOT exist in mocked response."

    @pytest.mark.api_handler
    def test_add_suite(self, api_request_handler: ApiRequestHandler, requests_mock):
        project_id = 3
        mocked_response = {
            "description": "..",
            "id": 1,
            "name": "Setup & Installation",
            "project_id": 1,
            "url": "http:///testrail/index.php?/suites/view/1",
        }
        api_request_handler.suites_data_from_provider.suite_id = None
        api_request_handler.suites_data_from_provider.name = None
        requests_mock.post(create_url(f"add_suite/{project_id}"), json=mocked_response)
        resources_added, error = api_request_handler.add_suites(project_id)

        assert (
            resources_added[0]["name"] == mocked_response["name"]
        ), "Added suite name doesn't match mocked response name."
        assert (
            resources_added[0]["suite_id"] == mocked_response["id"]
        ), "Added suite id doesn't match mocked response id."
        assert error == "", "Error occurred in add_suite"

        assert (
            api_request_handler.suites_data_from_provider.suite_id == mocked_response["id"]
        ), "Added suite id in DataProvider doesn't match mocked response id."

    @pytest.mark.api_handler
    def test_check_missing_sections_true(self, api_request_handler: ApiRequestHandler, requests_mock, mocker):
        project_id = 3
        update_data_mock = mocker.patch("trcli.api.api_request_handler.ApiDataProvider.update_data")
        mocked_response = {
            "_links": {"next": None, "prev": None},
            "sections": [
                {
                    "id": 0,
                    "suite_id": 4,
                    "name": "Skipped test",
                }
            ],
        }

        requests_mock.get(create_url(f"get_sections/{project_id}&suite_id=4"), json=mocked_response)

        missing, _ = api_request_handler.check_missing_section_ids(project_id)
        update_data_mock.assert_called_with(section_data=[{"section_id": 0, "suite_id": 4, "name": "Skipped test"}])
        assert missing, "There should be missing section"

    @pytest.mark.api_handler
    def test_check_missing_sections_false(self, api_request_handler: ApiRequestHandler, requests_mock, mocker):
        project_id = 3
        update_data_mock = mocker.patch("trcli.api.api_request_handler.ApiDataProvider.update_data")
        mocked_response = {
            "_links": {"next": None, "prev": None},
            "sections": [
                {
                    "id": 1,
                    "suite_id": 4,
                    "name": "Skipped test",
                },
                {
                    "id": 2,
                    "suite_id": 4,
                    "name": "Passed test",
                },
            ],
        }

        requests_mock.get(create_url(f"get_sections/{project_id}&suite_id=4"), json=mocked_response)

        missing, _ = api_request_handler.check_missing_section_ids(project_id)
        update_data_mock.assert_called_with(
            section_data=[
                {"name": "Skipped test", "section_id": 1, "suite_id": 4},
                {"name": "Passed test", "section_id": 2, "suite_id": 4},
            ]
        )
        assert not missing, "There should be no missing section"

    @pytest.mark.api_handler
    def test_add_sections(self, api_request_handler: ApiRequestHandler, requests_mock):
        project_id = 3
        mocked_response = {
            "id": 1235,
            "suite_id": 4,
            "name": "Passed test",
        }

        requests_mock.post(create_url(f"add_section/{project_id}"), json=mocked_response)
        resources_added, error = api_request_handler.add_sections(project_id)

        assert (
            resources_added[0]["name"] == mocked_response["name"]
        ), "Added section name doesn't match mocked response name."
        assert (
            resources_added[0]["section_id"] == mocked_response["id"]
        ), "Added section id doesn't match mocked response id."
        assert error == "", "Error occurred in add_section"

        assert (
            api_request_handler.suites_data_from_provider.testsections[1].section_id == mocked_response["id"]
        ), "Added section id in DataProvider doesn't match mocked response id."

    @pytest.mark.api_handler
    def test_add_section_and_cases(self, api_request_handler: ApiRequestHandler, requests_mock):
        project_id = 3
        mocked_response_for_section = {
            "id": 12345,
            "suite_id": 4,
            "name": "Passed test",
            "custom_automation_id": "className.testCase",
        }

        mocked_response_for_case_1 = {
            "id": 4,
            "suite_id": 4,
            "section_id": 1234,
            "title": "testCase2",
            "custom_automation_id": "className.testCase",
        }

        mocked_response_for_case_2 = {
            "id": 3,
            "suite_id": 4,
            "section_id": 12345,
            "title": "testCase3",
            "custom_automation_id": "className.testCase",
        }

        requests_mock.post(create_url(f"add_section/{project_id}"), json=mocked_response_for_section)
        requests_mock.post(
            create_url(f"add_case/{mocked_response_for_case_1['section_id']}"),
            json=mocked_response_for_case_1,
        )
        requests_mock.post(
            create_url(f"add_case/{mocked_response_for_case_2['section_id']}"),
            json=mocked_response_for_case_2,
        )

        api_request_handler.add_sections(project_id)
        resources_added, error = api_request_handler.add_cases()

        assert sorted([case["title"] for case in resources_added]) == sorted(
            [
                mocked_response_for_case_1["title"],
                mocked_response_for_case_2["title"],
            ]
        ), "Added case title doesn't match mocked response title"
        assert sorted([case["case_id"] for case in resources_added]) == sorted(
            [
                mocked_response_for_case_1["id"],
                mocked_response_for_case_2["id"],
            ]
        ), "Added case id doesn't match mocked response id"
        assert error == "", "Error occurred in add_case"

    @pytest.mark.api_handler
    def test_add_run(self, api_request_handler: ApiRequestHandler, requests_mock):
        project_id = 3
        run_name = "Test run name"

        mocked_response = {
            "description": None,
            "id": 81,
            "include_all": True,
            "is_completed": False,
        }

        requests_mock.post(create_url(f"add_run/{project_id}"), json=mocked_response)
        resources_added, error = api_request_handler.add_run(project_id, run_name)
        assert mocked_response["id"] == resources_added, "Added run id doesn't match mocked response id"
        assert error == "", "Error occurred in add_case"

    @pytest.mark.api_handler
    def test_add_results(self, api_request_handler: ApiRequestHandler, requests_mock):
        run_id = 2
        result_id = 9
        mocked_response = [
            {
                "assignedto_id": 1,
                "comment": "This test failed: ..",
                "created_by": 1,
                "created_on": 1393851801,
                "defects": "TR-1",
                "elapsed": "5m",
                "id": result_id,
                "status_id": 5,
                "test_id": 4,
                "version": "1.0RC1",
            }
        ]
        requests_mock.post(create_url(f"add_results_for_cases/{run_id}"), json=mocked_response)

        tests_mocked_response = {
            "offset": 0,
            "limit": 250,
            "size": 4,
            "_links": {"next": None, "prev": None},
            "tests": [
                {
                    "id": 4,
                    "case_id": 1,
                    "status_id": 5,
                    "assignedto_id": None,
                    "run_id": run_id,
                    "title": "Fail To Login With Invalid Password",
                }
            ],
        }
        requests_mock.get(create_url(f"get_tests/{run_id}"), json=tests_mocked_response)

        attachments_mock_response = {"attachment_id": 123}

        requests_mock.post(create_url(f"add_attachment_to_result/{result_id}"), json=attachments_mock_response)

        with patch("builtins.open", mock_open()) as mock_file:
            resources_added, error, results_added = api_request_handler.add_results(run_id)
            assert [mocked_response] == resources_added, "Invalid response from add_results"
            assert error == "", "Error occurred in add_results"
            assert results_added == len(
                mocked_response
            ), f"Expected {len(mocked_response)} results to be added but got {results_added} instead."
            mock_file.assert_any_call("./path1", "rb")
            mock_file.assert_any_call("./path2", "rb")

    @pytest.mark.api_handler
    def test_close_run(self, api_request_handler: ApiRequestHandler, requests_mock):
        run_id = 2
        mocked_response = {
            "assignedto_id": 6,
            "blocked_count": 0,
            "completed_on": "20211212",
        }

        requests_mock.post(create_url(f"close_run/{run_id}"), json=mocked_response)
        resources_added, error = api_request_handler.close_run(run_id)
        assert mocked_response == resources_added, "Invalid response from close_run"
        assert error == "", "Error occurred in close_run"

    @pytest.mark.api_handler
    def test_check_missing_test_cases_ids_true(self, api_request_handler: ApiRequestHandler, requests_mock, mocker):
        project_id = 3
        suite_id = api_request_handler.suites_data_from_provider.suite_id
        update_data_mock = mocker.patch("trcli.api.api_request_handler.ApiDataProvider.update_data")
        mocked_response_page_1 = {
            "_links": {
                "next": None,
                "prev": None,
            },
            "cases": [
                {"title": "testCase1", "custom_automation_id": "Skipped test.testCase1", "id": 1, "section_id": 1234},
                {"title": "testCase2", "custom_automation_id": "Skipped test.testCase2", "id": 2, "section_id": 1234},
            ],
        }
        requests_mock.get(
            create_url(f"get_cases/{project_id}&suite_id={suite_id}"),
            json=mocked_response_page_1,
        )
        missing_ids, error = api_request_handler.check_missing_test_cases_ids(project_id)

        update_data_mock.assert_called_with(
            case_data=[
                {
                    "case_id": 1,
                    "custom_automation_id": "Skipped test.testCase1",
                    "section_id": 1234,
                    "title": "testCase1",
                },
                {
                    "case_id": 2,
                    "custom_automation_id": "Skipped test.testCase2",
                    "section_id": 1234,
                    "title": "testCase2",
                },
            ]
        )
        assert missing_ids, "There is one missing test case"
        assert error == "", "Error occurred in check"

    @pytest.mark.api_handler
    def test_check_missing_test_cases_ids_false(self, api_request_handler: ApiRequestHandler, requests_mock, mocker):
        project_id = 3
        suite_id = api_request_handler.suites_data_from_provider.suite_id
        update_data_mock = mocker.patch("trcli.api.api_request_handler.ApiDataProvider.update_data")
        mocked_response_page_1 = {
            "_links": {
                "next": f"/api/v2/get_cases/{project_id}&suite_id={suite_id}&limit=1&offset=1",
                "prev": None,
            },
            "cases": [
                {"title": "testCase1", "custom_automation_id": "Skipped test.testCase1", "id": 1, "section_id": 1234},
                {"title": "testCase2", "custom_automation_id": "Skipped test.testCase2", "id": 2, "section_id": 1234},
            ],
        }
        mocked_response_page_2 = {
            "_links": {"next": None, "prev": None},
            "cases": [
                {"title": "testCase3", "custom_automation_id": "Passed test.testCase3", "id": 1, "section_id": 2},
            ],
        }
        requests_mock.get(
            create_url(f"get_cases/{project_id}&suite_id={suite_id}"),
            json=mocked_response_page_1,
        )
        requests_mock.get(
            create_url(f"get_cases/{project_id}&suite_id={suite_id}&limit=1&offset=1"),
            json=mocked_response_page_2,
        )
        missing_ids, error = api_request_handler.check_missing_test_cases_ids(project_id)
        update_data_mock.assert_called_with(
            case_data=[
                {
                    "case_id": 1,
                    "custom_automation_id": "Skipped test.testCase1",
                    "section_id": 1234,
                    "title": "testCase1",
                },
                {
                    "case_id": 2,
                    "custom_automation_id": "Skipped test.testCase2",
                    "section_id": 1234,
                    "title": "testCase2",
                },
                {"case_id": 1, "custom_automation_id": "Passed test.testCase3", "section_id": 2, "title": "testCase3"},
            ]
        )
        assert not missing_ids, "No missing ids"
        assert error == "", "No error should have occurred"

    @pytest.mark.api_handler
    def test_get_suite_ids(self, api_request_handler: ApiRequestHandler, requests_mock):
        project_id = 3
        mocked_response = [
            {"id": 100, "name": "Master"},
            {"id": 101, "name": "Smoke"},
        ]

        requests_mock.get(create_url(f"get_suites/{project_id}"), json=mocked_response)
        resources_added, error = api_request_handler.get_suite_ids(project_id)
        assert (
            resources_added[0] == mocked_response[0]["id"] and resources_added[1] == mocked_response[1]["id"]
        ), "ID in response doesn't match mocked response"

    @pytest.mark.api_handler
    def test_get_suite_ids_error(self, api_request_handler: ApiRequestHandler, requests_mock):
        project_id = 3

        requests_mock.get(create_url(f"get_suites/{project_id}"), exc=requests.exceptions.ConnectTimeout)

        suite_ids, error = api_request_handler.get_suite_ids(project_id)

        assert suite_ids == [], "Should return empty list on API error"
        assert (
            error == "Your upload to TestRail did not receive a successful response from your TestRail Instance."
            " Please check your settings and try again."
        ), "Should return connection error message"

    @pytest.mark.api_handler
    def test_resolve_suite_id_using_name(self, api_request_handler: ApiRequestHandler, requests_mock, mocker):
        project_id = 3
        suite_name = "Suite2"
        api_request_handler.suites_data_from_provider.name = suite_name

        update_data_mock = mocker.patch("trcli.api.api_request_handler.ApiDataProvider.update_data")

        mocked_response = {
            "offset": 0,
            "limit": 250,
            "size": 2,
            "_links": {"next": None, "prev": None},
            "suites": [
                {"id": 4, "name": "Suite1", "description": "Test1", "project_id": 3},
                {"id": 5, "name": "Suite2", "description": "Test2", "project_id": 3},
            ],
        }

        requests_mock.get(create_url(f"get_suites/{project_id}"), json=mocked_response)

        suite_id, error = api_request_handler.resolve_suite_id_using_name(project_id)

        assert suite_id == 5, "Should return the correct suite ID for matching name with pagination"
        assert error == "", "Should have no error message"

        update_data_mock.assert_called_once_with([{"suite_id": 5, "name": "Suite2"}])

    @pytest.mark.api_handler
    def test_resolve_suite_id_using_name_error(self, api_request_handler: ApiRequestHandler, requests_mock):
        project_id = 3

        requests_mock.get(create_url(f"get_suites/{project_id}"), exc=requests.exceptions.ConnectTimeout)

        suite_id, error = api_request_handler.resolve_suite_id_using_name(project_id)

        assert suite_id == -1, "Should return -1 on API error"
        assert (
            error == "Your upload to TestRail did not receive a successful response from your TestRail Instance."
            " Please check your settings and try again."
        ), "Should return connection error message"

    @pytest.mark.api_handler
    def test_return_project_error(self, api_request_handler: ApiRequestHandler, requests_mock):

        requests_mock.get(create_url("get_projects"), exc=requests.exceptions.ConnectTimeout)
        assert api_request_handler.get_project_data("Test Project") == ProjectData(
            project_id=-3,
            suite_mode=-1,
            error_message="Your upload to TestRail did not receive a successful response from your TestRail Instance."
            " Please check your settings and try again.",
        ), "Get project should return proper project data object with error"

    @pytest.mark.api_handler
    def test_add_suite_error(self, api_request_handler: ApiRequestHandler, requests_mock):

        project_id = 3
        api_request_handler.suites_data_from_provider.suite_id = None
        api_request_handler.suites_data_from_provider.name = None
        requests_mock.post(
            create_url(f"add_suite/{project_id}"),
            exc=requests.exceptions.ConnectTimeout,
        )
        resources_added, error = api_request_handler.add_suites(project_id)
        assert resources_added == [], "No resources should be added"

        assert (
            error == "Your upload to TestRail did not receive a successful response from your TestRail Instance."
            " Please check your settings and try again."
        ), "Connection error is expected"

    @pytest.mark.api_handler
    def test_add_sections_error(self, api_request_handler: ApiRequestHandler, requests_mock):
        project_id = 3
        requests_mock.post(
            create_url(f"add_section/{project_id}"),
            exc=requests.exceptions.ConnectTimeout,
        )
        resources_added, error = api_request_handler.add_sections(project_id)

        assert resources_added == [], "No resources should be added"
        assert (
            error == "Your upload to TestRail did not receive a successful response from your TestRail Instance."
            " Please check your settings and try again."
        ), "Connection error is expected"

        assert (
            api_request_handler.suites_data_from_provider.testsections[1].section_id is None
        ), "No resources should be added to DataProvider"

    @pytest.mark.api_handler
    def test_add_section_and_cases_error(self, api_request_handler: ApiRequestHandler, requests_mock):
        project_id = 3
        mocked_response_for_section = {
            "id": 12345,
            "suite_id": 4,
            "name": "Passed test",
        }

        mocked_response_for_case_1 = {
            "id": 4,
            "suite_id": 4,
            "section_id": 1234,
            "title": "testCase2",
            "custom_automation_id": "Skipped test.testCase2",
        }

        mocked_response_for_case_2 = {
            "id": 3,
            "suite_id": 4,
            "section_id": 12345,
            "title": "testCase3",
            "custom_automation_id": "Passed test.testCase3",
        }

        requests_mock.post(create_url(f"add_section/{project_id}"), json=mocked_response_for_section)
        requests_mock.post(
            create_url(f"add_case/{mocked_response_for_case_1['section_id']}"),
            json=mocked_response_for_case_1,
        )
        requests_mock.post(
            create_url(f"add_case/{mocked_response_for_case_2['section_id']}"),
            exc=requests.exceptions.ConnectTimeout,
        )

        api_request_handler.add_sections(project_id)
        resources_added, error = api_request_handler.add_cases()

        assert [case["title"] for case in resources_added] == [
            mocked_response_for_case_1["title"]
        ], "Added case title doesn't match mocked response title"
        assert [case["case_id"] for case in resources_added] == [
            mocked_response_for_case_1["id"],
        ], "Added case id doesn't match mocked response id"
        assert (
            error == "Your upload to TestRail did not receive a successful response from your TestRail Instance."
            " Please check your settings and try again."
        ), "Connection error is expected"

    @pytest.mark.api_handler
    def test_add_results_error(self, api_request_handler: ApiRequestHandler, requests_mock):
        run_id = 3
        requests_mock.post(
            create_url(f"add_results_for_cases/{run_id}"),
            exc=requests.exceptions.ConnectTimeout,
        )
        tests_mocked_response = {
            "offset": 0,
            "limit": 250,
            "size": 4,
            "_links": {"next": None, "prev": None},
            "tests": [
                {
                    "id": 18319,
                    "case_id": 6086,
                    "status_id": 5,
                    "assignedto_id": None,
                    "run_id": run_id,
                    "title": "Fail To Login With Invalid Password",
                }
            ],
        }
        requests_mock.get(create_url(f"get_tests/{run_id}"), json=tests_mocked_response)
        resources_added, error, results_added = api_request_handler.add_results(run_id)
        assert resources_added == [], "Expected empty list of added resources"
        assert (
            error == "Your upload to TestRail did not receive a successful response from your TestRail Instance."
            " Please check your settings and try again."
        ), "Connection error is expected"
        assert results_added == 0, "Expected 0 resources to be added."

    @pytest.mark.api_handler
    def test_add_results_keyboard_interrupt(self, api_request_handler: ApiRequestHandler, requests_mock, mocker):
        run_id = 3
        requests_mock.post(
            create_url(f"add_results_for_cases/{run_id}"),
            exc=requests.exceptions.ConnectTimeout,
        )
        mocker.patch("trcli.api.api_request_handler.as_completed", side_effect=KeyboardInterrupt)
        with pytest.raises(KeyboardInterrupt) as exception:
            api_request_handler.add_results(run_id)

    @pytest.mark.api_handler
    def test_add_suite_with_verify(self, api_request_handler_verify: ApiRequestHandler, requests_mock):
        project_id = 3
        mocked_response = {
            "description": "..",
            "id": 1,
            "name": "Suite1",
            "project_id": 1,
            "url": "http:///testrail/index.php?/suites/view/1",
        }

        api_request_handler_verify.suites_data_from_provider.suite_id = None
        requests_mock.post(create_url(f"add_suite/{project_id}"), json=mocked_response)
        resources_added, error = api_request_handler_verify.add_suites(project_id)
        assert error == "", "There should be no error in verification."

    @pytest.mark.api_handler
    def test_add_section_with_verify(self, handler_maker, requests_mock):
        project_id = 3
        mocked_response = {
            "id": 1235,
            "suite_id": 4,
            "name": "Passed test",
            "description": "Some description",
        }

        requests_mock.post(create_url(f"add_section/{project_id}"), json=mocked_response)
        api_request_handler_verify = handler_maker(verify=True)
        resources_added, error = api_request_handler_verify.add_sections(project_id)
        assert error == "", "There should be no error in verification."
        mocked_response["suite_id"] = 0
        api_request_handler_verify = handler_maker(verify=True)
        resources_added, error = api_request_handler_verify.add_sections(project_id)
        assert (
            error == "Data verification failed. Server added different resource than expected."
        ), "There should be error in verification."

    @pytest.mark.api_handler
    def test_add_case_with_verify(self, api_request_handler_verify: ApiRequestHandler, requests_mock):
        mocked_response_for_case = {
            "id": 3,
            "suite_id": 4,
            "section_id": 1234,
            "title": "testCase2",
            "estimate": "30s",
            "custom_automation_id": "Skipped test.testCase2",
        }

        requests_mock.post(
            create_url(f"add_case/{mocked_response_for_case['section_id']}"),
            json=mocked_response_for_case,
        )
        del api_request_handler_verify.suites_data_from_provider.testsections[1].testcases[0]
        resources_added, error = api_request_handler_verify.add_cases()
        assert error == "", "There should be no error in verification."
        mocked_response_for_case["estimate"] = "60s"
        api_request_handler_verify.suites_data_from_provider.testsections[0].testcases[1].case_id = None
        resources_added, error = api_request_handler_verify.add_cases()
        assert error == FAULT_MAPPING["data_verification_error"], "There should be error in verification."

    @pytest.mark.api_handler
    def test_delete_section(self, api_request_handler_verify: ApiRequestHandler, requests_mock):
        sections_id = [{"section_id": 1}]
        mocked_response_for_case = {"success": 200}

        requests_mock.post(
            create_url(f"delete_section/{sections_id[0]['section_id']}"),
            json=mocked_response_for_case,
        )

        resources_added, error = api_request_handler_verify.delete_sections(sections_id)
        assert error == "", "There should be no error in verification."

    @pytest.mark.api_handler
    def test_delete_suite(self, api_request_handler_verify: ApiRequestHandler, requests_mock):
        suite_id = 1
        mocked_response_for_case = {"success": 200}

        requests_mock.post(
            create_url(f"delete_suite/{suite_id}"),
            json=mocked_response_for_case,
        )

        resources_added, error = api_request_handler_verify.delete_suite(suite_id)
        assert error == "", "There should be no error in verification."

    @pytest.mark.api_handler
    def test_delete_cases(self, api_request_handler_verify: ApiRequestHandler, requests_mock):
        suite_id = 1
        cases = [{"case_id": 1}]
        mocked_response_for_case = {"success": 200}

        requests_mock.post(
            create_url(f"delete_cases/{suite_id}"),
            json=mocked_response_for_case,
        )

        resources_added, error = api_request_handler_verify.delete_cases(suite_id, cases)
        assert error == "", "There should be no error in verification."

    @pytest.mark.api_handler
    def test_delete_run(self, api_request_handler_verify: ApiRequestHandler, requests_mock):
        run_id = 1
        mocked_response_for_case = {"success": 200}

        requests_mock.post(
            create_url(f"delete_run/{run_id}"),
            json=mocked_response_for_case,
        )

        resources_added, error = api_request_handler_verify.delete_run(run_id)
        assert error == "", "There should be no error in verification."

    @pytest.mark.api_handler
    def test_update_run_with_include_all_false_standalone(self, api_request_handler: ApiRequestHandler, requests_mock):
        """Test update_run for standalone run with include_all=false"""
        run_id = 100
        run_name = "Updated Test Run"

        # Mock get_run response - standalone run (no plan_id), include_all=false
        get_run_response = {
            "id": run_id,
            "name": "Original Run",
            "description": "Original description",
            "refs": "REF-1",
            "include_all": False,
            "plan_id": None,
            "config_ids": [],
        }

        # Mock get_tests response - existing cases in run
        get_tests_response = {
            "offset": 0,
            "limit": 250,
            "size": 2,
            "_links": {"next": None, "prev": None},
            "tests": [{"id": 1, "case_id": 1, "status_id": 1}, {"id": 2, "case_id": 2, "status_id": 1}],
        }

        # Mock update_run response
        update_run_response = {"id": run_id, "name": run_name}

        requests_mock.get(create_url(f"get_run/{run_id}"), json=get_run_response)
        requests_mock.get(create_url(f"get_tests/{run_id}"), json=get_tests_response)
        requests_mock.post(create_url(f"update_run/{run_id}"), json=update_run_response)

        # Execute update_run
        run_data, error = api_request_handler.update_run(run_id, run_name)

        # Assertions
        assert error == "", "No error should occur"
        assert run_data["id"] == run_id, "Run ID should match"

        # Verify the payload sent to update_run
        request_history = requests_mock.request_history
        update_request = [r for r in request_history if "update_run" in r.url and r.method == "POST"][0]
        payload = update_request.json()

        assert payload["include_all"] == False, "include_all should be False"
        assert "case_ids" in payload, "case_ids should be present"
        # Should contain union of existing (1, 2) and report cases
        assert set(payload["case_ids"]) >= {1, 2}, "Should include existing case IDs"

    @pytest.mark.api_handler
    def test_update_run_with_include_all_false_plan_with_config(
        self, api_request_handler: ApiRequestHandler, requests_mock
    ):
        """Test update_run for run in plan with config and include_all=false (the bug scenario)"""
        run_id = 200
        run_name = "Updated Test Run in Plan"

        # Mock get_run response - run in plan with config, include_all=false
        get_run_response = {
            "id": run_id,
            "name": "Original Run",
            "description": "Original description",
            "refs": "REF-1",
            "include_all": False,
            "plan_id": 10,
            "config_ids": [5, 6],  # Has configs - will use update_run_in_plan_entry
        }

        # Mock get_tests response - existing cases
        get_tests_response = {
            "offset": 0,
            "limit": 250,
            "size": 3,
            "_links": {"next": None, "prev": None},
            "tests": [
                {"id": 1, "case_id": 188, "status_id": 1},
                {"id": 2, "case_id": 180, "status_id": 1},
                {"id": 3, "case_id": 191, "status_id": 1},
            ],
        }

        # Mock update_run_in_plan_entry response
        update_run_response = {"id": run_id, "name": run_name}

        requests_mock.get(create_url(f"get_run/{run_id}"), json=get_run_response)
        requests_mock.get(create_url(f"get_tests/{run_id}"), json=get_tests_response)
        requests_mock.post(create_url(f"update_run_in_plan_entry/{run_id}"), json=update_run_response)

        # Execute update_run
        run_data, error = api_request_handler.update_run(run_id, run_name)

        # Assertions
        assert error == "", "No error should occur"
        assert run_data["id"] == run_id, "Run ID should match"

        # Verify the payload sent to update_run_in_plan_entry
        request_history = requests_mock.request_history
        update_request = [r for r in request_history if "update_run_in_plan_entry" in r.url][0]
        payload = update_request.json()

        # THIS IS THE CRITICAL FIX - must include include_all=False
        assert payload["include_all"] == False, "include_all must be False (fixes the bug)"
        assert "case_ids" in payload, "case_ids should be present"
        # Should contain union of existing (188, 180, 191) and report cases
        assert set(payload["case_ids"]) >= {188, 180, 191}, "Should preserve existing case IDs"

    @pytest.mark.api_handler
    def test_update_run_with_include_all_true_preserves_setting(
        self, api_request_handler: ApiRequestHandler, requests_mock
    ):
        """Test update_run preserves include_all=true and doesn't send case_ids"""
        run_id = 300
        run_name = "Updated Run with Include All"

        # Mock get_run response - include_all=true
        get_run_response = {
            "id": run_id,
            "name": "Original Run",
            "description": "Original description",
            "refs": "REF-1",
            "include_all": True,  # Run includes all cases
            "plan_id": None,
            "config_ids": [],
        }

        # Mock update_run response
        update_run_response = {"id": run_id, "name": run_name, "include_all": True}

        requests_mock.get(create_url(f"get_run/{run_id}"), json=get_run_response)
        requests_mock.post(create_url(f"update_run/{run_id}"), json=update_run_response)

        # Execute update_run
        run_data, error = api_request_handler.update_run(run_id, run_name)

        # Assertions
        assert error == "", "No error should occur"
        assert run_data["include_all"] == True, "include_all should be preserved"

        # Verify the payload sent to update_run
        request_history = requests_mock.request_history
        update_request = [r for r in request_history if "update_run" in r.url and r.method == "POST"][0]
        payload = update_request.json()

        assert payload["include_all"] == True, "include_all should be True"
        assert "case_ids" not in payload, "case_ids should NOT be present when include_all=True"

    @pytest.mark.api_handler
    def test_update_run_handles_get_tests_error(self, api_request_handler: ApiRequestHandler, requests_mock):
        """Test update_run handles errors from get_tests gracefully"""
        run_id = 400
        run_name = "Test Run"

        # Mock get_run response - include_all=false
        get_run_response = {
            "id": run_id,
            "name": "Original Run",
            "description": "Original description",
            "refs": "REF-1",
            "include_all": False,
            "plan_id": None,
            "config_ids": [],
        }

        # Mock get_tests to return error (403 Forbidden, for example)
        requests_mock.get(create_url(f"get_run/{run_id}"), json=get_run_response)
        requests_mock.get(create_url(f"get_tests/{run_id}"), status_code=403, json={"error": "Access denied"})

        # Execute update_run - should fail gracefully
        run_data, error = api_request_handler.update_run(run_id, run_name)

        # Assertions
        assert run_data is None, "run_data should be None on error"
        assert error is not None, "Error message should be present"
        assert "Failed to get tests in run" in error, "Error should indicate get_tests failure"

    @pytest.mark.api_handler
    def test_update_run_with_include_all_false_plan_without_config(
        self, api_request_handler: ApiRequestHandler, requests_mock
    ):
        """Test update_run for run in plan without config uses update_plan_entry"""
        run_id = 500
        run_name = "Updated Test Run in Plan No Config"
        plan_id = 20
        entry_id = "abc-123"

        # Mock get_run response - run in plan without config
        get_run_response = {
            "id": run_id,
            "name": "Original Run",
            "description": "Original description",
            "refs": "REF-1",
            "include_all": False,
            "plan_id": plan_id,
            "config_ids": [],  # No configs - will use update_plan_entry
        }

        # Mock get_tests response
        get_tests_response = {
            "offset": 0,
            "limit": 250,
            "size": 1,
            "_links": {"next": None, "prev": None},
            "tests": [{"id": 1, "case_id": 50, "status_id": 1}],
        }

        # Mock get_plan response
        get_plan_response = {
            "id": plan_id,
            "entries": [{"id": entry_id, "runs": [{"id": run_id, "entry_id": entry_id}]}],
        }

        # Mock update_plan_entry response
        update_plan_response = {"id": run_id, "name": run_name}

        requests_mock.get(create_url(f"get_run/{run_id}"), json=get_run_response)
        requests_mock.get(create_url(f"get_tests/{run_id}"), json=get_tests_response)
        requests_mock.get(create_url(f"get_plan/{plan_id}"), json=get_plan_response)
        requests_mock.post(create_url(f"update_plan_entry/{plan_id}/{entry_id}"), json=update_plan_response)

        # Execute update_run
        run_data, error = api_request_handler.update_run(run_id, run_name)

        # Assertions
        assert error == "", "No error should occur"
        assert run_data["id"] == run_id, "Run ID should match"

        # Verify update_plan_entry was called with correct payload
        request_history = requests_mock.request_history
        update_request = [r for r in request_history if f"update_plan_entry/{plan_id}/{entry_id}" in r.url][0]
        payload = update_request.json()

        assert payload["include_all"] == False, "include_all should be False"
        assert "case_ids" in payload, "case_ids should be present"
        assert 50 in payload["case_ids"], "Should include existing case ID"

    @pytest.mark.api_handler
    def test_upload_attachments_413_error(self, api_request_handler: ApiRequestHandler, requests_mock, tmp_path):
        """Test that 413 errors (file too large) are properly reported."""
        run_id = 1

        # Mock get_tests endpoint
        mocked_tests_response = {
            "offset": 0,
            "limit": 250,
            "size": 1,
            "_links": {"next": None, "prev": None},
            "tests": [{"id": 1001, "case_id": 100}],
        }
        requests_mock.get(create_url(f"get_tests/{run_id}"), json=mocked_tests_response)

        # Create a temporary test file
        test_file = tmp_path / "large_attachment.jpg"
        test_file.write_text("test content")

        # Mock add_attachment_to_result endpoint to return 413
        requests_mock.post(
            create_url("add_attachment_to_result/2001"),
            status_code=413,
            text='<!DOCTYPE HTML PUBLIC "-//IETF//DTD HTML 2.0//EN">\n<html><head>\n<title>413 Request Entity Too Large</title>\n</head><body>\n<h1>Request Entity Too Large</h1>\n</body></html>\n',
        )

        # Prepare test data
        report_results = [{"case_id": 100, "attachments": [str(test_file)]}]
        results = [{"id": 2001, "test_id": 1001}]

        # Call upload_attachments
        api_request_handler.upload_attachments(report_results, results, run_id)

        # Verify the request was made (case-insensitive comparison)
        assert requests_mock.last_request.url.lower() == create_url("add_attachment_to_result/2001").lower()

    @pytest.mark.api_handler
    def test_upload_attachments_success(self, api_request_handler: ApiRequestHandler, requests_mock, tmp_path):
        """Test that successful attachment uploads work correctly."""
        run_id = 1

        # Mock get_tests endpoint
        mocked_tests_response = {
            "offset": 0,
            "limit": 250,
            "size": 1,
            "_links": {"next": None, "prev": None},
            "tests": [{"id": 1001, "case_id": 100}],
        }
        requests_mock.get(create_url(f"get_tests/{run_id}"), json=mocked_tests_response)

        # Create a temporary test file
        test_file = tmp_path / "test_attachment.jpg"
        test_file.write_text("test content")

        # Mock add_attachment_to_result endpoint to return success
        requests_mock.post(create_url("add_attachment_to_result/2001"), status_code=200, json={"attachment_id": 5001})

        # Prepare test data
        report_results = [{"case_id": 100, "attachments": [str(test_file)]}]
        results = [{"id": 2001, "test_id": 1001}]

        # Call upload_attachments
        api_request_handler.upload_attachments(report_results, results, run_id)

        # Verify the request was made (case-insensitive comparison)
        assert requests_mock.last_request.url.lower() == create_url("add_attachment_to_result/2001").lower()

    @pytest.mark.api_handler
    def test_upload_attachments_file_not_found(self, api_request_handler: ApiRequestHandler, requests_mock):
        """Test that missing attachment files are properly reported."""
        run_id = 1

        # Mock get_tests endpoint
        mocked_tests_response = {
            "offset": 0,
            "limit": 250,
            "size": 1,
            "_links": {"next": None, "prev": None},
            "tests": [{"id": 1001, "case_id": 100}],
        }
        requests_mock.get(create_url(f"get_tests/{run_id}"), json=mocked_tests_response)

        # Prepare test data with non-existent file
        report_results = [{"case_id": 100, "attachments": ["/path/to/nonexistent/file.jpg"]}]
        results = [{"id": 2001, "test_id": 1001}]

        # Call upload_attachments - should not raise exception
        api_request_handler.upload_attachments(report_results, results, run_id)
