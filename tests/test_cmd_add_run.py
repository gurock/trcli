from unittest import mock

from trcli.cli import Environment
from trcli.commands import cmd_add_run


class TestCmdAddRun:
    @mock.patch("builtins.open", new_callable=mock.mock_open)
    def test_write_run_to_file(self, mock_open_file):
        """The purpose of this test is to check that calling the write_run_to_file method
        writes the correct yaml file."""
        title = "Test run 1"
        run_id = 1
        file = "/fake/path/out.yaml"
        environment = Environment(cmd="add_run")
        environment.title = title
        environment.file = file
        expected_string = f"run_id: {run_id}\ntitle: {title}\n"

        cmd_add_run.write_run_to_file(environment, run_id)
        mock_open_file.assert_called_with(file, "w")
        mock_open_file.return_value.__enter__().write.assert_called_once_with(expected_string)
