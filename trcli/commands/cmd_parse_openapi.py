from xml.etree.ElementTree import ParseError

import click
from junitparser import JUnitXmlError

from trcli import settings
from trcli.api.results_uploader import ResultsUploader
from trcli.cli import pass_environment, Environment, CONTEXT_SETTINGS
from trcli.constants import FAULT_MAPPING
from trcli.data_classes.validation_exception import ValidationException
from trcli.readers.openapi_yml import OpenApiParser


def print_config(env: Environment):
    env.log(f"Parse OpenAPI Execution Parameters"
            f"\n> OpenAPI file: {env.file}"
            f"\n> Config file: {env.config}"
            f"\n> TestRail instance: {env.host} (user: {env.username})"
            f"\n> Project: {env.project if env.project else env.project_id}"
            f"\n> Auto-create entities: {env.auto_creation_response}")


@click.command(context_settings=CONTEXT_SETTINGS)
@click.option("-f", "--file", type=click.Path(), metavar="", help="Filename and path.")
@click.option(
    "--suite-id",
    type=click.IntRange(min=1),
    metavar="",
    help="Suite ID to create the tests in (if project is multi-suite).",
)
@click.option(
    "--case-fields",
    multiple=True,
    metavar="",
    default=[],
    help="List of case fields and values for new test cases creation. "
         "Usage: --case-fields type_id:1 --case-fields priority_id:3",
)
@click.pass_context
@pass_environment
def cli(environment: Environment, context: click.Context, *args, **kwargs):
    """Parse OpenAPI spec and create cases in TestRail"""
    environment.cmd = "parse_openapi"
    environment.set_parameters(context)
    environment.check_for_required_parameters()
    settings.ALLOW_ELAPSED_MS = environment.allow_ms
    print_config(environment)
    try:
        parsed_suites = OpenApiParser(environment).parse_file()
        for suite in parsed_suites:
            result_uploader = ResultsUploader(environment=environment, suite=suite, skip_run=True)
            result_uploader.upload_results()
    except FileNotFoundError:
        environment.elog(FAULT_MAPPING["missing_file"])
        exit(1)
    except (JUnitXmlError, ParseError):
        environment.elog(FAULT_MAPPING["invalid_file"])
        exit(1)
    except ValidationException as exception:
        environment.elog(
            FAULT_MAPPING["dataclass_validation_error"].format(
                field=exception.field_name,
                class_name=exception.class_name,
                reason=exception.reason,
            )
        )
        exit(1)
