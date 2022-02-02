import click
from junitparser import JUnitXmlError
from trcli.cli import pass_environment, Environment, CONTEXT_SETTINGS
from trcli.constants import FAULT_MAPPING
from trcli.readers.junit_xml import JunitParser
from trcli.api.results_uploader import ResultsUploader
from trcli.data_classes.validation_exception import ValidationException
from xml.etree.ElementTree import ParseError


@click.command(context_settings=CONTEXT_SETTINGS)
@click.option("-f", "--file", type=click.Path(), metavar="", help="Filename and path.")
@click.pass_context
@pass_environment
def cli(environment: Environment, context: click.Context, file):
    """Parse Junit XML files (& similar)"""
    environment.set_parameters(context)
    environment.check_for_required_parameters()
    try:
        result_uploader = ResultsUploader(
            environment=environment, result_file_parser=JunitParser(environment.file)
        )
        result_uploader.upload_results()
    except FileNotFoundError:
        environment.log(FAULT_MAPPING["missing_file"])
        exit(1)
    except (JUnitXmlError, ParseError):
        environment.log(FAULT_MAPPING["invalid_file"])
        exit(1)
    except ValidationException as exception:
        environment.log(
            FAULT_MAPPING["dataclass_validation_error"].format(
                field=exception.field_name,
                class_name=exception.class_name,
                reason=exception.reason,
            )
        )
        exit(1)
