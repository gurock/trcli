import pytest
from unittest import mock
from unittest.mock import MagicMock, patch
from click.testing import CliRunner

from trcli.cli import Environment
from trcli.commands import cmd_casefields


class TestCmdCaseFields:
    """Test class for case-fields command functionality"""

    def setup_method(self):
        """Set up test environment"""
        self.runner = CliRunner()
        self.environment = Environment(cmd="casefields")
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

    @mock.patch("trcli.commands.cmd_casefields.ProjectBasedClient")
    def test_list_case_fields_success(self, mock_project_client):
        """Test successful case fields listing"""
        mock_client = self._setup_project_client_mock(mock_project_client)
        mock_client.api_request_handler.case_field_handler.get_case_fields.return_value = (
            [
                {
                    "id": 1,
                    "label": "Preconditions",
                    "name": "preconds",
                    "system_name": "custom_preconds",
                    "type_id": 3,
                    "is_active": True,
                    "description": "The preconditions of this test case.",
                    "display_order": 1,
                    "configs": [
                        {
                            "context": {"is_global": True, "project_ids": None},
                            "id": "config1",
                            "options": {
                                "default_value": "",
                                "format": "markdown",
                                "is_required": False,
                                "rows": "5",
                            },
                        }
                    ],
                },
                {
                    "id": 2,
                    "label": "Steps",
                    "name": "steps",
                    "system_name": "custom_steps",
                    "type_id": 10,
                    "is_active": True,
                    "description": "Test steps",
                    "display_order": 2,
                    "configs": [
                        {
                            "context": {"is_global": False, "project_ids": [1, 2]},
                            "id": "config2",
                            "options": {"is_required": True},
                        }
                    ],
                },
            ],
            "",
        )

        with patch.object(self.environment, "log") as mock_log, patch.object(
            self.environment, "set_parameters"
        ), patch.object(self.environment, "check_for_required_parameters"):
            result = self.runner.invoke(cmd_casefields.cli, [], obj=self.environment)

            assert result.exit_code == 0
            mock_client.api_request_handler.case_field_handler.get_case_fields.assert_called_once()
            assert mock_log.called

    @mock.patch("trcli.commands.cmd_casefields.ProjectBasedClient")
    def test_list_case_fields_json_output(self, mock_project_client):
        """Test case fields listing with JSON output"""
        mock_client = self._setup_project_client_mock(mock_project_client)
        case_fields_data = [
            {
                "id": 1,
                "label": "Preconditions",
                "name": "preconds",
                "system_name": "custom_preconds",
                "type_id": 3,
                "is_active": True,
                "configs": [{"context": {"is_global": True, "project_ids": None}}],
            },
        ]
        mock_client.api_request_handler.case_field_handler.get_case_fields.return_value = (case_fields_data, "")

        with patch.object(self.environment, "set_parameters"), patch.object(
            self.environment, "check_for_required_parameters"
        ):
            result = self.runner.invoke(cmd_casefields.cli, ["--json-output"], obj=self.environment)

            assert result.exit_code == 0
            assert '"id": 1' in result.output
            assert '"label": "Preconditions"' in result.output
            assert "\n" in result.output

    @mock.patch("trcli.commands.cmd_casefields.ProjectBasedClient")
    def test_list_case_fields_show_all_fields(self, mock_project_client):
        """Test case fields listing with show all fields"""
        mock_client = self._setup_project_client_mock(mock_project_client)
        mock_client.api_request_handler.case_field_handler.get_case_fields.return_value = (
            [
                {
                    "id": 1,
                    "label": "Preconditions",
                    "name": "preconds",
                    "system_name": "custom_preconds",
                    "type_id": 3,
                    "is_active": True,
                    "description": "The preconditions of this test case.",
                    "display_order": 1,
                    "configs": [
                        {
                            "context": {"is_global": True, "project_ids": None},
                            "id": "config1",
                            "options": {"is_required": False, "default_value": "None"},
                        }
                    ],
                }
            ],
            "",
        )

        with patch.object(self.environment, "log") as mock_log, patch.object(
            self.environment, "set_parameters"
        ), patch.object(self.environment, "check_for_required_parameters"):
            result = self.runner.invoke(cmd_casefields.cli, ["--show-all-fields"], obj=self.environment)

            assert result.exit_code == 0
            assert mock_log.called

    @mock.patch("trcli.commands.cmd_casefields.ProjectBasedClient")
    def test_list_case_fields_with_project_auto_filter(self, mock_project_client):
        """Test case fields auto-filtering when project is specified"""
        mock_client = self._setup_project_client_mock(mock_project_client, project_id=1)
        mock_client.api_request_handler.case_field_handler.get_case_fields.return_value = (
            [
                {
                    "id": 1,
                    "label": "Global Field",
                    "name": "global_field",
                    "system_name": "custom_global",
                    "type_id": 1,
                    "is_active": True,
                    "configs": [{"context": {"is_global": True, "project_ids": None}}],
                },
                {
                    "id": 2,
                    "label": "Project Field",
                    "name": "project_field",
                    "system_name": "custom_project",
                    "type_id": 1,
                    "is_active": True,
                    "configs": [{"context": {"is_global": False, "project_ids": [1, 2]}}],
                },
                {
                    "id": 3,
                    "label": "Other Project Field",
                    "name": "other_field",
                    "system_name": "custom_other",
                    "type_id": 1,
                    "is_active": True,
                    "configs": [{"context": {"is_global": False, "project_ids": [3, 4]}}],
                },
            ],
            "",
        )

        with patch.object(self.environment, "log") as mock_log, patch.object(
            self.environment, "set_parameters"
        ), patch.object(self.environment, "check_for_required_parameters"):
            # Project is already set in self.environment.project
            result = self.runner.invoke(cmd_casefields.cli, [], obj=self.environment)

            assert result.exit_code == 0
            # Should show only 2 fields (global and project 1)
            assert mock_log.called

    @mock.patch("trcli.commands.cmd_casefields.ProjectBasedClient")
    def test_list_case_fields_without_project_shows_all(self, mock_project_client):
        """Test case fields shows all fields when no project specified"""
        mock_client = self._setup_project_client_mock(mock_project_client)
        self.environment.project = None
        self.environment.project_id = None

        mock_client.api_request_handler.case_field_handler.get_case_fields.return_value = (
            [
                {
                    "id": 1,
                    "label": "Field 1",
                    "name": "field1",
                    "system_name": "custom_field1",
                    "type_id": 1,
                    "is_active": True,
                    "configs": [{"context": {"is_global": True, "project_ids": None}}],
                },
                {
                    "id": 2,
                    "label": "Field 2",
                    "name": "field2",
                    "system_name": "custom_field2",
                    "type_id": 1,
                    "is_active": True,
                    "configs": [{"context": {"is_global": False, "project_ids": [1]}}],
                },
            ],
            "",
        )

        with patch.object(self.environment, "log") as mock_log, patch.object(
            self.environment, "set_parameters"
        ), patch.object(self.environment, "check_for_required_parameters"):
            result = self.runner.invoke(cmd_casefields.cli, [], obj=self.environment)

            assert result.exit_code == 0
            # Should show all fields (no filtering)
            assert mock_log.called

    @mock.patch("trcli.commands.cmd_casefields.ProjectBasedClient")
    def test_list_case_fields_empty_result(self, mock_project_client):
        """Test case fields listing with no fields"""
        mock_client = self._setup_project_client_mock(mock_project_client)
        mock_client.api_request_handler.case_field_handler.get_case_fields.return_value = ([], "")

        with patch.object(self.environment, "log") as mock_log, patch.object(
            self.environment, "set_parameters"
        ), patch.object(self.environment, "check_for_required_parameters"):
            result = self.runner.invoke(cmd_casefields.cli, [], obj=self.environment)

            assert result.exit_code == 0
            assert mock_log.called

    @mock.patch("trcli.commands.cmd_casefields.ProjectBasedClient")
    def test_list_case_fields_api_error(self, mock_project_client):
        """Test case fields listing with API error"""
        mock_client = self._setup_project_client_mock(mock_project_client)
        mock_client.api_request_handler.case_field_handler.get_case_fields.return_value = (
            [],
            "API connection failed",
        )

        with patch.object(self.environment, "elog") as mock_elog, patch.object(
            self.environment, "set_parameters"
        ), patch.object(self.environment, "check_for_required_parameters"):
            result = self.runner.invoke(cmd_casefields.cli, [], obj=self.environment)

            assert result.exit_code == 1
            mock_elog.assert_called_with("Error: Failed to retrieve case fields: API connection failed")

    @mock.patch("trcli.commands.cmd_casefields.ProjectBasedClient")
    def test_list_case_fields_all_type_ids(self, mock_project_client):
        """Test case fields with all different type IDs"""
        mock_client = self._setup_project_client_mock(mock_project_client)
        mock_client.api_request_handler.case_field_handler.get_case_fields.return_value = (
            [
                {
                    "id": 1,
                    "label": "String Field",
                    "name": "string_field",
                    "system_name": "custom_string",
                    "type_id": 1,
                    "is_active": True,
                    "configs": [{"context": {"is_global": True, "project_ids": None}}],
                },
                {
                    "id": 2,
                    "label": "Dropdown Field",
                    "name": "dropdown_field",
                    "system_name": "custom_dropdown",
                    "type_id": 6,
                    "is_active": True,
                    "configs": [{"context": {"is_global": True, "project_ids": None}}],
                },
                {
                    "id": 3,
                    "label": "Unknown Field",
                    "name": "unknown_field",
                    "system_name": "custom_unknown",
                    "type_id": 99,
                    "is_active": False,
                    "configs": [{"context": {"is_global": True, "project_ids": None}}],
                },
            ],
            "",
        )

        with patch.object(self.environment, "log") as mock_log, patch.object(
            self.environment, "set_parameters"
        ), patch.object(self.environment, "check_for_required_parameters"):
            result = self.runner.invoke(cmd_casefields.cli, [], obj=self.environment)

            assert result.exit_code == 0
            assert mock_log.called

    @mock.patch("trcli.commands.cmd_casefields.ProjectBasedClient")
    def test_list_case_fields_long_description_truncation(self, mock_project_client):
        """Test that long descriptions are truncated in show-all-fields mode"""
        mock_client = self._setup_project_client_mock(mock_project_client)
        long_description = "A" * 150  # 150 character description
        mock_client.api_request_handler.case_field_handler.get_case_fields.return_value = (
            [
                {
                    "id": 1,
                    "label": "Field",
                    "name": "field",
                    "system_name": "custom_field",
                    "type_id": 1,
                    "is_active": True,
                    "description": long_description,
                    "configs": [{"context": {"is_global": True, "project_ids": None}}],
                }
            ],
            "",
        )

        with patch.object(self.environment, "log") as mock_log, patch.object(
            self.environment, "set_parameters"
        ), patch.object(self.environment, "check_for_required_parameters"):
            result = self.runner.invoke(cmd_casefields.cli, ["--show-all-fields"], obj=self.environment)

            assert result.exit_code == 0
            assert mock_log.called
