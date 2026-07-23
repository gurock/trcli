import pytest
from unittest import mock
from unittest.mock import MagicMock, patch
from click.testing import CliRunner

from trcli.cli import Environment
from trcli.commands import cmd_users


class TestCmdUsers:
    """Test class for users command functionality"""

    def setup_method(self):
        """Set up test environment"""
        self.runner = CliRunner()
        self.environment = Environment(cmd="users")
        self.environment.host = "https://test.testrail.com"
        self.environment.username = "test@example.com"
        self.environment.password = "password"
        self.environment.api_key = None

    def _setup_project_client_mock(self, mock_project_client):
        """Helper to setup ProjectBasedClient mock"""
        mock_client_instance = MagicMock()
        mock_project_client.return_value = mock_client_instance
        return mock_client_instance

    # GET subcommand tests

    @mock.patch("trcli.commands.cmd_users.ProjectBasedClient")
    def test_get_current_user_success(self, mock_project_client):
        """Test getting current authenticated user"""
        mock_client = self._setup_project_client_mock(mock_project_client)
        mock_client.api_request_handler.user_handler.get_current_user.return_value = (
            {
                "id": 1,
                "email": "test@example.com",
                "is_active": True,
                "name": "Test User",
                "role_id": 3,
                "role": "Tester",
            },
            "",
        )

        with patch.object(self.environment, "log") as mock_log, patch.object(
            self.environment, "set_parameters"
        ), patch.object(self.environment, "check_for_required_parameters"):
            result = self.runner.invoke(cmd_users.get, ["--current"], obj=self.environment)

            assert result.exit_code == 0
            mock_client.api_request_handler.user_handler.get_current_user.assert_called_once()
            assert mock_log.called

    @mock.patch("trcli.commands.cmd_users.ProjectBasedClient")
    def test_get_user_by_id_success(self, mock_project_client):
        """Test getting user by ID"""
        mock_client = self._setup_project_client_mock(mock_project_client)
        mock_client.api_request_handler.user_handler.get_user.return_value = (
            {"id": 5, "email": "john.doe@example.com", "name": "John Doe", "role": "Tester", "is_active": True},
            "",
        )

        with patch.object(self.environment, "log") as mock_log, patch.object(
            self.environment, "set_parameters"
        ), patch.object(self.environment, "check_for_required_parameters"):
            result = self.runner.invoke(cmd_users.get, ["--user-id", "5"], obj=self.environment)

            assert result.exit_code == 0
            mock_client.api_request_handler.user_handler.get_user.assert_called_once_with(5)
            assert mock_log.called

    @mock.patch("trcli.commands.cmd_users.ProjectBasedClient")
    def test_get_user_by_email_success(self, mock_project_client):
        """Test getting user by email"""
        mock_client = self._setup_project_client_mock(mock_project_client)
        mock_client.api_request_handler.user_handler.get_user_by_email.return_value = (
            {"id": 3, "email": "jane@example.com", "name": "Jane Smith", "role": "Lead", "is_active": True},
            "",
        )

        with patch.object(self.environment, "log") as mock_log, patch.object(
            self.environment, "set_parameters"
        ), patch.object(self.environment, "check_for_required_parameters"):
            result = self.runner.invoke(cmd_users.get, ["--email", "jane@example.com"], obj=self.environment)

            assert result.exit_code == 0
            mock_client.api_request_handler.user_handler.get_user_by_email.assert_called_once_with("jane@example.com")
            assert mock_log.called

    @mock.patch("trcli.commands.cmd_users.ProjectBasedClient")
    def test_get_user_with_all_fields(self, mock_project_client):
        """Test getting user with all fields displayed"""
        mock_client = self._setup_project_client_mock(mock_project_client)
        mock_client.api_request_handler.user_handler.get_user.return_value = (
            {
                "id": 1,
                "email": "admin@example.com",
                "name": "Admin User",
                "role": "Administrator",
                "role_id": 1,
                "is_active": True,
                "is_admin": True,
                "group_ids": [1, 2, 3],
                "mfa_required": True,
                "email_notifications": True,
                "sso_enabled": False,
                "assigned_projects": [1, 3, 5],
            },
            "",
        )

        with patch.object(self.environment, "log") as mock_log, patch.object(
            self.environment, "set_parameters"
        ), patch.object(self.environment, "check_for_required_parameters"):
            result = self.runner.invoke(cmd_users.get, ["--user-id", "1", "--show-all-fields"], obj=self.environment)

            assert result.exit_code == 0
            assert mock_log.called

    @mock.patch("trcli.commands.cmd_users.ProjectBasedClient")
    def test_get_user_json_output(self, mock_project_client):
        """Test getting user with JSON output"""
        mock_client = self._setup_project_client_mock(mock_project_client)
        user_data = {"id": 2, "email": "user@example.com", "name": "Test User", "role": "Tester"}
        mock_client.api_request_handler.user_handler.get_user.return_value = (user_data, "")

        with patch.object(self.environment, "set_parameters"), patch.object(
            self.environment, "check_for_required_parameters"
        ):
            result = self.runner.invoke(cmd_users.get, ["--user-id", "2", "--json-output"], obj=self.environment)

            assert result.exit_code == 0
            assert '"email": "user@example.com"' in result.output

    @mock.patch("trcli.commands.cmd_users.ProjectBasedClient")
    def test_get_user_no_option_error(self, mock_project_client):
        """Test error when no option is provided"""
        self._setup_project_client_mock(mock_project_client)

        with patch.object(self.environment, "elog") as mock_elog, patch.object(
            self.environment, "set_parameters"
        ), patch.object(self.environment, "check_for_required_parameters"):
            result = self.runner.invoke(cmd_users.get, [], obj=self.environment)

            assert result.exit_code == 1
            mock_elog.assert_called_with("Error: Must specify one of --current, --user-id, or --email")

    @mock.patch("trcli.commands.cmd_users.ProjectBasedClient")
    def test_get_user_multiple_options_error(self, mock_project_client):
        """Test error when multiple exclusive options are provided"""
        self._setup_project_client_mock(mock_project_client)

        with patch.object(self.environment, "elog") as mock_elog, patch.object(
            self.environment, "set_parameters"
        ), patch.object(self.environment, "check_for_required_parameters"):
            result = self.runner.invoke(cmd_users.get, ["--current", "--user-id", "5"], obj=self.environment)

            assert result.exit_code == 1
            mock_elog.assert_called_with("Error: Options --current, --user-id, and --email are mutually exclusive")

    @mock.patch("trcli.commands.cmd_users.ProjectBasedClient")
    def test_get_user_api_error(self, mock_project_client):
        """Test getting user with API error"""
        mock_client = self._setup_project_client_mock(mock_project_client)
        mock_client.api_request_handler.user_handler.get_user.return_value = (None, "User not found")

        with patch.object(self.environment, "elog") as mock_elog, patch.object(
            self.environment, "set_parameters"
        ), patch.object(self.environment, "check_for_required_parameters"):
            result = self.runner.invoke(cmd_users.get, ["--user-id", "999"], obj=self.environment)

            assert result.exit_code == 1
            mock_elog.assert_called_with("Error: Failed to retrieve user: User not found")

    # LIST subcommand tests

    @mock.patch("trcli.commands.cmd_users.ProjectBasedClient")
    def test_list_all_users_success(self, mock_project_client):
        """Test listing all users"""
        mock_client = self._setup_project_client_mock(mock_project_client)
        mock_client.api_request_handler.user_handler.get_users.return_value = (
            [
                {"id": 1, "name": "John Doe", "email": "john@example.com"},
                {"id": 2, "name": "Jane Smith", "email": "jane@example.com"},
                {"id": 3, "name": "Bob Johnson", "email": "bob@example.com"},
            ],
            "",
        )

        with patch.object(self.environment, "log") as mock_log, patch.object(
            self.environment, "set_parameters"
        ), patch.object(self.environment, "check_for_required_parameters"):
            result = self.runner.invoke(cmd_users.list, [], obj=self.environment)

            assert result.exit_code == 0
            mock_client.api_request_handler.user_handler.get_users.assert_called_once_with(None)
            assert mock_log.called

    @mock.patch("trcli.commands.cmd_users.ProjectBasedClient")
    def test_list_users_by_project_success(self, mock_project_client):
        """Test listing users filtered by project"""
        mock_client = self._setup_project_client_mock(mock_project_client)
        mock_client.api_request_handler.user_handler.get_users.return_value = (
            [
                {"id": 1, "name": "John Doe", "role": "Tester", "role_id": 3},
                {"id": 2, "name": "Jane Smith", "role": "Lead", "role_id": 2},
            ],
            "",
        )

        with patch.object(self.environment, "log") as mock_log, patch.object(
            self.environment, "set_parameters"
        ), patch.object(self.environment, "check_for_required_parameters"):
            result = self.runner.invoke(cmd_users.list, ["--project-id", "5"], obj=self.environment)

            assert result.exit_code == 0
            mock_client.api_request_handler.user_handler.get_users.assert_called_once_with(5)
            assert mock_log.called

    @mock.patch("trcli.commands.cmd_users.ProjectBasedClient")
    def test_list_users_json_output(self, mock_project_client):
        """Test listing users with JSON output"""
        mock_client = self._setup_project_client_mock(mock_project_client)
        users_data = [{"id": 1, "name": "John Doe"}, {"id": 2, "name": "Jane Smith"}]
        mock_client.api_request_handler.user_handler.get_users.return_value = (users_data, "")

        with patch.object(self.environment, "set_parameters"), patch.object(
            self.environment, "check_for_required_parameters"
        ):
            result = self.runner.invoke(cmd_users.list, ["--json-output"], obj=self.environment)

            assert result.exit_code == 0
            assert '"name": "John Doe"' in result.output

    @mock.patch("trcli.commands.cmd_users.ProjectBasedClient")
    def test_list_users_empty_result(self, mock_project_client):
        """Test listing users with empty result"""
        mock_client = self._setup_project_client_mock(mock_project_client)
        mock_client.api_request_handler.user_handler.get_users.return_value = ([], "")

        with patch.object(self.environment, "log") as mock_log, patch.object(
            self.environment, "set_parameters"
        ), patch.object(self.environment, "check_for_required_parameters"):
            result = self.runner.invoke(cmd_users.list, [], obj=self.environment)

            assert result.exit_code == 0
            assert mock_log.called

    @mock.patch("trcli.commands.cmd_users.ProjectBasedClient")
    def test_list_users_api_error(self, mock_project_client):
        """Test listing users with API error"""
        mock_client = self._setup_project_client_mock(mock_project_client)
        mock_client.api_request_handler.user_handler.get_users.return_value = ([], "Permission denied")

        with patch.object(self.environment, "elog") as mock_elog, patch.object(
            self.environment, "set_parameters"
        ), patch.object(self.environment, "check_for_required_parameters"):
            result = self.runner.invoke(cmd_users.list, [], obj=self.environment)

            assert result.exit_code == 1
            mock_elog.assert_called_with("Error: Failed to retrieve users: Permission denied")
