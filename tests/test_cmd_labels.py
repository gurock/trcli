import pytest
from unittest import mock
from unittest.mock import MagicMock, patch
from click.testing import CliRunner

from trcli.cli import Environment
from trcli.commands import cmd_labels
from trcli.data_classes.dataclass_testrail import TestRailSuite
from trcli.api.project_based_client import ProjectBasedClient


class TestCmdLabels:
    """Test class for labels command functionality"""

    def setup_method(self):
        """Set up test environment"""
        self.runner = CliRunner()
        self.environment = Environment(cmd="labels")
        self.environment.host = "https://test.testrail.com"
        self.environment.username = "test@example.com"
        self.environment.password = "password"
        self.environment.project = "Test Project"
        self.environment.project_id = 1

    @mock.patch('trcli.commands.cmd_labels.ProjectBasedClient')
    def test_add_label_success(self, mock_project_client):
        """Test successful label addition"""
        # Mock the project client and its methods
        mock_client_instance = MagicMock()
        mock_project_client.return_value = mock_client_instance
        mock_client_instance.project.project_id = 1
        mock_client_instance.api_request_handler.add_label.return_value = (
            {"label": {"id": 1, "title": "Test Label"}}, None
        )

        # Mock environment methods
        with patch.object(self.environment, 'log') as mock_log, \
             patch.object(self.environment, 'set_parameters'), \
             patch.object(self.environment, 'check_for_required_parameters'):
            
            result = self.runner.invoke(cmd_labels.add, ['--title', 'Test Label'], 
                                       obj=self.environment)
            
            assert result.exit_code == 0
            mock_client_instance.api_request_handler.add_label.assert_called_once_with(
                project_id=1, title='Test Label'
            )
            mock_log.assert_any_call("Successfully added label: ID=1, Title='Test Label'")

    @mock.patch('trcli.commands.cmd_labels.ProjectBasedClient')
    def test_add_label_title_too_long(self, mock_project_client):
        """Test label addition with title too long"""
        long_title = "a" * 21  # 21 characters, exceeds 20 char limit
        
        with patch.object(self.environment, 'elog') as mock_elog, \
             patch.object(self.environment, 'set_parameters'), \
             patch.object(self.environment, 'check_for_required_parameters'):
            
            result = self.runner.invoke(cmd_labels.add, ['--title', long_title], 
                                       obj=self.environment)
            
            assert result.exit_code == 1
            mock_elog.assert_called_with("Error: Label title must be 20 characters or less.")

    @mock.patch('trcli.commands.cmd_labels.ProjectBasedClient')
    def test_add_label_api_error(self, mock_project_client):
        """Test label addition with API error"""
        mock_client_instance = MagicMock()
        mock_project_client.return_value = mock_client_instance
        mock_client_instance.project.project_id = 1
        mock_client_instance.api_request_handler.add_label.return_value = (
            None, "API Error: Label already exists"
        )

        with patch.object(self.environment, 'elog') as mock_elog, \
             patch.object(self.environment, 'set_parameters'), \
             patch.object(self.environment, 'check_for_required_parameters'):
            
            result = self.runner.invoke(cmd_labels.add, ['--title', 'Test Label'], 
                                       obj=self.environment)
            
            assert result.exit_code == 1
            mock_elog.assert_called_with("Failed to add label: API Error: Label already exists")

    @mock.patch('trcli.commands.cmd_labels.ProjectBasedClient')
    def test_update_label_success(self, mock_project_client):
        """Test successful label update"""
        mock_client_instance = MagicMock()
        mock_project_client.return_value = mock_client_instance
        mock_client_instance.project.project_id = 1
        mock_client_instance.api_request_handler.update_label.return_value = (
            {"id": 1, "title": "Updated Label"}, None
        )

        with patch.object(self.environment, 'log') as mock_log, \
             patch.object(self.environment, 'set_parameters'), \
             patch.object(self.environment, 'check_for_required_parameters'):
            
            result = self.runner.invoke(cmd_labels.update, ['--id', '1', '--title', 'Updated Label'], 
                                       obj=self.environment)
            
            assert result.exit_code == 0
            mock_client_instance.api_request_handler.update_label.assert_called_once_with(
                label_id=1, project_id=1, title='Updated Label'
            )
            mock_log.assert_any_call("Successfully updated label: ID=1, Title='Updated Label'")

    @mock.patch('trcli.commands.cmd_labels.ProjectBasedClient')
    def test_update_label_title_too_long(self, mock_project_client):
        """Test label update with title too long"""
        long_title = "a" * 21  # 21 characters, exceeds 20 char limit
        
        with patch.object(self.environment, 'elog') as mock_elog, \
             patch.object(self.environment, 'set_parameters'), \
             patch.object(self.environment, 'check_for_required_parameters'):
            
            result = self.runner.invoke(cmd_labels.update, ['--id', '1', '--title', long_title], 
                                       obj=self.environment)
            
            assert result.exit_code == 1
            mock_elog.assert_called_with("Error: Label title must be 20 characters or less.")

    @mock.patch('trcli.commands.cmd_labels.ProjectBasedClient')
    def test_delete_labels_success(self, mock_project_client):
        """Test successful label deletion"""
        mock_client_instance = MagicMock()
        mock_project_client.return_value = mock_client_instance
        mock_client_instance.api_request_handler.delete_labels.return_value = (True, None)

        with patch.object(self.environment, 'log') as mock_log, \
             patch.object(self.environment, 'set_parameters'), \
             patch.object(self.environment, 'check_for_required_parameters'):
            
            # Use input to automatically confirm deletion
            result = self.runner.invoke(cmd_labels.delete, ['--ids', '1,2,3'], 
                                       obj=self.environment, input='y\n')
            
            assert result.exit_code == 0
            mock_client_instance.api_request_handler.delete_labels.assert_called_once_with([1, 2, 3])
            mock_log.assert_any_call("Successfully deleted 3 label(s)")

    @mock.patch('trcli.commands.cmd_labels.ProjectBasedClient')
    def test_delete_single_label_success(self, mock_project_client):
        """Test successful single label deletion"""
        mock_client_instance = MagicMock()
        mock_project_client.return_value = mock_client_instance
        mock_client_instance.api_request_handler.delete_label.return_value = (True, None)

        with patch.object(self.environment, 'log') as mock_log, \
             patch.object(self.environment, 'set_parameters'), \
             patch.object(self.environment, 'check_for_required_parameters'):
            
            # Use input to automatically confirm deletion
            result = self.runner.invoke(cmd_labels.delete, ['--ids', '1'], 
                                       obj=self.environment, input='y\n')
            
            assert result.exit_code == 0
            mock_client_instance.api_request_handler.delete_label.assert_called_once_with(1)
            mock_log.assert_any_call("Successfully deleted 1 label(s)")

    @mock.patch('trcli.commands.cmd_labels.ProjectBasedClient')
    def test_delete_labels_invalid_format(self, mock_project_client):
        """Test label deletion with invalid ID format"""
        with patch.object(self.environment, 'elog') as mock_elog, \
             patch.object(self.environment, 'set_parameters'), \
             patch.object(self.environment, 'check_for_required_parameters'):
            
            result = self.runner.invoke(cmd_labels.delete, ['--ids', '1,abc,3'], 
                                       obj=self.environment, input='y\n')
            
            assert result.exit_code == 1
            mock_elog.assert_called_with("Error: Invalid label IDs format. Use comma-separated integers (e.g., 1,2,3).")

    @mock.patch('trcli.commands.cmd_labels.ProjectBasedClient')
    def test_delete_single_label_api_error(self, mock_project_client):
        """Test single label deletion with API error"""
        mock_client_instance = MagicMock()
        mock_project_client.return_value = mock_client_instance
        # Mock the single delete method since we're testing with a single ID
        mock_client_instance.api_request_handler.delete_label.return_value = (
            False, "API Error: Label not found"
        )

        with patch.object(self.environment, 'elog') as mock_elog, \
             patch.object(self.environment, 'set_parameters'), \
             patch.object(self.environment, 'check_for_required_parameters'):
            
            result = self.runner.invoke(cmd_labels.delete, ['--ids', '1'], 
                                       obj=self.environment, input='y\n')
            
            assert result.exit_code == 1
            mock_elog.assert_called_with("Failed to delete labels: API Error: Label not found")

    @mock.patch('trcli.commands.cmd_labels.ProjectBasedClient')
    def test_delete_batch_labels_api_error(self, mock_project_client):
        """Test batch label deletion with API error"""
        mock_client_instance = MagicMock()
        mock_project_client.return_value = mock_client_instance
        # Mock the batch delete method since we're testing with multiple IDs
        mock_client_instance.api_request_handler.delete_labels.return_value = (
            False, "API Error: Insufficient permissions"
        )

        with patch.object(self.environment, 'elog') as mock_elog, \
             patch.object(self.environment, 'set_parameters'), \
             patch.object(self.environment, 'check_for_required_parameters'):
            
            result = self.runner.invoke(cmd_labels.delete, ['--ids', '1,2,3'], 
                                       obj=self.environment, input='y\n')
            
            assert result.exit_code == 1
            mock_elog.assert_called_with("Failed to delete labels: API Error: Insufficient permissions")

    @mock.patch('trcli.commands.cmd_labels.ProjectBasedClient')
    def test_list_labels_success(self, mock_project_client):
        """Test successful labels listing"""
        mock_client_instance = MagicMock()
        mock_project_client.return_value = mock_client_instance
        mock_client_instance.project.project_id = 1
        
        labels_response = {
            "offset": 0,
            "limit": 250,
            "size": 2,
            "labels": [
                {"id": 1, "title": "Label 1", "created_by": "2"},
                {"id": 2, "title": "Label 2", "created_by": "3"}
            ]
        }
        mock_client_instance.api_request_handler.get_labels.return_value = (labels_response, None)

        with patch.object(self.environment, 'log') as mock_log, \
             patch.object(self.environment, 'set_parameters'), \
             patch.object(self.environment, 'check_for_required_parameters'):
            
            result = self.runner.invoke(cmd_labels.list, [], obj=self.environment)
            
            assert result.exit_code == 0
            mock_client_instance.api_request_handler.get_labels.assert_called_once_with(
                project_id=1, offset=0, limit=250
            )
            mock_log.assert_any_call("Found 2 labels (showing 1-2 of 2):")
            mock_log.assert_any_call("  ID: 1, Title: 'Label 1', Created by: 2")
            mock_log.assert_any_call("  ID: 2, Title: 'Label 2', Created by: 3")

    @mock.patch('trcli.commands.cmd_labels.ProjectBasedClient')
    def test_list_labels_with_pagination(self, mock_project_client):
        """Test labels listing with custom pagination"""
        mock_client_instance = MagicMock()
        mock_project_client.return_value = mock_client_instance
        mock_client_instance.project.project_id = 1
        
        labels_response = {"offset": 10, "limit": 5, "size": 1, "labels": []}
        mock_client_instance.api_request_handler.get_labels.return_value = (labels_response, None)

        with patch.object(self.environment, 'log') as mock_log, \
             patch.object(self.environment, 'set_parameters'), \
             patch.object(self.environment, 'check_for_required_parameters'):
            
            result = self.runner.invoke(cmd_labels.list, ['--offset', '10', '--limit', '5'], 
                                       obj=self.environment)
            
            assert result.exit_code == 0
            mock_client_instance.api_request_handler.get_labels.assert_called_once_with(
                project_id=1, offset=10, limit=5
            )
            mock_log.assert_any_call("  No labels found.")

    @mock.patch('trcli.commands.cmd_labels.ProjectBasedClient')
    def test_get_label_success(self, mock_project_client):
        """Test successful single label retrieval"""
        mock_client_instance = MagicMock()
        mock_project_client.return_value = mock_client_instance
        
        label_response = {
            "id": 1,
            "title": "Test Label",
            "created_by": "2",
            "created_on": "1234567890"
        }
        mock_client_instance.api_request_handler.get_label.return_value = (label_response, None)

        with patch.object(self.environment, 'log') as mock_log, \
             patch.object(self.environment, 'set_parameters'), \
             patch.object(self.environment, 'check_for_required_parameters'):
            
            result = self.runner.invoke(cmd_labels.get, ['--id', '1'], obj=self.environment)
            
            assert result.exit_code == 0
            mock_client_instance.api_request_handler.get_label.assert_called_once_with(1)
            mock_log.assert_any_call("  ID: 1")
            mock_log.assert_any_call("  Title: 'Test Label'")
            mock_log.assert_any_call("  Created by: 2")
            mock_log.assert_any_call("  Created on: 1234567890")

    @mock.patch('trcli.commands.cmd_labels.ProjectBasedClient')
    def test_get_label_with_name_field(self, mock_project_client):
        """Test single label retrieval with 'name' field instead of 'title'"""
        mock_client_instance = MagicMock()
        mock_project_client.return_value = mock_client_instance
        
        # Some responses might use 'name' instead of 'title'
        label_response = {
            "id": 1,
            "name": "Test Label",
            "created_by": "2",
            "created_on": "1234567890"
        }
        mock_client_instance.api_request_handler.get_label.return_value = (label_response, None)

        with patch.object(self.environment, 'log') as mock_log, \
             patch.object(self.environment, 'set_parameters'), \
             patch.object(self.environment, 'check_for_required_parameters'):
            
            result = self.runner.invoke(cmd_labels.get, ['--id', '1'], obj=self.environment)
            
            assert result.exit_code == 0
            mock_log.assert_any_call("  Title: 'Test Label'")

    @mock.patch('trcli.commands.cmd_labels.ProjectBasedClient')
    def test_get_label_api_error(self, mock_project_client):
        """Test single label retrieval with API error"""
        mock_client_instance = MagicMock()
        mock_project_client.return_value = mock_client_instance
        mock_client_instance.api_request_handler.get_label.return_value = (
            None, "API Error: Label not found"
        )

        with patch.object(self.environment, 'elog') as mock_elog, \
             patch.object(self.environment, 'set_parameters'), \
             patch.object(self.environment, 'check_for_required_parameters'):
            
            result = self.runner.invoke(cmd_labels.get, ['--id', '999'], obj=self.environment)
            
            assert result.exit_code == 1
            mock_elog.assert_called_with("Failed to retrieve label: API Error: Label not found")

    def test_print_config(self):
        """Test the print_config function"""
        with patch.object(self.environment, 'log') as mock_log:
            cmd_labels.print_config(self.environment, "Test")
            
            expected_message = (
                "Labels Test Execution Parameters"
                "\n> TestRail instance: https://test.testrail.com (user: test@example.com)"
                "\n> Project: Test Project"
            )
            mock_log.assert_called_once_with(expected_message) 