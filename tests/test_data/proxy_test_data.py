from trcli.settings import DEFAULT_API_CALL_TIMEOUT

FAKE_PROJECT_DATA = {"fake_project_data": "data"}
INVALID_TEST_CASE_ERROR = {"error": "Invalid or unknown test case"}
API_RATE_LIMIT_REACHED_ERROR = {"error": "API rate limit reached"}
NO_PERMISSION_PROJECT_ERROR = {
    "error": "No permissions to add projects (requires admin rights)"
}
TIMEOUT_PARSE_ERROR = (
    f"Warning. Could not convert provided 'timeout' to float. "
    f"Please make sure that timeout format is correct. Setting to default: "
    f"{DEFAULT_API_CALL_TIMEOUT}"
)

#proxy test data
FAKE_PROXY = "http://127.0.0.1:8080"
FAKE_PROXY_USER = "username:password"

PROXY_ERROR_MESSAGE = (
    f"Failed to connect to the proxy server. Please check the proxy settings and ensure the server is available."
)