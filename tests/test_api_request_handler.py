import json
from pathlib import Path

import pytest
from serde.json import from_json
from tests.helpers.api_client_helpers import TEST_RAIL_URL, create_url
from trcli.api.api_request_handler import ApiRequestHandler, ProjectData
from trcli.api.api_client import APIClient
from trcli.cli import Environment
from trcli.data_classes.dataclass_testrail import TestRailSuite
from trcli.constants import ProjectErrors


@pytest.fixture(scope="function")
def api_request_handler():
    api_client = APIClient(host_name=TEST_RAIL_URL)
    env = Environment()
    env.project = "Test Project"
    file_json = open(Path(__file__).parent / "test_data/json/api_request_handler.json")
    json_string = json.dumps(json.load(file_json))
    test_input = from_json(TestRailSuite, json_string)
    api_request = ApiRequestHandler(env, api_client, test_input)
    yield api_request


class TestApiRequestHandler:
    @pytest.mark.api_client
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
        ), "Invalid response from check_suite_id"
        api_request_handler.suites_data_from_provider.suite_id = 6
        assert api_request_handler.check_suite_id(project_id) == (
            False,
            "",
        ), "Invalid response from check_suite_id"

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
        resources_added, error = api_request_handler.add_suite(project_id)

        assert (
            resources_added[0]["name"] == mocked_response["name"]
        ), "Invalid response from add_suite"
        assert (
            resources_added[0]["suite_id"] == mocked_response["id"]
        ), "Invalid response from add_suite"
        assert error == "", "Error occurred in add_suite"

        assert (
            api_request_handler.suites_data_from_provider.suite_id
            == mocked_response["id"],
            "Invalid response from add_suite",
        )

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
            len(api_request_handler.check_missing_section_id(project_id)[0]) == 2
        ), "There should be one missing section"

        mocked_response["sections"][0]["id"] = 1234
        requests_mock.get(
            create_url(f"get_sections/{project_id}&suite_id=4"), json=mocked_response
        )

        assert (
            len(api_request_handler.check_missing_section_id(project_id)[0]) == 1
        ), "There should be no missing sections"

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
        resources_added, error = api_request_handler.add_section(project_id)

        assert (
            resources_added[0]["name"] == mocked_response["name"]
        ), "Invalid response from add_section"
        assert (
            resources_added[0]["section_id"] == mocked_response["id"]
        ), "Invalid response from add_section"
        assert error == "", "Error occurred in add_section"

    def test_add_section_and_case(
        self, api_request_handler: ApiRequestHandler, requests_mock
    ):
        project_id = 3
        mocked_response_for_section = {
            "id": 12345,
            "suite_id": 4,
            "name": "Passed test",
        }
        mocked_response_for_case = {
            "id": 3,
            "suite_id": 4,
            "section_id": 12345,
            "title": "testCase2",
        }

        requests_mock.post(
            create_url(f"add_section/{project_id}"), json=mocked_response_for_section
        )
        requests_mock.post(
            create_url(f"add_case/{mocked_response_for_case['section_id']}"),
            json=mocked_response_for_case,
        )
        api_request_handler.add_section(project_id)
        resources_added, error = api_request_handler.add_case()

        assert (
            resources_added[0]["title"] == mocked_response_for_case["title"]
        ), "Invalid response from add_case"
        assert (
            resources_added[0]["case_id"] == mocked_response_for_case["id"]
        ), "Invalid response from add_case"
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
        assert mocked_response["id"] == resources_added, "Invalid response from add_run"
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
        assert mocked_response == resources_added, "Invalid response from add_results"
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
        resources_added, error = api_request_handler.check_missing_test_cases_ids(3)
        assert resources_added == [1], "There should be one case missing"
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
        ), "Invalid response from get_suite_ids"
        assert error == "", "Error occurred in get_suite_ids"
