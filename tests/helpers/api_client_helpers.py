from trcli.api.api_client import APIClientResult

TEST_RAIL_URL = "https://FakeTestRail.io"
SUFFIX_API_VERSION = "/index.php?/api/v2/"


def create_url(resource: str):
    """Create url based on given resource and predefined host and API version suffix"""
    return TEST_RAIL_URL + SUFFIX_API_VERSION + resource


def check_response(
    expected_status_code: int,
    expected_response_text: str,
    expected_error_message: str,
    response: APIClientResult,
):
    assert (
        response.status_code == expected_status_code
    ), f"Status code {expected_status_code} expected. Got {response.status_code} instead."
    assert (
        response.response_text == expected_response_text
    ), f"response_text not equal to expected: {expected_response_text}. Got: {response.response_text}"
    assert (
        response.error_message == expected_error_message
    ), f"error_message not equal to expected: {expected_error_message}. Got: {response.error_message}"


def check_calls_count(function_mock, expected_call_count=1):
    assert (
        function_mock.call_count == expected_call_count
    ), f"Function expected to be called {expected_call_count} but it was called: {function_mock.call_count}."
