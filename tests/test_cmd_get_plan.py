from unittest import mock

import pytest
from click.testing import CliRunner

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

    @mock.patch("trcli.commands.cmd_get_plan.ApiRequestHandler")
    @mock.patch("trcli.commands.cmd_get_plan.APIClient")
    def test_happy_path_returns_json(self, mock_api_client_cls, mock_handler_cls):
        """Successful API response prints JSON to stdout."""
        plan_data = {"id": 42, "name": "My Plan", "entries": []}
        mock_handler = mock_handler_cls.return_value
        mock_handler.get_plan.return_value = (plan_data, None)
        mock_api_client_cls.build_uploader_metadata.return_value = {}

        runner = CliRunner()
        result = runner.invoke(trcli_cli, self.BASE_ARGS, catch_exceptions=False)

        assert result.exit_code == 0
        assert '"My Plan"' in result.output
        assert '"id": 42' in result.output
        mock_handler.get_plan.assert_called_once()

    @mock.patch("trcli.commands.cmd_get_plan.ApiRequestHandler")
    @mock.patch("trcli.commands.cmd_get_plan.APIClient")
    def test_api_error_exits_with_code_1(self, mock_api_client_cls, mock_handler_cls):
        """API error is output with exit code 1."""
        mock_handler = mock_handler_cls.return_value
        mock_handler.get_plan.return_value = (None, "Plan not found")
        mock_api_client_cls.build_uploader_metadata.return_value = {}

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
        assert "server address" in result.output

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
        assert "password" in result.output or "key" in result.output
