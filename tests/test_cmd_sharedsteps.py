import json
import pytest
from click.testing import CliRunner
from unittest import mock
from unittest.mock import MagicMock, patch, mock_open

from trcli.commands import cmd_sharedsteps
from trcli.cli import Environment


class TestCmdSharedsteps:
    """Test suite for sharedsteps command."""

    def setup_method(self):
        """Set up test environment"""
        self.runner = CliRunner()
        self.environment = Environment(cmd="sharedsteps")
        self.environment.host = "https://test.testrail.com"
        self.environment.username = "test@example.com"
        self.environment.password = "password"
        self.environment.api_key = None
        self.environment.project = None
        self.environment.project_id = 1

    def _setup_project_client_mock(self, mock_project_client):
        """Helper to setup ProjectBasedClient mock"""
        mock_client_instance = MagicMock()
        mock_project_client.return_value = mock_client_instance

        # Mock project resolution
        mock_project = MagicMock()
        mock_project.project_id = 1
        mock_client_instance.project = mock_project
        mock_client_instance.resolve_project = MagicMock()

        return mock_client_instance

    @mock.patch("trcli.commands.cmd_sharedsteps.ProjectBasedClient")
    def test_list_sharedsteps_success(self, mock_project_client):
        """Test successful listing of sharedsteps."""
        mock_client = self._setup_project_client_mock(mock_project_client)
        mock_client.api_request_handler.sharedstep_handler.get_shared_steps.return_value = (
            [
                {"id": 1, "title": "Login Steps", "project_id": 1},
                {"id": 2, "title": "Logout Steps", "project_id": 1},
            ],
            "",
        )

        with patch.object(self.environment, "log") as mock_log, patch.object(
            self.environment, "set_parameters"
        ), patch.object(self.environment, "check_for_required_parameters"):
            result = self.runner.invoke(cmd_sharedsteps.list, [], obj=self.environment)

            assert result.exit_code == 0
            assert mock_log.called

    @mock.patch("trcli.commands.cmd_sharedsteps.ProjectBasedClient")
    def test_list_sharedsteps_json_output(self, mock_project_client):
        """Test listing sharedsteps with JSON output."""
        mock_client = self._setup_project_client_mock(mock_project_client)
        sharedsteps = [
            {"id": 1, "title": "Login Steps", "project_id": 1},
            {"id": 2, "title": "Logout Steps", "project_id": 1},
        ]
        mock_client.api_request_handler.sharedstep_handler.get_shared_steps.return_value = (sharedsteps, "")

        with patch.object(self.environment, "log"), patch.object(self.environment, "set_parameters"), patch.object(
            self.environment, "check_for_required_parameters"
        ):
            result = self.runner.invoke(cmd_sharedsteps.list, ["--json-output"], obj=self.environment)

            assert result.exit_code == 0
            output_json = json.loads(result.output)
            assert len(output_json) == 2

    @mock.patch("trcli.commands.cmd_sharedsteps.ProjectBasedClient")
    def test_list_sharedsteps_with_filters(self, mock_project_client):
        """Test listing sharedsteps with filter parameters."""
        mock_client = self._setup_project_client_mock(mock_project_client)
        mock_client.api_request_handler.sharedstep_handler.get_shared_steps.return_value = ([], "")

        with patch.object(self.environment, "log"), patch.object(self.environment, "set_parameters"), patch.object(
            self.environment, "check_for_required_parameters"
        ):
            result = self.runner.invoke(
                cmd_sharedsteps.list,
                ["--created-by", "1,2", "--refs", "TR-123", "--limit", "50", "--offset", "10"],
                obj=self.environment,
            )

            assert result.exit_code == 0
            # Verify filters were passed
            call_kwargs = mock_client.api_request_handler.sharedstep_handler.get_shared_steps.call_args[1]
            assert call_kwargs["created_by"] == "1,2"
            assert call_kwargs["refs"] == "TR-123"

    @mock.patch("trcli.commands.cmd_sharedsteps.ProjectBasedClient")
    def test_list_sharedsteps_api_error(self, mock_project_client):
        """Test handling of API errors when listing."""
        mock_client = self._setup_project_client_mock(mock_project_client)
        mock_client.api_request_handler.sharedstep_handler.get_shared_steps.return_value = (
            [],
            "Invalid or unknown project",
        )

        with patch.object(self.environment, "elog") as mock_elog, patch.object(
            self.environment, "set_parameters"
        ), patch.object(self.environment, "check_for_required_parameters"):
            result = self.runner.invoke(cmd_sharedsteps.list, [], obj=self.environment)

            assert result.exit_code == 1
            mock_elog.assert_called()

    @mock.patch("trcli.commands.cmd_sharedsteps.ProjectBasedClient")
    def test_list_sharedsteps_no_project_id(self, mock_project_client):
        """Test error when no project ID is available."""
        mock_client = self._setup_project_client_mock(mock_project_client)
        mock_client.project = None
        self.environment.project_id = None
        self.environment.project = None

        with patch.object(self.environment, "elog") as mock_elog, patch.object(
            self.environment, "set_parameters"
        ), patch.object(self.environment, "check_for_required_parameters"):
            result = self.runner.invoke(cmd_sharedsteps.list, [], obj=self.environment)

            assert result.exit_code == 1
            assert mock_elog.called

    @mock.patch("trcli.commands.cmd_sharedsteps.ProjectBasedClient")
    def test_list_sharedsteps_resolves_project_name(self, mock_project_client):
        """Test that list resolves project name to project_id."""
        mock_client = self._setup_project_client_mock(mock_project_client)
        mock_client.api_request_handler.sharedstep_handler.get_shared_steps.return_value = ([], "")
        self.environment.project = "TestProject"
        self.environment.project_id = None

        with patch.object(self.environment, "log"), patch.object(self.environment, "set_parameters"), patch.object(
            self.environment, "check_for_required_parameters"
        ):
            result = self.runner.invoke(cmd_sharedsteps.list, [], obj=self.environment)

            assert result.exit_code == 0
            mock_client.resolve_project.assert_called_once()

    @mock.patch("trcli.commands.cmd_sharedsteps.ProjectBasedClient")
    def test_show_sharedstep_success(self, mock_project_client):
        """Test successful retrieval of shared step details."""
        mock_client = self._setup_project_client_mock(mock_project_client)
        mock_client.api_request_handler.sharedstep_handler.get_shared_step.return_value = (
            {
                "id": 1,
                "title": "Default Login",
                "project_id": 2,
                "created_by": 1,
                "created_on": 1612555977,
                "updated_by": 1,
                "updated_on": 1612555977,
                "custom_steps_separated": [
                    {
                        "content": "Navigate to https://localhost/some_app",
                        "expected": "Login screen loads",
                        "additional_info": None,
                        "refs": "TR-123",
                    }
                ],
                "case_ids": [25],
            },
            "",
        )

        with patch.object(self.environment, "log") as mock_log, patch.object(
            self.environment, "set_parameters"
        ), patch.object(self.environment, "check_for_required_parameters"):
            result = self.runner.invoke(cmd_sharedsteps.show, ["--sharedstep-id", "1"], obj=self.environment)

            assert result.exit_code == 0
            assert mock_log.called

    @mock.patch("trcli.commands.cmd_sharedsteps.ProjectBasedClient")
    def test_show_sharedstep_json_output(self, mock_project_client):
        """Test showing shared step with JSON output."""
        mock_client = self._setup_project_client_mock(mock_project_client)
        sharedstep = {
            "id": 1,
            "title": "Test Step",
            "custom_steps_separated": [],
        }
        mock_client.api_request_handler.sharedstep_handler.get_shared_step.return_value = (sharedstep, "")

        with patch.object(self.environment, "log"), patch.object(self.environment, "set_parameters"), patch.object(
            self.environment, "check_for_required_parameters"
        ):
            result = self.runner.invoke(
                cmd_sharedsteps.show, ["--sharedstep-id", "1", "--json-output"], obj=self.environment
            )

            assert result.exit_code == 0
            output_json = json.loads(result.output)
            assert output_json["id"] == 1

    @mock.patch("trcli.commands.cmd_sharedsteps.ProjectBasedClient")
    def test_show_sharedstep_api_error(self, mock_project_client):
        """Test handling of API errors when showing."""
        mock_client = self._setup_project_client_mock(mock_project_client)
        mock_client.api_request_handler.sharedstep_handler.get_shared_step.return_value = (
            None,
            "Invalid or unknown shared step",
        )

        with patch.object(self.environment, "elog") as mock_elog, patch.object(
            self.environment, "set_parameters"
        ), patch.object(self.environment, "check_for_required_parameters"):
            result = self.runner.invoke(cmd_sharedsteps.show, ["--sharedstep-id", "999"], obj=self.environment)

            assert result.exit_code == 1
            assert mock_elog.called

    @mock.patch(
        "builtins.open", new_callable=mock_open, read_data='{"custom_steps_separated": [{"content": "Step 1"}]}'
    )
    @mock.patch("pathlib.Path.exists", return_value=True)
    @mock.patch("pathlib.Path.is_file", return_value=True)
    @mock.patch("trcli.commands.cmd_sharedsteps.ProjectBasedClient")
    def test_create_sharedstep_success(self, mock_project_client, mock_is_file, mock_exists, mock_file):
        """Test successful creation of a shared step."""
        mock_client = self._setup_project_client_mock(mock_project_client)
        mock_client.api_request_handler.sharedstep_handler.add_shared_step.return_value = (
            {
                "id": 1,
                "title": "New Step",
                "project_id": 1,
                "custom_steps_separated": [{"content": "Step 1"}],
                "case_ids": [],
            },
            "",
        )

        with patch.object(self.environment, "log") as mock_log, patch.object(
            self.environment, "set_parameters"
        ), patch.object(self.environment, "check_for_required_parameters"):
            result = self.runner.invoke(
                cmd_sharedsteps.create, ["--name", "New Step", "--steps-file", "steps.json"], obj=self.environment
            )

            assert result.exit_code == 0
            assert mock_log.called

    @mock.patch("trcli.commands.cmd_sharedsteps.ProjectBasedClient")
    def test_create_sharedstep_file_not_found(self, mock_project_client):
        """Test error when steps file doesn't exist."""
        mock_client = self._setup_project_client_mock(mock_project_client)

        with patch.object(self.environment, "elog") as mock_elog, patch.object(
            self.environment, "set_parameters"
        ), patch.object(self.environment, "check_for_required_parameters"):
            result = self.runner.invoke(
                cmd_sharedsteps.create,
                ["--name", "New Step", "--steps-file", "nonexistent.json"],
                obj=self.environment,
            )

            assert result.exit_code == 1

    @mock.patch(
        "builtins.open", new_callable=mock_open, read_data='{"custom_steps_separated": [{"content": "Step 1"}]}'
    )
    @mock.patch("pathlib.Path.exists", return_value=True)
    @mock.patch("pathlib.Path.is_file", return_value=True)
    @mock.patch("trcli.commands.cmd_sharedsteps.ProjectBasedClient")
    def test_update_sharedstep_with_file(self, mock_project_client, mock_is_file, mock_exists, mock_file):
        """Test updating shared step with new steps file."""
        mock_client = self._setup_project_client_mock(mock_project_client)
        mock_client.api_request_handler.sharedstep_handler.update_shared_step.return_value = (
            {
                "id": 1,
                "title": "Same Title",
                "custom_steps_separated": [{"content": "Updated"}],
            },
            "",
        )

        with patch.object(self.environment, "log") as mock_log, patch.object(
            self.environment, "set_parameters"
        ), patch.object(self.environment, "check_for_required_parameters"):
            result = self.runner.invoke(
                cmd_sharedsteps.update,
                ["--sharedstep-id", "1", "--steps-file", "updated.json"],
                obj=self.environment,
            )

            assert result.exit_code == 0
            assert mock_log.called

    @mock.patch("trcli.commands.cmd_sharedsteps.ProjectBasedClient")
    def test_update_sharedstep_title_only(self, mock_project_client):
        """Test updating only the title."""
        mock_client = self._setup_project_client_mock(mock_project_client)
        mock_client.api_request_handler.sharedstep_handler.update_shared_step.return_value = (
            {"id": 1, "title": "New Title"},
            "",
        )

        with patch.object(self.environment, "log") as mock_log, patch.object(
            self.environment, "set_parameters"
        ), patch.object(self.environment, "check_for_required_parameters"):
            result = self.runner.invoke(
                cmd_sharedsteps.update, ["--sharedstep-id", "1", "--name", "New Title"], obj=self.environment
            )

            assert result.exit_code == 0
            assert mock_log.called

    @mock.patch("trcli.commands.cmd_sharedsteps.ProjectBasedClient")
    def test_update_sharedstep_no_fields(self, mock_project_client):
        """Test error when no fields are provided for update."""
        mock_client = self._setup_project_client_mock(mock_project_client)

        with patch.object(self.environment, "elog") as mock_elog, patch.object(
            self.environment, "set_parameters"
        ), patch.object(self.environment, "check_for_required_parameters"):
            result = self.runner.invoke(cmd_sharedsteps.update, ["--sharedstep-id", "1"], obj=self.environment)

            assert result.exit_code == 1
            assert mock_elog.called

    @mock.patch("trcli.commands.cmd_sharedsteps.ProjectBasedClient")
    def test_update_sharedstep_api_error(self, mock_project_client):
        """Test handling of API errors when updating."""
        mock_client = self._setup_project_client_mock(mock_project_client)
        mock_client.api_request_handler.sharedstep_handler.update_shared_step.return_value = (
            None,
            "Invalid or unknown test",
        )

        with patch.object(self.environment, "elog") as mock_elog, patch.object(
            self.environment, "set_parameters"
        ), patch.object(self.environment, "check_for_required_parameters"):
            result = self.runner.invoke(
                cmd_sharedsteps.update, ["--sharedstep-id", "999", "--name", "Test"], obj=self.environment
            )

            assert result.exit_code == 1
            assert mock_elog.called

    @mock.patch("trcli.commands.cmd_sharedsteps.ProjectBasedClient")
    def test_delete_sharedstep_keep_in_cases_default(self, mock_project_client):
        """Test successful deletion with default keep_in_cases."""
        mock_client = self._setup_project_client_mock(mock_project_client)
        mock_client.api_request_handler.sharedstep_handler.delete_shared_step.return_value = (True, "")

        with patch.object(self.environment, "log") as mock_log, patch.object(
            self.environment, "set_parameters"
        ), patch.object(self.environment, "check_for_required_parameters"):
            result = self.runner.invoke(cmd_sharedsteps.delete, ["--sharedstep-id", "1"], obj=self.environment)

            assert result.exit_code == 0
            assert mock_log.called
            # Verify keep_in_cases defaults to True
            call_kwargs = mock_client.api_request_handler.sharedstep_handler.delete_shared_step.call_args[1]
            assert call_kwargs["keep_in_cases"] is True

    @mock.patch("trcli.commands.cmd_sharedsteps.ProjectBasedClient")
    def test_delete_sharedstep_no_keep_in_cases(self, mock_project_client):
        """Test deletion with --no-keep-in-cases flag."""
        mock_client = self._setup_project_client_mock(mock_project_client)
        mock_client.api_request_handler.sharedstep_handler.delete_shared_step.return_value = (True, "")

        with patch.object(self.environment, "log") as mock_log, patch.object(
            self.environment, "set_parameters"
        ), patch.object(self.environment, "check_for_required_parameters"):
            result = self.runner.invoke(
                cmd_sharedsteps.delete, ["--sharedstep-id", "5", "--no-keep-in-cases"], obj=self.environment
            )

            assert result.exit_code == 0
            assert mock_log.called
            # Verify keep_in_cases is False
            call_kwargs = mock_client.api_request_handler.sharedstep_handler.delete_shared_step.call_args[1]
            assert call_kwargs["keep_in_cases"] is False

    @mock.patch("trcli.commands.cmd_sharedsteps.ProjectBasedClient")
    def test_delete_sharedstep_api_error(self, mock_project_client):
        """Test handling of API errors when deleting."""
        mock_client = self._setup_project_client_mock(mock_project_client)
        mock_client.api_request_handler.sharedstep_handler.delete_shared_step.return_value = (
            False,
            "Invalid or unknown shared step",
        )

        with patch.object(self.environment, "elog") as mock_elog, patch.object(self.environment, "log"), patch.object(
            self.environment, "set_parameters"
        ), patch.object(self.environment, "check_for_required_parameters"):
            result = self.runner.invoke(cmd_sharedsteps.delete, ["--sharedstep-id", "999"], obj=self.environment)

            assert result.exit_code == 1
            assert mock_elog.called
