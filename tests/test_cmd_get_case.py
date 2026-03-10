from unittest import mock

import pytest
from click.testing import CliRunner

from trcli.api.api_client import APIClientResult
from trcli.cli import cli as trcli_cli


class TestCmdGetCase:
    """Tests for the get_case CLI command."""

    BASE_ARGS = [
        "-h", "https://test.testrail.com",
        "-u", "user@example.com",
        "-p", "password123",
        "get_case",
        "--case-id", "99",
    ]

    @mock.patch("trcli.commands.cmd_get_case._create_api_client")
    def test_happy_path_returns_json(self, mock_create_client):
        """Successful API response prints JSON to stdout."""
        case_data = {"id": 99, "title": "My Test Case", "section_id": 5}
        mock_client = mock_create_client.return_value
        mock_client.send_get.return_value = APIClientResult(
            status_code=200, response_text=case_data, error_message=""
        )

        runner = CliRunner()
        result = runner.invoke(trcli_cli, self.BASE_ARGS, catch_exceptions=False)

        assert result.exit_code == 0
        assert '"My Test Case"' in result.output
        assert '"id": 99' in result.output
        mock_client.send_get.assert_called_once_with("get_case/99")

    @mock.patch("trcli.commands.cmd_get_case._create_api_client")
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

    @mock.patch("trcli.commands.cmd_get_case._create_api_client")
    def test_api_non_200_status_exits_with_code_1(self, mock_create_client):
        """Non-200 status code prints error with exit code 1."""
        mock_client = mock_create_client.return_value
        mock_client.send_get.return_value = APIClientResult(
            status_code=404, response_text="", error_message=""
        )

        runner = CliRunner()
        result = runner.invoke(trcli_cli, self.BASE_ARGS)

        assert result.exit_code == 1
        assert "404" in result.output

    def test_missing_case_id_exits_nonzero(self):
        """Missing --case-id triggers a Click error."""
        args = [
            "-h", "https://test.testrail.com",
            "-u", "user@example.com",
            "-p", "password123",
            "get_case",
        ]
        runner = CliRunner()
        result = runner.invoke(trcli_cli, args)

        assert result.exit_code != 0

    def test_missing_host_exits_nonzero(self):
        """Missing -h triggers an error."""
        args = [
            "-u", "user@example.com",
            "-p", "password123",
            "get_case",
            "--case-id", "99",
        ]
        runner = CliRunner()
        result = runner.invoke(trcli_cli, args)

        assert result.exit_code == 1
        assert "--host is required" in result.output

    def test_missing_password_and_key_exits_nonzero(self):
        """Missing both -p and -k triggers an error."""
        args = [
            "-h", "https://test.testrail.com",
            "-u", "user@example.com",
            "get_case",
            "--case-id", "99",
        ]
        runner = CliRunner()
        result = runner.invoke(trcli_cli, args)

        assert result.exit_code == 1
        assert "--password or --key is required" in result.output
