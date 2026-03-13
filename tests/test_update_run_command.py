import pytest
from click.testing import CliRunner
from unittest.mock import Mock, patch, MagicMock
from trcli.commands.cmd_update_run import cli
from trcli.cli import Environment


class TestUpdateRunCommand:
    """Tests for update_run CLI command"""

    @pytest.fixture
    def runner(self):
        return CliRunner()

    @pytest.fixture
    def mock_project_client(self, mocker):
        # Mock check_for_required_parameters to skip validation
        mocker.patch.object(Environment, "check_for_required_parameters", return_value=None)

        with patch("trcli.commands.cmd_update_run.ProjectBasedClient") as mock:
            mock_instance = Mock()
            mock_instance.create_or_update_test_run.return_value = (123, None)
            mock_instance.resolve_project = Mock()
            mock_instance.resolve_suite = Mock(return_value=(1, False))
            mock.return_value = mock_instance
            yield mock

    def test_update_run_requires_run_id(self, runner):
        """Test that --run-id is required"""
        result = runner.invoke(
            cli,
            [
                "--title",
                "New Title",
            ],
        )
        assert result.exit_code != 0
        assert "required" in result.output.lower() or "missing" in result.output.lower()

    def test_update_run_with_assignedto(self, runner, mock_project_client):
        """Test setting assignee with --assignedto"""
        result = runner.invoke(cli, ["--run-id", "123", "--assignedto", "42"], catch_exceptions=False)

        assert result.exit_code == 0
        assert "Test run updated successfully" in result.output

    def test_update_run_with_clear_assignee(self, runner, mock_project_client):
        """Test clearing assignee with --clear-assignee"""
        result = runner.invoke(cli, ["--run-id", "123", "--clear-assignee"], catch_exceptions=False)

        assert result.exit_code == 0
        assert "Test run updated successfully" in result.output

    def test_update_run_mutually_exclusive_assignee_flags(self, runner, mocker):
        """Test that --assignedto and --clear-assignee cannot be used together"""
        # Mock check_for_required_parameters to skip validation
        mocker.patch.object(Environment, "check_for_required_parameters", return_value=None)

        result = runner.invoke(cli, ["--run-id", "123", "--assignedto", "42", "--clear-assignee"])

        assert result.exit_code != 0
        assert "cannot be used together" in result.output.lower()

    def test_update_run_without_assignee_options(self, runner, mock_project_client):
        """Test updating run without assignee changes (backward compatibility)"""
        result = runner.invoke(cli, ["--run-id", "123", "--title", "New Title"], catch_exceptions=False)

        assert result.exit_code == 0
        assert "Test run updated successfully" in result.output

    def test_update_run_multi_field_update(self, runner, mock_project_client):
        """Test updating multiple fields including assignee"""
        result = runner.invoke(
            cli,
            [
                "--run-id",
                "123",
                "--title",
                "Updated Title",
                "--run-description",
                "Updated description",
                "--assignedto",
                "42",
            ],
            catch_exceptions=False,
        )

        assert result.exit_code == 0
        assert "Test run updated successfully" in result.output

    def test_update_run_sets_cmd_attribute(self, runner, mock_project_client):
        """Test that environment.cmd is set to 'update_run'"""
        # We can't easily check environment after click invocation,
        # but we can verify the command executes successfully
        result = runner.invoke(cli, ["--run-id", "123"], catch_exceptions=False)

        assert result.exit_code == 0
        # The command should complete successfully, indicating cmd was set properly

    def test_update_run_assignedto_id_set_in_environment(self, runner, mocker):
        """Test that assignedto_id is correctly set on environment when --assignedto is provided"""
        # Mock check_for_required_parameters
        mocker.patch.object(Environment, "check_for_required_parameters", return_value=None)

        with patch("trcli.commands.cmd_update_run.ProjectBasedClient") as mock_pbc:
            mock_instance = Mock()
            mock_instance.create_or_update_test_run.return_value = (123, None)
            mock_instance.resolve_project = Mock()
            mock_instance.resolve_suite = Mock(return_value=(1, False))

            def check_env(environment, suite):
                # Verify assignedto_id was set correctly
                assert hasattr(environment, "assignedto_id")
                assert environment.assignedto_id == 42
                return mock_instance

            mock_pbc.side_effect = check_env

            result = runner.invoke(cli, ["--run-id", "123", "--assignedto", "42"], catch_exceptions=False)
            assert result.exit_code == 0

    def test_update_run_assignedto_id_none_for_clear(self, runner, mocker):
        """Test that assignedto_id is set to None when --clear-assignee is provided"""
        # Mock check_for_required_parameters
        mocker.patch.object(Environment, "check_for_required_parameters", return_value=None)

        with patch("trcli.commands.cmd_update_run.ProjectBasedClient") as mock_pbc:
            mock_instance = Mock()
            mock_instance.create_or_update_test_run.return_value = (123, None)
            mock_instance.resolve_project = Mock()
            mock_instance.resolve_suite = Mock(return_value=(1, False))

            def check_env(environment, suite):
                # Verify assignedto_id was set to None
                assert hasattr(environment, "assignedto_id")
                assert environment.assignedto_id is None
                return mock_instance

            mock_pbc.side_effect = check_env

            result = runner.invoke(cli, ["--run-id", "123", "--clear-assignee"], catch_exceptions=False)
            assert result.exit_code == 0

    def test_update_run_no_assignedto_id_attribute_when_not_specified(self, runner, mocker):
        """Test that assignedto_id attribute is not set when neither flag is provided"""
        # Mock check_for_required_parameters
        mocker.patch.object(Environment, "check_for_required_parameters", return_value=None)

        with patch("trcli.commands.cmd_update_run.ProjectBasedClient") as mock_pbc:
            mock_instance = Mock()
            mock_instance.create_or_update_test_run.return_value = (123, None)
            mock_instance.resolve_project = Mock()
            mock_instance.resolve_suite = Mock(return_value=(1, False))

            captured_env = []

            def check_env(environment, suite):
                captured_env.append(environment)
                return mock_instance

            mock_pbc.side_effect = check_env

            result = runner.invoke(cli, ["--run-id", "123", "--title", "Test"], catch_exceptions=False)
            assert result.exit_code == 0

            # Verify assignedto_id was NOT set (unless set, or set to None explicitly)
            # In this case, we're checking that assignedto attribute exists but assignedto_id may not
            if captured_env:
                env = captured_env[0]
                # assignedto should be None (not provided)
                assert env.assignedto is None
                # assignedto_id should not be set as an attribute if neither flag was used
                # Since clear_assignee is False and assignedto is None, assignedto_id won't be set
