from unittest import mock

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
