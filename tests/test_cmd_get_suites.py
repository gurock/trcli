from unittest import mock

import pytest
from click.testing import CliRunner

from trcli.api.api_client import APIClientResult
from trcli.cli import cli as trcli_cli


class TestCmdGetSuites:
    """Tests for the get_suites CLI command."""

    BASE_ARGS = [
        "-h", "https://test.testrail.com",
        "-u", "user@example.com",
        "-p", "password123",
        "get_suites",
        "--project-id", "1",
    ]

    @mock.patch("trcli.commands.cmd_get_suites._create_api_client")
    def test_happy_path_returns_json(self, mock_create_client):
        """Successful API response prints JSON to stdout."""
        suites_data = [{"id": 1, "name": "Suite A"}, {"id": 2, "name": "Suite B"}]
        mock_client = mock_create_client.return_value
        mock_client.send_get.return_value = APIClientResult(
            status_code=200, response_text=suites_data, error_message=""
        )

        runner = CliRunner()
        result = runner.invoke(trcli_cli, self.BASE_ARGS, catch_exceptions=False)

        assert result.exit_code == 0
        assert '"Suite A"' in result.output
        assert '"Suite B"' in result.output
        mock_client.send_get.assert_called_once_with("get_suites/1")

    @mock.patch("trcli.commands.cmd_get_suites._create_api_client")
    def test_api_error_message_exits_with_code_1(self, mock_create_client):
        """API error message is output with exit code 1."""
        mock_client = mock_create_client.return_value
        mock_client.send_get.return_value = APIClientResult(
            status_code=-1, response_text="", error_message="Connection refused"
        )

        runner = CliRunner()
        result = runner.invoke(trcli_cli, self.BASE_ARGS)

        assert result.exit_code == 1
        assert "Connection refused" in result.output

    @mock.patch("trcli.commands.cmd_get_suites._create_api_client")
    def test_api_non_200_status_exits_with_code_1(self, mock_create_client):
        """Non-200 status code prints error with exit code 1."""
        mock_client = mock_create_client.return_value
        mock_client.send_get.return_value = APIClientResult(
            status_code=403, response_text="", error_message=""
        )

        runner = CliRunner()
        result = runner.invoke(trcli_cli, self.BASE_ARGS)

        assert result.exit_code == 1
        assert "403" in result.output

    def test_missing_project_id_exits_nonzero(self):
        """Missing --project-id triggers a Click error."""
        args = [
            "-h", "https://test.testrail.com",
            "-u", "user@example.com",
            "-p", "password123",
            "get_suites",
        ]
        runner = CliRunner()
        result = runner.invoke(trcli_cli, args)

        assert result.exit_code != 0

    def test_missing_host_exits_nonzero(self):
        """Missing -h triggers an error."""
        args = [
            "-u", "user@example.com",
            "-p", "password123",
            "get_suites",
            "--project-id", "1",
        ]
        runner = CliRunner()
        result = runner.invoke(trcli_cli, args)

        assert result.exit_code == 1
        assert "--host is required" in result.output
