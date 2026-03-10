from unittest import mock

import pytest
from click.testing import CliRunner

from trcli.cli import cli as trcli_cli


class TestCmdGetPlans:
    """Tests for the get_plans CLI command."""

    BASE_ARGS = [
        "-h", "https://test.testrail.com",
        "-u", "user@example.com",
        "-p", "password123",
        "--project-id", "1",
        "get_plans",
    ]

    @mock.patch("trcli.commands.cmd_get_plans.ApiRequestHandler")
    @mock.patch("trcli.commands.cmd_get_plans.APIClient")
    def test_happy_path_returns_json(self, mock_api_client_cls, mock_handler_cls):
        """Successful API response prints JSON to stdout."""
        plans_data = [{"id": 1, "name": "Plan A"}, {"id": 2, "name": "Plan B"}]
        mock_handler = mock_handler_cls.return_value
        mock_handler.get_plans.return_value = (plans_data, None)
        mock_api_client_cls.build_uploader_metadata.return_value = {}

        runner = CliRunner()
        result = runner.invoke(trcli_cli, self.BASE_ARGS, catch_exceptions=False)

        assert result.exit_code == 0
        assert '"Plan A"' in result.output
        assert '"Plan B"' in result.output
        mock_handler.get_plans.assert_called_once()

    @mock.patch("trcli.commands.cmd_get_plans.ApiRequestHandler")
    @mock.patch("trcli.commands.cmd_get_plans.APIClient")
    def test_api_error_exits_with_code_1(self, mock_api_client_cls, mock_handler_cls):
        """API error message is output with exit code 1."""
        mock_handler = mock_handler_cls.return_value
        mock_handler.get_plans.return_value = (None, "Could not connect to TestRail")
        mock_api_client_cls.build_uploader_metadata.return_value = {}

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

        assert result.exit_code == 1
        assert "project ID" in result.output or "project-id" in result.output.lower()

    def test_missing_host_exits_nonzero(self):
        """Missing -h triggers an error."""
        args = [
            "-u", "user@example.com",
            "-p", "password123",
            "--project-id", "1",
            "get_plans",
        ]
        runner = CliRunner()
        result = runner.invoke(trcli_cli, args)

        assert result.exit_code == 1
        assert "server address" in result.output

    def test_missing_username_exits_nonzero(self):
        """Missing -u triggers an error."""
        args = [
            "-h", "https://test.testrail.com",
            "-p", "password123",
            "--project-id", "1",
            "get_plans",
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
            "--project-id", "1",
            "get_plans",
        ]
        runner = CliRunner()
        result = runner.invoke(trcli_cli, args)

        assert result.exit_code == 1
        assert "password" in result.output or "key" in result.output
