import os
import sys
import click
from pathlib import Path

from click.core import ParameterSource
from trcli.constants import (
    FAULT_MAPPING,
    TOOL_VERSION_AND_USAGE,
    MISSING_COMMAND_SLOGAN,
)
from trcli.utilities import get_params_from_config_file


CONTEXT_SETTINGS = dict(auto_envvar_prefix="TR_CLI")

trcli_folder = Path(__file__).parent
cmd_folder = trcli_folder / "commands/"
default_config_file_path = trcli_folder / "config.yaml"


class Environment:
    def __init__(self):
        self.home = os.getcwd()
        self.default_config_file = True
        self.file = None
        self.host = None
        self.project = None
        self.title = None
        self.username = None
        self.password = None
        self.key = None
        self.verbose = None
        self.verify = None
        self.config = None
        self.batch_size = None
        self.timeout = None
        self.suite_id = None
        self.run_id = None
        self.case_id = None
        self.prompt_auto_creation = None
        self.silent = None

    def log(self, msg: str, *args):
        """Logs a message to stderr."""
        if not self.silent:
            if args:
                msg %= args
            click.echo(msg, file=sys.stderr)

    def vlog(self, msg: str, *args):
        """Logs a message to stderr only if the verbose option is enabled"""
        if self.verbose:
            self.log(msg, *args)

    def get_prompt_response_for_auto_creation(self, msg: str, *args):
        """Prompts for confirmation (yes/no) if prompt_auto_creation (--no/--yes parameters) is not set"""
        if not self.prompt_auto_creation:
            return click.confirm(msg)
        else:
            return True if self.prompt_auto_creation == "True" else False

    def set_parameters(self, context: click.core.Context):
        """Sets parameters based on context. The function will override parameters with config file values
        depending on the parameter source and config file source (default or custom)"""
        if self.default_config_file:
            param_sources_types = [ParameterSource.DEFAULT]
        else:
            param_sources_types = [ParameterSource.DEFAULT, ParameterSource.ENVIRONMENT]

        params_from_config = get_params_from_config_file(self.config)
        for param, value in context.params.items():
            # Don't set config again
            if param == "config":
                continue
            param_config_value = params_from_config.get(param, None)
            param_source = context.get_parameter_source(param)
            if param_source in param_sources_types and param_config_value:
                setattr(self, param, param_config_value)
            else:
                setattr(self, param, value)

    def check_for_required_parameters(self):
        """Checks that all required parameters were set. If not error message would be printed and
        program will exit with exit code 1"""
        for param, value in vars(self).items():
            if "missing_" + param in FAULT_MAPPING and not value:
                self.log(FAULT_MAPPING["missing_" + param])
                exit(1)
        # special case for password and key (both needs to be missing for the error message to show up)
        if not self.password and not self.key:
            self.log(FAULT_MAPPING["missing_password_and_key"])
            exit(1)

    def set_config_file(self, context: click.Context):
        """Sets config file path from context and information if default or custom config file should be used."""
        self.config = context.params["config"]
        self.default_config_file = (
            False
            if context.get_parameter_source("config") == ParameterSource.COMMANDLINE
            else True
        )


pass_environment = click.make_pass_decorator(Environment, ensure=True)


class TRCLI(click.MultiCommand):
    def __init__(self, *args, **kwargs):
        # Use invoke_without_command=True to be able to print
        # short tool description when starting without parameters
        click.MultiCommand.__init__(self, invoke_without_command=True, *args, **kwargs)

    def list_commands(self, context: click.Context):
        commands = []
        for filename in cmd_folder.iterdir():
            if filename.name.endswith(".py") and filename.name.startswith("cmd_"):
                commands.append(filename.name[4:-3])
        commands.sort()
        return commands

    def get_command(self, context: click.Context, name: str):
        try:
            mod = __import__(f"trcli.commands.cmd_{name}", None, None, ["cli"])
        except ImportError:
            print("trcli failed to load")
            return
        return mod.cli


@click.command(cls=TRCLI, context_settings=CONTEXT_SETTINGS)
@click.pass_context
@pass_environment
@click.option(
    "-c",
    "--config",
    type=click.Path(),
    default=default_config_file_path,
    help="Optional path definition for testrail-credentials file or CF file.",
)
@click.option("-h", "--host", help="Hostname of instance.")
@click.option("--project", help="Name of project the Test Run should be created under.")
@click.option("--title", help="Title of Test Run to be created in TestRail.")
@click.option("-u", "--username", type=click.STRING, help="Username.")
@click.option("-p", "--password", type=click.STRING, help="Password.")
@click.option("-k", "--key", help="API key.")
@click.option("-v", "--verbose", is_flag=True, help="Enables verbose logging.")
@click.option("--verify", is_flag=True, help="Verify the data was added correctly.")
@click.option(
    "-b",
    "--batch-size",
    type=click.IntRange(min=2),
    default=50,
    show_default="50",
    help="Configurable batch size.",
)
@click.option(
    "-t",
    "--timeout",
    type=click.IntRange(min=0),
    default=30,
    show_default="30",
    help="Batch timeout duration.",
)
@click.option(
    "--suite-id",
    type=click.IntRange(min=1),
    help="Suite ID for the results they are reporting.",
)
@click.option(
    "--run-id",
    type=click.IntRange(min=1),
    help="Run ID for the results they are reporting (otherwise the tool will attempt to create a new run).",
)
@click.option(
    "--case-id",
    type=click.IntRange(min=1),
    help=" (otherwise the tool will attempt to create a new run).",
)
@click.option(
    "-y",
    "--yes",
    "prompt_auto_creation",
    flag_value="True",
    help="answer 'yes' to all prompts around auto-creation",
)
@click.option(
    "-n",
    "--no",
    "prompt_auto_creation",
    flag_value="False",
    help="answer 'no' to all prompts around auto-creation",
)
@click.option("-s", "--silent", flag_value="yes", help="Silence stdout")
def cli(environment: Environment, context: click.core.Context, *args, **kwargs):
    """TestRail CLI"""
    if not sys.argv[1:]:
        click.echo(TOOL_VERSION_AND_USAGE)
        exit(0)

    # This check is due to usage of invoke_without_command=True in TRCLI class.
    if not context.invoked_subcommand:
        print(MISSING_COMMAND_SLOGAN)
        exit(2)

    environment.set_config_file(context)
    environment.set_parameters(context)
