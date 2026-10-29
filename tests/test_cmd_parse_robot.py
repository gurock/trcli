"""
Unit tests for cmd_parse_robot.py CLI wiring, in particular the
--update-existing-cases / --update-strategy options (added to close the gap
where RobotParser populated TestRailCase._junit_case_refs from RF tags, but
the CLI command never exposed the flag needed to actually trigger
ResultsUploader.update_existing_cases_with_junit_refs()).
"""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

from trcli.cli import Environment
from trcli.commands import cmd_parse_robot


class TestCmdParseRobotUpdateExistingCases:
    """Test coverage for the --update-existing-cases/--update-strategy wiring in cmd_parse_robot.py"""

    def setup_method(self):
        self.runner = CliRunner()
        self.test_robot_path = str(Path(__file__).parent / "test_data" / "XML" / "robotframework_simple_RF70.xml")

        self.environment = Environment(cmd="parse_robot")
        self.environment.host = "https://test.testrail.com"
        self.environment.username = "test@example.com"
        self.environment.password = "password"
        self.environment.project = "Test Project"
        self.environment.project_id = 1
        self.environment.auto_creation_response = True

    def _mock_parser_and_uploader(self, mock_parser_class, mock_uploader_class, case_update_results=None):
        mock_parser = MagicMock()
        mock_parser_class.return_value = mock_parser
        mock_suite = MagicMock()
        mock_suite.name = "Test Suite"
        mock_parser.parse_file.return_value = [mock_suite]
        mock_parser.invalid_quality_ratings_found = False

        mock_uploader = MagicMock()
        mock_uploader_class.return_value = mock_uploader
        mock_uploader.last_run_id = 123
        mock_uploader.case_update_results = case_update_results

        return mock_parser, mock_uploader

    def test_update_existing_cases_options_are_registered(self):
        """The --update-existing-cases/--update-strategy options must actually be
        wired into the command (this is the core of the PR review comment: they
        were previously only defined in results_parser_helpers.py but never
        attached to cmd_parse_robot.cli, making them unreachable)."""
        param_names = {p.name for p in cmd_parse_robot.cli.params}
        assert "update_existing_cases" in param_names
        assert "update_strategy" in param_names

    @pytest.mark.cmd_parse_robot
    @patch("trcli.api.api_request_handler.ApiRequestHandler")
    @patch("trcli.api.api_client.APIClient")
    @patch("trcli.commands.cmd_parse_robot.ResultsUploader")
    @patch("trcli.commands.cmd_parse_robot.RobotParser")
    def test_parse_robot_default_does_not_report_case_updates(
        self, mock_parser_class, mock_uploader_class, mock_api_client_class, mock_api_handler_class
    ):
        """Without --update-existing-cases, no case-update reporting should occur,
        even if the uploader happens to expose case_update_results."""
        self._mock_parser_and_uploader(
            mock_parser_class,
            mock_uploader_class,
            case_update_results={"updated_cases": [{"case_id": 1}], "skipped_cases": [], "failed_cases": []},
        )

        with patch("trcli.commands.cmd_parse_robot.handle_case_update_reporting") as mock_handle:
            result = self.runner.invoke(
                cmd_parse_robot.cli,
                ["--file", self.test_robot_path, "--suite-id", "2", "--title", "Test Run"],
                obj=self.environment,
            )

        assert result.exit_code == 0
        mock_handle.assert_not_called()

    @pytest.mark.cmd_parse_robot
    @patch("trcli.api.api_request_handler.ApiRequestHandler")
    @patch("trcli.api.api_client.APIClient")
    @patch("trcli.commands.cmd_parse_robot.ResultsUploader")
    @patch("trcli.commands.cmd_parse_robot.RobotParser")
    def test_parse_robot_update_existing_cases_yes_reports_updates(
        self, mock_parser_class, mock_uploader_class, mock_api_client_class, mock_api_handler_class
    ):
        """With --update-existing-cases yes and a successful case_update_results
        (no failed_cases), the shared handle_case_update_reporting() must be
        invoked with the uploader's results, and the command should exit 0."""
        case_update_results = {
            "updated_cases": [{"case_id": 123, "added_refs": ["JIRA-1"], "skipped_refs": []}],
            "skipped_cases": [],
            "failed_cases": [],
        }
        self._mock_parser_and_uploader(mock_parser_class, mock_uploader_class, case_update_results=case_update_results)

        with patch("trcli.commands.cmd_parse_robot.handle_case_update_reporting") as mock_handle:
            result = self.runner.invoke(
                cmd_parse_robot.cli,
                [
                    "--file",
                    self.test_robot_path,
                    "--suite-id",
                    "2",
                    "--title",
                    "Test Run",
                    "--update-existing-cases",
                    "yes",
                ],
                obj=self.environment,
            )

        assert result.exit_code == 0
        mock_handle.assert_called_once_with(self.environment, case_update_results)

    @pytest.mark.cmd_parse_robot
    @patch("trcli.api.api_request_handler.ApiRequestHandler")
    @patch("trcli.api.api_client.APIClient")
    @patch("trcli.commands.cmd_parse_robot.ResultsUploader")
    @patch("trcli.commands.cmd_parse_robot.RobotParser")
    def test_parse_robot_update_existing_cases_failed_cases_exits_nonzero(
        self, mock_parser_class, mock_uploader_class, mock_api_client_class, mock_api_handler_class
    ):
        """If case_update_results contains failed_cases, the command must exit
        with a non-zero code after reporting (mirroring cmd_parse_junit.py)."""
        case_update_results = {
            "updated_cases": [],
            "skipped_cases": [],
            "failed_cases": [{"case_id": 456, "error": "API error"}],
        }
        self._mock_parser_and_uploader(mock_parser_class, mock_uploader_class, case_update_results=case_update_results)

        result = self.runner.invoke(
            cmd_parse_robot.cli,
            [
                "--file",
                self.test_robot_path,
                "--suite-id",
                "2",
                "--title",
                "Test Run",
                "--update-existing-cases",
                "yes",
            ],
            obj=self.environment,
        )

        assert result.exit_code != 0

    @pytest.mark.cmd_parse_robot
    @patch("trcli.api.api_request_handler.ApiRequestHandler")
    @patch("trcli.api.api_client.APIClient")
    @patch("trcli.commands.cmd_parse_robot.ResultsUploader")
    @patch("trcli.commands.cmd_parse_robot.RobotParser")
    def test_parse_robot_update_strategy_option_accepted(
        self, mock_parser_class, mock_uploader_class, mock_api_client_class, mock_api_handler_class
    ):
        """--update-strategy must be a recognized option accepted alongside
        --update-existing-cases (values: append/replace)."""
        self._mock_parser_and_uploader(mock_parser_class, mock_uploader_class, case_update_results=None)

        result = self.runner.invoke(
            cmd_parse_robot.cli,
            [
                "--file",
                self.test_robot_path,
                "--suite-id",
                "2",
                "--title",
                "Test Run",
                "--update-existing-cases",
                "yes",
                "--update-strategy",
                "replace",
            ],
            obj=self.environment,
        )

        assert result.exit_code == 0
        assert self.environment.update_strategy == "replace"
