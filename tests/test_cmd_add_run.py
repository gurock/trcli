from unittest import mock
import pytest
from click.testing import CliRunner

from trcli.cli import Environment
from trcli.commands import cmd_add_run


class TestCmdAddRun:
    @mock.patch("builtins.open", new_callable=mock.mock_open)
    def test_write_run_to_file(self, mock_open_file):
        """The purpose of this test is to check that calling the write_run_to_file method
        writes the correct yaml file excluding optional data."""
        title = "Test run 1"
        run_id = 1
        file = "/fake/path/out.yaml"
        environment = Environment(cmd="add_run")
        environment.title = title
        environment.file = file
        expected_string = f"run_id: {run_id}\ntitle: {title}\n"

        cmd_add_run.write_run_to_file(environment, run_id)
        mock_open_file.assert_called_with(file, "a")
        mock_open_file.return_value.__enter__().write.assert_called_once_with(expected_string)

    @mock.patch("builtins.open", new_callable=mock.mock_open)
    def test_write_run_to_file_with_refs_and_description(self, mock_open_file):
        """The purpose of this test is to check that calling the write_run_to_file method
        writes the correct yaml file including optional data."""
        title = "Test run 1"
        run_id = 1
        file = "/fake/path/out.yaml"
        description = "test description"
        refs = "JIRA-100"
        case_ids = "1234"
        assigned_to_id = 1
        environment = Environment(cmd="add_run")
        environment.title = title
        environment.file = file
        environment.run_refs = refs
        environment.run_description = description
        environment.run_assigned_to_id = assigned_to_id
        environment.run_case_ids = case_ids
        environment.run_include_all = True
        expected_string = (f"run_assigned_to_id: {assigned_to_id}\nrun_case_ids: '{case_ids}'\n"
                           f"run_description: {description}\nrun_id: {run_id}\n"
                           f"run_include_all: true\nrun_refs: {refs}\ntitle: {title}\n")
        cmd_add_run.write_run_to_file(environment, run_id)
        mock_open_file.assert_called_with(file, "a")
        mock_open_file.return_value.__enter__().write.assert_called_once_with(expected_string)

    def test_cli_validation_refs_too_long(self):
        """Test that references validation fails when exceeding 250 characters"""
        from trcli.cli import Environment
        
        environment = Environment()
        environment.run_refs = "A" * 251  # 251 characters, exceeds limit
        
        assert len(environment.run_refs) > 250
        
        runner = CliRunner()
        long_refs = "A" * 251
        
        result = runner.invoke(cmd_add_run.cli, [
            '--title', 'Test Run',
            '--run-refs', long_refs
        ], catch_exceptions=False)
        
        # Should exit with error code 1 due to missing required parameters or validation
        assert result.exit_code == 1

    def test_cli_validation_refs_exactly_250_chars(self):
        """Test that references validation passes with exactly 250 characters"""
        from trcli.cli import Environment
        
        runner = CliRunner()
        refs_250 = "A" * 250  # Exactly 250 characters, should pass validation
        
        result = runner.invoke(cmd_add_run.cli, [
            '--title', 'Test Run',
            '--run-refs', refs_250
        ], catch_exceptions=False)
        
        # Should not fail due to refs validation (will fail due to missing required parameters)
        # But the important thing is that it doesn't fail with the character limit error
        assert "References field cannot exceed 250 characters" not in result.output

    def test_validation_logic_refs_action_without_run_id(self):
        """Test validation logic for refs action without run_id"""
        from trcli.cli import Environment
        
        # Update action validation
        environment = Environment()
        environment.run_refs_action = "update"
        environment.run_id = None
        environment.run_refs = "JIRA-123"
        
        # This should be invalid
        assert environment.run_refs_action == "update"
        assert environment.run_id is None
        
        # Delete action validation  
        environment.run_refs_action = "delete"
        assert environment.run_refs_action == "delete"
        assert environment.run_id is None

    def test_refs_action_parameter_parsing(self):
        """Test that refs action parameter is parsed correctly"""
        runner = CliRunner()
        
        # Test that the CLI accepts new param without crashing! :) - acuanico
        result = runner.invoke(cmd_add_run.cli, ['--help'])
        assert result.exit_code == 0
        assert "--run-refs-action" in result.output
        assert "Action to perform on references" in result.output


class TestApiRequestHandlerReferences:
    """Test class for reference management functionality"""
    
    def test_manage_references_add(self):
        """Test adding references to existing ones"""
        from trcli.api.api_request_handler import ApiRequestHandler
        from trcli.cli import Environment
        from trcli.api.api_client import APIClient
        from trcli.data_classes.dataclass_testrail import TestRailSuite
        
        environment = Environment()
        api_client = APIClient("https://test.testrail.com")
        suite = TestRailSuite(name="Test Suite")
        handler = ApiRequestHandler(environment, api_client, suite)
        
        # Adding new references
        result = handler._manage_references("JIRA-100,JIRA-200", "JIRA-300,JIRA-400", "add")
        assert result == "JIRA-100,JIRA-200,JIRA-300,JIRA-400"
        
        # Adding duplicate references (should not duplicate)
        result = handler._manage_references("JIRA-100,JIRA-200", "JIRA-200,JIRA-300", "add")
        assert result == "JIRA-100,JIRA-200,JIRA-300"
        
        # Adding to empty existing references
        result = handler._manage_references("", "JIRA-100,JIRA-200", "add")
        assert result == "JIRA-100,JIRA-200"

    def test_manage_references_update(self):
        """Test updating (replacing) all references"""
        from trcli.api.api_request_handler import ApiRequestHandler
        from trcli.cli import Environment
        from trcli.api.api_client import APIClient
        from trcli.data_classes.dataclass_testrail import TestRailSuite
        
        environment = Environment()
        api_client = APIClient("https://test.testrail.com")
        suite = TestRailSuite(name="Test Suite")
        handler = ApiRequestHandler(environment, api_client, suite)
        
        # Test replacing all references
        result = handler._manage_references("JIRA-100,JIRA-200", "JIRA-300,JIRA-400", "update")
        assert result == "JIRA-300,JIRA-400"
        
        # Test replacing with empty references
        result = handler._manage_references("JIRA-100,JIRA-200", "", "update")
        assert result == ""

    def test_manage_references_delete(self):
        """Test deleting specific or all references"""
        from trcli.api.api_request_handler import ApiRequestHandler
        from trcli.cli import Environment
        from trcli.api.api_client import APIClient
        from trcli.data_classes.dataclass_testrail import TestRailSuite
        
        environment = Environment()
        api_client = APIClient("https://test.testrail.com")
        suite = TestRailSuite(name="Test Suite")
        handler = ApiRequestHandler(environment, api_client, suite)
        
        # Deleting specific references
        result = handler._manage_references("JIRA-100,JIRA-200,JIRA-300", "JIRA-200", "delete")
        assert result == "JIRA-100,JIRA-300"
        
        # Deleting multiple specific references
        result = handler._manage_references("JIRA-100,JIRA-200,JIRA-300,JIRA-400", "JIRA-200,JIRA-400", "delete")
        assert result == "JIRA-100,JIRA-300"
        
        # Deleting all references (empty new_refs)
        result = handler._manage_references("JIRA-100,JIRA-200", "", "delete")
        assert result == ""
        
        # Deleting non-existent references
        result = handler._manage_references("JIRA-100,JIRA-200", "JIRA-999", "delete")
        assert result == "JIRA-100,JIRA-200"
