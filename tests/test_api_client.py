import pytest

import trcli.cli
from trcli.constants import FAULT_MAPPING
from trcli.cli import Environment
from trcli.api.api_client import APIClient
from requests.exceptions import RequestException, Timeout, ConnectionError
from tests.helpers.api_client_helpers import (
    TEST_RAIL_URL,
    create_url,
    check_response,
    check_calls_count,
)
from tests.test_data.api_client_test_data import (
    FAKE_PROJECT_DATA,
    INVALID_TEST_CASE_ERROR,
    NO_PERMISSION_PROJECT_ERROR,
    API_RATE_LIMIT_REACHED_ERROR,
)


@pytest.fixture(scope="class")
def api_resources():
    environment = Environment()
    environment.verbose = False
    api_client = APIClient(host_name=TEST_RAIL_URL, logging_function=environment.vlog)
    yield api_client


class TestAPIClient:
    @pytest.mark.api_client
    def test_send_get_status_code_success(self, api_resources, requests_mock):
        """The purpose of this test is to check behaviour of send_get one receiving successful status code.
        Check that response was packed into APIClientResult, retry mechanism was not triggered."""
        requests_mock.get(
            create_url("get_projects"), status_code=200, json=FAKE_PROJECT_DATA
        )
        api_client = api_resources
        response = api_client.send_get("get_projects")

        check_calls_count(requests_mock)
        check_response(200, FAKE_PROJECT_DATA, "", response)

    @pytest.mark.api_client
    def test_send_post_status_code_success(self, api_resources, requests_mock):
        """The purpose of this test is to check behaviour of send_post one receiving successful status code.
        Check that response was packed into APIClientResult, retry mechanism was not triggered."""
        requests_mock.post(
            create_url("add_project"), status_code=201, json=FAKE_PROJECT_DATA
        )
        api_client = api_resources
        response = api_client.send_post("add_project", FAKE_PROJECT_DATA)

        check_calls_count(requests_mock)
        check_response(201, FAKE_PROJECT_DATA, "", response)

    @pytest.mark.api_client
    def test_send_get_status_code_not_success(self, api_resources, requests_mock):
        """The purpose of this test is to check behaviour of send_get one receiving not successful status code.
        Check that response was packed into APIClientResult, retry mechanism was not triggered."""
        requests_mock.get(
            create_url("get_cases/1&suite_id=3"),
            status_code=400,
            json=INVALID_TEST_CASE_ERROR,
        )
        api_client = api_resources
        response = api_client.send_get(
            "get_cases/1&suite_id=3",
        )

        check_calls_count(requests_mock)
        check_response(
            400, INVALID_TEST_CASE_ERROR, INVALID_TEST_CASE_ERROR["error"], response
        )

    @pytest.mark.api_client
    def test_send_post_status_code_not_success(self, api_resources, requests_mock):
        """The purpose of this test is to check behaviour of send_post one receiving not successful status code.
        Check that response was packed into APIClientResult, retry mechanism was not triggered."""
        requests_mock.post(
            create_url("add_project"), status_code=403, json=NO_PERMISSION_PROJECT_ERROR
        )
        api_client = api_resources
        response = api_client.send_post("add_project", {"fake_project_data": "data"})

        check_calls_count(requests_mock)
        check_response(
            403,
            NO_PERMISSION_PROJECT_ERROR,
            NO_PERMISSION_PROJECT_ERROR["error"],
            response,
        )

    @pytest.mark.api_client
    @pytest.mark.parametrize("retries, retry_after", [(4, "30"), (10, "60")])
    def test_retry_mechanism_too_many_requests(
        self, retries, retry_after, requests_mock, mocker
    ):
        """The purpose of this test is to check that retry mechanism will work as expected when
        429 - too many requests will be received as an answer on get request."""
        requests_mock.get(
            create_url("get_projects"),
            status_code=429,
            headers={"Retry-After": retry_after},
            json=API_RATE_LIMIT_REACHED_ERROR,
        )
        sleep_mock = mocker.patch("trcli.api.api_client.sleep")
        environment = Environment()
        environment.verbose = False
        api_client = APIClient(
            TEST_RAIL_URL, logging_function=environment.vlog, retries=retries
        )
        response = api_client.send_get("get_projects")

        check_calls_count(requests_mock, retries + 1)
        sleep_mock.assert_called_with(float(retry_after))
        check_response(
            429,
            API_RATE_LIMIT_REACHED_ERROR,
            API_RATE_LIMIT_REACHED_ERROR["error"],
            response,
        )

    @pytest.mark.api_client
    @pytest.mark.parametrize(
        "retries, exception, expected_error_msg",
        [
            (4, Timeout, FAULT_MAPPING["no_response_from_host"]),
            (10, ConnectionError, FAULT_MAPPING["connection_error"]),
        ],
        ids=["retry_on_timeout", "retry_on_connection_error"],
    )
    def test_retry_mechanism_exceptions(
        self, retries, exception, expected_error_msg, requests_mock
    ):
        """The purpose of this test is to check that retry mechanism will work as expected when
        facing Timeout and ConnectionError during sending get request."""
        requests_mock.get(create_url("get_projects"), exc=exception)
        environment = Environment()
        environment.verbose = False
        api_client = APIClient(
            TEST_RAIL_URL, logging_function=environment.vlog, retries=retries
        )
        response = api_client.send_get("get_projects")

        check_calls_count(requests_mock, retries + 1)
        check_response(-1, "", expected_error_msg, response)

    @pytest.mark.api_client
    def test_request_exception(self, api_resources, requests_mock):
        """The purpose of this test is to check that request exception during request sending would be caught and handled
        in a proper way (status code returned will be -1, proper error message would be returned)."""
        requests_mock.get(create_url("get_projects"), exc=RequestException)
        api_client = api_resources
        response = api_client.send_get("get_projects")

        check_calls_count(requests_mock)
        check_response(-1, "", FAULT_MAPPING["host_issues"], response)

    @pytest.mark.api_client
    def test_authentication_password(self, api_resources, requests_mock, mocker):
        """The purpose of this test is to check that proper credentials would be set
        when user would like to authenticate with username and password"""
        username = "user_name"
        password = "password_for_user_name"
        requests_mock.get(create_url("get_projects"))
        api_client = api_resources
        api_client.username = "user_name"
        api_client.password = "password_for_user_name"
        basic_auth_mock = mocker.patch("trcli.api.api_client.HTTPBasicAuth")
        _ = api_client.send_get("get_projects")

        basic_auth_mock.assert_called_with(username=username, password=password)

    @pytest.mark.api_client
    def test_authentication_api_key(self, api_resources, requests_mock, mocker):
        """The purpose of this test is to check that proper credentials would be set
        when user would like to authenticate with username and API key"""
        username = "user_name"
        api_key = "api_key_for_user_name"
        requests_mock.get(create_url("get_projects"))
        api_client = api_resources
        api_client.username = username
        api_client.api_key = api_key
        basic_auth_mock = mocker.patch("trcli.api.api_client.HTTPBasicAuth")
        _ = api_client.send_get("get_projects")

        basic_auth_mock.assert_called_with(username=username, password=api_key)

    @pytest.mark.api_client
    def test_not_json_response(self, api_resources, requests_mock, mocker):
        """The purpose of this test is to check if APIClient will handle properly situation
        where request response was not in json format."""
        requests_mock.get(create_url("get_projects"), json=["test", "list"])
        api_client = api_resources
        response = api_client.send_get("get_projects")

        check_calls_count(requests_mock)
        check_response(200, ["test", "list"], "", response)

    @pytest.mark.api_client
    def test_api_calls_are_logged(self, requests_mock, mocker):
        """The purpose of this test is to check if APIClient will log API request and responses."""
        environment = mocker.patch("trcli.cli.Environment")
        requests_mock.get(create_url("get_projects"), json=["test", "list"])
        expected_log_calls = [
            mocker.call(
                f"\n**** API Call\n"
                f"method: GET\n"
                f"url: https://FakeTestRail.io/index.php?/api/v2/get_projects\n"
            ),
            mocker.call(
                f"response status code: 200\n"
                + f"response body: ['test', 'list']\n"
                + "****"
            ),
        ]
        api_client = APIClient(TEST_RAIL_URL, logging_function=environment.vlog)
        _ = api_client.send_get("get_projects")

        environment.vlog.assert_has_calls(expected_log_calls)
