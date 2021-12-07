import pytest
from trcli.constants import FAULT_MAPPING
from requests_mock import Mocker
from trcli.api_client import APIClient
from requests.exceptions import RequestException, Timeout, ConnectionError
from tests.helpers.api_client_helpers import TEST_RAIL_URL, create_url
from tests.test_data.api_client_test_data import (
    FAKE_PROJECT_DATA,
    INVALID_TEST_CASE_ERROR,
    NO_PERMISSION_PROJECT_ERROR,
)


@pytest.fixture(scope="class")
def api_resources():
    api_client = APIClient(host_name=TEST_RAIL_URL)
    yield api_client


class TestAPIClient:
    @pytest.mark.api_client
    def test_get_status_code_success(self, api_resources, requests_mock):
        requests_mock.get(
            create_url("get_projects"), status_code=200, json=FAKE_PROJECT_DATA
        )
        api_client = api_resources
        result = api_client.send_get("get_projects")

        assert requests_mock.called_once
        assert result.status_code == 200
        assert result.response_text == FAKE_PROJECT_DATA
        assert result.error_message == ""

    @pytest.mark.api_client
    def test_post_status_code_success(self, api_resources, requests_mock):
        requests_mock.post(
            create_url("add_project"), status_code=200, json=FAKE_PROJECT_DATA
        )
        api_client = api_resources
        result = api_client.send_post("add_project", FAKE_PROJECT_DATA)

        assert requests_mock.called_once
        assert result.status_code == 200
        assert result.response_text == FAKE_PROJECT_DATA
        assert result.error_message == ""

    @pytest.mark.api_client
    def test_get_status_code_not_success(self, api_resources, requests_mock):
        requests_mock.get(
            create_url("get_cases/1&suite_id=3"),
            status_code=400,
            json=INVALID_TEST_CASE_ERROR,
        )
        api_client = api_resources
        result = api_client.send_get(
            "get_cases/1&suite_id=3",
        )

        assert requests_mock.called_once
        assert result.status_code == 400
        assert result.response_text == INVALID_TEST_CASE_ERROR
        assert result.error_message == INVALID_TEST_CASE_ERROR["error"]

    @pytest.mark.api_client
    def test_post_status_code_not_success(self, api_resources, requests_mock):
        requests_mock.post(
            create_url("add_project"), status_code=403, json=NO_PERMISSION_PROJECT_ERROR
        )
        api_client = api_resources
        response = api_client.send_post("add_project", {"fake_project_data": "data"})

        assert response.status_code == 403
        assert response.response_text == NO_PERMISSION_PROJECT_ERROR
        assert response.error_message == NO_PERMISSION_PROJECT_ERROR["error"]

    @pytest.mark.api_client
    @pytest.mark.parametrize("retries", [4, 10])
    def test_retry_mechanism_too_many_requests(
        self, retries, requests_mock: Mocker, mocker
    ):
        requests_mock.get(
            create_url("get_projects"), status_code=429, headers={"Retry-After": "30"}
        )
        sleep_mock = mocker.patch("trcli.api_client.sleep")
        api_client = APIClient(TEST_RAIL_URL, retries=retries)
        response = api_client.send_get("get_projects")

        assert requests_mock.call_count == retries + 1
        sleep_mock.assert_called_with(float("30"))
        assert response.status_code == 429

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
        requests_mock.get(create_url("get_projects"), exc=exception)
        api_client = APIClient(TEST_RAIL_URL, retries=retries)
        response = api_client.send_get("get_projects")

        assert requests_mock.call_count == retries + 1
        assert response.status_code == -1
        assert response.response_text == ""
        assert response.error_message == expected_error_msg

    @pytest.mark.api_client
    def test_request_exception(self, api_resources, requests_mock):
        requests_mock.get(create_url("get_projects"), exc=RequestException)
        api_client = api_resources
        response = api_client.send_get("get_projects")

        assert requests_mock.call_count == 1
        assert response.status_code == -1
        assert response.response_text == ""
        assert response.error_message == FAULT_MAPPING["host_issues"]

    @pytest.mark.api_client
    def test_authentication_password(self, api_resources, requests_mock, mocker):
        username = "user_name"
        password = "password_for_user_name"
        requests_mock.get(create_url("get_projects"))
        api_client = api_resources
        api_client.username = "user_name"
        api_client.password = "password_for_user_name"
        basic_auth_mock = mocker.patch("trcli.api_client.HTTPBasicAuth")

        _ = api_client.send_get("get_projects")
        basic_auth_mock.assert_called_with(username=username, password=password)

    @pytest.mark.api_client
    def test_authentication_api_key(self, api_resources, requests_mock, mocker):
        username = "user_name"
        api_key = "api_key_for_user_name"
        requests_mock.get(create_url("get_projects"))
        api_client = api_resources
        api_client.username = username
        api_client.api_key = api_key
        basic_auth_mock = mocker.patch("trcli.api_client.HTTPBasicAuth")
        _ = api_client.send_get("get_projects")
        basic_auth_mock.assert_called_with(username=username, password=api_key)
