from unittest import mock

import pytest
from click.testing import CliRunner

from trcli.api.api_client import APIClientResult
from trcli.cli import cli as trcli_cli


class TestCmdGetCases:
    """Tests for the get_cases CLI command."""

    BASE_ARGS = [
        "-h", "https://test.testrail.com",
        "-u", "user@example.com",
        "-p", "password123",
        "get_cases",
        "--project-id", "1",
        "--suite-id", "10",
    ]

    @mock.patch("trcli.commands.cmd_get_cases._create_api_client")
    def test_happy_path_returns_json(self, mock_create_client):
        """Successful API response prints JSON to stdout."""
        cases_data = [{"id": 100, "title": "Login test"}, {"id": 101, "title": "Logout test"}]
        mock_client = mock_create_client.return_value
        mock_client.send_get.return_value = APIClientResult(
            status_code=200, response_text=cases_data, error_message=""
        )

        runner = CliRunner()
        result = runner.invoke(trcli_cli, self.BASE_ARGS, catch_exceptions=False)

        assert result.exit_code == 0
        assert '"Login test"' in result.output
        assert '"Logout test"' in result.output

    @mock.patch("trcli.commands.cmd_get_cases._create_api_client")
    def test_happy_path_paginated(self, mock_create_client):
        """Paginated API response collects all pages."""
        page1 = {
            "cases": [{"id": 1, "title": "Case 1"}],
            "_links": {"next": "get_cases/1&suite_id=10&offset=1"},
        }
        page2 = {
            "cases": [{"id": 2, "title": "Case 2"}],
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
        assert '"Case 1"' in result.output
        assert '"Case 2"' in result.output
        assert mock_client.send_get.call_count == 2

    @mock.patch("trcli.commands.cmd_get_cases._create_api_client")
    def test_with_section_id_filter(self, mock_create_client):
        """Optional --section-id is appended to the API URL."""
        cases_data = [{"id": 100, "title": "Filtered case"}]
        mock_client = mock_create_client.return_value
        mock_client.send_get.return_value = APIClientResult(
            status_code=200, response_text=cases_data, error_message=""
        )

        args = self.BASE_ARGS + ["--section-id", "5"]
        runner = CliRunner()
        result = runner.invoke(trcli_cli, args, catch_exceptions=False)

        assert result.exit_code == 0
        call_args = mock_client.send_get.call_args[0][0]
        assert "section_id=5" in call_args

    @mock.patch("trcli.commands.cmd_get_cases._create_api_client")
    def test_api_error_message_exits_with_code_1(self, mock_create_client):
        """API error message is output with exit code 1."""
        mock_client = mock_create_client.return_value
        mock_client.send_get.return_value = APIClientResult(
            status_code=-1, response_text="", error_message="Timeout"
        )

        runner = CliRunner()
        result = runner.invoke(trcli_cli, self.BASE_ARGS)

        assert result.exit_code == 1
        assert "Timeout" in result.output

    @mock.patch("trcli.commands.cmd_get_cases._create_api_client")
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

    def test_missing_project_id_exits_nonzero(self):
        """Missing --project-id triggers a Click error."""
        args = [
            "-h", "https://test.testrail.com",
            "-u", "user@example.com",
            "-p", "password123",
            "get_cases",
            "--suite-id", "10",
        ]
        runner = CliRunner()
        result = runner.invoke(trcli_cli, args)

        assert result.exit_code != 0

    def test_missing_suite_id_exits_nonzero(self):
        """Missing --suite-id triggers a Click error."""
        args = [
            "-h", "https://test.testrail.com",
            "-u", "user@example.com",
            "-p", "password123",
            "get_cases",
            "--project-id", "1",
        ]
        runner = CliRunner()
        result = runner.invoke(trcli_cli, args)

        assert result.exit_code != 0

    def test_missing_host_exits_nonzero(self):
        """Missing -h triggers an error."""
        args = [
            "-u", "user@example.com",
            "-p", "password123",
            "get_cases",
            "--project-id", "1",
            "--suite-id", "10",
        ]
        runner = CliRunner()
        result = runner.invoke(trcli_cli, args)

        assert result.exit_code == 1
        assert "--host is required" in result.output
