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
from trcli.constants import ProjectErrors, FAULT_MAPPING


@pytest.fixture(scope="function")
def handler_maker():
    def _make_handler(verify=False, custom_json=None):
        api_client = APIClient(host_name=TEST_RAIL_URL)
        environment = Environment()
        environment.project = "Test Project"
        environment.batch_size = 10
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
            error_message="Given project name matches more than one result."
            "Please specify which should be used using the --project-id argument",
        ), "Get project should return proper project data object"
        assert api_request_handler.get_project_id("DataHub", 2) == ProjectData(
            project_id=ProjectErrors.multiple_project_same_name,
            suite_mode=-1,
            error_message="Given project name matches more than one result."
            "Please specify which should be used using the --project-id argument",
        ), (
            "Get project should return proper project data object when passing"
            "project_id and project_id doesn't match the response"
        )
        assert api_request_handler.get_project_id("DataHub", 3) == ProjectData(
            project_id=3, suite_mode=1, error_message=""
        ), (
            "Get project should return proper project data object when passing"
            "project_id and project_id matches response"
        )

        assert api_request_handler.get_project_id("Some project") == ProjectData(
            project_id=ProjectErrors.not_existing_project,
            suite_mode=-1,
            error_message="Please specify a valid project name using the --project argument",
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

        _, error = api_request_handler.check_missing_section_ids(project_id)
        assert (
            error == FAULT_MAPPING["unknown_section_id"]
        ), " Extra section ID that is not in testrail should be detected."

        mocked_response["sections"][0]["id"] = 1234
        requests_mock.get(
            create_url(f"get_sections/{project_id}&suite_id=4"), json=mocked_response
        )
        missing, _ = api_request_handler.check_missing_section_ids(project_id)
        assert missing, "There should be missing section"

        mocked_response["sections"].append({"id": 1})
        api_request_handler.suites_data_from_provider.testsections[1].section_id = 1
        requests_mock.get(
            create_url(f"get_sections/{project_id}&suite_id=4"), json=mocked_response
        )
        missing, _ = api_request_handler.check_missing_section_ids(project_id)
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
        resources_added, error, results_added = api_request_handler.add_results(run_id)
        assert [mocked_response] == resources_added, "Invalid response from add_results"
        assert error == "", "Error occurred in add_results"
        assert results_added == len(
            mocked_response["results"]
        ), f"Expected {len(mocked_response['results'])} results to be added but got {results_added} instead."

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
    def test_check_missing_test_cases_ids(
        self, api_request_handler: ApiRequestHandler, requests_mock
    ):
        project_id = 3
        suite_id = api_request_handler.suites_data_from_provider.suite_id
        mocked_response_page_1 = {
            "_links": {
                "next": f"/api/v2/get_cases/{project_id}&suite_id={suite_id}&limit=1&offset=1",
                "prev": None,
            },
            "cases": [{"id": 2, "title": ".."}],
        }
        mocked_response_page_2 = {
            "_links": {"next": None, "prev": None},
            "cases": [{"id": 1, "title": ".."}],
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
        assert missing_ids, "There should be one, None type case missing"
        assert error == "", "Error occurred in check"
        mocked_response_page_2["cases"] = [{"id": 10, "title": ".."}]
        missing_ids, error = api_request_handler.check_missing_test_cases_ids(
            project_id
        )
        assert (
            error == FAULT_MAPPING["unknown_test_case_id"]
        ), "There should be an error because of invalid test case id"

    @pytest.mark.api_handler
    def test_get_cases_from_run(
        self, api_request_handler: ApiRequestHandler, requests_mock
    ):
        run_id = 1
        mocked_response_page_1 = {
            "_links": {
                "next": f"/api/v2/get_tests/{run_id}&limit=1&offset=1",
                "prev": None,
            },
            "tests": [{"id": 2, "title": "..", "case_id": 111}],
        }
        mocked_response_page_2 = {
            "_links": {"next": None, "prev": None},
            "tests": [{"id": 1, "title": "..", "case_id": 222}],
        }
        requests_mock.get(
            create_url(f"get_tests/{run_id}"),
            json=mocked_response_page_1,
        )
        requests_mock.get(
            create_url(f"get_tests/{run_id}&limit=1&offset=1"),
            json=mocked_response_page_2,
        )
        cases, error = api_request_handler.get_cases_from_run(run_id)
        assert cases == [111, 222], "There should be list of cases"
        assert error == "", "Error occurred in check"
        requests_mock.get(
            create_url(f"get_tests/{run_id}&limit=1&offset=1"),
            json={"error": "Field :run_id is not a valid test run."},
            status_code=400,
        )
        cases, error = api_request_handler.get_cases_from_run(run_id)
        assert (
            error == FAULT_MAPPING["error_during_get_cases_from_run"]
        ), "There should be an error because of error in page 2"

        requests_mock.get(
            create_url(f"get_tests/{run_id}"),
            json={
                "_links": {
                    "next": None,
                    "prev": None,
                },
                "tests": [],
            },
        )
        cases, error = api_request_handler.get_cases_from_run(run_id)
        assert cases == [], "Empty run"
        assert error == "", "Error occurred in check"

    @pytest.mark.api_handler
    def test_check_missing_test_case_id_not_found(
        self, api_request_handler: ApiRequestHandler, requests_mock
    ):
        project_id = 3
        suite_id = api_request_handler.suites_data_from_provider.suite_id
        section_1 = api_request_handler.suites_data_from_provider.testsections[0]
        section_2 = api_request_handler.suites_data_from_provider.testsections[1]
        mocked_response_page = {
            "_links": {"next": None, "prev": None},
            "cases": [{"id": 1, "title": ".."}, {"id": 2, "title": ".."}],
        }
        requests_mock.get(
            create_url(f"get_cases/{project_id}&suite_id={suite_id}"),
            json=mocked_response_page,
        )
        section_1.testcases[1].case_id = 1
        section_2.testcases[0].case_id = 123
        missing_ids, error = api_request_handler.check_missing_test_cases_ids(
            project_id
        )
        assert (
            error == FAULT_MAPPING["unknown_test_case_id"]
        ), "There should be an error because of invalid test case id"

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
        assert api_request_handler.get_project_id("Test Project") == ProjectData(
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

    @pytest.mark.api_handler
    def test_add_results_error(
        self, api_request_handler: ApiRequestHandler, requests_mock
    ):
        run_id = 3
        requests_mock.post(
            create_url(f"add_results_for_cases/{run_id}"),
            exc=requests.exceptions.ConnectTimeout,
        )
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

    def test_update_case_succeed(
        self, api_request_handler_update_case_json: ApiRequestHandler, requests_mock
    ):
        mocked_response = {
            "id": 62228,
            "test_id": 10,
            "status_id": 5,
            "created_on": 1643188787,
            "assignedto_id": None,
            "comment": "Type: pytest.failure\nMessage: Fail due to...\nText: failed due to...",
            "version": None,
            "elapsed": "2m 39s",
            "defects": None,
            "created_by": 2,
            "custom_step_results": None,
            "attachment_ids": [],
        }
        run_id = 20
        case_id = 10

        requests_mock.post(
            create_url(f"add_result_for_case/{run_id}/{case_id}"),
            json=mocked_response,
        )
        response_text, error = api_request_handler_update_case_json.update_case_result(
            run_id, case_id
        )
        assert (
            response_text == mocked_response
        ), "Updated test case result doesn't match expected."
        assert error == "", "No error should be present."

    def test_update_case_result_error(
        self, api_request_handler_update_case_json: ApiRequestHandler, requests_mock
    ):
        """The purpose of this test is to check that proper message will be printed in
        case of error during test case result update."""
        run_id = 20
        case_id = 10
        requests_mock.post(
            create_url(f"add_result_for_case/{run_id}/{case_id}"),
            exc=requests.exceptions.ConnectTimeout,
        )
        response_text, error = api_request_handler_update_case_json.update_case_result(
            run_id, case_id
        )

        assert response_text == "", "No response text should be returned"
        assert (
            error
            == "Your upload to TestRail did not receive a successful response from your TestRail Instance."
            " Please check your settings and try again."
        ), "Connection error is expected."

    def test_update_case_no_cases_for_update(
        self, api_request_handler_update_case_json: ApiRequestHandler
    ):
        """The purpose of this test is to check that proper error message will be printed in case
        there are no test case result to be updated."""
        run_id = 20
        case_id = 100
        response_text, error = api_request_handler_update_case_json.update_case_result(
            run_id, case_id
        )

        assert response_text == "", "No response text should be returned"
        assert (
            error
            == "Could not match --case-id with result file. Please make sure that:\n"
            "--case-id matches ID (if present) under `testcase` tag in result xml file\nand\n"
            "only one result is present in result xml file."
        ), "Expected error message to be printed."
