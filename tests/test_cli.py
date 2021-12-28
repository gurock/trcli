import pytest

from click.testing import CliRunner
from trcli.cli import cli
from helpers.cli_helpers import CLIParametersHelper

from tests.test_data.cli_test_data import (
    CHECK_ERROR_MESSAGE_FOR_REQUIRED_PARAMETERS_TEST_DATA,
    CHECK_ERROR_MESSAGE_FOR_REQUIRED_PARAMETERS_TEST_IDS,
    ENVIRONMENT_VARIABLES,
    RETURN_VALUE_FROM_DEFAULT_CONFIG_FILE,
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
            ["parse_junit", "file"]
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
            result.output == expected_output
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
        get_params_mock = mocker.patch(
            "trcli.cli.get_params_from_config_file",
            return_value={argument_name: argument_value},
        )
        setattr_mock = mocker.patch("trcli.cli.setattr")

        _ = cli_runner.invoke(cli, args)
        assert get_params_mock.call_count == 2, (
            f"Function get_params_from_config_file expected to be called 2 times but was called:"
            f"{get_params_mock.call_count}"
        )
        for call_item in get_params_mock.call_args_list:
            assert "fake_config_file.yaml" in call_item.args[0], (
                f"Function get_params_from_config_file expected to be called with 'fake_config_file.yaml'"
                f"\nbut was called with: {call_item.args[0]}"
            )
        setattr_mock.assert_any_call(mocker.ANY, argument_name, argument_value)

    @pytest.mark.cli
    def test_check_custom_config_overrides_environment(self, mocker, cli_resources):
        """the purpose of this test is to check that custom config overrides parameter values taken from
        environment"""
        cli_agrs_helper, cli_runner = cli_resources
        args = ["--config", "fake_config_file.yaml", "parse_junit"]

        mocker.patch("sys.argv", ["trcli", *args])
        get_params_mock = mocker.patch(
            "trcli.cli.get_params_from_config_file",
            return_value=RETURN_VALUE_FROM_CUSTOM_CONFIG_FILE,
        )
        setattr_mock = mocker.patch("trcli.cli.setattr")

        _ = cli_runner.invoke(
            cli,
            args,
            env=ENVIRONMENT_VARIABLES,
        )

        assert get_params_mock.call_count == 2, (
            f"Function get_params_from_config_file expected to be called 2 times but was called:"
            f"{get_params_mock.call_count}"
        )
        for call_item in get_params_mock.call_args_list:
            assert "fake_config_file.yaml" in call_item.args[0], (
                f"Function get_params_from_config_file expected to be called with 'fake_config_file.yaml'"
                f"\nbut was called with: {call_item.args[0]}"
            )
        for arg_name, arg_value in RETURN_VALUE_FROM_CUSTOM_CONFIG_FILE.items():
            setattr_mock.assert_any_call(mocker.ANY, arg_name, arg_value)

    @pytest.mark.cli
    def test_custom_config_does_not_override_parameters(self, mocker, cli_resources):
        """The purpose of this test is to check that custom config will not override parameters (when specified in
        command line)"""
        cli_agrs_helper, cli_runner = cli_resources
        args = cli_agrs_helper.get_all_required_parameters_plus_optional(
            ["--config", "fake_config_file.yaml"]
        )

        mocker.patch("sys.argv", ["trcli", *args])
        get_params_mock = mocker.patch(
            "trcli.cli.get_params_from_config_file",
            return_value=RETURN_VALUE_FROM_CUSTOM_CONFIG_FILE,
        )
        setattr_mock = mocker.patch("trcli.cli.setattr")
        _ = cli_runner.invoke(cli, args)

        assert get_params_mock.call_count == 2, (
            f"Function get_params_from_config_file expected to be called 2 times but was called:"
            f"{get_params_mock.call_count}"
        )
        for call_item in get_params_mock.call_args_list:
            assert "fake_config_file.yaml" in call_item.args[0], (
                f"Function get_params_from_config_file expected to be called with 'fake_config_file.yaml'"
                f"\nbut was called with: {call_item.args[0]}"
            )

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

        get_params_mock = mocker.patch(
            "trcli.cli.get_params_from_config_file",
            return_value={argument_name: argument_value},
        )
        setattr_mock = mocker.patch("trcli.cli.setattr")

        _ = cli_runner.invoke(cli, args)

        assert get_params_mock.call_count == 2, (
            f"Function get_params_from_config_file expected to be called 2 times but was called:"
            f"{get_params_mock.call_count}"
        )
        for call_item in get_params_mock.call_args_list:
            assert "config.yaml" in call_item.args[0].name, (
                f"Function get_params_from_config_file expected to be called with 'config.yaml'"
                f"\nbut was called with: {call_item.args[0].name}"
            )
        setattr_mock.assert_any_call(mocker.ANY, argument_name, argument_value)

    @pytest.mark.cli
    def test_default_config_does_not_override_environments(self, mocker, cli_resources):
        """The purpose of this test is to check that default config will not override parameter values taken
        from environment variables"""
        cli_agrs_helper, cli_runner = cli_resources
        args = ["parse_junit"]

        mocker.patch("sys.argv", ["trcli", *args])
        get_params_mock = mocker.patch(
            "trcli.cli.get_params_from_config_file",
            return_value=RETURN_VALUE_FROM_DEFAULT_CONFIG_FILE,
        )
        setattr_mock = mocker.patch("trcli.cli.setattr")

        _ = cli_runner.invoke(
            cli,
            args,
            env=ENVIRONMENT_VARIABLES,
        )

        assert get_params_mock.call_count == 2, (
            f"Function get_params_from_config_file expected to be called 2 times but was called:"
            f"{get_params_mock.call_count}"
        )
        for call_item in get_params_mock.call_args_list:
            assert "config.yaml" in call_item.args[0].name, (
                f"Function get_params_from_config_file expected to be called with 'config.yaml'"
                f"\nbut was called with: {call_item.args[0].name}"
            )
        for arg_name, arg_value in ENVIRONMENT_VARIABLES.items():
            setattr_mock.assert_any_call(
                mocker.ANY, arg_name.split("_")[-1].lower(), arg_value
            )

    @pytest.mark.cli
    def test_default_config_does_not_override_parameters(self, mocker, cli_resources):
        """The purpose of this test is to check that default config will not override parameter values when
        specified in command line"""
        cli_agrs_helper, cli_runner = cli_resources
        tool_args = cli_agrs_helper.get_all_required_parameters()
        mocker.patch("sys.argv", ["trcli", *tool_args])
        get_params_mock = mocker.patch(
            "trcli.cli.get_params_from_config_file",
            return_value=RETURN_VALUE_FROM_DEFAULT_CONFIG_FILE,
        )
        setattr_mock = mocker.patch("trcli.cli.setattr")

        _ = cli_runner.invoke(cli, tool_args)

        assert get_params_mock.call_count == 2, (
            f"Function get_params_from_config_file expected to be called 2 times but was called:"
            f"{get_params_mock.call_count}"
        )
        for call_item in get_params_mock.call_args_list:
            assert "config.yaml" in call_item.args[0].name, (
                f"Function get_params_from_config_file expected to be called with 'config.yaml'"
                f"\nbut was called with: {call_item.args[0].name}"
            )

        expected = cli_agrs_helper.get_required_parameters_without_command_no_dashes()
        for arg_name, arg_value in expected:
            setattr_mock.assert_any_call(mocker.ANY, arg_name, arg_value)
