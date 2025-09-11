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


class TestLabelsCasesCommands:
    """Test cases for test case label CLI commands"""
    
    def setup_method(self):
        """Set up test fixtures"""
        self.runner = CliRunner()
        self.environment = Environment()
        
    @mock.patch('trcli.commands.cmd_labels.ProjectBasedClient')
    def test_add_labels_to_cases_success(self, mock_project_client):
        """Test successful addition of labels to test cases"""
        mock_client_instance = MagicMock()
        mock_project_client.return_value = mock_client_instance
        mock_client_instance.project.project_id = 1
        mock_client_instance.suite.suite_id = None
        mock_client_instance.api_request_handler.add_labels_to_cases.return_value = (
            {
                'successful_cases': [
                    {'case_id': 1, 'message': "Successfully added label 'test-label' to case 1"},
                    {'case_id': 2, 'message': "Successfully added label 'test-label' to case 2"}
                ],
                'failed_cases': [],
                'max_labels_reached': [],
                'case_not_found': []
            },
            ""
        )
        
        with patch.object(self.environment, 'log') as mock_log, \
             patch.object(self.environment, 'set_parameters'), \
             patch.object(self.environment, 'check_for_required_parameters'):
            
            result = self.runner.invoke(
                cmd_labels.cases, 
                ['add', '--case-ids', '1,2', '--title', 'test-label'], 
                obj=self.environment
            )
            
            assert result.exit_code == 0
            mock_client_instance.api_request_handler.add_labels_to_cases.assert_called_once_with(
                case_ids=[1, 2],
                title='test-label',
                project_id=1,
                suite_id=None
            )
            
            # Verify success messages were logged
            mock_log.assert_any_call("Successfully processed 2 case(s):")
            mock_log.assert_any_call("  Case 1: Successfully added label 'test-label' to case 1")
            mock_log.assert_any_call("  Case 2: Successfully added label 'test-label' to case 2")
    
    @mock.patch('trcli.commands.cmd_labels.ProjectBasedClient')
    def test_add_labels_to_cases_with_max_labels_reached(self, mock_project_client):
        """Test addition of labels with some cases reaching maximum labels"""
        mock_client_instance = MagicMock()
        mock_project_client.return_value = mock_client_instance
        mock_client_instance.project.project_id = 1
        mock_client_instance.api_request_handler.add_labels_to_cases.return_value = (
            {
                'successful_cases': [
                    {'case_id': 1, 'message': "Successfully added label 'test-label' to case 1"}
                ],
                'failed_cases': [],
                'max_labels_reached': [2, 3],
                'case_not_found': []
            },
            ""
        )
        
        with patch.object(self.environment, 'log') as mock_log, \
             patch.object(self.environment, 'set_parameters'), \
             patch.object(self.environment, 'check_for_required_parameters'):
            
            result = self.runner.invoke(
                cmd_labels.cases, 
                ['add', '--case-ids', '1,2,3', '--title', 'test-label'], 
                obj=self.environment
            )
            
            assert result.exit_code == 0
            
            # Verify warning messages were logged
            mock_log.assert_any_call("Warning: 2 case(s) already have maximum labels (10):")
            mock_log.assert_any_call("  Case 2: Maximum labels reached")
            mock_log.assert_any_call("  Case 3: Maximum labels reached")
    
    @mock.patch('trcli.commands.cmd_labels.ProjectBasedClient')
    def test_add_labels_to_cases_title_too_long(self, mock_project_client):
        """Test title length validation"""
        with patch.object(self.environment, 'elog') as mock_elog, \
             patch.object(self.environment, 'set_parameters'), \
             patch.object(self.environment, 'check_for_required_parameters'):
            
            result = self.runner.invoke(
                cmd_labels.cases, 
                ['add', '--case-ids', '1', '--title', 'this-title-is-way-too-long-for-testrail'], 
                obj=self.environment
            )
            
            assert result.exit_code == 1
            mock_elog.assert_called_with("Error: Label title must be 20 characters or less.")
    
    @mock.patch('trcli.commands.cmd_labels.ProjectBasedClient')
    def test_add_labels_to_cases_invalid_case_ids(self, mock_project_client):
        """Test invalid case IDs format"""
        with patch.object(self.environment, 'elog') as mock_elog, \
             patch.object(self.environment, 'set_parameters'), \
             patch.object(self.environment, 'check_for_required_parameters'):
            
            result = self.runner.invoke(
                cmd_labels.cases, 
                ['add', '--case-ids', 'invalid,ids', '--title', 'test-label'], 
                obj=self.environment
            )
            
            assert result.exit_code == 1
            mock_elog.assert_called_with("Error: Invalid case IDs format. Use comma-separated integers (e.g., 1,2,3).")
    
    @mock.patch('trcli.commands.cmd_labels.ProjectBasedClient')
    def test_add_labels_to_cases_case_not_found(self, mock_project_client):
        """Test handling of non-existent case IDs"""
        mock_client_instance = MagicMock()
        mock_project_client.return_value = mock_client_instance
        mock_client_instance.project.project_id = 1
        mock_client_instance.api_request_handler.add_labels_to_cases.return_value = (
            {
                'successful_cases': [
                    {'case_id': 1, 'message': "Successfully added label 'test-label' to case 1"}
                ],
                'failed_cases': [],
                'max_labels_reached': [],
                'case_not_found': [999, 1000]
            },
            ""
        )
        
        with patch.object(self.environment, 'log') as mock_log, \
             patch.object(self.environment, 'elog') as mock_elog, \
             patch.object(self.environment, 'set_parameters'), \
             patch.object(self.environment, 'check_for_required_parameters'):
            
            result = self.runner.invoke(
                cmd_labels.cases, 
                ['add', '--case-ids', '1,999,1000', '--title', 'test-label'], 
                obj=self.environment
            )
            
            assert result.exit_code == 1
            
            # Verify error messages were logged
            mock_elog.assert_any_call("Error: 2 test case(s) not found:")
            mock_elog.assert_any_call("  Case ID 999 does not exist in the project")
            mock_elog.assert_any_call("  Case ID 1000 does not exist in the project")
            
            # Verify success messages were still logged
            mock_log.assert_any_call("Successfully processed 1 case(s):")
    
    @mock.patch('trcli.commands.cmd_labels.ProjectBasedClient')
    def test_list_cases_by_label_ids_success(self, mock_project_client):
        """Test successful listing of cases by label IDs"""
        mock_client_instance = MagicMock()
        mock_project_client.return_value = mock_client_instance
        mock_client_instance.project.project_id = 1
        mock_client_instance.suite = None
        mock_client_instance.api_request_handler.get_cases_by_label.return_value = (
            [
                {
                    'id': 1, 
                    'title': 'Test Case 1', 
                    'labels': [{'id': 5, 'title': 'test-label'}]
                },
                {
                    'id': 2, 
                    'title': 'Test Case 2', 
                    'labels': [{'id': 5, 'title': 'test-label'}, {'id': 6, 'title': 'other-label'}]
                }
            ],
            ""
        )
        
        with patch.object(self.environment, 'log') as mock_log, \
             patch.object(self.environment, 'set_parameters'), \
             patch.object(self.environment, 'check_for_required_parameters'):
            
            result = self.runner.invoke(
                cmd_labels.cases, 
                ['list', '--ids', '5'], 
                obj=self.environment
            )
            
            assert result.exit_code == 0
            mock_client_instance.api_request_handler.get_cases_by_label.assert_called_once_with(
                project_id=1,
                suite_id=None,
                label_ids=[5],
                label_title=None
            )
            
            # Verify cases were logged
            mock_log.assert_any_call("Found 2 matching test case(s):")
            mock_log.assert_any_call("  Case ID: 1, Title: 'Test Case 1' [Labels: ID:5,Title:'test-label']")
            mock_log.assert_any_call("  Case ID: 2, Title: 'Test Case 2' [Labels: ID:5,Title:'test-label'; ID:6,Title:'other-label']")
    
    @mock.patch('trcli.commands.cmd_labels.ProjectBasedClient')
    def test_list_cases_by_label_title_success(self, mock_project_client):
        """Test successful listing of cases by label title"""
        mock_client_instance = MagicMock()
        mock_project_client.return_value = mock_client_instance
        mock_client_instance.project.project_id = 1
        mock_client_instance.suite = None
        mock_client_instance.api_request_handler.get_cases_by_label.return_value = (
            [
                {
                    'id': 1, 
                    'title': 'Test Case 1', 
                    'labels': [{'id': 5, 'title': 'test-label'}]
                }
            ],
            ""
        )
        
        with patch.object(self.environment, 'log') as mock_log, \
             patch.object(self.environment, 'set_parameters'), \
             patch.object(self.environment, 'check_for_required_parameters'):
            
            result = self.runner.invoke(
                cmd_labels.cases, 
                ['list', '--title', 'test-label'], 
                obj=self.environment
            )
            
            assert result.exit_code == 0
            mock_client_instance.api_request_handler.get_cases_by_label.assert_called_once_with(
                project_id=1,
                suite_id=None,
                label_ids=None,
                label_title='test-label'
            )
    
    @mock.patch('trcli.commands.cmd_labels.ProjectBasedClient')
    def test_list_cases_no_filter_provided(self, mock_project_client):
        """Test error when neither ids nor title is provided"""
        with patch.object(self.environment, 'elog') as mock_elog, \
             patch.object(self.environment, 'set_parameters'), \
             patch.object(self.environment, 'check_for_required_parameters'):
            
            result = self.runner.invoke(
                cmd_labels.cases, 
                ['list'], 
                obj=self.environment
            )
            
            assert result.exit_code == 1
            mock_elog.assert_called_with("Error: Either --ids or --title must be provided.")
    
    @mock.patch('trcli.commands.cmd_labels.ProjectBasedClient')
    def test_list_cases_no_matching_cases(self, mock_project_client):
        """Test listing when no cases match the label"""
        mock_client_instance = MagicMock()
        mock_project_client.return_value = mock_client_instance
        mock_client_instance.project.project_id = 1
        mock_client_instance.suite = None
        mock_client_instance.api_request_handler.get_cases_by_label.return_value = ([], "")
        
        with patch.object(self.environment, 'log') as mock_log, \
             patch.object(self.environment, 'set_parameters'), \
             patch.object(self.environment, 'check_for_required_parameters'):
            
            result = self.runner.invoke(
                cmd_labels.cases, 
                ['list', '--title', 'non-existent'], 
                obj=self.environment
            )
            
            assert result.exit_code == 0
            mock_log.assert_any_call("Found 0 matching test case(s):")
            mock_log.assert_any_call("  No test cases found with label title 'non-existent'.")
class TestCmdLabelsTests:
    """Test class for test labels command functionality"""

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
    def test_add_label_to_tests_success(self, mock_project_client):
        """Test successful label addition to tests"""
        # Mock the project client and its methods
        mock_client_instance = MagicMock()
        mock_project_client.return_value = mock_client_instance
        mock_client_instance.project.project_id = 1
        mock_client_instance.resolve_project.return_value = None
        mock_client_instance.api_request_handler.add_labels_to_tests.return_value = (
            {
                'successful_tests': [{'test_id': 1, 'message': 'Success'}],
                'failed_tests': [],
                'max_labels_reached': [],
                'test_not_found': []
            }, 
            ""
        )

        # Mock environment methods
        with patch.object(self.environment, 'log') as mock_log, \
             patch.object(self.environment, 'set_parameters'), \
             patch.object(self.environment, 'check_for_required_parameters'):
            
            result = self.runner.invoke(
                cmd_labels.tests, 
                ['add', '--test-ids', '1', '--title', 'Test Label'], 
                obj=self.environment
            )
            
            assert result.exit_code == 0
            mock_client_instance.api_request_handler.add_labels_to_tests.assert_called_once_with(
                test_ids=[1], titles=['Test Label'], project_id=1
            )
            mock_log.assert_any_call("Successfully processed 1 test(s):")

    @mock.patch('trcli.commands.cmd_labels.ProjectBasedClient')
    def test_add_label_to_tests_with_csv_file(self, mock_project_client):
        """Test label addition to tests using CSV file"""
        # Mock the project client
        mock_client_instance = MagicMock()
        mock_project_client.return_value = mock_client_instance
        mock_client_instance.project.project_id = 1
        mock_client_instance.resolve_project.return_value = None
        mock_client_instance.api_request_handler.add_labels_to_tests.return_value = (
            {
                'successful_tests': [{'test_id': 1, 'message': 'Success'}, {'test_id': 2, 'message': 'Success'}],
                'failed_tests': [],
                'max_labels_reached': [],
                'test_not_found': []
            }, 
            ""
        )

        # Create a temporary CSV file
        with self.runner.isolated_filesystem():
            with open('test_ids.csv', 'w') as f:
                f.write('test_id,description\n1,Test One\n2,Test Two\n')
            
            # Mock environment methods
            with patch.object(self.environment, 'log') as mock_log, \
                 patch.object(self.environment, 'set_parameters'), \
                 patch.object(self.environment, 'check_for_required_parameters'):
                
                result = self.runner.invoke(
                    cmd_labels.tests, 
                    ['add', '--test-id-file', 'test_ids.csv', '--title', 'Test Label'], 
                    obj=self.environment
                )
                
                assert result.exit_code == 0
                mock_client_instance.api_request_handler.add_labels_to_tests.assert_called_once_with(
                    test_ids=[1, 2], titles=['Test Label'], project_id=1
                )
                mock_log.assert_any_call("Loaded 2 test ID(s) from file 'test_ids.csv'")

    @mock.patch('trcli.commands.cmd_labels.ProjectBasedClient')
    def test_add_label_to_tests_validation_error(self, mock_project_client):
        """Test validation error when neither test-ids nor file provided"""
        with patch.object(self.environment, 'elog') as mock_elog, \
             patch.object(self.environment, 'set_parameters'), \
             patch.object(self.environment, 'check_for_required_parameters'):
            
            result = self.runner.invoke(
                cmd_labels.tests, 
                ['add', '--title', 'Test Label'], 
                obj=self.environment
            )
            
            assert result.exit_code == 1
            mock_elog.assert_any_call("Error: Either --test-ids or --test-id-file must be provided.")

    @mock.patch('trcli.commands.cmd_labels.ProjectBasedClient')
    def test_add_label_to_tests_title_too_long(self, mock_project_client):
        """Test validation error for title too long - should fail when all labels are invalid"""
        long_title = "a" * 21  # 21 characters, exceeds limit
        
        with patch.object(self.environment, 'elog') as mock_elog, \
             patch.object(self.environment, 'set_parameters'), \
             patch.object(self.environment, 'check_for_required_parameters'):
            
            result = self.runner.invoke(
                cmd_labels.tests, 
                ['add', '--test-ids', '1', '--title', long_title], 
                obj=self.environment
            )
            
            assert result.exit_code == 1
            # Should show warning for invalid label, then error for no valid labels
            mock_elog.assert_any_call(f"Warning: Label title '{long_title}' exceeds 20 character limit and will be skipped.")
            mock_elog.assert_any_call("Error: No valid label titles provided after filtering.")

    @mock.patch('trcli.commands.cmd_labels.ProjectBasedClient')
    def test_list_tests_by_label_success(self, mock_project_client):
        """Test successful listing of tests by label"""
        # Mock the project client and its methods
        mock_client_instance = MagicMock()
        mock_project_client.return_value = mock_client_instance
        mock_client_instance.project.project_id = 1
        mock_client_instance.resolve_project.return_value = None
        mock_client_instance.api_request_handler.get_tests_by_label.return_value = (
            [
                {'id': 1, 'title': 'Test 1', 'status_id': 1, 'labels': [{'id': 5, 'title': 'Test Label'}]},
                {'id': 2, 'title': 'Test 2', 'status_id': 2, 'labels': [{'id': 5, 'title': 'Test Label'}]}
            ], 
            ""
        )

        # Mock environment methods
        with patch.object(self.environment, 'log') as mock_log, \
             patch.object(self.environment, 'set_parameters'), \
             patch.object(self.environment, 'check_for_required_parameters'):
            
            result = self.runner.invoke(
                cmd_labels.tests, 
                ['list', '--run-id', '1', '--ids', '5'], 
                obj=self.environment
            )
            
            assert result.exit_code == 0
            mock_client_instance.api_request_handler.get_tests_by_label.assert_called_once_with(
                project_id=1, label_ids=[5], run_ids=[1]
            )
            mock_log.assert_any_call("Found 2 matching test(s):")

    @mock.patch('trcli.commands.cmd_labels.ProjectBasedClient')
    def test_get_test_labels_success(self, mock_project_client):
        """Test successful retrieval of test labels"""
        # Mock the project client and its methods
        mock_client_instance = MagicMock()
        mock_project_client.return_value = mock_client_instance
        mock_client_instance.project.project_id = 1
        mock_client_instance.resolve_project.return_value = None
        mock_client_instance.api_request_handler.get_test_labels.return_value = (
            [
                {
                    'test_id': 1, 
                    'title': 'Test 1', 
                    'status_id': 1,
                    'labels': [{'id': 5, 'title': 'Test Label'}],
                    'error': None
                }
            ], 
            ""
        )

        # Mock environment methods
        with patch.object(self.environment, 'log') as mock_log, \
             patch.object(self.environment, 'set_parameters'), \
             patch.object(self.environment, 'check_for_required_parameters'):
            
            result = self.runner.invoke(
                cmd_labels.tests, 
                ['get', '--test-ids', '1'], 
                obj=self.environment
            )
            
            assert result.exit_code == 0
            mock_client_instance.api_request_handler.get_test_labels.assert_called_once_with([1])
            mock_log.assert_any_call("Test label information:")
            mock_log.assert_any_call("  Test ID: 1")

    @mock.patch('trcli.commands.cmd_labels.ProjectBasedClient')
    def test_list_tests_invalid_ids(self, mock_project_client):
        """Test invalid label IDs format in list command"""
        with patch.object(self.environment, 'elog') as mock_elog, \
             patch.object(self.environment, 'set_parameters'), \
             patch.object(self.environment, 'check_for_required_parameters'):
            
            result = self.runner.invoke(
                cmd_labels.tests, 
                ['list', '--run-id', '1', '--ids', 'invalid,ids'], 
                obj=self.environment
            )
            
            assert result.exit_code == 1
            mock_elog.assert_any_call("Error: Invalid label IDs format. Use comma-separated integers (e.g., 1,2,3).")

    @mock.patch('trcli.commands.cmd_labels.ProjectBasedClient')
    def test_list_tests_invalid_run_ids(self, mock_project_client):
        """Test invalid run IDs format in list command"""
        with patch.object(self.environment, 'elog') as mock_elog, \
             patch.object(self.environment, 'set_parameters'), \
             patch.object(self.environment, 'check_for_required_parameters'):
            
            result = self.runner.invoke(
                cmd_labels.tests, 
                ['list', '--run-id', 'invalid,run', '--ids', '5'], 
                obj=self.environment
            )
            
            assert result.exit_code == 1
            mock_elog.assert_any_call("Error: Invalid run IDs format. Use comma-separated integers (e.g., 1,2,3).")

    @mock.patch('trcli.commands.cmd_labels.ProjectBasedClient')  
    def test_add_label_to_tests_csv_file_not_found(self, mock_project_client):
        """Test error when CSV file is not found"""
        with patch.object(self.environment, 'elog') as mock_elog, \
             patch.object(self.environment, 'set_parameters'), \
             patch.object(self.environment, 'check_for_required_parameters'):
            
            result = self.runner.invoke(
                cmd_labels.tests, 
                ['add', '--test-id-file', 'nonexistent.csv', '--title', 'Test Label'], 
                obj=self.environment
            )
            
            assert result.exit_code == 1
            mock_elog.assert_any_call("Error: File 'nonexistent.csv' not found.")

    @mock.patch('trcli.commands.cmd_labels.ProjectBasedClient')
    def test_add_label_to_tests_with_warnings(self, mock_project_client):
        """Test label addition with warnings for not found tests and max labels"""
        # Mock the project client
        mock_client_instance = MagicMock()
        mock_project_client.return_value = mock_client_instance
        mock_client_instance.project.project_id = 1
        mock_client_instance.resolve_project.return_value = None
        mock_client_instance.api_request_handler.add_labels_to_tests.return_value = (
            {
                'successful_tests': [{'test_id': 1, 'message': 'Success'}],
                'failed_tests': [],
                'max_labels_reached': [2],
                'test_not_found': [999]
            }, 
            ""
        )

        # Mock environment methods
        with patch.object(self.environment, 'log') as mock_log, \
             patch.object(self.environment, 'set_parameters'), \
             patch.object(self.environment, 'check_for_required_parameters'):
            
            result = self.runner.invoke(
                cmd_labels.tests, 
                ['add', '--test-ids', '1,2,999', '--title', 'Test Label'], 
                obj=self.environment
            )
            
            assert result.exit_code == 0
            mock_log.assert_any_call("Warning: 1 test(s) not found or not accessible:")
            mock_log.assert_any_call("  Test ID 999 does not exist or is not accessible")
            mock_log.assert_any_call("Warning: 1 test(s) already have maximum labels (10):")
            mock_log.assert_any_call("  Test 2: Maximum labels reached")

    @mock.patch('trcli.commands.cmd_labels.ProjectBasedClient')
    def test_add_multiple_labels_to_tests_success(self, mock_project_client):
        """Test successful addition of multiple labels to tests"""
        mock_client_instance = MagicMock()
        mock_project_client.return_value = mock_client_instance
        mock_client_instance.project.project_id = 1
        mock_client_instance.resolve_project.return_value = None
        mock_client_instance.api_request_handler.add_labels_to_tests.return_value = (
            {
                'successful_tests': [
                    {'test_id': 1, 'message': 'Successfully added 2 labels (label1, label2) to test 1'},
                    {'test_id': 2, 'message': 'Successfully added 2 labels (label1, label2) to test 2'}
                ],
                'failed_tests': [],
                'max_labels_reached': [],
                'test_not_found': []
            }, 
            ""
        )

        with patch.object(self.environment, 'log') as mock_log, \
             patch.object(self.environment, 'set_parameters'), \
             patch.object(self.environment, 'check_for_required_parameters'):
            
            result = self.runner.invoke(
                cmd_labels.tests, 
                ['add', '--test-ids', '1,2', '--title', 'label1,label2'], 
                obj=self.environment
            )
            
            assert result.exit_code == 0
            mock_client_instance.api_request_handler.add_labels_to_tests.assert_called_once_with(
                test_ids=[1, 2], titles=['label1', 'label2'], project_id=1
            )
            mock_log.assert_any_call("Successfully processed 2 test(s):")

    @mock.patch('trcli.commands.cmd_labels.ProjectBasedClient')
    def test_add_labels_to_tests_mixed_valid_invalid(self, mock_project_client):
        """Test mixed valid/invalid labels - should process valid ones and warn about invalid ones"""
        mock_client_instance = MagicMock()
        mock_project_client.return_value = mock_client_instance
        mock_client_instance.project.project_id = 1
        mock_client_instance.resolve_project.return_value = None
        mock_client_instance.api_request_handler.add_labels_to_tests.return_value = (
            {
                'successful_tests': [
                    {'test_id': 1, 'message': "Successfully added label 'valid-label' to test 1"}
                ],
                'failed_tests': [],
                'max_labels_reached': [],
                'test_not_found': []
            }, 
            ""
        )

        with patch.object(self.environment, 'log') as mock_log, \
             patch.object(self.environment, 'elog') as mock_elog, \
             patch.object(self.environment, 'set_parameters'), \
             patch.object(self.environment, 'check_for_required_parameters'):
            
            result = self.runner.invoke(
                cmd_labels.tests, 
                ['add', '--test-ids', '1', '--title', 'valid-label,this-title-is-way-too-long-for-testrail'], 
                obj=self.environment
            )
            
            # Should succeed with valid label
            assert result.exit_code == 0
            
            # Should warn about invalid label
            mock_elog.assert_any_call("Warning: Label title 'this-title-is-way-too-long-for-testrail' exceeds 20 character limit and will be skipped.")
            
            # Should process the valid label
            mock_client_instance.api_request_handler.add_labels_to_tests.assert_called_once_with(
                test_ids=[1], titles=['valid-label'], project_id=1
            )
            
            # Should show success for valid label
            mock_log.assert_any_call("Successfully processed 1 test(s):")

    @mock.patch('trcli.commands.cmd_labels.ProjectBasedClient')
    def test_add_labels_to_tests_all_invalid_titles(self, mock_project_client):
        """Test when all labels are invalid - should fail"""
        with patch.object(self.environment, 'elog') as mock_elog, \
             patch.object(self.environment, 'set_parameters'), \
             patch.object(self.environment, 'check_for_required_parameters'):
            
            result = self.runner.invoke(
                cmd_labels.tests, 
                ['add', '--test-ids', '1', '--title', 'this-title-is-way-too-long,another-title-that-is-also-too-long'], 
                obj=self.environment
            )
            
            # Should fail when all labels are invalid
            assert result.exit_code == 1
            
            # Should show warnings for all invalid labels
            mock_elog.assert_any_call("Warning: Label title 'this-title-is-way-too-long' exceeds 20 character limit and will be skipped.")
            mock_elog.assert_any_call("Warning: Label title 'another-title-that-is-also-too-long' exceeds 20 character limit and will be skipped.")
            mock_elog.assert_any_call("Error: No valid label titles provided after filtering.")

    @mock.patch('trcli.commands.cmd_labels.ProjectBasedClient')
    def test_add_labels_to_tests_max_labels_validation(self, mock_project_client):
        """Test early validation for more than 10 labels"""
        with patch.object(self.environment, 'elog') as mock_elog, \
             patch.object(self.environment, 'set_parameters'), \
             patch.object(self.environment, 'check_for_required_parameters'):
            
            # Create a title string with 11 labels
            long_title_list = ','.join([f'label{i}' for i in range(1, 12)])
            
            result = self.runner.invoke(
                cmd_labels.tests, 
                ['add', '--test-ids', '1', '--title', long_title_list], 
                obj=self.environment
            )
            
            assert result.exit_code == 1
            mock_elog.assert_called_with("Error: Cannot add more than 10 labels at once. You provided 11 valid labels.")
     
   