import json
from unittest import mock

import pytest
from click.testing import CliRunner

from trcli.api.api_client import APIClientResult
from trcli.cli import cli as trcli_cli


class TestCmdGetPlan:
    """Tests for the get_plan CLI command."""

    BASE_ARGS = [
        "-h", "https://test.testrail.com",
        "-u", "user@example.com",
        "-p", "password123",
        "get_plan",
        "--plan-id", "42",
    ]

    @mock.patch("trcli.commands.cmd_get_plan.create_api_client")
    def test_happy_path_returns_json(self, mock_create_client):
        """Successful API response prints JSON to stdout."""
        plan_data = {"id": 42, "name": "My Plan", "entries": []}
        mock_client = mock_create_client.return_value
        mock_client.send_get.return_value = APIClientResult(
            status_code=200, response_text=plan_data, error_message=""
        )

        runner = CliRunner()
        result = runner.invoke(trcli_cli, self.BASE_ARGS, catch_exceptions=False)

        assert result.exit_code == 0
        assert json.loads(result.output) == plan_data
        mock_client.send_get.assert_called_once_with("get_plan/42")

    @mock.patch("trcli.commands.cmd_get_plan.create_api_client")
    def test_api_error_exits_with_code_1(self, mock_create_client):
        """API error is output with exit code 1."""
        mock_client = mock_create_client.return_value
        mock_client.send_get.return_value = APIClientResult(
            status_code=400, response_text={"error": "Plan not found"}, error_message="Plan not found"
        )

        runner = CliRunner()
        result = runner.invoke(trcli_cli, self.BASE_ARGS)

        assert result.exit_code == 1
        assert "Plan not found" in result.output

    def test_missing_plan_id_exits_nonzero(self):
        """Missing --plan-id triggers a Click error."""
        args = [
            "-h", "https://test.testrail.com",
            "-u", "user@example.com",
            "-p", "password123",
            "get_plan",
        ]
        runner = CliRunner()
        result = runner.invoke(trcli_cli, args)

        assert result.exit_code != 0

    def test_missing_host_exits_nonzero(self):
        """Missing -h triggers an error."""
        args = [
            "-u", "user@example.com",
            "-p", "password123",
            "get_plan",
            "--plan-id", "42",
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
            "get_plan",
            "--plan-id", "42",
        ]
        runner = CliRunner()
        result = runner.invoke(trcli_cli, args)

        assert result.exit_code == 1
        assert "--password or --key is required" in result.output
