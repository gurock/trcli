from xml.etree.ElementTree import ParseError

import click
from junitparser import JUnitXmlError

from trcli import settings
from trcli.api.results_uploader import ResultsUploader
from trcli.cli import pass_environment, Environment, CONTEXT_SETTINGS
from trcli.commands.results_parser_helpers import results_parser_options, print_config
from trcli.constants import FAULT_MAPPING
from trcli.data_classes.validation_exception import ValidationException
from trcli.readers.junit_xml import JunitParser


@click.command(context_settings=CONTEXT_SETTINGS)
@results_parser_options
@click.option(
    "--special-parser",
    metavar="",
    default="junit",
    type=click.Choice(["junit", "saucectl"], case_sensitive=False),
    help="Optional special parser option for specialized JUnit reports."
)
@click.pass_context
@pass_environment
def cli(environment: Environment, context: click.Context, *args, **kwargs):
    """Parse JUnit report and upload results to TestRail"""
    environment.cmd = "parse_junit"
    environment.set_parameters(context)
    environment.check_for_required_parameters()
    settings.ALLOW_ELAPSED_MS = environment.allow_ms
    print_config(environment)
    try:
        parsed_suites = JunitParser(environment).parse_file()
        for suite in parsed_suites:
            result_uploader = ResultsUploader(environment=environment, suite=suite)
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
