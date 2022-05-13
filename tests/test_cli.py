import unittest
from pathlib import Path

import pytest

from click.testing import CliRunner

import trcli.cli
from shutil import copyfile
from trcli.cli import cli
from trcli.constants import FAULT_MAPPING
from tests.helpers.cli_helpers import CLIParametersHelper

from tests.test_data.cli_test_data import (
    CHECK_ERROR_MESSAGE_FOR_REQUIRED_PARAMETERS_TEST_DATA,
    CHECK_ERROR_MESSAGE_FOR_REQUIRED_PARAMETERS_TEST_IDS,
    ENVIRONMENT_VARIABLES,
    RETURN_VALUE_FROM_CUSTOM_CONFIG_FILE,
    trcli_description,
    trcli_help_description,
)


@pytest.fixture(scope="class")
def cli_resources():
    cli_args_helper = CLIParametersHelper()
    cli_runner = CliRunner()
    yield cli_args_helper, cli_runner


class TestCli:
    @pytest.mark.cli
    def test_run_without_parameters(self, mocker, cli_resources):
        """The purpose of this test is to check that calling trcli without parameters
        will result in printing version information."""
        _, cli_runner = cli_resources
        mocker.patch("sys.argv", ["trcli"])
        result = cli_runner.invoke(cli)
        assert (
            result.exit_code == 0
        ), f"Exit code 0 expected. Got: {result.exit_code} instead."
        assert (
            result.output == trcli_description
        ), f"Output should show trcli description (version, tool information)."

    @pytest.mark.cli
    def test_run_with_help_parameter(self, cli_resources):
        """The purpose of this test is to check that calling trcli with --help parameter
        will result in printing short tool description and usage"""
        _, cli_runner = cli_resources
        result = cli_runner.invoke(cli, ["--help"])
        assert (
            result.exit_code == 0
        ), f"Exit code 0 expected. Got: {result.exit_code} instead."
        assert (
            trcli_help_description in result.output
        ), "Trcli tool description is not present in output when calling trcli with --help parameter."
        assert (
            "Usage:" in result.output
        ), "'Usage:' is not present in output message when calling trcli with --help parameter."
        assert (
            "Options:" in result.output
        ), "'Options:' is not present in output message when calling trcli with --help parameter."

    @pytest.mark.cli
    def test_run_without_command(self, mocker, cli_resources):
        """The purpose of this test is to check that calling trcli without command will result is
        printing message about missing command"""
        cli_args_helper, cli_runner = cli_resources
        args = cli_args_helper.get_all_required_parameters_without_specified(
            ["parse_junit", "file", "title"]
        )
        mocker.patch("sys.argv", ["trcli", *args])
        result = cli_runner.invoke(cli, args)
        assert (
            result.exit_code == 2
        ), f"Exit code 2 expected. Got: {result.exit_code} instead."
        assert (
            "Missing command." in result.output
        ), "'Missing command.' is not present in output when calling trcli without command parameter."

    @pytest.mark.cli
    # @pytest.mark.parametrize()
    def test_run_with_case_id_project_title_not_required(self, mocker, cli_resources):
        cli_args_helper, cli_runner = cli_resources

        args = cli_args_helper.get_all_required_parameters_without_specified(
            ["project", "title"]
        )
        args = ["--run-id 20", "--case-id", "10", *args]
        mocker.patch("sys.argv", ["trcli", *args])
        result = cli_runner.invoke(cli, args)
        assert FAULT_MAPPING["missing_project"] not in result.output, ""
        assert FAULT_MAPPING["missing_title"] not in result.output, ""

    @pytest.mark.cli
    @pytest.mark.parametrize(
        "missing_args, expected_output, expected_exit_code",
        CHECK_ERROR_MESSAGE_FOR_REQUIRED_PARAMETERS_TEST_DATA,
        ids=CHECK_ERROR_MESSAGE_FOR_REQUIRED_PARAMETERS_TEST_IDS,
    )
    def test_check_error_message_for_required_parameters(
        self, missing_args, expected_output, expected_exit_code, mocker, cli_resources
    ):
        """The purpose of this test is to check that proper error message would be
        printed when parameter is not passed to the script and there is no
        configuration file and environment variables set"""
        cli_agrs_helper, cli_runner = cli_resources
        args = cli_agrs_helper.get_all_required_parameters_without_specified(
            missing_args
        )

        mocker.patch("sys.argv", ["trcli", *args])
        result = cli_runner.invoke(cli, args)
        assert (
            result.exit_code == expected_exit_code
        ), f"Exit code {expected_exit_code} expected. Got: {result.exit_code} instead."
        assert (
            expected_output in result.output
        ), f"Error message: '{expected_output}' expected.\nGot: {result.output} instead."

    @pytest.mark.api_client
    @pytest.mark.parametrize(
        "host",
        ["http://", "fake_host.com/", "http:/fake_host.com"],
        ids=["only scheme", "no scheme", "wrong scheme separator"],
    )
    def test_host_syntax_is_validated(self, host, cli_resources, mocker):
        cli_agrs_helper, cli_runner = cli_resources
        expected_exit_code = 1
        expected_output = "Please provide a valid TestRail server address."
        args = cli_agrs_helper.get_all_required_parameters_without_specified(["host"])
        args = ["--host", host, *args]

        mocker.patch("sys.argv", ["trcli", *args])
        result = cli_runner.invoke(cli, args)
        assert (
            result.exit_code == expected_exit_code
        ), f"Exit code {expected_exit_code} expected. Got: {result.exit_code} instead."
        assert (
            expected_output in result.output
        ), f"Error message: '{expected_output}' expected.\nGot: {result.output} instead."

    @pytest.mark.cli
    @pytest.mark.parametrize(
        "argument_name, argument_value",
        [("batch_size", 1000), ("timeout", 160)],
        ids=["batch_size", "timeout"],
    )
    def test_check_custom_config_overrides_defaults(
        self, argument_name, argument_value, mocker, cli_resources
    ):
        """The purpose of this test is to check that custom config overrides default values of parameters."""
        cli_agrs_helper, cli_runner = cli_resources

        args = cli_agrs_helper.get_all_required_parameters_plus_optional(
            ["--config", "fake_config_file.yaml"]
        )
        mocker.patch("sys.argv", ["trcli", *args])

        with cli_runner.isolated_filesystem():
            with open("fake_config_file.yaml", "w+") as f:
                f.write(f"{argument_name}: {argument_value}")
            setattr_mock = mocker.patch("trcli.cli.setattr")
            _ = cli_runner.invoke(cli, args)

        setattr_mock.assert_any_call(mocker.ANY, argument_name, argument_value)

    @pytest.mark.cli
    def test_check_custom_config_overrides_environment(self, mocker, cli_resources):
        """the purpose of this test is to check that custom config overrides parameter values taken from
        environment"""
        cli_agrs_helper, cli_runner = cli_resources
        custom_config_file = (
            Path(__file__).parent / "test_data/yaml/custom_config_file.yaml"
        )
        args = ["--config", custom_config_file, "parse_junit"]

        mocker.patch("sys.argv", ["trcli", *args])
        setattr_mock = mocker.patch("trcli.cli.setattr")

        _ = cli_runner.invoke(
            cli,
            args,
            env=ENVIRONMENT_VARIABLES,
        )

        for arg_name, arg_value in RETURN_VALUE_FROM_CUSTOM_CONFIG_FILE.items():
            setattr_mock.assert_any_call(mocker.ANY, arg_name, arg_value)

    @pytest.mark.cli
    def test_custom_config_does_not_override_parameters(self, mocker, cli_resources):
        """The purpose of this test is to check that custom config will not override parameters (when specified in
        command line)"""
        cli_agrs_helper, cli_runner = cli_resources
        custom_config_file = (
            Path(__file__).parent / "test_data/yaml/custom_config_file.yaml"
        )
        args = cli_agrs_helper.get_all_required_parameters_plus_optional(
            ["--config", custom_config_file]
        )
        mocker.patch("sys.argv", ["trcli", *args])
        setattr_mock = mocker.patch("trcli.cli.setattr")
        _ = cli_runner.invoke(cli, args)

        expected = cli_agrs_helper.get_required_parameters_without_command_no_dashes()
        for arg_name, arg_value in expected:
            setattr_mock.assert_any_call(mocker.ANY, arg_name, arg_value)

    @pytest.mark.cli
    @pytest.mark.parametrize(
        "argument_name, argument_value",
        [("batch_size", 1000), ("timeout", 160)],
        ids=["batch_size", "timeout"],
    )
    def test_default_config_overrides_defaults_of_parameters(
        self, argument_name, argument_value, mocker, cli_resources
    ):
        """The purpose of this test is to check that default config file will override default values of
        parameters"""
        cli_agrs_helper, cli_runner = cli_resources
        args = cli_agrs_helper.get_all_required_parameters()
        mocker.patch("sys.argv", ["trcli", *args])

        with cli_runner.isolated_filesystem():
            with open("config.yaml", "w+") as f:
                f.write(f"{argument_name}: {argument_value}")

            setattr_mock = mocker.patch("trcli.cli.setattr")
            _ = cli_runner.invoke(cli, args)

        setattr_mock.assert_any_call(mocker.ANY, argument_name, argument_value)

    @pytest.mark.cli
    def test_default_config_does_not_override_environments(self, mocker, cli_resources):
        """The purpose of this test is to check that default config will not override parameter values taken
        from environment variables"""
        cli_agrs_helper, cli_runner = cli_resources
        args = ["parse_junit"]
        default_config_file = (
            Path(__file__).parent / "test_data/yaml/default_config_file.yaml"
        )

        mocker.patch("sys.argv", ["trcli", *args])
        setattr_mock = mocker.patch("trcli.cli.setattr")

        with cli_runner.isolated_filesystem():
            copyfile(default_config_file, "config.yaml")
            _ = cli_runner.invoke(
                cli,
                args,
                env=ENVIRONMENT_VARIABLES,
            )

        for arg_name, arg_value in ENVIRONMENT_VARIABLES.items():
            setattr_mock.assert_any_call(
                mocker.ANY, arg_name.removeprefix("TR_CLI_").lower(), arg_value
            )

    @pytest.mark.cli
    def test_default_config_does_not_override_parameters(self, mocker, cli_resources):
        """The purpose of this test is to check that default config will not override parameter values when
        specified in command line"""
        cli_agrs_helper, cli_runner = cli_resources
        tool_args = cli_agrs_helper.get_all_required_parameters()
        mocker.patch("sys.argv", ["trcli", *tool_args])
        default_config_file = (
            Path(__file__).parent / "test_data/yaml/default_config_file.yaml"
        )
        setattr_mock = mocker.patch("trcli.cli.setattr")
        with cli_runner.isolated_filesystem():
            copyfile(default_config_file, "config.yaml")
            _ = cli_runner.invoke(cli, tool_args)

        expected = cli_agrs_helper.get_required_parameters_without_command_no_dashes()
        for arg_name, arg_value in expected:
            setattr_mock.assert_any_call(mocker.ANY, arg_name, arg_value)
