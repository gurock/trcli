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
            json_path = (
                Path(__file__).parent / "test_data/json/api_request_handler.json"
            )
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
    json_path = (
        Path(__file__).parent / "test_data/json/update_case_result_single_with_id.json"
    )
    yield handler_maker(custom_json=json_path, verify=False)


class TestApiRequestHandler:
    @pytest.mark.api_handler
    def test_return_project(
        self, api_request_handler: ApiRequestHandler, requests_mock
    ):
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
            ]
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
    def test_return_project_legacy_response(
        self, api_request_handler: ApiRequestHandler, requests_mock
    ):
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
            api_request_handler.suites_data_from_provider.suite_id
            == mocked_response["id"]
        ), "Added suite id in DataProvider doesn't match mocked response id."

    @pytest.mark.api_handler
    def test_check_missing_sections_true(
        self, api_request_handler: ApiRequestHandler, requests_mock, mocker
    ):
        project_id = 3
        update_data_mock = mocker.patch('trcli.api.api_request_handler.ApiDataProvider.update_data')
        mocked_response = {
            "_links": {"next": None, "prev": None},
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

        missing, _ = api_request_handler.check_missing_section_ids(project_id)
        update_data_mock.assert_called_with(
            section_data=[{'section_id': 0, 'suite_id': 4, 'name': 'Skipped test'}]
        )
        assert missing, "There should be missing section"

    @pytest.mark.api_handler
    def test_check_missing_sections_false(
        self, api_request_handler: ApiRequestHandler, requests_mock, mocker
    ):
        project_id = 3
        update_data_mock = mocker.patch('trcli.api.api_request_handler.ApiDataProvider.update_data')
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
                }
            ]
        }

        requests_mock.get(
            create_url(f"get_sections/{project_id}&suite_id=4"), json=mocked_response
        )

        missing, _ = api_request_handler.check_missing_section_ids(project_id)
        update_data_mock.assert_called_with(
            section_data=[
                {'name': 'Skipped test', 'section_id': 1, 'suite_id': 4},
                {'name': 'Passed test', 'section_id': 2, 'suite_id': 4}
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

    @pytest.mark.api_handler
    def test_add_section_and_cases(
        self, api_request_handler: ApiRequestHandler, requests_mock
    ):
        project_id = 3
        mocked_response_for_section = {
            "id": 12345,
            "suite_id": 4,
            "name": "Passed test",
            "custom_automation_id": "className.testCase"
        }

        mocked_response_for_case_1 = {
            "id": 4,
            "suite_id": 4,
            "section_id": 1234,
            "title": "testCase2",
            "custom_automation_id": "className.testCase"
        }

        mocked_response_for_case_2 = {
            "id": 3,
            "suite_id": 4,
            "section_id": 12345,
            "title": "testCase3",
            "custom_automation_id": "className.testCase"
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
        assert (
            mocked_response["id"] == resources_added
        ), "Added run id doesn't match mocked response id"
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
        requests_mock.post(
            create_url(f"add_results_for_cases/{run_id}"), json=mocked_response
        )

        tests_mocked_response = {
            'offset': 0,
            'limit': 250,
            'size': 4,
            '_links': {'next': None, 'prev': None},
            'tests': [
                {
                    'id': 4,
                    'case_id': 1,
                    'status_id': 5,
                    'assignedto_id': None,
                    'run_id': run_id,
                    'title': 'Fail To Login With Invalid Password'
                 }
            ]
        }
        requests_mock.get(create_url(f"get_tests/{run_id}"), json=tests_mocked_response)

        attachments_mock_response = {"attachment_id": 123}

        requests_mock.post(
            create_url(f"add_attachment_to_result/{result_id}"), json=attachments_mock_response
        )

        with patch("builtins.open", mock_open()) as mock_file:
            resources_added, error, results_added = api_request_handler.add_results(run_id)
            assert [mocked_response] == resources_added, "Invalid response from add_results"
            assert error == "", "Error occurred in add_results"
            assert results_added == len(mocked_response), \
                f"Expected {len(mocked_response)} results to be added but got {results_added} instead."
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
    def test_check_missing_test_cases_ids_true(
        self, api_request_handler: ApiRequestHandler, requests_mock, mocker
    ):
        project_id = 3
        suite_id = api_request_handler.suites_data_from_provider.suite_id
        update_data_mock = mocker.patch('trcli.api.api_request_handler.ApiDataProvider.update_data')
        mocked_response_page_1 = {
            "_links": {
                "next": None,
                "prev": None,
            },
            "cases": [
                {"title": "testCase1", "custom_automation_id": "Skipped test.testCase1", "id": 1, "section_id": 1234},
                {"title": "testCase2", "custom_automation_id": "Skipped test.testCase2", "id": 2, "section_id": 1234}
            ],
        }
        requests_mock.get(
            create_url(f"get_cases/{project_id}&suite_id={suite_id}"),
            json=mocked_response_page_1,
        )
        missing_ids, error = api_request_handler.check_missing_test_cases_ids(
            project_id
        )

        update_data_mock.assert_called_with(
            case_data=[
                {
                    "case_id": 1,
                    "custom_automation_id": "Skipped test.testCase1",
                    "section_id": 1234,
                    "title": "testCase1"
                },
                {
                    "case_id": 2,
                    "custom_automation_id":
                    "Skipped test.testCase2",
                    "section_id": 1234,
                    "title": "testCase2"
                }
            ]
        )
        assert missing_ids, "There is one missing test case"
        assert error == "", "Error occurred in check"

    @pytest.mark.api_handler
    def test_check_missing_test_cases_ids_false(
        self, api_request_handler: ApiRequestHandler, requests_mock, mocker
    ):
        project_id = 3
        suite_id = api_request_handler.suites_data_from_provider.suite_id
        update_data_mock = mocker.patch('trcli.api.api_request_handler.ApiDataProvider.update_data')
        mocked_response_page_1 = {
            "_links": {
                "next": f"/api/v2/get_cases/{project_id}&suite_id={suite_id}&limit=1&offset=1",
                "prev": None,
            },
            "cases": [
                {"title": "testCase1", "custom_automation_id": "Skipped test.testCase1", "id": 1, "section_id": 1234},
                {"title": "testCase2", "custom_automation_id": "Skipped test.testCase2", "id": 2, "section_id": 1234}
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
        missing_ids, error = api_request_handler.check_missing_test_cases_ids(
            project_id
        )
        update_data_mock.assert_called_with(
            case_data=[
                {
                    "case_id": 1,
                    "custom_automation_id": "Skipped test.testCase1",
                    "section_id": 1234,
                    "title": "testCase1"
                },
                {
                    "case_id": 2,
                    "custom_automation_id": "Skipped test.testCase2",
                    "section_id": 1234,
                    "title": "testCase2"
                },
                {
                    "case_id": 1,
                    "custom_automation_id": "Passed test.testCase3",
                    "section_id": 2,
                    "title": "testCase3"
                }
            ]
        )
        assert not missing_ids, "No missing ids"
        assert error == "", "No error should have occurred"

    @pytest.mark.api_handler
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

    @pytest.mark.api_handler
    def test_return_project_error(
        self, api_request_handler: ApiRequestHandler, requests_mock
    ):

        requests_mock.get(
            create_url("get_projects"), exc=requests.exceptions.ConnectTimeout
        )
        assert api_request_handler.get_project_data("Test Project") == ProjectData(
            project_id=-3,
            suite_mode=-1,
            error_message="Your upload to TestRail did not receive a successful response from your TestRail Instance."
            " Please check your settings and try again.",
        ), "Get project should return proper project data object with error"

    @pytest.mark.api_handler
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

    @pytest.mark.api_handler
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

    @pytest.mark.api_handler
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
            "custom_automation_id": "Skipped test.testCase2"
        }

        mocked_response_for_case_2 = {
            "id": 3,
            "suite_id": 4,
            "section_id": 12345,
            "title": "testCase3",
            "custom_automation_id": "Passed test.testCase3"
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

    @pytest.mark.api_handler
    def test_add_results_error(
        self, api_request_handler: ApiRequestHandler, requests_mock
    ):
        run_id = 3
        requests_mock.post(
            create_url(f"add_results_for_cases/{run_id}"),
            exc=requests.exceptions.ConnectTimeout,
        )
        tests_mocked_response = {
            'offset': 0,
            'limit': 250,
            'size': 4,
            '_links': {'next': None, 'prev': None},
            'tests': [
                {
                    'id': 18319,
                    'case_id': 6086,
                    'status_id': 5,
                    'assignedto_id': None,
                    'run_id': run_id,
                    'title': 'Fail To Login With Invalid Password'
                 }
            ]
        }
        requests_mock.get(create_url(f"get_tests/{run_id}"), json=tests_mocked_response)
        resources_added, error, results_added = api_request_handler.add_results(run_id)
        assert resources_added == [], "Expected empty list of added resources"
        assert (
            error
            == "Your upload to TestRail did not receive a successful response from your TestRail Instance."
            " Please check your settings and try again."
        ), "Connection error is expected"
        assert results_added == 0, "Expected 0 resources to be added."

    @pytest.mark.api_handler
    def test_add_results_keyboard_interrupt(
        self, api_request_handler: ApiRequestHandler, requests_mock, mocker
    ):
        run_id = 3
        requests_mock.post(
            create_url(f"add_results_for_cases/{run_id}"),
            exc=requests.exceptions.ConnectTimeout,
        )
        mocker.patch(
            "trcli.api.api_request_handler.as_completed", side_effect=KeyboardInterrupt
        )
        with pytest.raises(KeyboardInterrupt) as exception:
            api_request_handler.add_results(run_id)

    @pytest.mark.api_handler
    def test_add_suite_with_verify(
        self, api_request_handler_verify: ApiRequestHandler, requests_mock
    ):
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

        requests_mock.post(
            create_url(f"add_section/{project_id}"), json=mocked_response
        )
        api_request_handler_verify = handler_maker(verify=True)
        resources_added, error = api_request_handler_verify.add_sections(project_id)
        assert error == "", "There should be no error in verification."
        mocked_response["suite_id"] = 0
        api_request_handler_verify = handler_maker(verify=True)
        resources_added, error = api_request_handler_verify.add_sections(project_id)
        assert (
            error
            == "Data verification failed. Server added different resource than expected."
        ), "There should be error in verification."

    @pytest.mark.api_handler
    def test_add_case_with_verify(
        self, api_request_handler_verify: ApiRequestHandler, requests_mock
    ):
        mocked_response_for_case = {
            "id": 3,
            "suite_id": 4,
            "section_id": 1234,
            "title": "testCase2",
            "estimate": "30s",
            "custom_automation_id": "Skipped test.testCase2"
        }

        requests_mock.post(
            create_url(f"add_case/{mocked_response_for_case['section_id']}"),
            json=mocked_response_for_case,
        )
        del api_request_handler_verify.suites_data_from_provider.testsections[
            1
        ].testcases[0]
        resources_added, error = api_request_handler_verify.add_cases()
        assert error == "", "There should be no error in verification."
        mocked_response_for_case["estimate"] = "60s"
        api_request_handler_verify.suites_data_from_provider.testsections[0].testcases[
            1
        ].case_id = None
        resources_added, error = api_request_handler_verify.add_cases()
        assert (
            error == FAULT_MAPPING["data_verification_error"]
        ), "There should be error in verification."

    @pytest.mark.api_handler
    def test_delete_section(
        self, api_request_handler_verify: ApiRequestHandler, requests_mock
    ):
        sections_id = [{"section_id": 1}]
        mocked_response_for_case = {"success": 200}

        requests_mock.post(
            create_url(f"delete_section/{sections_id[0]['section_id']}"),
            json=mocked_response_for_case,
        )

        resources_added, error = api_request_handler_verify.delete_sections(sections_id)
        assert error == "", "There should be no error in verification."

    @pytest.mark.api_handler
    def test_delete_suite(
        self, api_request_handler_verify: ApiRequestHandler, requests_mock
    ):
        suite_id = 1
        mocked_response_for_case = {"success": 200}

        requests_mock.post(
            create_url(f"delete_suite/{suite_id}"),
            json=mocked_response_for_case,
        )

        resources_added, error = api_request_handler_verify.delete_suite(suite_id)
        assert error == "", "There should be no error in verification."

    @pytest.mark.api_handler
    def test_delete_cases(
        self, api_request_handler_verify: ApiRequestHandler, requests_mock
    ):
        suite_id = 1
        cases = [{"case_id": 1}]
        mocked_response_for_case = {"success": 200}

        requests_mock.post(
            create_url(f"delete_cases/{suite_id}"),
            json=mocked_response_for_case,
        )

        resources_added, error = api_request_handler_verify.delete_cases(
            suite_id, cases
        )
        assert error == "", "There should be no error in verification."

    @pytest.mark.api_handler
    def test_delete_run(
        self, api_request_handler_verify: ApiRequestHandler, requests_mock
    ):
        run_id = 1
        mocked_response_for_case = {"success": 200}

        requests_mock.post(
            create_url(f"delete_run/{run_id}"),
            json=mocked_response_for_case,
        )

        resources_added, error = api_request_handler_verify.delete_run(run_id)
        assert error == "", "There should be no error in verification."
