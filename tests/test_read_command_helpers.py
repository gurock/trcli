from unittest import mock

from trcli.api.api_client import APIClientResult
from trcli.cli import Environment
from trcli.commands.read_command_helpers import (
    build_endpoint,
    create_api_client,
    fetch_all_pages,
    fetch_single_resource,
)


def test_build_endpoint_omits_none_values():
    assert build_endpoint("get_cases", 1, suite_id=2, section_id=None) == "get_cases/1&suite_id=2"


def test_fetch_single_resource_returns_error_for_non_200():
    client = mock.Mock()
    client.send_get.return_value = APIClientResult(status_code=404, response_text="", error_message="")

    data, error = fetch_single_resource(client, "get_case/99")

    assert data is None
    assert error == "API returned status 404"


def test_fetch_all_pages_collects_paginated_response():
    client = mock.Mock()
    client.send_get.side_effect = [
        APIClientResult(
            status_code=200,
            response_text={"cases": [{"id": 1}], "_links": {"next": "get_cases/1&offset=250"}},
            error_message="",
        ),
        APIClientResult(
            status_code=200,
            response_text={"cases": [{"id": 2}], "_links": {"next": None}},
            error_message="",
        ),
    ]

    data, error = fetch_all_pages(client, "cases", "get_cases/1")

    assert error == ""
    assert data == [{"id": 1}, {"id": 2}]
    assert client.send_get.call_args_list == [mock.call("get_cases/1"), mock.call("get_cases/1&offset=250")]


def test_fetch_all_pages_supports_legacy_list_response():
    client = mock.Mock()
    client.send_get.return_value = APIClientResult(
        status_code=200,
        response_text=[{"id": 1}, {"id": 2}],
        error_message="",
    )

    data, error = fetch_all_pages(client, "suites", "get_suites/1")

    assert error == ""
    assert data == [{"id": 1}, {"id": 2}]


def test_fetch_all_pages_returns_error_from_later_page():
    client = mock.Mock()
    client.send_get.side_effect = [
        APIClientResult(
            status_code=200,
            response_text={"cases": [{"id": 1}], "_links": {"next": "get_cases/1&offset=250"}},
            error_message="",
        ),
        APIClientResult(status_code=-1, response_text="", error_message="Connection refused"),
    ]

    data, error = fetch_all_pages(client, "cases", "get_cases/1")

    assert data is None
    assert error == "Connection refused"


@mock.patch("trcli.commands.read_command_helpers.APIClient")
def test_create_api_client_passes_connection_options(mock_api_client_cls):
    environment = Environment()
    environment.host = "https://test.testrail.com"
    environment.username = "user@example.com"
    environment.password = "password"
    environment.key = "api-key"
    environment.insecure = True
    environment.proxy = "http://proxy.example.com:8080"
    environment.proxy_user = "proxy-user:proxy-password"
    environment.noproxy = "localhost,127.0.0.1"
    environment.timeout = 12.5

    client = create_api_client(environment)

    mock_api_client_cls.assert_called_once()
    _, kwargs = mock_api_client_cls.call_args
    assert kwargs["verify"] is False
    assert kwargs["proxy"] == "http://proxy.example.com:8080"
    assert kwargs["proxy_user"] == "proxy-user:proxy-password"
    assert kwargs["noproxy"] == "localhost,127.0.0.1"
    assert kwargs["timeout"] == 12.5
    assert client.username == "user@example.com"
    assert client.password == "password"
    assert client.api_key == "api-key"
