import pytest
from unittest import mock
from unittest.mock import MagicMock, patch
from click.testing import CliRunner

from trcli.cli import Environment
from trcli.commands import cmd_references
from trcli.data_classes.dataclass_testrail import TestRailSuite
from trcli.api.project_based_client import ProjectBasedClient


class TestCmdReferences:
    """Test class for references command functionality"""

    def setup_method(self):
        """Set up test environment"""
        self.runner = CliRunner()
        self.environment = Environment(cmd="references")
        self.environment.host = "https://test.testrail.com"
        self.environment.username = "test@example.com"
        self.environment.password = "password"
        self.environment.project = "Test Project"
        self.environment.project_id = 1

    @mock.patch('trcli.commands.cmd_references.ProjectBasedClient')
    def test_add_references_success(self, mock_project_client):
        """Test successful addition of references to test cases"""
        # Mock the project client and its methods
        mock_client_instance = MagicMock()
        mock_project_client.return_value = mock_client_instance
        mock_client_instance.project.project_id = 1
        mock_client_instance.api_request_handler.add_case_references.return_value = (True, "")

        # Mock environment methods
        with patch.object(self.environment, 'log') as mock_log, \
             patch.object(self.environment, 'set_parameters'), \
             patch.object(self.environment, 'check_for_required_parameters'):
            
            result = self.runner.invoke(
                cmd_references.cases, 
                ['add', '--case-ids', '1,2', '--refs', 'REQ-1,REQ-2'], 
                obj=self.environment
            )
            
            assert result.exit_code == 0
            # Verify API calls were made for each test case
            assert mock_client_instance.api_request_handler.add_case_references.call_count == 2
            mock_log.assert_any_call("Adding references to 2 test case(s)...")
            mock_log.assert_any_call("References: REQ-1, REQ-2")
            mock_log.assert_any_call("Successfully added references to 2 test case(s)")

    @mock.patch('trcli.commands.cmd_references.ProjectBasedClient')
    def test_add_references_invalid_test_ids(self, mock_project_client):
        """Test invalid test case IDs format in add command"""
        with patch.object(self.environment, 'elog') as mock_elog, \
             patch.object(self.environment, 'set_parameters'), \
             patch.object(self.environment, 'check_for_required_parameters'):
            
            result = self.runner.invoke(
                cmd_references.cases, 
                ['add', '--case-ids', 'invalid,ids', '--refs', 'REQ-1'], 
                obj=self.environment
            )
            
            assert result.exit_code == 1
            mock_elog.assert_any_call("Error: Invalid test case IDs format. Use comma-separated integers (e.g., 1,2,3).")

    @mock.patch('trcli.commands.cmd_references.ProjectBasedClient')
    def test_add_references_empty_refs(self, mock_project_client):
        """Test empty references in add command"""
        with patch.object(self.environment, 'elog') as mock_elog, \
             patch.object(self.environment, 'set_parameters'), \
             patch.object(self.environment, 'check_for_required_parameters'):
            
            result = self.runner.invoke(
                cmd_references.cases, 
                ['add', '--case-ids', '1,2', '--refs', ',,,'], 
                obj=self.environment
            )
            
            assert result.exit_code == 1
            mock_elog.assert_any_call("Error: No valid references provided.")

    @mock.patch('trcli.commands.cmd_references.ProjectBasedClient')
    def test_add_references_too_long(self, mock_project_client):
        """Test references exceeding 2000 character limit"""
        long_refs = ','.join([f'REQ-{i}' * 100 for i in range(10)])  # Create very long references
        
        with patch.object(self.environment, 'elog') as mock_elog, \
             patch.object(self.environment, 'set_parameters'), \
             patch.object(self.environment, 'check_for_required_parameters'):
            
            result = self.runner.invoke(
                cmd_references.cases, 
                ['add', '--case-ids', '1', '--refs', long_refs], 
                obj=self.environment
            )
            
            assert result.exit_code == 1
            mock_elog.assert_any_call(mock.ANY)  # Check that an error was logged

    @mock.patch('trcli.commands.cmd_references.ProjectBasedClient')
    def test_add_references_api_failure(self, mock_project_client):
        """Test API failure during reference addition"""
        # Mock the project client and its methods
        mock_client_instance = MagicMock()
        mock_project_client.return_value = mock_client_instance
        mock_client_instance.project.project_id = 1
        mock_client_instance.api_request_handler.add_case_references.return_value = (False, "API Error")

        # Mock environment methods
        with patch.object(self.environment, 'log') as mock_log, \
             patch.object(self.environment, 'elog') as mock_elog, \
             patch.object(self.environment, 'set_parameters'), \
             patch.object(self.environment, 'check_for_required_parameters'):
            
            result = self.runner.invoke(
                cmd_references.cases, 
                ['add', '--case-ids', '1', '--refs', 'REQ-1'], 
                obj=self.environment
            )
            
            assert result.exit_code == 1
            mock_elog.assert_any_call("  ✗ Test case 1: API Error")
            mock_elog.assert_any_call("Failed to add references to 1 test case(s)")

    @mock.patch('trcli.commands.cmd_references.ProjectBasedClient')
    def test_update_references_success(self, mock_project_client):
        """Test successful update of references on test cases"""
        # Mock the project client and its methods
        mock_client_instance = MagicMock()
        mock_project_client.return_value = mock_client_instance
        mock_client_instance.project.project_id = 1
        mock_client_instance.api_request_handler.update_case_references.return_value = (True, "")

        # Mock environment methods
        with patch.object(self.environment, 'log') as mock_log, \
             patch.object(self.environment, 'set_parameters'), \
             patch.object(self.environment, 'check_for_required_parameters'):
            
            result = self.runner.invoke(
                cmd_references.cases, 
                ['update', '--case-ids', '1,2', '--refs', 'REQ-3,REQ-4'], 
                obj=self.environment
            )
            
            assert result.exit_code == 0
            # Verify API calls were made for each test case
            assert mock_client_instance.api_request_handler.update_case_references.call_count == 2
            mock_log.assert_any_call("Updating references for 2 test case(s)...")
            mock_log.assert_any_call("New references: REQ-3, REQ-4")
            mock_log.assert_any_call("Successfully updated references for 2 test case(s)")

    @mock.patch('trcli.commands.cmd_references.ProjectBasedClient')
    def test_delete_references_all_success(self, mock_project_client):
        """Test successful deletion of all references from test cases"""
        # Mock the project client and its methods
        mock_client_instance = MagicMock()
        mock_project_client.return_value = mock_client_instance
        mock_client_instance.project.project_id = 1
        mock_client_instance.api_request_handler.delete_case_references.return_value = (True, "")

        # Mock environment methods
        with patch.object(self.environment, 'log') as mock_log, \
             patch.object(self.environment, 'set_parameters'), \
             patch.object(self.environment, 'check_for_required_parameters'):
            
            result = self.runner.invoke(
                cmd_references.cases, 
                ['delete', '--case-ids', '1,2', '--yes'], 
                obj=self.environment
            )
            
            assert result.exit_code == 0
            # Verify API calls were made for each test case
            assert mock_client_instance.api_request_handler.delete_case_references.call_count == 2
            # Check that None was passed for specific_references (delete all)
            mock_client_instance.api_request_handler.delete_case_references.assert_called_with(
                case_id=mock.ANY, specific_references=None
            )
            mock_log.assert_any_call("Deleting all references from 2 test case(s)...")
            mock_log.assert_any_call("Successfully deleted references from 2 test case(s)")

    @mock.patch('trcli.commands.cmd_references.ProjectBasedClient')
    def test_delete_references_specific_success(self, mock_project_client):
        """Test successful deletion of specific references from test cases"""
        # Mock the project client and its methods
        mock_client_instance = MagicMock()
        mock_project_client.return_value = mock_client_instance
        mock_client_instance.project.project_id = 1
        mock_client_instance.api_request_handler.delete_case_references.return_value = (True, "")

        # Mock environment methods
        with patch.object(self.environment, 'log') as mock_log, \
             patch.object(self.environment, 'set_parameters'), \
             patch.object(self.environment, 'check_for_required_parameters'):
            
            result = self.runner.invoke(
                cmd_references.cases, 
                ['delete', '--case-ids', '1', '--refs', 'REQ-1,REQ-2', '--yes'], 
                obj=self.environment
            )
            
            assert result.exit_code == 0
            # Verify API call was made with specific references
            mock_client_instance.api_request_handler.delete_case_references.assert_called_with(
                case_id=1, specific_references=['REQ-1', 'REQ-2']
            )
            mock_log.assert_any_call("Deleting specific references from 1 test case(s)...")
            mock_log.assert_any_call("References to delete: REQ-1, REQ-2")
            mock_log.assert_any_call("Successfully deleted references from 1 test case(s)")

    @mock.patch('trcli.commands.cmd_references.ProjectBasedClient')
    def test_delete_references_empty_specific_refs(self, mock_project_client):
        """Test deletion with empty specific references"""
        with patch.object(self.environment, 'elog') as mock_elog, \
             patch.object(self.environment, 'set_parameters'), \
             patch.object(self.environment, 'check_for_required_parameters'):
            
            result = self.runner.invoke(
                cmd_references.cases, 
                ['delete', '--case-ids', '1', '--refs', ',,,', '--yes'], 
                obj=self.environment
            )
            
            assert result.exit_code == 1
            mock_elog.assert_any_call("Error: No valid references provided.")

    @mock.patch('trcli.commands.cmd_references.ProjectBasedClient')
    def test_mixed_success_and_failure(self, mock_project_client):
        """Test scenario with mixed success and failure results"""
        # Mock the project client and its methods
        mock_client_instance = MagicMock()
        mock_project_client.return_value = mock_client_instance
        mock_client_instance.project.project_id = 1
        
        # Mock different responses for different test cases
        def mock_add_refs(case_id, references):
            if case_id == 1:
                return True, ""
            else:
                return False, "Test case not found"
        
        mock_client_instance.api_request_handler.add_case_references.side_effect = mock_add_refs

        # Mock environment methods
        with patch.object(self.environment, 'log') as mock_log, \
             patch.object(self.environment, 'elog') as mock_elog, \
             patch.object(self.environment, 'set_parameters'), \
             patch.object(self.environment, 'check_for_required_parameters'):
            
            result = self.runner.invoke(
                cmd_references.cases, 
                ['add', '--case-ids', '1,2', '--refs', 'REQ-1'], 
                obj=self.environment
            )
            
            assert result.exit_code == 1
            mock_log.assert_any_call("  ✓ Test case 1: References added successfully")
            mock_elog.assert_any_call("  ✗ Test case 2: Test case not found")
            mock_log.assert_any_call("Successfully added references to 1 test case(s)")
            mock_elog.assert_any_call("Failed to add references to 1 test case(s)")

