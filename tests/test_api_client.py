import pytest
from unittest.mock import patch, MagicMock
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
    TIMEOUT_PARSE_ERROR,
)


@pytest.fixture(scope="class")
def api_resources_maker():
    def _make_api_resources(retries=3, environment=Environment(), timeout=30):
        environment.verbose = False
        api_client = APIClient(
            host_name=TEST_RAIL_URL,
            verbose_logging_function=environment.vlog,
            logging_function=environment.log,
            retries=retries,
            timeout=timeout,
        )
        return api_client

    return _make_api_resources


@pytest.fixture(scope="class")
def api_resources(api_resources_maker):
    yield api_resources_maker()


class TestAPIClient:
    @pytest.mark.api_client
    def test_send_get_status_code_success(self, api_resources, requests_mock):
        """The purpose of this test is to check behaviour of send_get one receiving successful status code.
        Check that response was packed into APIClientResult, retry mechanism was not triggered."""
        requests_mock.get(create_url("get_projects"), status_code=200, json=FAKE_PROJECT_DATA)
        api_client = api_resources
        response = api_client.send_get("get_projects")

        check_calls_count(requests_mock)
        check_response(200, FAKE_PROJECT_DATA, "", response)

    @pytest.mark.api_client
    def test_send_post_status_code_success(self, api_resources, requests_mock):
        """The purpose of this test is to check behaviour of send_post one receiving successful status code.
        Check that response was packed into APIClientResult, retry mechanism was not triggered."""
        requests_mock.post(create_url("add_project"), status_code=201, json=FAKE_PROJECT_DATA)
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
        check_response(400, INVALID_TEST_CASE_ERROR, INVALID_TEST_CASE_ERROR["error"], response)

    @pytest.mark.api_client
    def test_send_post_status_code_not_success(self, api_resources, requests_mock):
        """The purpose of this test is to check behaviour of send_post one receiving not successful status code.
        Check that response was packed into APIClientResult, retry mechanism was not triggered."""
        requests_mock.post(create_url("add_project"), status_code=403, json=NO_PERMISSION_PROJECT_ERROR)
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
    def test_retry_mechanism_too_many_requests(self, retries, retry_after, api_resources_maker, requests_mock, mocker):
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
        api_client = api_resources_maker(retries=retries)
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
        self,
        retries,
        exception,
        expected_error_msg,
        api_resources_maker,
        requests_mock,
        mocker,
    ):
        """The purpose of this test is to check that retry mechanism will work as expected when
        facing Timeout and ConnectionError during sending get request."""
        requests_mock.get(create_url("get_projects"), exc=exception)
        environment = mocker.patch("trcli.cli.Environment")
        api_client = api_resources_maker(retries=retries, environment=environment)
        response = api_client.send_get("get_projects")
        expected_log_calls = retries * [
            mocker.call(
                f"\n**** API Call\n"
                f"method: GET\n"
                f"url: https://FakeTestRail.io/index.php?/api/v2/get_projects\n"
                f"headers:\n"
                f"  User-Agent: TRCLI\n"
                f"  Content-Type: application/json\n"
            ),
        ]

        check_calls_count(requests_mock, retries + 1)
        check_response(-1, "", expected_error_msg, response)
        environment.vlog.assert_has_calls(expected_log_calls)

    @pytest.mark.api_client
    def test_request_exception(self, api_resources_maker, requests_mock, mocker):
        """The purpose of this test is to check that request exception during request sending would be caught and handled
        in a proper way (status code returned will be -1, proper error message would be returned)."""
        environment = mocker.patch("trcli.cli.Environment")
        request = create_url("get_projects")
        requests_mock.get(request, exc=RequestException(request=request))
        api_client = api_resources_maker(environment=environment)

        expected_log_calls = [
            mocker.call(
                f"\n**** API Call\n"
                f"method: GET\n"
                f"url: https://FakeTestRail.io/index.php?/api/v2/get_projects\n"
                f"headers:\n"
                f"  User-Agent: TRCLI\n"
                f"  Content-Type: application/json\n"
            )
        ]
        response = api_client.send_get("get_projects")

        check_calls_count(requests_mock)
        check_response(
            -1,
            "",
            FAULT_MAPPING["unexpected_error_during_request_send"].format(request=request),
            response,
        )
        environment.vlog.assert_has_calls(expected_log_calls)

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
        content = b"Test"
        requests_mock.get(create_url("get_projects"), content=content)
        api_client = api_resources
        response = api_client.send_get("get_projects")
        check_calls_count(requests_mock)
        expected_error_message = FAULT_MAPPING["invalid_json_response"].format(status_code=200, response_preview="Test")
        check_response(200, str(content), expected_error_message, response)

    @pytest.mark.api_client
    def test_api_calls_are_logged(self, api_resources_maker, requests_mock, mocker):
        """The purpose of this test is to check if APIClient will log API request and responses."""
        environment = mocker.patch("trcli.cli.Environment")
        requests_mock.get(create_url("get_projects"), json=["test", "list"])
        expected_log_calls = [
            mocker.call(
                f"\n**** API Call\n"
                f"method: GET\n"
                f"url: https://FakeTestRail.io/index.php?/api/v2/get_projects\n"
                f"headers:\n"
                f"  User-Agent: TRCLI\n"
                f"  Content-Type: application/json\n"
                f"response status code: 200\n"
                f"response body: ['test', 'list']\n"
                "****"
            )
        ]
        api_client = api_resources_maker(environment=environment)
        _ = api_client.send_get("get_projects")

        environment.vlog.assert_has_calls(expected_log_calls)

    @pytest.mark.api_client
    @pytest.mark.parametrize(
        "timeout_value, expected_message",
        [
            (10.5, ""),
            (10, ""),
            ("10", ""),
            ("10.5", ""),
            ("10.5a", TIMEOUT_PARSE_ERROR),
        ],
        ids=["float", "int", "int as string", "float as string", "invalid value"],
    )
    def test_timeout_is_parsed_and_validated(self, timeout_value, expected_message, api_resources_maker, mocker):
        environment = mocker.patch("trcli.cli.Environment")
        api_client = api_resources_maker(environment=environment, timeout=timeout_value)

        if expected_message:
            environment.log.assert_has_calls([mocker.call(TIMEOUT_PARSE_ERROR)])
        else:
            with pytest.raises(AssertionError):
                environment.log.assert_has_calls([mocker.call(TIMEOUT_PARSE_ERROR)])

    @pytest.mark.api_client
    @patch("requests.post")
    def test_send_post_with_json_default(self, mock_post, api_resources_maker):
        """Test that send_post uses JSON by default"""
        # Mock response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"id": 1, "title": "Test"}
        mock_response.content = b'{"id": 1, "title": "Test"}'
        mock_post.return_value = mock_response

        # Create API client
        api_client = api_resources_maker()

        # Call send_post without as_form_data parameter (should default to JSON)
        result = api_client.send_post("test_endpoint", {":title": "Test Label"})

        # Verify the result
        assert result.status_code == 200
        assert result.response_text == {"id": 1, "title": "Test"}

        # Verify JSON was used
        mock_post.assert_called_once()
        call_args = mock_post.call_args

        # Should use json parameter, not data
        assert "json" in call_args[1]
        assert "data" not in call_args[1]
        assert call_args[1]["json"] == {":title": "Test Label"}

        # Should have JSON content type header
        headers = call_args[1]["headers"]
        assert headers.get("Content-Type") == "application/json"

    @pytest.mark.api_client
    @patch("requests.post")
    def test_send_post_with_form_data_true(self, mock_post, api_resources_maker):
        """Test that send_post uses form-data when as_form_data=True"""
        # Mock response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"id": 1, "title": "Test"}
        mock_response.content = b'{"id": 1, "title": "Test"}'
        mock_post.return_value = mock_response

        # Create API client
        api_client = api_resources_maker()

        # Call send_post with as_form_data=True
        result = api_client.send_post("test_endpoint", {":title": "Test Label"}, as_form_data=True)

        # Verify the result
        assert result.status_code == 200
        assert result.response_text == {"id": 1, "title": "Test"}

        # Verify form-data was used
        mock_post.assert_called_once()
        call_args = mock_post.call_args

        # Should use data parameter, not json
        assert "data" in call_args[1]
        assert "json" not in call_args[1]
        assert call_args[1]["data"] == {":title": "Test Label"}

        # Should NOT have files parameter (uses application/x-www-form-urlencoded)
        assert "files" not in call_args[1] or call_args[1]["files"] is None

        # Should NOT have JSON content type header when using form-data
        headers = call_args[1]["headers"]
        assert headers.get("Content-Type") != "application/json"

    @pytest.mark.api_client
    @patch("requests.post")
    def test_send_post_with_form_data_false(self, mock_post, api_resources_maker):
        """Test that send_post uses JSON when as_form_data=False explicitly"""
        # Mock response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"id": 1, "title": "Test"}
        mock_response.content = b'{"id": 1, "title": "Test"}'
        mock_post.return_value = mock_response

        # Create API client
        api_client = api_resources_maker()

        # Call send_post with as_form_data=False
        result = api_client.send_post("test_endpoint", {":title": "Test Label"}, as_form_data=False)

        # Verify the result
        assert result.status_code == 200
        assert result.response_text == {"id": 1, "title": "Test"}

        # Verify JSON was used
        mock_post.assert_called_once()
        call_args = mock_post.call_args

        # Should use json parameter, not data
        assert "json" in call_args[1]
        assert "data" not in call_args[1]
        assert call_args[1]["json"] == {":title": "Test Label"}

        # Should have JSON content type header
        headers = call_args[1]["headers"]
        assert headers.get("Content-Type") == "application/json"

    @pytest.mark.api_client
    @patch("requests.post")
    def test_send_post_with_files_and_form_data(self, mock_post, api_resources_maker):
        """Test that send_post handles files parameter with form-data"""
        # Mock response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"id": 1, "title": "Test"}
        mock_response.content = b'{"id": 1, "title": "Test"}'
        mock_post.return_value = mock_response

        # Create API client
        api_client = api_resources_maker()

        # Call send_post with files and form-data
        files = {"file1": "/path/to/file"}
        result = api_client.send_post("test_endpoint", {":title": "Test Label"}, files=files, as_form_data=True)

        # Verify the result
        assert result.status_code == 200
        assert result.response_text == {"id": 1, "title": "Test"}

        # Verify form-data was used
        mock_post.assert_called_once()
        call_args = mock_post.call_args

        # Should use data parameter, not json
        assert "data" in call_args[1]
        assert "json" not in call_args[1]
        assert call_args[1]["data"] == {":title": "Test Label"}
        # Files should be passed through as provided (not replaced with empty dict)
        assert call_args[1]["files"] == files

        # Should NOT have JSON content type header when using files
        headers = call_args[1]["headers"]
        assert headers.get("Content-Type") != "application/json"

    @pytest.mark.api_client
    def test_empty_response_is_valid(self, api_resources_maker, requests_mock):
        """Test that empty response body with HTTP 200 is treated as valid (e.g., for DELETE operations)."""
        api_client = api_resources_maker()
        api_client.uploader_metadata = "test_metadata_value"

        # DELETE operations may return empty body with HTTP 200
        requests_mock.post(create_url("delete_section/123"), status_code=200, content=b"")

        response = api_client.send_post("delete_section/123")

        # Verify that the request was made only once (no retry)
        assert requests_mock.call_count == 1

        # Verify successful response with empty dict
        check_response(200, {}, "", response)

    @pytest.mark.api_client
    def test_metadata_header_sent_when_enabled(self, api_resources_maker, requests_mock):
        """Test that X-Uploader-Metadata header is sent when enabled."""
        api_client = api_resources_maker()
        test_metadata = "test_metadata_value"
        api_client.uploader_metadata = test_metadata

        requests_mock.get(create_url("get_projects"), json=FAKE_PROJECT_DATA)

        response = api_client.send_get("get_projects")

        # Check that metadata header was sent
        request_headers = requests_mock.last_request.headers
        assert "X-Uploader-Metadata" in request_headers
        assert request_headers["X-Uploader-Metadata"] == test_metadata

        # Verify successful response
        check_response(200, FAKE_PROJECT_DATA, "", response)
