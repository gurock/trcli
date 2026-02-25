"""
Unit tests for cmd_update command.
"""

import pytest
from unittest.mock import patch, MagicMock
from click.testing import CliRunner

from trcli.commands.cmd_update import cli as update_cli
from trcli import __version__


@pytest.fixture
def runner():
    """Create a Click test runner."""
    return CliRunner()


class TestUpdateCommand:
    """Tests for trcli update command."""

    def test_update_check_only_with_newer_version(self, runner):
        """Test --check-only flag when newer version is available."""
        mock_msg = "\nA new version of TestRail CLI is available!\n..."
        with patch("trcli.commands.cmd_update._query_pypi", return_value="1.14.0"), patch(
            "trcli.commands.cmd_update.__version__", "1.13.1"
        ), patch("trcli.commands.cmd_update._compare_and_format", return_value=mock_msg):
            result = runner.invoke(update_cli, ["--check-only"])

            assert result.exit_code == 0
            assert "Current version: 1.13.1" in result.output
            assert "Latest version on PyPI: 1.14.0" in result.output
            assert "A new version of TestRail CLI is available" in result.output

    def test_update_check_only_already_latest(self, runner):
        """Test --check-only flag when already on latest version."""
        with patch("trcli.commands.cmd_update._query_pypi", return_value="1.13.1"), patch(
            "trcli.commands.cmd_update.__version__", "1.13.1"
        ), patch("trcli.commands.cmd_update._compare_and_format", return_value=None):
            result = runner.invoke(update_cli, ["--check-only"])

            assert result.exit_code == 0
            assert "You are already on the latest version" in result.output

    def test_update_check_only_pypi_failure(self, runner):
        """Test --check-only flag when PyPI query fails."""
        with patch("trcli.commands.cmd_update._query_pypi", return_value=None):
            result = runner.invoke(update_cli, ["--check-only"])

            assert result.exit_code == 1
            assert "Failed to query PyPI" in result.output

    def test_update_already_latest_no_force(self, runner):
        """Test update when already on latest version without --force."""
        with patch("trcli.commands.cmd_update._query_pypi", return_value="1.13.1"), patch(
            "trcli.commands.cmd_update.__version__", "1.13.1"
        ), patch("trcli.commands.cmd_update._compare_and_format", return_value=None):
            result = runner.invoke(update_cli)

            assert result.exit_code == 0
            assert "You are already on the latest version" in result.output
            assert "Use --force to reinstall" in result.output

    def test_update_cancelled_by_user(self, runner):
        """Test update cancelled by user at confirmation prompt."""
        mock_msg = "\nA new version available\n"
        with patch("trcli.commands.cmd_update._query_pypi", return_value="1.14.0"), patch(
            "trcli.commands.cmd_update.__version__", "1.13.1"
        ), patch("trcli.commands.cmd_update._compare_and_format", return_value=mock_msg):
            # Simulate user saying 'no' at confirmation
            result = runner.invoke(update_cli, input="n\n")

            assert result.exit_code == 0
            assert "Update cancelled" in result.output

    def test_update_successful(self, runner):
        """Test successful update."""
        mock_subprocess_result = MagicMock()
        mock_subprocess_result.returncode = 0
        mock_msg = "\nA new version available\n"

        with patch("trcli.commands.cmd_update._query_pypi", return_value="1.14.0"), patch(
            "trcli.commands.cmd_update.__version__", "1.13.1"
        ), patch("trcli.commands.cmd_update._compare_and_format", return_value=mock_msg), patch(
            "subprocess.run", return_value=mock_subprocess_result
        ):
            # Simulate user saying 'yes' at confirmation
            result = runner.invoke(update_cli, input="y\n")

            assert result.exit_code == 0
            assert "Update completed successfully" in result.output

    def test_update_failed_subprocess(self, runner):
        """Test update when pip subprocess fails."""
        mock_subprocess_result = MagicMock()
        mock_subprocess_result.returncode = 1
        mock_msg = "\nA new version available\n"

        with patch("trcli.commands.cmd_update._query_pypi", return_value="1.14.0"), patch(
            "trcli.commands.cmd_update.__version__", "1.13.1"
        ), patch("trcli.commands.cmd_update._compare_and_format", return_value=mock_msg), patch(
            "subprocess.run", return_value=mock_subprocess_result
        ):
            # Simulate user saying 'yes' at confirmation
            result = runner.invoke(update_cli, input="y\n")

            assert result.exit_code == 1
            assert "Update failed" in result.output
            assert "Common issues and solutions" in result.output

    def test_update_force_reinstall(self, runner):
        """Test update with --force flag."""
        mock_subprocess_result = MagicMock()
        mock_subprocess_result.returncode = 0

        with patch("trcli.commands.cmd_update._query_pypi", return_value="1.13.1"), patch(
            "trcli.commands.cmd_update.__version__", "1.13.1"
        ), patch("subprocess.run", return_value=mock_subprocess_result) as mock_run:
            # Simulate user saying 'yes' at confirmation
            result = runner.invoke(update_cli, ["--force"], input="y\n")

            assert result.exit_code == 0
            assert "Forcing reinstall" in result.output
            assert "Update completed successfully" in result.output

            # Verify --force-reinstall was passed to pip
            call_args = mock_run.call_args[0][0]
            assert "--force-reinstall" in call_args

    def test_update_pip_not_found(self, runner):
        """Test update when pip is not available."""
        mock_msg = "\nA new version available\n"
        with patch("trcli.commands.cmd_update._query_pypi", return_value="1.14.0"), patch(
            "trcli.commands.cmd_update.__version__", "1.13.1"
        ), patch("trcli.commands.cmd_update._compare_and_format", return_value=mock_msg), patch(
            "subprocess.run", side_effect=FileNotFoundError("pip not found")
        ):
            # Simulate user saying 'yes' at confirmation
            result = runner.invoke(update_cli, input="y\n")

            assert result.exit_code == 1
            assert "pip not found" in result.output

    def test_update_keyboard_interrupt(self, runner):
        """Test update interrupted by user (Ctrl+C)."""
        mock_msg = "\nA new version available\n"
        with patch("trcli.commands.cmd_update._query_pypi", return_value="1.14.0"), patch(
            "trcli.commands.cmd_update.__version__", "1.13.1"
        ), patch("trcli.commands.cmd_update._compare_and_format", return_value=mock_msg), patch(
            "subprocess.run", side_effect=KeyboardInterrupt()
        ):
            # Simulate user saying 'yes' at confirmation
            result = runner.invoke(update_cli, input="y\n")

            assert result.exit_code == 130
            assert "interrupted" in result.output

    def test_update_unexpected_exception(self, runner):
        """Test update with unexpected exception."""
        mock_msg = "\nA new version available\n"
        with patch("trcli.commands.cmd_update._query_pypi", return_value="1.14.0"), patch(
            "trcli.commands.cmd_update.__version__", "1.13.1"
        ), patch("trcli.commands.cmd_update._compare_and_format", return_value=mock_msg), patch(
            "subprocess.run", side_effect=Exception("Unexpected error")
        ):
            # Simulate user saying 'yes' at confirmation
            result = runner.invoke(update_cli, input="y\n")

            assert result.exit_code == 1
            assert "Unexpected error" in result.output

    def test_update_shows_current_and_latest_version(self, runner):
        """Test that update command shows current and latest versions."""
        mock_msg = "\nA new version available\n"
        with patch("trcli.commands.cmd_update._query_pypi", return_value="1.14.0"), patch(
            "trcli.commands.cmd_update.__version__", "1.13.1"
        ), patch("trcli.commands.cmd_update._compare_and_format", return_value=mock_msg):
            result = runner.invoke(update_cli, input="n\n")

            assert "Current version: 1.13.1" in result.output
            assert "Latest version on PyPI: 1.14.0" in result.output

    def test_update_command_uses_sys_executable(self, runner):
        """Test that update uses sys.executable to call pip."""
        import sys

        mock_subprocess_result = MagicMock()
        mock_subprocess_result.returncode = 0
        mock_msg = "\nA new version available\n"

        with patch("trcli.commands.cmd_update._query_pypi", return_value="1.14.0"), patch(
            "trcli.commands.cmd_update.__version__", "1.13.1"
        ), patch("trcli.commands.cmd_update._compare_and_format", return_value=mock_msg), patch(
            "subprocess.run", return_value=mock_subprocess_result
        ) as mock_run:
            # Simulate user saying 'yes' at confirmation
            result = runner.invoke(update_cli, input="y\n")

            # Verify sys.executable was used
            call_args = mock_run.call_args[0][0]
            assert call_args[0] == sys.executable
            assert call_args[1:4] == ["-m", "pip", "install"]
