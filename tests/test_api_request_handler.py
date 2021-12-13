import pytest
from click.testing import CliRunner
from requests_mock import Mocker
from tests.helpers.api_client_helpers import TEST_RAIL_URL, create_url
from tests.test_data.data_provider_post import test_input
from trcli.api.api_request_handler import ApiRequestHandler
from trcli.api_client import APIClient
from trcli.cli import Environment


@pytest.fixture(scope="class")
def api_request_handler():
    api_client = APIClient(host_name=TEST_RAIL_URL)
    env = Environment()
    env.project = "Test Project"
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
            ]
        }
        requests_mock.get(create_url("get_projects"), json=mocked_response)
        assert api_request_handler.get_project_id("Test Project") == 2
        assert api_request_handler.get_project_id("Some project") == -1

    def test_check_suite_exists(
        self, api_request_handler: ApiRequestHandler, requests_mock
    ):
        project_id = 3
        mocked_response = [
            {"id": 4, "name": "Test 1", "description": "Test1", "project_id": 3},
            {"id": 5, "name": "Test 1", "description": "Test1", "project_id": 3},
        ]
        requests_mock.get(create_url(f"get_suites/{project_id}"), json=mocked_response)
        assert api_request_handler.check_suite_id(project_id)
        assert not api_request_handler.check_suite_id(project_id)

    def test_add_suite(self, api_request_handler: ApiRequestHandler, requests_mock):
        project_id = 3
        mocked_response = {
            "description": "..",
            "id": 1,
            "name": "Setup & Installation",
            "project_id": 1,
            "url": "http:///testrail/index.php?/suites/view/1",
        }

        requests_mock.post(create_url(f"add_suite/{project_id}"), json=mocked_response)
        for i in api_request_handler.add_suite(project_id):
            assert i["name"] == mocked_response["name"]
            assert i["suite_id"] == mocked_response["id"]

    def test_check_missing_sections(
        self, api_request_handler: ApiRequestHandler, requests_mock
    ):
        project_id = 3
        mocked_response = [
            {
                "id": 2,
                "suite_id": 5,
                "name": "This is a new section",
            },
            {
                "id": 4,
                "suite_id": 5,
                "name": "This is a new section",
            },
        ]

        requests_mock.get(
            create_url(f"get_sections/{project_id}&suite_id=1"), json=mocked_response
        )
        assert len(api_request_handler.check_missing_section_id(project_id)) == 0
        mocked_response[0]["id"] = 66
        requests_mock.get(
            create_url(f"get_sections/{project_id}&suite_id=1"), json=mocked_response
        )
        assert api_request_handler.check_missing_section_id(project_id) == [2]

    def test_add_sections(self, api_request_handler: ApiRequestHandler, requests_mock):
        project_id = 3
        mocked_response = {
            "id": 5,
            "suite_id": 5,
            "name": "This is a new section",
        }

        requests_mock.post(
            create_url(f"add_section/{project_id}"), json=mocked_response
        )
        assert (
            api_request_handler.add_section(project_id)[0]["section_id"]
            == mocked_response["id"]
        )

    def test_add_case(self, api_request_handler: ApiRequestHandler, requests_mock):
        project_id = 3
        mocked_response = {
            "id": 3,
            "suite_id": 5,
            "name": "This is a new testcase",
        }

        requests_mock.post(create_url(f"add_case/{project_id}"), json=mocked_response)
        assert api_request_handler.add_case()
