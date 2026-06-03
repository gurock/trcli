import json
from unittest import mock

import pytest
from click.testing import CliRunner

from trcli.api.api_client import APIClientResult
from trcli.cli import cli as trcli_cli


class TestCmdGetPlans:
    """Tests for the get_plans CLI command."""

    BASE_ARGS = [
        "-h", "https://test.testrail.com",
        "-u", "user@example.com",
        "-p", "password123",
        "get_plans",
        "--project-id", "1",
    ]

    @mock.patch("trcli.commands.cmd_get_plans.create_api_client")
    def test_happy_path_returns_json(self, mock_create_client):
        """Successful API response prints JSON to stdout."""
        plans_data = [{"id": 1, "name": "Plan A"}, {"id": 2, "name": "Plan B"}]
        mock_client = mock_create_client.return_value
        mock_client.send_get.return_value = APIClientResult(
            status_code=200, response_text=plans_data, error_message=""
        )

        runner = CliRunner()
        result = runner.invoke(trcli_cli, self.BASE_ARGS, catch_exceptions=False)

        assert result.exit_code == 0
        assert json.loads(result.output) == plans_data
        mock_client.send_get.assert_called_once_with("get_plans/1")

    @mock.patch("trcli.commands.cmd_get_plans.create_api_client")
    def test_api_error_exits_with_code_1(self, mock_create_client):
        """API error message is output with exit code 1."""
        mock_client = mock_create_client.return_value
        mock_client.send_get.return_value = APIClientResult(
            status_code=-1, response_text="", error_message="Could not connect to TestRail"
        )

        runner = CliRunner()
        result = runner.invoke(trcli_cli, self.BASE_ARGS)

        assert result.exit_code == 1
        assert "Could not connect to TestRail" in result.output

    def test_missing_project_id_exits_nonzero(self):
        """Missing --project-id triggers an error."""
        args = [
            "-h", "https://test.testrail.com",
            "-u", "user@example.com",
            "-p", "password123",
            "get_plans",
        ]
        runner = CliRunner()
        result = runner.invoke(trcli_cli, args)

        assert result.exit_code == 2
        assert "project ID" in result.output or "project-id" in result.output.lower()

    def test_missing_host_exits_nonzero(self):
        """Missing -h triggers an error."""
        args = [
            "-u", "user@example.com",
            "-p", "password123",
            "get_plans",
            "--project-id", "1",
        ]
        runner = CliRunner()
        result = runner.invoke(trcli_cli, args)

        assert result.exit_code == 1
        assert "--host is required" in result.output

    def test_missing_username_exits_nonzero(self):
        """Missing -u triggers an error."""
        args = [
            "-h", "https://test.testrail.com",
            "-p", "password123",
            "get_plans",
            "--project-id", "1",
        ]
        runner = CliRunner()
        result = runner.invoke(trcli_cli, args)

        assert result.exit_code == 1
        assert "username" in result.output

    def test_missing_password_and_key_exits_nonzero(self):
        """Missing both -p and -k triggers an error."""
        args = [
            "-h", "https://test.testrail.com",
            "-u", "user@example.com",
            "get_plans",
            "--project-id", "1",
        ]
        runner = CliRunner()
        result = runner.invoke(trcli_cli, args)

        assert result.exit_code == 1
        assert "--password or --key is required" in result.output
