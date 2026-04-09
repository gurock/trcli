import pytest
import json
from unittest.mock import MagicMock

from click.testing import CliRunner

from trcli.cli import cli


@pytest.fixture
def runner():
    return CliRunner()


class TestStatusCommand:
    @pytest.mark.cli
    def test_status_suppresses_global_update_banner(self, runner, mocker):
        mocker.patch(
            "trcli.cli.check_for_updates",
            return_value="\n A new version of TestRail CLI is available!\n   Current: 1.13.3 | Latest: 1.14.0\n",
        )
        mocker.patch("trcli.commands.cmd_status._query_pypi", return_value="1.14.0")

        result = runner.invoke(cli, ["status"])

        assert result.exit_code == 0
        assert result.output.count("A new version of TestRail CLI is available!") == 0
        assert "Version:" in result.output

    @pytest.mark.cli
    def test_status_reports_partial_without_configuration(self, runner, mocker):
        mocker.patch("trcli.cli.check_for_updates", return_value=None)
        mocker.patch("trcli.commands.cmd_status._query_pypi", return_value="1.14.0")

        with runner.isolated_filesystem():
            result = runner.invoke(cli, ["status"])

        assert result.exit_code == 0
        assert "TRCLI Status: Partial" in result.output
        assert "Host: not configured" in result.output
        assert "Auth: not configured" in result.output
        assert "Project: not configured" in result.output

    @pytest.mark.cli
    def test_status_reports_error_for_invalid_host(self, runner, mocker):
        mocker.patch("trcli.cli.check_for_updates", return_value=None)
        mocker.patch("trcli.commands.cmd_status._query_pypi", return_value="1.14.0")

        result = runner.invoke(
            cli,
            ["--host", "fake_host.com/", "--username", "user@example.com", "--key", "secret", "status"],
        )

        assert result.exit_code == 1
        assert "TRCLI Status: Error" in result.output
        assert "Host is invalid." in result.output

    @pytest.mark.cli
    def test_status_reports_ready_with_valid_project(self, runner, mocker):
        mocker.patch("trcli.cli.check_for_updates", return_value=None)
        mocker.patch("trcli.commands.cmd_status._query_pypi", return_value="1.14.0")
        mock_api_client = MagicMock()
        mock_api_client.send_get.return_value = MagicMock(status_code=200, error_message="", response_text=[])
        mocker.patch("trcli.commands.cmd_status._build_api_client", return_value=mock_api_client)
        mock_api_handler = MagicMock()
        mock_api_handler.get_project_data.return_value = MagicMock(project_id=12)
        mock_api_handler.check_suite_id.return_value = (True, "")
        mocker.patch("trcli.commands.cmd_status.ApiRequestHandler", return_value=mock_api_handler)

        result = runner.invoke(
            cli,
            [
                "--host",
                "https://example.testrail.io",
                "--project",
                "My Project",
                "--username",
                "user@example.com",
                "--key",
                "secret",
                "status",
            ],
        )

        assert result.exit_code == 0
        assert "TRCLI Status: Ready" in result.output
        assert "Reachable: yes" in result.output
        assert "Authentication: valid" in result.output
        assert "Project Check: valid" in result.output
        assert "Project ID: 12" in result.output

    @pytest.mark.cli
    def test_status_verbose_shows_parameter_sources(self, runner, mocker):
        mocker.patch("trcli.cli.check_for_updates", return_value=None)
        mocker.patch("trcli.commands.cmd_status._query_pypi", return_value="1.14.0")
        mock_api_client = MagicMock()
        mock_api_client.send_get.return_value = MagicMock(status_code=200, error_message="", response_text=[])
        mocker.patch("trcli.commands.cmd_status._build_api_client", return_value=mock_api_client)
        mock_api_handler = MagicMock()
        mock_api_handler.get_project_data.return_value = MagicMock(project_id=12)
        mock_api_handler.check_suite_id.return_value = (True, "")
        mocker.patch("trcli.commands.cmd_status.ApiRequestHandler", return_value=mock_api_handler)

        result = runner.invoke(
            cli,
            ["--verbose", "status"],
            env={
                "TR_CLI_HOST": "https://example.testrail.io",
                "TR_CLI_PROJECT": "My Project",
                "TR_CLI_USERNAME": "user@example.com",
                "TR_CLI_KEY": "secret",
            },
        )

        assert result.exit_code == 0
        assert "Verbose:" in result.output
        assert "Resolved parameter sources:" in result.output
        assert "host: environment variable" in result.output
        assert "project: environment variable" in result.output

    @pytest.mark.cli
    def test_status_json_output(self, runner, mocker):
        mocker.patch("trcli.cli.check_for_updates", return_value=None)
        mocker.patch("trcli.commands.cmd_status._query_pypi", return_value="1.14.0")
        mock_api_client = MagicMock()
        mock_api_client.send_get.return_value = MagicMock(status_code=200, error_message="", response_text=[])
        mocker.patch("trcli.commands.cmd_status._build_api_client", return_value=mock_api_client)
        mock_api_handler = MagicMock()
        mock_api_handler.get_project_data.return_value = MagicMock(project_id=12)
        mock_api_handler.check_suite_id.return_value = (True, "")
        mocker.patch("trcli.commands.cmd_status.ApiRequestHandler", return_value=mock_api_handler)

        result = runner.invoke(
            cli,
            [
                "--host",
                "https://example.testrail.io",
                "--project",
                "My Project",
                "--username",
                "user@example.com",
                "--key",
                "secret",
                "status",
                "--json",
            ],
        )

        assert result.exit_code == 0
        payload = json.loads(result.output)
        assert payload["ok"] is True
        assert payload["command"] == "status"
        assert payload["data"]["verdict"] == "Ready"
        assert payload["data"]["connection"]["reachable"] == "yes"
        assert payload["data"]["context"]["project_check"] == "valid"

    @pytest.mark.cli
    def test_status_json_output_error(self, runner, mocker):
        mocker.patch("trcli.cli.check_for_updates", return_value=None)
        mocker.patch("trcli.commands.cmd_status._query_pypi", return_value="1.14.0")

        result = runner.invoke(
            cli,
            ["--host", "fake_host.com/", "--username", "user@example.com", "--key", "secret", "status", "--json"],
        )

        assert result.exit_code == 1
        payload = json.loads(result.output)
        assert payload["ok"] is False
        assert payload["data"]["verdict"] == "Error"
        assert "Host is invalid." in payload["errors"]
