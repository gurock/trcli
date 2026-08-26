import pytest
import json
from unittest import mock
from unittest.mock import MagicMock, patch
from click.testing import CliRunner

from trcli.cli import Environment
from trcli.commands import cmd_datasets


class TestCmdDatasets:
    """Test class for datasets command functionality"""

    def setup_method(self):
        """Set up test environment"""
        self.runner = CliRunner()
        self.environment = Environment(cmd="datasets")
        self.environment.host = "https://test.testrail.com"
        self.environment.username = "test@example.com"
        self.environment.password = "password"
        self.environment.api_key = None
        self.environment.project = "Test Project"

    def _setup_project_client_mock(self, mock_project_client):
        """Helper to setup ProjectBasedClient mock"""
        mock_client_instance = MagicMock()
        mock_project_client.return_value = mock_client_instance
        mock_client_instance.project.project_id = 1
        return mock_client_instance

    @mock.patch("trcli.commands.cmd_datasets.ProjectBasedClient")
    def test_list_datasets_success(self, mock_project_client):
        """Test successful datasets listing"""
        mock_client = self._setup_project_client_mock(mock_project_client)
        mock_client.api_request_handler.datasets_handler.get_datasets.return_value = (
            {
                "datasets": [
                    {
                        "id": 1,
                        "name": "Default",
                        "variables": [
                            {"name": "browser", "value": "Chrome"},
                            {"name": "version", "value": "120.0"},
                        ],
                    },
                    {
                        "id": 2,
                        "name": "Firefox_Dataset",
                        "variables": [],
                    },
                ],
                "offset": 0,
                "limit": 250,
                "size": 2,
                "_links": {},
            },
            "",
        )

        with patch.object(self.environment, "log") as mock_log, patch.object(
            self.environment, "set_parameters"
        ), patch.object(self.environment, "check_for_required_parameters"):
            result = self.runner.invoke(cmd_datasets.list, [], obj=self.environment)

            assert result.exit_code == 0
            mock_client.api_request_handler.datasets_handler.get_datasets.assert_called_once_with(
                project_id=1, limit=250, offset=0
            )
            assert mock_log.called

    @mock.patch("trcli.commands.cmd_datasets.ProjectBasedClient")
    def test_list_datasets_json_output(self, mock_project_client):
        """Test datasets listing with JSON output"""
        mock_client = self._setup_project_client_mock(mock_project_client)
        datasets_data = {
            "datasets": [{"id": 1, "name": "Default", "variables": []}],
            "offset": 0,
            "limit": 250,
            "size": 1,
            "_links": {},
        }
        mock_client.api_request_handler.datasets_handler.get_datasets.return_value = (datasets_data, "")

        with patch.object(self.environment, "log"), patch.object(self.environment, "set_parameters"), patch.object(
            self.environment, "check_for_required_parameters"
        ):
            result = self.runner.invoke(cmd_datasets.list, ["--json-output"], obj=self.environment)

            assert result.exit_code == 0
            # When --json-output is used, the output should be valid JSON printed to stdout
            # The runner captures this in result.output, but we need to skip log lines
            output_lines = result.output.strip().split("\n")
            # Find the JSON output (should be the last substantial output)
            json_output = None
            for line in output_lines:
                try:
                    json_output = json.loads(line)
                    break
                except json.JSONDecodeError:
                    continue

            # If JSON wasn't found in individual lines, try the whole output
            if json_output is None:
                # Try to extract JSON from mixed output
                import re

                json_match = re.search(r"\{.*\}", result.output, re.DOTALL)
                if json_match:
                    json_output = json.loads(json_match.group(0))

            assert json_output == datasets_data

    @mock.patch("trcli.commands.cmd_datasets.ProjectBasedClient")
    def test_show_dataset_success(self, mock_project_client):
        """Test showing a specific dataset"""
        mock_client = self._setup_project_client_mock(mock_project_client)
        dataset_data = {
            "id": 123,
            "name": "Chrome_Dataset",
            "variables": [
                {"name": "browser", "value": "Chrome"},
                {"name": "version", "value": "120.0"},
            ],
        }
        mock_client.api_request_handler.datasets_handler.get_dataset.return_value = (dataset_data, "")

        with patch.object(self.environment, "log") as mock_log, patch.object(
            self.environment, "set_parameters"
        ), patch.object(self.environment, "check_for_required_parameters"):
            result = self.runner.invoke(cmd_datasets.show, ["--dataset-id", "123"], obj=self.environment)

            assert result.exit_code == 0
            mock_client.api_request_handler.datasets_handler.get_dataset.assert_called_once_with(dataset_id=123)
            assert mock_log.called

    @mock.patch("trcli.commands.cmd_datasets.ProjectBasedClient")
    def test_add_dataset_with_variables(self, mock_project_client):
        """Test adding a dataset with variables"""
        mock_client = self._setup_project_client_mock(mock_project_client)
        created_dataset = {
            "id": 456,
            "name": "Chrome_Dataset",
            "variables": [
                {"name": "browser", "value": "Chrome"},
                {"name": "version", "value": "120.0"},
            ],
        }
        mock_client.api_request_handler.datasets_handler.add_dataset.return_value = (created_dataset, "")

        with patch.object(self.environment, "log") as mock_log, patch.object(
            self.environment, "set_parameters"
        ), patch.object(self.environment, "check_for_required_parameters"):
            result = self.runner.invoke(
                cmd_datasets.add,
                ["--name", "Chrome_Dataset", "--variables", '{"browser":"Chrome","version":"120.0"}'],
                obj=self.environment,
            )

            assert result.exit_code == 0
            mock_client.api_request_handler.datasets_handler.add_dataset.assert_called_once_with(
                project_id=1, name="Chrome_Dataset", variables={"browser": "Chrome", "version": "120.0"}
            )
            assert mock_log.called

    @mock.patch("trcli.commands.cmd_datasets.ProjectBasedClient")
    def test_add_dataset_without_variables(self, mock_project_client):
        """Test adding a dataset without variables (should send None)"""
        mock_client = self._setup_project_client_mock(mock_project_client)
        created_dataset = {"id": 456, "name": "Firefox_Dataset", "variables": []}
        mock_client.api_request_handler.datasets_handler.add_dataset.return_value = (created_dataset, "")

        with patch.object(self.environment, "log") as mock_log, patch.object(
            self.environment, "set_parameters"
        ), patch.object(self.environment, "check_for_required_parameters"):
            result = self.runner.invoke(cmd_datasets.add, ["--name", "Firefox_Dataset"], obj=self.environment)

            assert result.exit_code == 0
            mock_client.api_request_handler.datasets_handler.add_dataset.assert_called_once_with(
                project_id=1, name="Firefox_Dataset", variables=None
            )
            assert mock_log.called

    @mock.patch("trcli.commands.cmd_datasets.ProjectBasedClient")
    def test_add_dataset_with_empty_variables(self, mock_project_client):
        """Test adding a dataset with explicit empty variables object"""
        mock_client = self._setup_project_client_mock(mock_project_client)
        created_dataset = {"id": 456, "name": "Edge_Dataset", "variables": []}
        mock_client.api_request_handler.datasets_handler.add_dataset.return_value = (created_dataset, "")

        with patch.object(self.environment, "log") as mock_log, patch.object(
            self.environment, "set_parameters"
        ), patch.object(self.environment, "check_for_required_parameters"):
            result = self.runner.invoke(
                cmd_datasets.add, ["--name", "Edge_Dataset", "--variables", "{}"], obj=self.environment
            )

            assert result.exit_code == 0
            mock_client.api_request_handler.datasets_handler.add_dataset.assert_called_once_with(
                project_id=1, name="Edge_Dataset", variables={}
            )
            assert mock_log.called

    @mock.patch("trcli.commands.cmd_datasets.ProjectBasedClient")
    def test_add_dataset_invalid_json(self, mock_project_client):
        """Test adding a dataset with invalid JSON variables"""
        mock_client = self._setup_project_client_mock(mock_project_client)

        with patch.object(self.environment, "elog") as mock_elog, patch.object(
            self.environment, "set_parameters"
        ), patch.object(self.environment, "check_for_required_parameters"):
            result = self.runner.invoke(
                cmd_datasets.add, ["--name", "Test_Dataset", "--variables", "{invalid}"], obj=self.environment
            )

            assert result.exit_code == 1
            assert mock_elog.called

    @mock.patch("trcli.commands.cmd_datasets.ProjectBasedClient")
    def test_update_dataset_name_only(self, mock_project_client):
        """Test updating dataset name only (should send None for variables)"""
        mock_client = self._setup_project_client_mock(mock_project_client)
        updated_dataset = {
            "id": 123,
            "name": "Chrome_Latest",
            "variables": [{"name": "browser", "value": "Chrome"}],
        }
        mock_client.api_request_handler.datasets_handler.update_dataset.return_value = (updated_dataset, "")

        with patch.object(self.environment, "log") as mock_log, patch.object(
            self.environment, "set_parameters"
        ), patch.object(self.environment, "check_for_required_parameters"):
            result = self.runner.invoke(
                cmd_datasets.update, ["--dataset-id", "123", "--name", "Chrome_Latest"], obj=self.environment
            )

            assert result.exit_code == 0
            mock_client.api_request_handler.datasets_handler.update_dataset.assert_called_once_with(
                dataset_id=123, name="Chrome_Latest", variables=None
            )
            assert mock_log.called

    @mock.patch("trcli.commands.cmd_datasets.ProjectBasedClient")
    def test_update_dataset_variables_only(self, mock_project_client):
        """Test updating dataset variables only"""
        mock_client = self._setup_project_client_mock(mock_project_client)
        updated_dataset = {
            "id": 456,
            "name": "Chrome_Dataset",
            "variables": [
                {"name": "browser", "value": "Chrome"},
                {"name": "version", "value": "121.0"},
            ],
        }
        mock_client.api_request_handler.datasets_handler.update_dataset.return_value = (updated_dataset, "")

        with patch.object(self.environment, "log") as mock_log, patch.object(
            self.environment, "set_parameters"
        ), patch.object(self.environment, "check_for_required_parameters"):
            result = self.runner.invoke(
                cmd_datasets.update,
                ["--dataset-id", "456", "--variables", '{"browser":"Chrome","version":"121.0"}'],
                obj=self.environment,
            )

            assert result.exit_code == 0
            mock_client.api_request_handler.datasets_handler.update_dataset.assert_called_once_with(
                dataset_id=456, name=None, variables={"browser": "Chrome", "version": "121.0"}
            )
            assert mock_log.called

    @mock.patch("trcli.commands.cmd_datasets.ProjectBasedClient")
    def test_update_dataset_with_empty_variables(self, mock_project_client):
        """Test updating dataset with explicit empty variables (should preserve existing)"""
        mock_client = self._setup_project_client_mock(mock_project_client)
        updated_dataset = {
            "id": 123,
            "name": "Chrome_Latest",
            "variables": [{"name": "browser", "value": "Chrome"}],
        }
        mock_client.api_request_handler.datasets_handler.update_dataset.return_value = (updated_dataset, "")

        with patch.object(self.environment, "log") as mock_log, patch.object(
            self.environment, "set_parameters"
        ), patch.object(self.environment, "check_for_required_parameters"):
            result = self.runner.invoke(
                cmd_datasets.update,
                ["--dataset-id", "123", "--name", "Chrome_Latest", "--variables", "{}"],
                obj=self.environment,
            )

            assert result.exit_code == 0
            mock_client.api_request_handler.datasets_handler.update_dataset.assert_called_once_with(
                dataset_id=123, name="Chrome_Latest", variables={}
            )
            assert mock_log.called

    @mock.patch("trcli.commands.cmd_datasets.ProjectBasedClient")
    def test_update_dataset_both_fields(self, mock_project_client):
        """Test updating both dataset name and variables"""
        mock_client = self._setup_project_client_mock(mock_project_client)
        updated_dataset = {
            "id": 789,
            "name": "Production_Environment",
            "variables": [
                {"name": "api_url", "value": "https://api.prod.com"},
                {"name": "timeout", "value": "30"},
            ],
        }
        mock_client.api_request_handler.datasets_handler.update_dataset.return_value = (updated_dataset, "")

        with patch.object(self.environment, "log") as mock_log, patch.object(
            self.environment, "set_parameters"
        ), patch.object(self.environment, "check_for_required_parameters"):
            result = self.runner.invoke(
                cmd_datasets.update,
                [
                    "--dataset-id",
                    "789",
                    "--name",
                    "Production_Environment",
                    "--variables",
                    '{"api_url":"https://api.prod.com","timeout":"30"}',
                ],
                obj=self.environment,
            )

            assert result.exit_code == 0
            mock_client.api_request_handler.datasets_handler.update_dataset.assert_called_once_with(
                dataset_id=789,
                name="Production_Environment",
                variables={"api_url": "https://api.prod.com", "timeout": "30"},
            )
            assert mock_log.called

    @mock.patch("trcli.commands.cmd_datasets.ProjectBasedClient")
    def test_update_dataset_no_fields_provided(self, mock_project_client):
        """Test update with no fields provided (should fail)"""
        mock_client = self._setup_project_client_mock(mock_project_client)

        with patch.object(self.environment, "elog") as mock_elog, patch.object(
            self.environment, "set_parameters"
        ), patch.object(self.environment, "check_for_required_parameters"):
            result = self.runner.invoke(cmd_datasets.update, ["--dataset-id", "123"], obj=self.environment)

            assert result.exit_code == 1
            assert mock_elog.called

    @mock.patch("trcli.commands.cmd_datasets.ProjectBasedClient")
    def test_delete_dataset_success(self, mock_project_client):
        """Test deleting a dataset"""
        mock_client = self._setup_project_client_mock(mock_project_client)
        mock_client.api_request_handler.datasets_handler.delete_dataset.return_value = ({}, "")

        with patch.object(self.environment, "log") as mock_log, patch.object(
            self.environment, "set_parameters"
        ), patch.object(self.environment, "check_for_required_parameters"):
            result = self.runner.invoke(cmd_datasets.delete, ["--dataset-id", "123"], obj=self.environment)

            assert result.exit_code == 0
            mock_client.api_request_handler.datasets_handler.delete_dataset.assert_called_once_with(dataset_id=123)
            assert mock_log.called

    @mock.patch("trcli.commands.cmd_datasets.ProjectBasedClient")
    def test_add_dataset_api_error(self, mock_project_client):
        """Test adding a dataset when API returns error"""
        mock_client = self._setup_project_client_mock(mock_project_client)
        mock_client.api_request_handler.datasets_handler.add_dataset.return_value = ({}, "API Error occurred")

        with patch.object(self.environment, "elog") as mock_elog, patch.object(
            self.environment, "set_parameters"
        ), patch.object(self.environment, "check_for_required_parameters"):
            result = self.runner.invoke(cmd_datasets.add, ["--name", "Test_Dataset"], obj=self.environment)

            assert result.exit_code == 1
            assert mock_elog.called

    @mock.patch("trcli.commands.cmd_datasets.ProjectBasedClient")
    def test_update_dataset_api_error(self, mock_project_client):
        """Test updating a dataset when API returns error"""
        mock_client = self._setup_project_client_mock(mock_project_client)
        mock_client.api_request_handler.datasets_handler.update_dataset.return_value = ({}, "API Error occurred")

        with patch.object(self.environment, "elog") as mock_elog, patch.object(
            self.environment, "set_parameters"
        ), patch.object(self.environment, "check_for_required_parameters"):
            result = self.runner.invoke(
                cmd_datasets.update, ["--dataset-id", "123", "--name", "New_Name"], obj=self.environment
            )

            assert result.exit_code == 1
            assert mock_elog.called

    @mock.patch("trcli.commands.cmd_datasets.ProjectBasedClient")
    def test_delete_dataset_api_error(self, mock_project_client):
        """Test deleting a dataset when API returns error"""
        mock_client = self._setup_project_client_mock(mock_project_client)
        mock_client.api_request_handler.datasets_handler.delete_dataset.return_value = ({}, "API Error occurred")

        with patch.object(self.environment, "elog") as mock_elog, patch.object(
            self.environment, "set_parameters"
        ), patch.object(self.environment, "check_for_required_parameters"):
            result = self.runner.invoke(cmd_datasets.delete, ["--dataset-id", "123"], obj=self.environment)

            assert result.exit_code == 1
            assert mock_elog.called
