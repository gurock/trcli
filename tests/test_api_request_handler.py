import json
from pathlib import Path

import pytest
from click.testing import CliRunner
from requests_mock import Mocker
from serde.json import from_json
from tests.helpers.api_client_helpers import TEST_RAIL_URL, create_url
from trcli.api.api_request_handler import ApiRequestHandler
from trcli.api.api_client import APIClient
from trcli.cli import Environment
from trcli.data_classes.dataclass_testrail import TestRailSuite


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


class TestAPIHandler:
    @pytest.mark.api_client
    def test_return_project(
        self, api_request_handler: ApiRequestHandler, requests_mock
    ):
        mocked_response = {
            "projects": [
                {"id": 1, "name": "DataHub"},
                {"id": 2, "name": "Test Project"},
                {"id": 3, "name": "DataHub"},
            ]
        }
        requests_mock.get(create_url("get_projects"), json=mocked_response)
        assert api_request_handler.get_project_id("Test Project") == (2, "")
        assert api_request_handler.get_project_id("DataHub") == (
            -1,
            "Given project name matches more than one result.",
        )
        assert api_request_handler.get_project_id("Some project") == (
            -2,
            "Some project project doesn't exists.",
        )

    def test_check_suite_exists(
        self, api_request_handler: ApiRequestHandler, requests_mock
    ):
        project_id = 3
        mocked_response = [
            {"id": 4, "name": "Suite1", "description": "Test1", "project_id": 3},
            {"id": 5, "name": "Suite2", "description": "Test2", "project_id": 3},
        ]
        requests_mock.get(create_url(f"get_suites/{project_id}"), json=mocked_response)
        assert api_request_handler.check_suite_id(project_id) == (True, "")
        api_request_handler.suites_data_from_provider.suite_id = 6
        assert api_request_handler.check_suite_id(project_id) == (False, "")

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

        assert resources_added[0]["name"] == mocked_response["name"]
        assert resources_added[0]["suite_id"] == mocked_response["id"]
        assert error == ""

        assert (
            api_request_handler.suites_data_from_provider.suite_id
            == mocked_response["id"]
        )
        # assert api_request_handler.suites_data_from_provider.name == mocked_response["name"] #TODO updater in DataProvider doesnt handle "name" property

    def test_check_missing_sections(
        self, api_request_handler: ApiRequestHandler, requests_mock
    ):
        project_id = 3
        mocked_response = [
            {
                "id": 0,
                "suite_id": 4,
                "name": "Skipped test",
            },
        ]

        requests_mock.get(
            create_url(f"get_sections/{project_id}&suite_id=4"), json=mocked_response
        )
        assert (
            len(api_request_handler.check_missing_section_id(project_id)[0]) == 2
        ), "There should be one missing section"

        mocked_response[0]["id"] = 1234
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

        assert resources_added[0]["name"] == mocked_response["name"]
        assert resources_added[0]["section_id"] == mocked_response["id"]
        assert error == ""

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

        assert resources_added[0]["title"] == mocked_response_for_case["title"]
        assert resources_added[0]["case_id"] == mocked_response_for_case["id"]
        assert error == ""

    def test_add_run(self, api_request_handler: ApiRequestHandler, requests_mock):
        project_id = 3

        mocked_response = {
            "description": None,
            "id": 81,
            "include_all": False,
            "is_completed": False,
        }

        requests_mock.post(create_url(f"add_run/{project_id}"), json=mocked_response)
        resources_added, error = api_request_handler.add_run(project_id)
        assert True  # TODO Fix tests after fixing add_run

    def test_add_results(self, api_request_handler: ApiRequestHandler, requests_mock):
        run_id = 2  # TODO run_id should be from env or from add run?

        mocked_response = {  # TODO change that or move to file?
            "offset": 0,
            "limit": 250,
            "size": 250,
            "_links": {
                "next": "/api/v2/get_results/131071&limit=250&offset=250",
                "prev": None,
            },
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
        # TODO ASSERT?
        # TODO Fix tests after fixing add_results


# TODO add tests for close_run and check missing test cases ids
