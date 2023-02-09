import json
import os
import sys
from typing import List, Union

import click
import yaml
from pathlib import Path
from requests.models import PreparedRequest, InvalidURL, MissingSchema

from click.core import ParameterSource
from tqdm import tqdm

from trcli.constants import (
    FAULT_MAPPING,
    MISSING_COMMAND_SLOGAN,
    TOOL_USAGE,
    TOOL_VERSION,
)
from trcli.data_classes.data_parsers import FieldsParser
from trcli.settings import DEFAULT_API_CALL_TIMEOUT, DEFAULT_BATCH_SIZE

CONTEXT_SETTINGS = dict(auto_envvar_prefix="TR_CLI")

trcli_folder = Path(__file__).parent
cmd_folder = trcli_folder / "commands/"


class Environment:
    def __init__(self):
        self.home = os.getcwd()
        self.default_config_file = True
        self.params_from_config = dict()
        self.file = None
        self.host = None
        self.project = None
        self.project_id = None
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
        self.milestone_id = None
        self.auto_creation_response = None
        self.silent = None
        self.close_run = None
        self.insecure = None
        self.run_description = None
        self.case_matcher = None
        self.special_parser = None
        self._case_fields = None
        self._result_fields = None
        self.allow_ms = False

    @property
    def case_fields(self):
        return self._case_fields

    @case_fields.setter
    def case_fields(self, case_fields: Union[List[str], dict]):
        fields_dict, error = FieldsParser.resolve_fields(case_fields)
        if error:
            self.elog(error)
            exit(1)
        self._case_fields = fields_dict

    @property 
    def result_fields(self):
        return self._result_fields

    @result_fields.setter
    def result_fields(self, result_fields: Union[List[str], dict]):
        fields_dict, error = FieldsParser.resolve_fields(result_fields)
        if error:
            self.elog(error)
            exit(1)
        self._result_fields = fields_dict

    def log(self, msg: str, new_line=True, *args):
        """Logs a message to stdout only is silent mode is disabled."""
        if not self.silent:
            if args:
                msg %= args
            click.echo(msg, file=sys.stdout, nl=new_line)

    def vlog(self, msg: str, *args):
        """Logs a message to stdout only if the verbose option is enabled."""
        if self.verbose:
            self.log(msg, *args)

    @staticmethod
    def elog(msg: str, new_line=True, *args):
        """Logs a message to stderr."""
        if args:
            msg %= args
        click.echo(msg, file=sys.stderr, nl=new_line)

    def get_progress_bar(self, results_amount: int, prefix: str):
        disabled = True if self.silent else False
        return tqdm(
            total=results_amount,
            bar_format=prefix + ": {n_fmt}/{total_fmt}{postfix}",
            disable=disabled,
        )

    def get_prompt_response_for_auto_creation(self, msg: str, *args):
        """Prompts for confirmation (yes/no) if auto_creation_response (--no/--yes parameters) is not set"""
        if self.auto_creation_response is None:
            return click.confirm(msg)
        else:
            return self.auto_creation_response

    def set_parameters(self, context: click.core.Context):
        """Sets parameters based on context. The function will override parameters with config file values
        depending on the parameter source and config file source (default or custom)"""
        if self.default_config_file:
            param_sources_types = [ParameterSource.DEFAULT]
        else:
            param_sources_types = [ParameterSource.DEFAULT, ParameterSource.ENVIRONMENT]
        for param, value in context.params.items():
            # Don't set config again
            if param == "config":
                continue
            param_config_value = self.params_from_config.get(param, None)
            param_source = context.get_parameter_source(param)
            if param_source in param_sources_types and (param_config_value is not None):
                setattr(self, param, param_config_value)
            else:
                setattr(self, param, value)

    def check_for_required_parameters(self):
        """Checks that all required parameters were set. If not error message would be printed and
        program will exit with exit code 1"""
        for param, value in vars(self).items():
            if "missing_" + param in FAULT_MAPPING and not value:
                self.elog(FAULT_MAPPING["missing_" + param])
                exit(1)
        # special case for password and key (both needs to be missing for the error message to show up)
        if not self.password and not self.key:
            self.elog(FAULT_MAPPING["missing_password_and_key"])
            exit(1)
        # validate host syntax
        try:
            request = PreparedRequest()
            request.prepare_url(self.host, params=None)
        except (InvalidURL, MissingSchema):
            self.elog(FAULT_MAPPING["host_issues"])
            exit(1)

    def parse_config_file(self, context: click.Context):
        """Sets config file path from context and information if default or custom config file should be used."""
        executable_folder = Path(sys.argv[0]).parent

        if context.params["config"]:
            self.config = context.params["config"]
            self.default_config_file = False
        else:
            if Path(executable_folder / "config.yml").is_file():
                self.config = executable_folder / "config.yml"
            elif Path(executable_folder / "config.yaml").is_file():
                self.config = executable_folder / "config.yaml"
            else:
                self.config = None
        if self.config:
            self.parse_params_from_config_file(self.config)

    def parse_params_from_config_file(self, file_path: Path):
        self.params_from_config = {}
        try:
            with open(file_path, "r") as f:
                file_content = yaml.safe_load_all(f)
                for page_content in file_content:
                    if page_content:
                        self.params_from_config.update(page_content)
                        if (
                            self.params_from_config.get("config") is not None
                            and self.default_config_file
                        ):
                            self.default_config_file = False
                            self.parse_params_from_config_file(
                                self.params_from_config["config"]
                            )
        except (yaml.YAMLError, ValueError, TypeError) as e:
            self.elog(
                FAULT_MAPPING["yaml_file_parse_issue"].format(file_path=file_path)
            )
            self.elog(f"Error details:\n{e}")
            if not self.default_config_file:
                exit(1)
            self.params_from_config = {}
        except IOError:
            self.elog(FAULT_MAPPING["file_open_issue"].format(file_path=file_path))
            if not self.default_config_file:
                exit(1)
            self.params_from_config = {}


pass_environment = click.make_pass_decorator(Environment, ensure=True)


class TRCLI(click.MultiCommand):
    def __init__(self, *args, **kwargs):
        # Use invoke_without_command=True to be able to print
        # short tool description when starting without parameters
        print(TOOL_VERSION)
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
    metavar="",
    help="Optional path definition for testrail-credentials file or CF file.",
)
@click.option("-h", "--host", metavar="", help="Hostname of instance.")
@click.option(
    "--project",
    metavar="",
    help="Name of project the Test Run should be created under.",
)
@click.option(
    "--project-id",
    type=click.IntRange(min=1),
    metavar="",
    help="Project id. Will be only used in case project name will be duplicated in TestRail",
)
@click.option("-u", "--username", type=click.STRING, metavar="", help="Username.")
@click.option("-p", "--password", type=click.STRING, metavar="", help="Password.")
@click.option("-k", "--key", metavar="", help="API key.")
@click.option(
    "-v", "--verbose", is_flag=True, help="Output all API calls and their results."
)
@click.option("--verify", is_flag=True, help="Verify the data was added correctly.")
@click.option("--insecure", is_flag=True, help="Allow insecure requests.")
@click.option(
    "-b",
    "--batch-size",
    type=click.IntRange(min=2),
    default=DEFAULT_BATCH_SIZE,
    show_default=str(DEFAULT_BATCH_SIZE),
    metavar="",
    help="Configurable batch size.",
)
@click.option(
    "-t",
    "--timeout",
    type=click.FloatRange(min=0),
    default=DEFAULT_API_CALL_TIMEOUT,
    show_default=str(DEFAULT_API_CALL_TIMEOUT),
    metavar="",
    help="Batch timeout duration.",
)
@click.option(
    "-y",
    "--yes",
    "auto_creation_response",
    flag_value=True,
    help="answer 'yes' to all prompts around auto-creation",
    default=None,
)
@click.option(
    "-n",
    "--no",
    "auto_creation_response",
    flag_value=False,
    help="answer 'no' to all prompts around auto-creation",
    default=None,
)
@click.option(
    "-s",
    "--silent",
    flag_value=True,
    is_flag=True,
    help="Silence stdout",
    default=False,
)
def cli(environment: Environment, context: click.core.Context, *args, **kwargs):
    """TestRail CLI"""
    if not sys.argv[1:]:
        click.echo(TOOL_USAGE)
        exit(0)

    # This check is due to usage of invoke_without_command=True in TRCLI class.
    if not context.invoked_subcommand:
        print(MISSING_COMMAND_SLOGAN)
        exit(2)

    environment.parse_config_file(context)
    environment.set_parameters(context)
