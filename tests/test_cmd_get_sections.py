import json
from unittest import mock

from click.testing import CliRunner

from trcli.api.api_client import APIClientResult
from trcli.cli import cli as trcli_cli


class TestCmdGetSections:
    """Tests for the get_sections CLI command."""

    BASE_ARGS = [
        "-h", "https://test.testrail.com",
        "-u", "user@example.com",
        "-p", "password123",
        "get_sections",
        "--project-id", "1",
    ]

    @mock.patch("trcli.commands.cmd_get_sections.create_api_client")
    def test_happy_path_returns_json(self, mock_create_client):
        sections_data = [{"id": 10, "name": "Login"}, {"id": 11, "name": "Checkout"}]
        mock_client = mock_create_client.return_value
        mock_client.send_get.return_value = APIClientResult(
            status_code=200, response_text=sections_data, error_message=""
        )

        runner = CliRunner()
        result = runner.invoke(trcli_cli, self.BASE_ARGS, catch_exceptions=False)

        assert result.exit_code == 0
        assert json.loads(result.output) == sections_data
        mock_client.send_get.assert_called_once_with("get_sections/1")

    @mock.patch("trcli.commands.cmd_get_sections.create_api_client")
    def test_with_suite_id_filter(self, mock_create_client):
        sections_data = [{"id": 10, "name": "Suite Section"}]
        mock_client = mock_create_client.return_value
        mock_client.send_get.return_value = APIClientResult(
            status_code=200, response_text=sections_data, error_message=""
        )

        args = self.BASE_ARGS + ["--suite-id", "5"]
        runner = CliRunner()
        result = runner.invoke(trcli_cli, args, catch_exceptions=False)

        assert result.exit_code == 0
        assert json.loads(result.output) == sections_data
        mock_client.send_get.assert_called_once_with("get_sections/1&suite_id=5")

    @mock.patch("trcli.commands.cmd_get_sections.create_api_client")
    def test_paginated_response_collects_all_pages(self, mock_create_client):
        page1 = {
            "sections": [{"id": 1, "name": "Section 1"}],
            "_links": {"next": "get_sections/1&offset=250"},
        }
        page2 = {
            "sections": [{"id": 2, "name": "Section 2"}],
            "_links": {"next": None},
        }
        mock_client = mock_create_client.return_value
        mock_client.send_get.side_effect = [
            APIClientResult(status_code=200, response_text=page1, error_message=""),
            APIClientResult(status_code=200, response_text=page2, error_message=""),
        ]

        runner = CliRunner()
        result = runner.invoke(trcli_cli, self.BASE_ARGS, catch_exceptions=False)

        assert result.exit_code == 0
        assert json.loads(result.output) == [
            {"id": 1, "name": "Section 1"},
            {"id": 2, "name": "Section 2"},
        ]
        assert mock_client.send_get.call_count == 2

    @mock.patch("trcli.commands.cmd_get_sections.create_api_client")
    def test_api_error_message_exits_with_code_1(self, mock_create_client):
        mock_client = mock_create_client.return_value
        mock_client.send_get.return_value = APIClientResult(
            status_code=-1, response_text="", error_message="Connection refused"
        )

        runner = CliRunner()
        result = runner.invoke(trcli_cli, self.BASE_ARGS)

        assert result.exit_code == 1
        assert "Connection refused" in result.output

    def test_missing_project_id_exits_nonzero(self):
        args = [
            "-h", "https://test.testrail.com",
            "-u", "user@example.com",
            "-p", "password123",
            "get_sections",
        ]
        runner = CliRunner()
        result = runner.invoke(trcli_cli, args)

        assert result.exit_code == 2
        assert "project-id" in result.output.lower()

    def test_missing_host_exits_nonzero(self):
        args = [
            "-u", "user@example.com",
            "-p", "password123",
            "get_sections",
            "--project-id",
            "1",
        ]
        runner = CliRunner()
        result = runner.invoke(trcli_cli, args)

        assert result.exit_code == 1
        assert "--host is required" in result.output
