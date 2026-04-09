from unittest.mock import MagicMock, patch
import json

import pytest
from click.testing import CliRunner

from trcli.cli import Environment
from trcli.commands import cmd_parse_junit, cmd_parse_robot, cmd_parse_openapi


def _make_environment(command_name: str) -> Environment:
    environment = Environment(cmd=command_name)
    environment.host = "https://test.testrail.com"
    environment.username = "test@example.com"
    environment.password = "password"
    environment.project = "Test Project"
    environment.project_id = 1
    environment.title = "Dry Run Preview"
    environment.dry_run = True
    return environment


class TestDryRunParserCommands:
    @pytest.mark.cli
    @patch("trcli.commands.cmd_parse_junit.ResultsUploader")
    @patch("trcli.commands.cmd_parse_junit.JunitParser")
    def test_parse_junit_dry_run_skips_uploader(self, mock_parser_class, mock_uploader_class):
        runner = CliRunner()
        environment = _make_environment("parse_junit")

        mock_parser = MagicMock()
        mock_parser_class.return_value = mock_parser
        mock_suite = MagicMock()
        mock_suite.testsections = []
        mock_parser.parse_file.return_value = [mock_suite]

        result = runner.invoke(cmd_parse_junit.cli, ["--file", "results.xml", "--title", "Dry Run Preview"], obj=environment)

        assert result.exit_code == 0
        mock_parser.parse_file.assert_called_once()
        mock_uploader_class.assert_not_called()
        assert "dry run: would upload junit results to testrail." in result.output.lower()

    @pytest.mark.cli
    @patch("trcli.commands.cmd_parse_junit.ResultsUploader")
    @patch("trcli.commands.cmd_parse_junit.JunitParser")
    def test_parse_junit_dry_run_json_output(self, mock_parser_class, mock_uploader_class):
        runner = CliRunner()
        environment = _make_environment("parse_junit")
        environment.json_output = True

        mock_parser = MagicMock()
        mock_parser_class.return_value = mock_parser
        mock_suite = MagicMock()
        mock_suite.testsections = []
        mock_parser.parse_file.return_value = [mock_suite]

        result = runner.invoke(
            cmd_parse_junit.cli,
            ["--file", "results.xml", "--title", "Dry Run Preview", "--json"],
            obj=environment,
        )

        assert result.exit_code == 0
        payload = json.loads(result.output[result.output.find("{"):])
        assert payload["ok"] is True
        assert payload["dry_run"] is True
        assert payload["data"]["parsed"]["suites"] == 1
        mock_uploader_class.assert_not_called()

    @pytest.mark.cli
    @patch("trcli.commands.cmd_parse_junit.ResultsUploader")
    @patch("trcli.commands.cmd_parse_junit.JunitParser")
    def test_parse_junit_json_output(self, mock_parser_class, mock_uploader_class):
        runner = CliRunner()
        environment = _make_environment("parse_junit")
        environment.dry_run = False

        mock_parser = MagicMock()
        mock_parser_class.return_value = mock_parser
        mock_case = MagicMock()
        mock_case.result = MagicMock()
        mock_section = MagicMock()
        mock_section.testcases = [mock_case]
        mock_suite = MagicMock()
        mock_suite.testsections = [mock_section]
        mock_parser.parse_file.return_value = [mock_suite]

        mock_uploader = MagicMock()
        mock_uploader.last_run_id = 555
        mock_uploader.case_update_results = {"updated_cases": [], "skipped_cases": [], "failed_cases": []}
        mock_uploader_class.return_value = mock_uploader

        result = runner.invoke(
            cmd_parse_junit.cli,
            ["--file", "results.xml", "--title", "Dry Run Preview", "--json"],
            obj=environment,
        )

        assert result.exit_code == 0
        payload = json.loads(result.output[result.output.find("{"):])
        assert payload["command"] == "parse_junit"
        assert payload["data"]["run_id"] == 555
        assert payload["data"]["parsed"]["results"] == 1
        mock_uploader.upload_results.assert_called_once()

    @pytest.mark.cli
    @patch("trcli.commands.cmd_parse_robot.ResultsUploader")
    @patch("trcli.commands.cmd_parse_robot.RobotParser")
    def test_parse_robot_dry_run_skips_uploader(self, mock_parser_class, mock_uploader_class):
        runner = CliRunner()
        environment = _make_environment("parse_robot")

        mock_parser = MagicMock()
        mock_parser_class.return_value = mock_parser
        mock_suite = MagicMock()
        mock_suite.testsections = []
        mock_parser.parse_file.return_value = [mock_suite]

        result = runner.invoke(cmd_parse_robot.cli, ["--file", "results.xml", "--title", "Dry Run Preview"], obj=environment)

        assert result.exit_code == 0
        mock_parser.parse_file.assert_called_once()
        mock_uploader_class.assert_not_called()
        assert "dry run: would upload robot framework results to testrail." in result.output.lower()

    @pytest.mark.cli
    @patch("trcli.commands.cmd_parse_robot.ResultsUploader")
    @patch("trcli.commands.cmd_parse_robot.RobotParser")
    def test_parse_robot_dry_run_json_output(self, mock_parser_class, mock_uploader_class):
        runner = CliRunner()
        environment = _make_environment("parse_robot")
        environment.json_output = True

        mock_parser = MagicMock()
        mock_parser_class.return_value = mock_parser
        mock_suite = MagicMock()
        mock_suite.testsections = []
        mock_parser.parse_file.return_value = [mock_suite]

        result = runner.invoke(
            cmd_parse_robot.cli,
            ["--file", "results.xml", "--title", "Dry Run Preview", "--json"],
            obj=environment,
        )

        assert result.exit_code == 0
        payload = json.loads(result.output[result.output.find("{"):])
        assert payload["command"] == "parse_robot"
        assert payload["dry_run"] is True
        mock_uploader_class.assert_not_called()

    @pytest.mark.cli
    @patch("trcli.commands.cmd_parse_openapi.ResultsUploader")
    @patch("trcli.commands.cmd_parse_openapi.OpenApiParser")
    def test_parse_openapi_dry_run_skips_uploader(self, mock_parser_class, mock_uploader_class):
        runner = CliRunner()
        environment = _make_environment("parse_openapi")

        mock_parser = MagicMock()
        mock_parser_class.return_value = mock_parser
        mock_suite = MagicMock()
        mock_suite.testsections = []
        mock_parser.parse_file.return_value = [mock_suite]

        result = runner.invoke(cmd_parse_openapi.cli, ["--file", "openapi.yml"], obj=environment)

        assert result.exit_code == 0
        mock_parser.parse_file.assert_called_once()
        mock_uploader_class.assert_not_called()
        assert "dry run: would create openapi-derived test cases in testrail." in result.output.lower()

    @pytest.mark.cli
    @patch("trcli.commands.cmd_parse_openapi.ResultsUploader")
    @patch("trcli.commands.cmd_parse_openapi.OpenApiParser")
    def test_parse_openapi_dry_run_json_output(self, mock_parser_class, mock_uploader_class):
        runner = CliRunner()
        environment = _make_environment("parse_openapi")
        environment.json_output = True

        mock_parser = MagicMock()
        mock_parser_class.return_value = mock_parser
        mock_suite = MagicMock()
        mock_suite.testsections = []
        mock_parser.parse_file.return_value = [mock_suite]

        result = runner.invoke(cmd_parse_openapi.cli, ["--file", "openapi.yml", "--json"], obj=environment)

        assert result.exit_code == 0
        payload = json.loads(result.output[result.output.find("{"):])
        assert payload["command"] == "parse_openapi"
        assert payload["dry_run"] is True
        mock_uploader_class.assert_not_called()
