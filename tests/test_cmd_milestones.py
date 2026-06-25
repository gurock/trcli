import pytest
from unittest import mock
from unittest.mock import MagicMock, patch
from click.testing import CliRunner

from trcli.cli import Environment
from trcli.commands import cmd_milestones


class TestCmdMilestones:
    """Test class for milestones command functionality"""

    def setup_method(self):
        """Set up test environment"""
        self.runner = CliRunner()
        self.environment = Environment(cmd="milestones")
        self.environment.host = "https://test.testrail.com"
        self.environment.username = "test@example.com"
        self.environment.password = "password"
        self.environment.project = "Test Project"
        self.environment.project_id = 1

    def _setup_project_client_mock(self, mock_project_client, project_id=1):
        """Helper to setup ProjectBasedClient mock"""
        mock_client_instance = MagicMock()
        mock_project_client.return_value = mock_client_instance
        mock_client_instance.project.project_id = project_id
        return mock_client_instance

    @mock.patch("trcli.commands.cmd_milestones.ProjectBasedClient")
    def test_get_milestone_success(self, mock_project_client):
        """Test successful milestone retrieval"""
        mock_client = self._setup_project_client_mock(mock_project_client)
        mock_client.api_request_handler.milestone_handler.get_milestone.return_value = (
            {
                "id": 1,
                "name": "Release 1.5",
                "description": "Major feature release",
                "project_id": 1,
                "is_completed": True,
                "completed_on": 1389968184,
                "due_on": 1391968184,
                "refs": "RF-1, RF-2",
                "url": "http://test.testrail.com/index.php?/milestones/view/1",
            },
            "",
        )

        with patch.object(self.environment, "log") as mock_log, patch.object(
            self.environment, "set_parameters"
        ), patch.object(self.environment, "check_for_required_parameters"):
            result = self.runner.invoke(cmd_milestones.get, ["--milestone-id", "1"], obj=self.environment)

            assert result.exit_code == 0
            mock_client.api_request_handler.milestone_handler.get_milestone.assert_called_once_with(1)
            assert mock_log.called

    @mock.patch("trcli.commands.cmd_milestones.ProjectBasedClient")
    def test_get_milestone_json_output(self, mock_project_client):
        """Test milestone retrieval with JSON output"""
        mock_client = self._setup_project_client_mock(mock_project_client)
        milestone_data = {
            "id": 1,
            "name": "Release 1.5",
            "description": "Major feature release",
            "project_id": 1,
            "is_completed": False,
            "due_on": 1391968184,
        }
        mock_client.api_request_handler.milestone_handler.get_milestone.return_value = (milestone_data, "")

        with patch.object(self.environment, "set_parameters"), patch.object(
            self.environment, "check_for_required_parameters"
        ):
            result = self.runner.invoke(
                cmd_milestones.get, ["--milestone-id", "1", "--json-output"], obj=self.environment
            )

            assert result.exit_code == 0
            # Check for prettified JSON (with newlines and indentation)
            assert '"id": 1' in result.output
            assert "\n" in result.output  # Prettified has newlines

    @mock.patch("trcli.commands.cmd_milestones.ProjectBasedClient")
    def test_get_milestone_show_all_fields(self, mock_project_client):
        """Test milestone retrieval with show all fields"""
        mock_client = self._setup_project_client_mock(mock_project_client)
        mock_client.api_request_handler.milestone_handler.get_milestone.return_value = (
            {
                "id": 1,
                "name": "Release 1.5",
                "description": "Major feature release with new capabilities",
                "project_id": 1,
                "is_completed": True,
                "completed_on": 1389968184,
                "due_on": 1391968184,
                "refs": "RF-1, RF-2",
                "url": "http://test.testrail.com/index.php?/milestones/view/1",
            },
            "",
        )

        with patch.object(self.environment, "log") as mock_log, patch.object(
            self.environment, "set_parameters"
        ), patch.object(self.environment, "check_for_required_parameters"):
            result = self.runner.invoke(
                cmd_milestones.get, ["--milestone-id", "1", "--show-all-fields"], obj=self.environment
            )

            assert result.exit_code == 0
            assert mock_log.called

    @mock.patch("trcli.commands.cmd_milestones.ProjectBasedClient")
    def test_get_milestone_api_error(self, mock_project_client):
        """Test milestone retrieval with API error"""
        mock_client = self._setup_project_client_mock(mock_project_client)
        mock_client.api_request_handler.milestone_handler.get_milestone.return_value = ({}, "Milestone not found")

        with patch.object(self.environment, "elog") as mock_elog, patch.object(
            self.environment, "set_parameters"
        ), patch.object(self.environment, "check_for_required_parameters"):
            result = self.runner.invoke(cmd_milestones.get, ["--milestone-id", "999"], obj=self.environment)

            assert result.exit_code == 1
            mock_elog.assert_called_with("Error: Failed to retrieve milestone: Milestone not found")

    @mock.patch("trcli.commands.cmd_milestones.ProjectBasedClient")
    def test_list_milestones_success(self, mock_project_client):
        """Test successful milestones listing"""
        mock_client = self._setup_project_client_mock(mock_project_client)
        mock_client.api_request_handler.milestone_handler.get_milestones.return_value = (
            {
                "offset": 0,
                "limit": 250,
                "size": 2,
                "_links": {"next": None, "prev": None},
                "milestones": [
                    {
                        "id": 1,
                        "name": "Release 1.5",
                        "description": "Major feature release",
                        "project_id": 1,
                        "is_completed": False,
                        "due_on": 1391968184,
                    },
                    {
                        "id": 2,
                        "name": "Release 1.6",
                        "description": "Bug fix release",
                        "project_id": 1,
                        "is_completed": False,
                        "due_on": 1393968184,
                    },
                ],
            },
            "",
        )

        with patch.object(self.environment, "log") as mock_log, patch.object(
            self.environment, "set_parameters"
        ), patch.object(self.environment, "check_for_required_parameters"):
            result = self.runner.invoke(cmd_milestones.list, [], obj=self.environment)

            assert result.exit_code == 0
            mock_client.api_request_handler.milestone_handler.get_milestones.assert_called_once_with(
                project_id=1, limit=250, offset=0
            )
            assert mock_log.called

    @mock.patch("trcli.commands.cmd_milestones.ProjectBasedClient")
    def test_list_milestones_with_pagination(self, mock_project_client):
        """Test milestones listing with custom pagination"""
        mock_client = self._setup_project_client_mock(mock_project_client)
        mock_client.api_request_handler.milestone_handler.get_milestones.return_value = (
            {
                "offset": 50,
                "limit": 100,
                "size": 1,
                "_links": {"next": None, "prev": None},
                "milestones": [
                    {
                        "id": 3,
                        "name": "Release 2.0",
                        "description": "Next generation",
                        "project_id": 1,
                        "is_completed": False,
                        "due_on": 1395968184,
                    }
                ],
            },
            "",
        )

        with patch.object(self.environment, "log") as mock_log, patch.object(
            self.environment, "set_parameters"
        ), patch.object(self.environment, "check_for_required_parameters"):
            result = self.runner.invoke(cmd_milestones.list, ["--offset", "50", "--limit", "100"], obj=self.environment)

            assert result.exit_code == 0
            mock_client.api_request_handler.milestone_handler.get_milestones.assert_called_once_with(
                project_id=1, limit=100, offset=50
            )
            assert mock_log.called

    @mock.patch("trcli.commands.cmd_milestones.ProjectBasedClient")
    def test_list_milestones_json_output(self, mock_project_client):
        """Test milestones listing with JSON output"""
        mock_client = self._setup_project_client_mock(mock_project_client)
        milestones_data = {
            "offset": 0,
            "limit": 250,
            "size": 1,
            "_links": {"next": None, "prev": None},
            "milestones": [
                {
                    "id": 1,
                    "name": "Release 1.5",
                    "is_completed": False,
                }
            ],
        }
        mock_client.api_request_handler.milestone_handler.get_milestones.return_value = (milestones_data, "")

        with patch.object(self.environment, "set_parameters"), patch.object(
            self.environment, "check_for_required_parameters"
        ):
            result = self.runner.invoke(cmd_milestones.list, ["--json-output"], obj=self.environment)

            assert result.exit_code == 0
            # Check for prettified JSON
            assert '"milestones"' in result.output
            assert "\n" in result.output

    @mock.patch("trcli.commands.cmd_milestones.ProjectBasedClient")
    def test_list_milestones_show_all_fields(self, mock_project_client):
        """Test milestones listing with show all fields"""
        mock_client = self._setup_project_client_mock(mock_project_client)
        mock_client.api_request_handler.milestone_handler.get_milestones.return_value = (
            {
                "offset": 0,
                "limit": 250,
                "size": 1,
                "_links": {"next": None, "prev": None},
                "milestones": [
                    {
                        "id": 1,
                        "name": "Release 1.5",
                        "description": "Major feature release",
                        "project_id": 1,
                        "is_completed": True,
                        "completed_on": 1389968184,
                        "due_on": 1391968184,
                        "refs": "RF-1, RF-2",
                        "url": "http://test.testrail.com/index.php?/milestones/view/1",
                    }
                ],
            },
            "",
        )

        with patch.object(self.environment, "log") as mock_log, patch.object(
            self.environment, "set_parameters"
        ), patch.object(self.environment, "check_for_required_parameters"):
            result = self.runner.invoke(cmd_milestones.list, ["--show-all-fields"], obj=self.environment)

            assert result.exit_code == 0
            assert mock_log.called

    @mock.patch("trcli.commands.cmd_milestones.ProjectBasedClient")
    def test_list_milestones_empty_result(self, mock_project_client):
        """Test milestones listing with no milestones"""
        mock_client = self._setup_project_client_mock(mock_project_client)
        mock_client.api_request_handler.milestone_handler.get_milestones.return_value = (
            {"offset": 0, "limit": 250, "size": 0, "_links": {"next": None, "prev": None}, "milestones": []},
            "",
        )

        with patch.object(self.environment, "log") as mock_log, patch.object(
            self.environment, "set_parameters"
        ), patch.object(self.environment, "check_for_required_parameters"):
            result = self.runner.invoke(cmd_milestones.list, [], obj=self.environment)

            assert result.exit_code == 0
            assert mock_log.called

    @mock.patch("trcli.commands.cmd_milestones.ProjectBasedClient")
    def test_list_milestones_api_error(self, mock_project_client):
        """Test milestones listing with API error"""
        mock_client = self._setup_project_client_mock(mock_project_client)
        mock_client.api_request_handler.milestone_handler.get_milestones.return_value = ({}, "Project not found")

        with patch.object(self.environment, "elog") as mock_elog, patch.object(
            self.environment, "set_parameters"
        ), patch.object(self.environment, "check_for_required_parameters"):
            result = self.runner.invoke(cmd_milestones.list, [], obj=self.environment)

            assert result.exit_code == 1
            mock_elog.assert_called_with("Error: Failed to retrieve milestones: Project not found")

    @mock.patch("trcli.commands.cmd_milestones.ProjectBasedClient")
    def test_list_milestones_with_next_link(self, mock_project_client):
        """Test milestones listing with pagination next link"""
        mock_client = self._setup_project_client_mock(mock_project_client)
        mock_client.api_request_handler.milestone_handler.get_milestones.return_value = (
            {
                "offset": 0,
                "limit": 250,
                "size": 251,
                "_links": {
                    "next": "index.php?/api/v2/get_milestones/1&offset=250",
                    "prev": None,
                },
                "milestones": [
                    {
                        "id": 1,
                        "name": "Release 1.5",
                        "is_completed": False,
                    }
                ],
            },
            "",
        )

        with patch.object(self.environment, "log") as mock_log, patch.object(
            self.environment, "set_parameters"
        ), patch.object(self.environment, "check_for_required_parameters"):
            result = self.runner.invoke(cmd_milestones.list, [], obj=self.environment)

            assert result.exit_code == 0
            assert mock_log.called

    @mock.patch("trcli.commands.cmd_milestones.ProjectBasedClient")
    def test_get_milestone_with_project_id_from_config(self, mock_project_client):
        """Test get milestone using project_id from configuration"""
        mock_client = self._setup_project_client_mock(mock_project_client, project_id=5)
        self.environment.project_id = 5
        mock_client.api_request_handler.milestone_handler.get_milestone.return_value = (
            {"id": 1, "name": "Release 1.0", "project_id": 5, "is_completed": False},
            "",
        )

        with patch.object(self.environment, "log"), patch.object(self.environment, "set_parameters"), patch.object(
            self.environment, "check_for_required_parameters"
        ):
            result = self.runner.invoke(cmd_milestones.get, ["--milestone-id", "1"], obj=self.environment)

            assert result.exit_code == 0

    @mock.patch("trcli.commands.cmd_milestones.ProjectBasedClient")
    def test_list_milestones_with_project_id_from_config(self, mock_project_client):
        """Test list milestones using project_id from configuration"""
        mock_client = self._setup_project_client_mock(mock_project_client, project_id=5)
        self.environment.project_id = 5
        mock_client.api_request_handler.milestone_handler.get_milestones.return_value = (
            {"offset": 0, "limit": 250, "size": 0, "_links": {}, "milestones": []},
            "",
        )

        with patch.object(self.environment, "log"), patch.object(self.environment, "set_parameters"), patch.object(
            self.environment, "check_for_required_parameters"
        ):
            result = self.runner.invoke(cmd_milestones.list, [], obj=self.environment)

            assert result.exit_code == 0
            mock_client.api_request_handler.milestone_handler.get_milestones.assert_called_once_with(
                project_id=5, limit=250, offset=0
            )

    @mock.patch("trcli.commands.cmd_milestones.ProjectBasedClient")
    def test_get_milestone_with_project_name(self, mock_project_client):
        """Test get milestone using project name resolution"""
        mock_client = self._setup_project_client_mock(mock_project_client)
        self.environment.project = "Test Project"
        mock_client.api_request_handler.milestone_handler.get_milestone.return_value = (
            {"id": 1, "name": "Release 1.0", "project_id": 1, "is_completed": False},
            "",
        )

        with patch.object(self.environment, "log"), patch.object(self.environment, "set_parameters"), patch.object(
            self.environment, "check_for_required_parameters"
        ):
            result = self.runner.invoke(cmd_milestones.get, ["--milestone-id", "1"], obj=self.environment)

            assert result.exit_code == 0
