import pytest
from unittest import mock
from unittest.mock import MagicMock, patch
from click.testing import CliRunner

from trcli.cli import Environment
from trcli.commands import cmd_sections


class TestCmdSections:
    """Test class for sections command functionality"""

    def setup_method(self):
        """Set up test environment"""
        self.runner = CliRunner()
        self.environment = Environment(cmd="sections")
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

    @mock.patch("trcli.commands.cmd_sections.ProjectBasedClient")
    def test_get_section_success(self, mock_project_client):
        """Test successful section retrieval"""
        mock_client = self._setup_project_client_mock(mock_project_client)
        mock_client.api_request_handler.section_handler.get_section.return_value = (
            {
                "depth": 0,
                "description": "Section for prerequisites",
                "display_order": 1,
                "id": 1,
                "name": "Prerequisites",
                "parent_id": None,
                "suite_id": 1,
            },
            "",
        )

        with patch.object(self.environment, "log") as mock_log, patch.object(
            self.environment, "set_parameters"
        ), patch.object(self.environment, "check_for_required_parameters"):
            result = self.runner.invoke(cmd_sections.get, ["--section-id", "1"], obj=self.environment)

            assert result.exit_code == 0
            mock_client.api_request_handler.section_handler.get_section.assert_called_once_with(1)
            assert mock_log.called

    @mock.patch("trcli.commands.cmd_sections.ProjectBasedClient")
    def test_get_section_json_output(self, mock_project_client):
        """Test section retrieval with JSON output"""
        mock_client = self._setup_project_client_mock(mock_project_client)
        section_data = {"id": 1, "name": "Test Section", "suite_id": 1, "depth": 0, "display_order": 1}
        mock_client.api_request_handler.section_handler.get_section.return_value = (section_data, "")

        with patch.object(self.environment, "set_parameters"), patch.object(
            self.environment, "check_for_required_parameters"
        ):
            result = self.runner.invoke(cmd_sections.get, ["--section-id", "1", "--json-output"], obj=self.environment)

            assert result.exit_code == 0
            # Check for prettified JSON (with newlines and indentation)
            assert '"id": 1' in result.output
            assert "\n" in result.output  # Prettified has newlines

    @mock.patch("trcli.commands.cmd_sections.ProjectBasedClient")
    def test_get_section_show_all_fields(self, mock_project_client):
        """Test section retrieval with show all fields"""
        mock_client = self._setup_project_client_mock(mock_project_client)
        mock_client.api_request_handler.section_handler.get_section.return_value = (
            {
                "id": 1,
                "name": "Test Section",
                "description": "Section description",
                "suite_id": 1,
                "depth": 0,
                "display_order": 1,
                "parent_id": None,
            },
            "",
        )

        with patch.object(self.environment, "log") as mock_log, patch.object(
            self.environment, "set_parameters"
        ), patch.object(self.environment, "check_for_required_parameters"):
            result = self.runner.invoke(
                cmd_sections.get,
                ["--section-id", "1", "--show-all-fields"],
                obj=self.environment,
            )

            assert result.exit_code == 0
            assert mock_log.called

    @mock.patch("trcli.commands.cmd_sections.ProjectBasedClient")
    def test_get_section_api_error(self, mock_project_client):
        """Test section retrieval with API error"""
        mock_client = self._setup_project_client_mock(mock_project_client)
        mock_client.api_request_handler.section_handler.get_section.return_value = ({}, "Section not found")

        with patch.object(self.environment, "elog") as mock_elog, patch.object(
            self.environment, "set_parameters"
        ), patch.object(self.environment, "check_for_required_parameters"):
            result = self.runner.invoke(cmd_sections.get, ["--section-id", "999"], obj=self.environment)

            assert result.exit_code == 1
            mock_elog.assert_called_with("Error: Failed to retrieve section: Section not found")

    @mock.patch("trcli.commands.cmd_sections.ProjectBasedClient")
    def test_list_sections_success(self, mock_project_client):
        """Test successful sections listing"""
        mock_client = self._setup_project_client_mock(mock_project_client)
        mock_client.api_request_handler.section_handler.get_sections.return_value = (
            {
                "offset": 0,
                "limit": 250,
                "size": 3,
                "_links": {"next": None, "prev": None},
                "sections": [
                    {
                        "depth": 0,
                        "display_order": 1,
                        "id": 1,
                        "name": "Prerequisites",
                        "parent_id": None,
                        "suite_id": 1,
                    },
                    {
                        "depth": 0,
                        "display_order": 2,
                        "id": 2,
                        "name": "Documentation & Help",
                        "parent_id": None,
                        "suite_id": 1,
                    },
                    {
                        "depth": 1,
                        "display_order": 3,
                        "id": 3,
                        "name": "Licensing & Terms",
                        "parent_id": 2,
                        "suite_id": 1,
                    },
                ],
            },
            "",
        )

        with patch.object(self.environment, "log") as mock_log, patch.object(
            self.environment, "set_parameters"
        ), patch.object(self.environment, "check_for_required_parameters"):
            result = self.runner.invoke(cmd_sections.list, ["--suite-id", "1"], obj=self.environment)

            assert result.exit_code == 0
            mock_client.api_request_handler.section_handler.get_sections.assert_called_once_with(
                project_id=1, suite_id=1, limit=250, offset=0
            )
            assert mock_log.called

    @mock.patch("trcli.commands.cmd_sections.ProjectBasedClient")
    def test_list_sections_with_pagination(self, mock_project_client):
        """Test sections listing with pagination parameters"""
        mock_client = self._setup_project_client_mock(mock_project_client)
        mock_client.api_request_handler.section_handler.get_sections.return_value = (
            {
                "offset": 100,
                "limit": 50,
                "size": 50,
                "_links": {
                    "next": "/api/v2/get_sections/1&suite_id=1&offset=150",
                    "prev": "/api/v2/get_sections/1&suite_id=1&offset=50",
                },
                "sections": [
                    {"id": i, "name": f"Section {i}", "suite_id": 1, "depth": 0, "display_order": i}
                    for i in range(100, 150)
                ],
            },
            "",
        )

        with patch.object(self.environment, "log") as mock_log, patch.object(
            self.environment, "set_parameters"
        ), patch.object(self.environment, "check_for_required_parameters"):
            result = self.runner.invoke(
                cmd_sections.list, ["--suite-id", "1", "--offset", "100", "--limit", "50"], obj=self.environment
            )

            assert result.exit_code == 0
            mock_client.api_request_handler.section_handler.get_sections.assert_called_once_with(
                project_id=1, suite_id=1, limit=50, offset=100
            )

    @mock.patch("trcli.commands.cmd_sections.ProjectBasedClient")
    def test_list_sections_json_output(self, mock_project_client):
        """Test sections listing with JSON output"""
        mock_client = self._setup_project_client_mock(mock_project_client)
        response_data = {
            "offset": 0,
            "limit": 250,
            "size": 1,
            "sections": [{"id": 1, "name": "Test", "suite_id": 1, "depth": 0}],
        }
        mock_client.api_request_handler.section_handler.get_sections.return_value = (response_data, "")

        with patch.object(self.environment, "set_parameters"), patch.object(
            self.environment, "check_for_required_parameters"
        ):
            result = self.runner.invoke(cmd_sections.list, ["--suite-id", "1", "--json-output"], obj=self.environment)

            assert result.exit_code == 0
            # Check for prettified JSON (with newlines and indentation)
            assert '"offset": 0' in result.output
            assert "\n" in result.output  # Prettified has newlines

    @mock.patch("trcli.commands.cmd_sections.ProjectBasedClient")
    def test_list_sections_show_all_fields(self, mock_project_client):
        """Test sections listing with show all fields"""
        mock_client = self._setup_project_client_mock(mock_project_client)
        mock_client.api_request_handler.section_handler.get_sections.return_value = (
            {
                "offset": 0,
                "limit": 250,
                "size": 1,
                "sections": [
                    {
                        "id": 1,
                        "name": "Test Section",
                        "description": "Description",
                        "suite_id": 1,
                        "depth": 0,
                        "display_order": 1,
                        "parent_id": None,
                    }
                ],
            },
            "",
        )

        with patch.object(self.environment, "log") as mock_log, patch.object(
            self.environment, "set_parameters"
        ), patch.object(self.environment, "check_for_required_parameters"):
            result = self.runner.invoke(
                cmd_sections.list, ["--suite-id", "1", "--show-all-fields"], obj=self.environment
            )

            assert result.exit_code == 0
            assert mock_log.called

    @mock.patch("trcli.commands.cmd_sections.ProjectBasedClient")
    def test_list_sections_empty_result(self, mock_project_client):
        """Test sections listing with empty result"""
        mock_client = self._setup_project_client_mock(mock_project_client)
        mock_client.api_request_handler.section_handler.get_sections.return_value = (
            {"offset": 0, "limit": 250, "size": 0, "sections": []},
            "",
        )

        with patch.object(self.environment, "log") as mock_log, patch.object(
            self.environment, "set_parameters"
        ), patch.object(self.environment, "check_for_required_parameters"):
            result = self.runner.invoke(cmd_sections.list, ["--suite-id", "1"], obj=self.environment)

            assert result.exit_code == 0
            mock_log.assert_any_call("No sections found.")

    @mock.patch("trcli.commands.cmd_sections.ProjectBasedClient")
    def test_list_sections_api_error(self, mock_project_client):
        """Test sections listing with API error"""
        mock_client = self._setup_project_client_mock(mock_project_client)
        mock_client.api_request_handler.section_handler.get_sections.return_value = ({}, "Suite not found")

        with patch.object(self.environment, "elog") as mock_elog, patch.object(
            self.environment, "set_parameters"
        ), patch.object(self.environment, "check_for_required_parameters"):
            result = self.runner.invoke(cmd_sections.list, ["--suite-id", "999"], obj=self.environment)

            assert result.exit_code == 1
            mock_elog.assert_called_with("Error: Failed to retrieve sections: Suite not found")

    @mock.patch("trcli.commands.cmd_sections.ProjectBasedClient")
    def test_list_sections_with_next_link(self, mock_project_client):
        """Test sections listing shows pagination hint when next link is present"""
        mock_client = self._setup_project_client_mock(mock_project_client)
        mock_client.api_request_handler.section_handler.get_sections.return_value = (
            {
                "offset": 0,
                "limit": 250,
                "size": 250,
                "_links": {"next": "/api/v2/get_sections/1&suite_id=1&offset=250", "prev": None},
                "sections": [
                    {"id": i, "name": f"Section {i}", "suite_id": 1, "depth": 0, "display_order": i}
                    for i in range(1, 251)
                ],
            },
            "",
        )

        with patch.object(self.environment, "log") as mock_log, patch.object(
            self.environment, "set_parameters"
        ), patch.object(self.environment, "check_for_required_parameters"):
            result = self.runner.invoke(cmd_sections.list, ["--suite-id", "1"], obj=self.environment)

            assert result.exit_code == 0
            log_calls = [str(call) for call in mock_log.call_args_list]
            pagination_hint_found = any("More results available" in str(call) for call in log_calls)
            assert pagination_hint_found

    @mock.patch("trcli.commands.cmd_sections.ProjectBasedClient")
    def test_get_section_with_project_id_from_config(self, mock_project_client):
        """Test section retrieval uses project_id from environment when not provided"""
        mock_client = self._setup_project_client_mock(mock_project_client, project_id=42)
        section_data = {"id": 1, "name": "Test Section", "suite_id": 1, "depth": 0, "display_order": 1}
        mock_client.api_request_handler.section_handler.get_section.return_value = (section_data, "")

        self.environment.project_id = 42

        with patch.object(self.environment, "log") as mock_log, patch.object(
            self.environment, "set_parameters"
        ), patch.object(self.environment, "check_for_required_parameters"):
            result = self.runner.invoke(cmd_sections.get, ["--section-id", "1"], obj=self.environment)

            assert result.exit_code == 0
            mock_client.api_request_handler.section_handler.get_section.assert_called_once_with(1)

    @mock.patch("trcli.commands.cmd_sections.ProjectBasedClient")
    def test_list_sections_with_project_id_from_config(self, mock_project_client):
        """Test sections listing uses project_id from environment when not provided"""
        mock_client = self._setup_project_client_mock(mock_project_client, project_id=99)
        mock_client.api_request_handler.section_handler.get_sections.return_value = (
            {"offset": 0, "limit": 250, "size": 1, "sections": [{"id": 1, "name": "Test", "suite_id": 1, "depth": 0}]},
            "",
        )

        self.environment.project_id = 99

        with patch.object(self.environment, "log") as mock_log, patch.object(
            self.environment, "set_parameters"
        ), patch.object(self.environment, "check_for_required_parameters"):
            result = self.runner.invoke(cmd_sections.list, ["--suite-id", "1"], obj=self.environment)

            assert result.exit_code == 0
            mock_client.api_request_handler.section_handler.get_sections.assert_called_once_with(
                project_id=99, suite_id=1, limit=250, offset=0
            )

    @mock.patch("trcli.commands.cmd_sections.ProjectBasedClient")
    def test_get_section_with_project_name(self, mock_project_client):
        """Test section retrieval with project name from config"""
        mock_client = self._setup_project_client_mock(mock_project_client, project_id=42)
        section_data = {"id": 1, "name": "Test Section", "suite_id": 1, "depth": 0, "display_order": 1}
        mock_client.api_request_handler.section_handler.get_section.return_value = (section_data, "")

        # Set project name in environment (as if from config file)
        self.environment.project = "TRCLI Test Project"
        self.environment.project_id = None  # No project_id, only name

        with patch.object(self.environment, "log") as mock_log, patch.object(
            self.environment, "set_parameters"
        ), patch.object(self.environment, "check_for_required_parameters"):
            result = self.runner.invoke(cmd_sections.get, ["--section-id", "1"], obj=self.environment)

            assert result.exit_code == 0
            # Verify resolve_project was called to convert name to ID
            mock_client.resolve_project.assert_called_once()
            mock_client.api_request_handler.section_handler.get_section.assert_called_once_with(1)

    @mock.patch("trcli.commands.cmd_sections.ProjectBasedClient")
    def test_list_sections_with_project_name(self, mock_project_client):
        """Test sections listing with project name from config"""
        mock_client = self._setup_project_client_mock(mock_project_client, project_id=99)
        mock_client.api_request_handler.section_handler.get_sections.return_value = (
            {"offset": 0, "limit": 250, "size": 1, "sections": [{"id": 1, "name": "Test", "suite_id": 1, "depth": 0}]},
            "",
        )

        # Set project name in environment (as if from config file)
        self.environment.project = "TRCLI Test Project"
        self.environment.project_id = None  # No project_id, only name

        with patch.object(self.environment, "log") as mock_log, patch.object(
            self.environment, "set_parameters"
        ), patch.object(self.environment, "check_for_required_parameters"):
            result = self.runner.invoke(cmd_sections.list, ["--suite-id", "1"], obj=self.environment)

            assert result.exit_code == 0
            # Verify resolve_project was called to convert name to ID
            mock_client.resolve_project.assert_called_once()
            mock_client.api_request_handler.section_handler.get_sections.assert_called_once_with(
                project_id=99, suite_id=1, limit=250, offset=0
            )
