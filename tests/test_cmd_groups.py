import pytest
from unittest import mock
from unittest.mock import MagicMock, patch
from click.testing import CliRunner

from trcli.cli import Environment
from trcli.commands import cmd_groups


class TestCmdGroups:
    """Test class for groups command functionality"""

    def setup_method(self):
        """Set up test environment"""
        self.runner = CliRunner()
        self.environment = Environment(cmd="groups")
        self.environment.host = "https://test.testrail.com"
        self.environment.username = "test@example.com"
        self.environment.password = "password"
        self.environment.api_key = None

    def _setup_project_client_mock(self, mock_project_client):
        """Helper to setup ProjectBasedClient mock"""
        mock_client_instance = MagicMock()
        mock_project_client.return_value = mock_client_instance
        return mock_client_instance

    # SHOW subcommand tests

    @mock.patch("trcli.commands.cmd_groups.ProjectBasedClient")
    def test_show_group_success(self, mock_project_client):
        """Test showing a specific group by ID"""
        mock_client = self._setup_project_client_mock(mock_project_client)
        mock_client.api_request_handler.groups_handler.get_group.return_value = (
            {"id": 1, "name": "QA Team", "user_ids": [1, 3, 5, 7]},
            "",
        )

        with patch.object(self.environment, "log") as mock_log, patch.object(
            self.environment, "set_parameters"
        ), patch.object(self.environment, "check_for_required_parameters"):
            result = self.runner.invoke(cmd_groups.show, ["--group-id", "1"], obj=self.environment)

            assert result.exit_code == 0
            mock_client.api_request_handler.groups_handler.get_group.assert_called_once_with(1)
            assert mock_log.called

    @mock.patch("trcli.commands.cmd_groups.ProjectBasedClient")
    def test_show_group_with_no_members(self, mock_project_client):
        """Test showing a group with no members"""
        mock_client = self._setup_project_client_mock(mock_project_client)
        mock_client.api_request_handler.groups_handler.get_group.return_value = (
            {"id": 2, "name": "Empty Group", "user_ids": []},
            "",
        )

        with patch.object(self.environment, "log") as mock_log, patch.object(
            self.environment, "set_parameters"
        ), patch.object(self.environment, "check_for_required_parameters"):
            result = self.runner.invoke(cmd_groups.show, ["--group-id", "2"], obj=self.environment)

            assert result.exit_code == 0
            mock_client.api_request_handler.groups_handler.get_group.assert_called_once_with(2)
            assert mock_log.called

    @mock.patch("trcli.commands.cmd_groups.ProjectBasedClient")
    def test_show_group_json_output(self, mock_project_client):
        """Test showing group with JSON output"""
        mock_client = self._setup_project_client_mock(mock_project_client)
        group_data = {"id": 3, "name": "Developers", "user_ids": [2, 4, 6]}
        mock_client.api_request_handler.groups_handler.get_group.return_value = (group_data, "")

        with patch.object(self.environment, "set_parameters"), patch.object(
            self.environment, "check_for_required_parameters"
        ):
            result = self.runner.invoke(cmd_groups.show, ["--group-id", "3", "--json-output"], obj=self.environment)

            assert result.exit_code == 0
            assert '"name": "Developers"' in result.output
            assert '"user_ids"' in result.output

    @mock.patch("trcli.commands.cmd_groups.ProjectBasedClient")
    def test_show_group_api_error(self, mock_project_client):
        """Test showing group with API error"""
        mock_client = self._setup_project_client_mock(mock_project_client)
        mock_client.api_request_handler.groups_handler.get_group.return_value = ({}, "Group not found")

        with patch.object(self.environment, "elog") as mock_elog, patch.object(
            self.environment, "set_parameters"
        ), patch.object(self.environment, "check_for_required_parameters"), patch.object(self.environment, "log"):
            result = self.runner.invoke(cmd_groups.show, ["--group-id", "999"], obj=self.environment)

            assert result.exit_code == 1
            mock_elog.assert_called_with("Error: Failed to retrieve group: Group not found")

    @mock.patch("trcli.commands.cmd_groups.ProjectBasedClient")
    def test_show_group_not_found(self, mock_project_client):
        """Test showing group when group is not found (empty response)"""
        mock_client = self._setup_project_client_mock(mock_project_client)
        mock_client.api_request_handler.groups_handler.get_group.return_value = ({}, "")

        with patch.object(self.environment, "log") as mock_log, patch.object(
            self.environment, "set_parameters"
        ), patch.object(self.environment, "check_for_required_parameters"):
            result = self.runner.invoke(cmd_groups.show, ["--group-id", "100"], obj=self.environment)

            assert result.exit_code == 0
            # Check that "No group found" message appears in logs
            log_calls = [str(call) for call in mock_log.call_args_list]
            assert any("No group found" in str(call) for call in log_calls)

    # LIST subcommand tests

    @mock.patch("trcli.commands.cmd_groups.ProjectBasedClient")
    def test_list_groups_success(self, mock_project_client):
        """Test listing groups successfully"""
        mock_client = self._setup_project_client_mock(mock_project_client)
        mock_client.api_request_handler.groups_handler.get_groups.return_value = (
            {
                "offset": 0,
                "limit": 250,
                "size": 2,
                "_links": {"next": None, "prev": None},
                "groups": [
                    {"id": 1, "name": "QA Team", "user_ids": [1, 3, 5]},
                    {"id": 2, "name": "Developers", "user_ids": [2, 4, 6, 8]},
                ],
            },
            "",
        )

        with patch.object(self.environment, "log") as mock_log, patch.object(
            self.environment, "set_parameters"
        ), patch.object(self.environment, "check_for_required_parameters"):
            result = self.runner.invoke(cmd_groups.list, [], obj=self.environment)

            assert result.exit_code == 0
            mock_client.api_request_handler.groups_handler.get_groups.assert_called_once_with(limit=250, offset=0)
            assert mock_log.called

    @mock.patch("trcli.commands.cmd_groups.ProjectBasedClient")
    def test_list_groups_with_pagination(self, mock_project_client):
        """Test listing groups with custom pagination"""
        mock_client = self._setup_project_client_mock(mock_project_client)
        mock_client.api_request_handler.groups_handler.get_groups.return_value = (
            {
                "offset": 10,
                "limit": 5,
                "size": 15,
                "_links": {"next": "/api/v2/get_groups?offset=15", "prev": "/api/v2/get_groups?offset=5"},
                "groups": [{"id": i, "name": f"Group {i}", "user_ids": [i, i + 1]} for i in range(11, 16)],
            },
            "",
        )

        with patch.object(self.environment, "log") as mock_log, patch.object(
            self.environment, "set_parameters"
        ), patch.object(self.environment, "check_for_required_parameters"):
            result = self.runner.invoke(cmd_groups.list, ["--limit", "5", "--offset", "10"], obj=self.environment)

            assert result.exit_code == 0
            mock_client.api_request_handler.groups_handler.get_groups.assert_called_once_with(limit=5, offset=10)
            assert mock_log.called

    @mock.patch("trcli.commands.cmd_groups.ProjectBasedClient")
    def test_list_groups_json_output(self, mock_project_client):
        """Test listing groups with JSON output"""
        mock_client = self._setup_project_client_mock(mock_project_client)
        response_data = {
            "offset": 0,
            "limit": 250,
            "size": 1,
            "_links": {"next": None, "prev": None},
            "groups": [{"id": 1, "name": "Test Group", "user_ids": [1, 2]}],
        }
        mock_client.api_request_handler.groups_handler.get_groups.return_value = (response_data, "")

        with patch.object(self.environment, "set_parameters"), patch.object(
            self.environment, "check_for_required_parameters"
        ):
            result = self.runner.invoke(cmd_groups.list, ["--json-output"], obj=self.environment)

            assert result.exit_code == 0
            assert '"groups"' in result.output
            assert '"Test Group"' in result.output

    @mock.patch("trcli.commands.cmd_groups.ProjectBasedClient")
    def test_list_groups_empty(self, mock_project_client):
        """Test listing groups when no groups exist"""
        mock_client = self._setup_project_client_mock(mock_project_client)
        mock_client.api_request_handler.groups_handler.get_groups.return_value = (
            {"offset": 0, "limit": 250, "size": 0, "_links": {"next": None, "prev": None}, "groups": []},
            "",
        )

        with patch.object(self.environment, "log") as mock_log, patch.object(
            self.environment, "set_parameters"
        ), patch.object(self.environment, "check_for_required_parameters"):
            result = self.runner.invoke(cmd_groups.list, [], obj=self.environment)

            assert result.exit_code == 0
            # Check that "No groups found" message appears in logs
            log_calls = [str(call) for call in mock_log.call_args_list]
            assert any("No groups found" in str(call) for call in log_calls)

    @mock.patch("trcli.commands.cmd_groups.ProjectBasedClient")
    def test_list_groups_api_error(self, mock_project_client):
        """Test listing groups with API error"""
        mock_client = self._setup_project_client_mock(mock_project_client)
        mock_client.api_request_handler.groups_handler.get_groups.return_value = ({}, "API connection error")

        with patch.object(self.environment, "elog") as mock_elog, patch.object(
            self.environment, "set_parameters"
        ), patch.object(self.environment, "check_for_required_parameters"), patch.object(self.environment, "log"):
            result = self.runner.invoke(cmd_groups.list, [], obj=self.environment)

            assert result.exit_code == 1
            mock_elog.assert_called_with("Error: Failed to retrieve groups: API connection error")

    @mock.patch("trcli.commands.cmd_groups.ProjectBasedClient")
    def test_list_groups_with_pagination_hint(self, mock_project_client):
        """Test listing groups shows pagination hint when more results available"""
        mock_client = self._setup_project_client_mock(mock_project_client)
        mock_client.api_request_handler.groups_handler.get_groups.return_value = (
            {
                "offset": 0,
                "limit": 2,
                "size": 10,
                "_links": {"next": "/api/v2/get_groups?offset=2", "prev": None},
                "groups": [
                    {"id": 1, "name": "Group 1", "user_ids": [1]},
                    {"id": 2, "name": "Group 2", "user_ids": [2]},
                ],
            },
            "",
        )

        with patch.object(self.environment, "log") as mock_log, patch.object(
            self.environment, "set_parameters"
        ), patch.object(self.environment, "check_for_required_parameters"):
            result = self.runner.invoke(cmd_groups.list, ["--limit", "2"], obj=self.environment)

            assert result.exit_code == 0
            # Check that pagination hint appears
            log_calls = [str(call) for call in mock_log.call_args_list]
            assert any("--offset 2" in str(call) for call in log_calls)

    # Helper function tests

    def test_display_group_with_members(self):
        """Test display_group helper function with members"""
        group = {"id": 1, "name": "Test Group", "user_ids": [1, 2, 3]}

        with patch.object(self.environment, "log") as mock_log:
            cmd_groups.display_group(self.environment, group)

            # Verify all expected log calls
            log_calls = [call[0][0] for call in mock_log.call_args_list]
            assert "Group ID: 1" in log_calls
            assert "  Name: Test Group" in log_calls
            assert "  Members: 3 user(s)" in log_calls
            assert "  User IDs: 1, 2, 3" in log_calls

    def test_display_group_without_members(self):
        """Test display_group helper function without members"""
        group = {"id": 2, "name": "Empty Group", "user_ids": []}

        with patch.object(self.environment, "log") as mock_log:
            cmd_groups.display_group(self.environment, group)

            # Verify all expected log calls
            log_calls = [call[0][0] for call in mock_log.call_args_list]
            assert "Group ID: 2" in log_calls
            assert "  Name: Empty Group" in log_calls
            assert "  Members: 0 user(s)" in log_calls

    def test_display_group_missing_fields(self):
        """Test display_group helper with missing fields"""
        group = {"id": 3}  # Missing name and user_ids

        with patch.object(self.environment, "log") as mock_log:
            cmd_groups.display_group(self.environment, group)

            # Verify it handles missing fields gracefully
            log_calls = [call[0][0] for call in mock_log.call_args_list]
            assert "Group ID: 3" in log_calls
            assert "  Name: N/A" in log_calls
            assert "  Members: 0 user(s)" in log_calls
