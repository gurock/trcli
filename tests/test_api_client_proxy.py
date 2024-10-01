import pytest
from trcli.constants import FAULT_MAPPING
from trcli.cli import Environment
from requests.exceptions import ProxyError
from trcli.api.api_client import APIClient
from tests.helpers.api_client_helpers import (
    TEST_RAIL_URL,
    create_url,
    check_response,
    check_calls_count,
)
from tests.test_data.proxy_test_data import FAKE_PROJECT_DATA, FAKE_PROXY, FAKE_PROXY_USER, PROXY_ERROR_MESSAGE


@pytest.fixture(scope="class")
def api_resources_maker():
    def _make_api_resources(retries=3, environment=None, timeout=30, proxy=None, proxy_user=None, noproxy=None):
        if environment is None:
            environment = Environment()
        environment.verbose = False
        api_client = APIClient(
            host_name=TEST_RAIL_URL,
            verbose_logging_function=environment.vlog,
            logging_function=environment.log,
            retries=retries,
            timeout=timeout,
            proxy=proxy,
            proxy_user=proxy_user,
            noproxy=noproxy,  # For bypassing proxy when using --noproxy
        )
        return api_client

    return _make_api_resources


@pytest.fixture(scope="class")
def api_resources(api_resources_maker):
    yield api_resources_maker()


class TestAPIClientProxy:
    @pytest.mark.proxy
    def test_send_get_with_proxy(self, api_resources_maker, requests_mock):
        """Test send_get works correctly with a proxy."""
        requests_mock.get(create_url("get_projects"), status_code=200, json=FAKE_PROJECT_DATA)
        api_client = api_resources_maker(proxy=FAKE_PROXY)

        response = api_client.send_get("get_projects")

        check_calls_count(requests_mock)
        check_response(200, FAKE_PROJECT_DATA, "", response)

    @pytest.mark.proxy
    def test_send_post_with_proxy(self, api_resources_maker, requests_mock):
        """Test send_post works correctly with a proxy."""
        requests_mock.post(create_url("add_project"), status_code=201, json=FAKE_PROJECT_DATA)
        api_client = api_resources_maker(proxy=FAKE_PROXY)

        response = api_client.send_post("add_project", FAKE_PROJECT_DATA)

        check_calls_count(requests_mock)
        check_response(201, FAKE_PROJECT_DATA, "", response)

    @pytest.mark.proxy
    def test_send_get_with_proxy_authentication(self, api_resources_maker, requests_mock, mocker):
        """Test proxy with authentication (proxy_user)."""
        requests_mock.get(create_url("get_projects"), status_code=200, json=FAKE_PROJECT_DATA)
        basic_auth_mock = mocker.patch("trcli.api.api_client.b64encode")

        api_client = api_resources_maker(proxy=FAKE_PROXY, proxy_user=FAKE_PROXY_USER)
        _ = api_client.send_get("get_projects")

        basic_auth_mock.assert_called_once_with(FAKE_PROXY_USER.encode('utf-8'))

    @pytest.mark.proxy
    def test_send_get_proxy_error(self, api_resources_maker, requests_mock):
        """Test handling a proxy authentication failure."""
        requests_mock.get(create_url("get_projects"), exc=ProxyError)

        api_client = api_resources_maker(proxy=FAKE_PROXY)

        response = api_client.send_get("get_projects")

        check_calls_count(requests_mock)
        check_response(-1, "", PROXY_ERROR_MESSAGE, response)

    @pytest.mark.proxy
    def test_send_get_no_proxy(self, api_resources_maker, requests_mock):
        """Test API request without a proxy (no --proxy provided)."""
        requests_mock.get(create_url("get_projects"), status_code=200, json=FAKE_PROJECT_DATA)
        api_client = api_resources_maker()

        response = api_client.send_get("get_projects")

        check_calls_count(requests_mock)
        check_response(200, FAKE_PROJECT_DATA, "", response)

    @pytest.mark.proxy
    def test_send_get_bypass_proxy(self, api_resources_maker, requests_mock, mocker):
        """Test that proxy is bypassed for certain hosts using --noproxy option."""
        requests_mock.get(create_url("get_projects"), status_code=200, json=FAKE_PROJECT_DATA)
        proxy_bypass_mock = mocker.patch("trcli.api.api_client.APIClient._get_proxies_for_request", return_value=None)

        api_client = api_resources_maker(proxy=FAKE_PROXY, noproxy="127.0.0.1")
        _ = api_client.send_get("get_projects")

        proxy_bypass_mock.assert_called_once()

    @pytest.mark.proxy
    def test_send_get_with_invalid_proxy_user(self, api_resources_maker, requests_mock, mocker):
        """Test handling invalid proxy authentication."""
        requests_mock.get(create_url("get_projects"), exc=ProxyError)

        api_client = api_resources_maker(proxy=FAKE_PROXY, proxy_user="invalid_user:invalid_password")

        response = api_client.send_get("get_projects")

        check_calls_count(requests_mock)
        check_response(-1, "", PROXY_ERROR_MESSAGE, response)