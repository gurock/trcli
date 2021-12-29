import json
import requests
import pytest
from pathlib import Path
from serde.json import from_json
from tests.helpers.api_client_helpers import TEST_RAIL_URL, create_url
from trcli.cli import Environment
from trcli.api.api_request_handler import ApiRequestHandler, ProjectData
from trcli.api.api_client import APIClient
from trcli.data_classes.dataclass_testrail import TestRailSuite
from trcli.constants import ProjectErrors


@pytest.fixture(scope="function")
def api_request_handler():
    api_client = APIClient(host_name=TEST_RAIL_URL)
    environment = Environment()
    environment.project = "Test Project"
    environment.batch_size = 10
    file_json = open(Path(__file__).parent / "test_data/json/api_request_handler.json")
    json_string = json.dumps(json.load(file_json))
    test_input = from_json(TestRailSuite, json_string)
    api_request = ApiRequestHandler(environment, api_client, test_input)
    yield api_request


class TestApiRequestHandler:
    def test_return_project(
        self, api_request_handler: ApiRequestHandler, requests_mock
    ):
        mocked_response = {
            "projects": [
                {"id": 1, "name": "DataHub", "suite_mode": 1},
                {"id": 2, "name": "Test Project", "suite_mode": 1},
                {"id": 3, "name": "DataHub", "suite_mode": 1},
            ]
        }
        requests_mock.get(create_url("get_projects"), json=mocked_response)
        assert api_request_handler.get_project_id("Test Project") == ProjectData(
            project_id=2, suite_mode=1, error_message=""
        ), "Get project should return proper project data object"
        assert api_request_handler.get_project_id("DataHub") == ProjectData(
            project_id=ProjectErrors.multiple_project_same_name,
            suite_mode=-1,
            error_message="Given project name matches more than one result.",
        ), "Get project should return proper project data object"
        assert api_request_handler.get_project_id("Some project") == ProjectData(
            project_id=ProjectErrors.not_existing_project,
            suite_mode=-1,
            error_message="Some project project doesn't exists.",
        ), "Get project should return proper project data object"

    def test_check_suite_exists(
        self, api_request_handler: ApiRequestHandler, requests_mock
    ):
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
            "",
        ), "Given suite id should NOT exist in mocked response."

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
            api_request_handler.suites_data_from_provider.suite_id
            == mocked_response["id"]
        ), "Added suite id in DataProvider doesn't match mocked response id."

    def test_check_missing_sections(
        self, api_request_handler: ApiRequestHandler, requests_mock
    ):
        project_id = 3
        mocked_response = {
            "sections": [
                {
                    "id": 0,
                    "suite_id": 4,
                    "name": "Skipped test",
                }
            ]
        }

        requests_mock.get(
            create_url(f"get_sections/{project_id}&suite_id=4"), json=mocked_response
        )

        assert (
            len(api_request_handler.check_missing_section_ids(project_id)[0]) == 2
        ), "There should be two missing section"

        mocked_response["sections"][0]["id"] = 1234
        requests_mock.get(
            create_url(f"get_sections/{project_id}&suite_id=4"), json=mocked_response
        )

        assert (
            len(api_request_handler.check_missing_section_ids(project_id)[0]) == 1
        ), "There should be one missing section"

    def test_add_sections(self, api_request_handler: ApiRequestHandler, requests_mock):
        project_id = 3
        mocked_response = {
            "id": 1235,
            "suite_id": 4,
            "name": "Passed test",
        }

        requests_mock.post(
            create_url(f"add_section/{project_id}"), json=mocked_response
        )
        resources_added, error = api_request_handler.add_sections(project_id)

        assert (
            resources_added[0]["name"] == mocked_response["name"]
        ), "Added section name doesn't match mocked response name."
        assert (
            resources_added[0]["section_id"] == mocked_response["id"]
        ), "Added section id doesn't match mocked response id."
        assert error == "", "Error occurred in add_section"

        assert (
            api_request_handler.suites_data_from_provider.testsections[1].section_id
            == mocked_response["id"]
        ), "Added section id in DataProvider doesn't match mocked response id."

    def test_add_section_and_cases(
        self, api_request_handler: ApiRequestHandler, requests_mock
    ):
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
        }

        mocked_response_for_case_2 = {
            "id": 3,
            "suite_id": 4,
            "section_id": 12345,
            "title": "testCase3",
        }

        requests_mock.post(
            create_url(f"add_section/{project_id}"), json=mocked_response_for_section
        )
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
        assert (
            mocked_response["id"] == resources_added
        ), "Added run id doesn't match mocked response id"
        assert error == "", "Error occurred in add_case"

    def test_add_results(self, api_request_handler: ApiRequestHandler, requests_mock):
        run_id = 2
        mocked_response = {
            "offset": 0,
            "limit": 250,
            "size": 250,
            "results": [
                {
                    "assignedto_id": 1,
                    "comment": "This test failed: ..",
                    "created_by": 1,
                    "created_on": 1393851801,
                    "defects": "TR-1",
                    "elapsed": "5m",
                    "id": 1,
                    "status_id": 5,
                    "test_id": 1,
                    "version": "1.0RC1",
                }
            ],
        }

        requests_mock.post(
            create_url(f"add_results_for_cases/{run_id}"), json=mocked_response
        )
        resources_added, error = api_request_handler.add_results(run_id)
        assert [mocked_response] == resources_added, "Invalid response from add_results"
        assert error == "", "Error occurred in add_results"

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

    def test_check_missing_test_cases_ids(
        self, api_request_handler: ApiRequestHandler, requests_mock
    ):
        project_id = 3
        suite_id = api_request_handler.suites_data_from_provider.suite_id
        mocked_response = {
            "offset": 0,
            "limit": 250,
            "size": 250,
            "cases": [{"id": 10, "title": ".."}, {"id": 20, "title": ".."}],
        }
        requests_mock.get(
            create_url(f"get_cases/{project_id}&suite_id={suite_id}"),
            json=mocked_response,
        )
        missing_ids, error = api_request_handler.check_missing_test_cases_ids(3)
        assert missing_ids == [1], "There should be one case missing"
        assert error == "", "Error occurred in close_run"

    def test_get_suites_id(self, api_request_handler: ApiRequestHandler, requests_mock):
        project_id = 3
        mocked_response = [
            {"id": 100, "name": "Master"},
        ]

        requests_mock.get(create_url(f"get_suites/{project_id}"), json=mocked_response)
        resources_added, error = api_request_handler.get_suite_ids(project_id)
        assert (
            resources_added[0] == mocked_response[0]["id"]
        ), "ID in response doesn't match mocked response"
        assert error == "", "Error occurred in get_suite_ids"

    def test_return_project_error(
        self, api_request_handler: ApiRequestHandler, requests_mock
    ):

        requests_mock.get(
            create_url("get_projects"), exc=requests.exceptions.ConnectTimeout
        )
        assert api_request_handler.get_project_id("Test Project") == ProjectData(
            project_id=-3,
            suite_mode=-1,
            error_message="Your upload to TestRail did not receive a successful response from your TestRail Instance."
            " Please check your settings and try again.",
        ), "Get project should return proper project data object with error"

    def test_add_suite_error(
        self, api_request_handler: ApiRequestHandler, requests_mock
    ):

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
            error
            == "Your upload to TestRail did not receive a successful response from your TestRail Instance."
            " Please check your settings and try again."
        ), "Connection error is expected"

    def test_add_sections_error(
        self, api_request_handler: ApiRequestHandler, requests_mock
    ):
        project_id = 3
        requests_mock.post(
            create_url(f"add_section/{project_id}"),
            exc=requests.exceptions.ConnectTimeout,
        )
        resources_added, error = api_request_handler.add_sections(project_id)

        assert resources_added == [], "No resources should be added"
        assert (
            error
            == "Your upload to TestRail did not receive a successful response from your TestRail Instance."
            " Please check your settings and try again."
        ), "Connection error is expected"

        assert (
            api_request_handler.suites_data_from_provider.testsections[1].section_id
            is None
        ), "No resources should be added to DataProvider"

    def test_add_section_and_cases_error(
        self, api_request_handler: ApiRequestHandler, requests_mock
    ):
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
        }

        mocked_response_for_case_2 = {
            "id": 3,
            "suite_id": 4,
            "section_id": 12345,
            "title": "testCase3",
        }

        requests_mock.post(
            create_url(f"add_section/{project_id}"), json=mocked_response_for_section
        )
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
            error
            == "Your upload to TestRail did not receive a successful response from your TestRail Instance."
            " Please check your settings and try again."
        ), "Connection error is expected"
