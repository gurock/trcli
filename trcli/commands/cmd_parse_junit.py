import click
from junitparser import JUnitXmlError
from trcli.cli import pass_environment, Environment, CONTEXT_SETTINGS
from trcli.constants import FAULT_MAPPING
from trcli.readers.junit_xml import JunitParser
from trcli.api.results_uploader import ResultsUploader
from trcli.data_classes.validation_exception import ValidationException
from xml.etree.ElementTree import ParseError


def print_config(env: Environment):
    env.log(f"TestRail CLI - Execution Parameters"
            f"\n> Report file: {env.file}"
            f"\n> Config file: {env.config}"
            f"\n> TestRail instance: {env.host} (user: {env.username})"
            f"\n> Project: {env.project if env.project else env.project_id}"
            f"\n> Run title: {env.title}"
            f"\n> Auto-create entities: {env.auto_creation_response}")


@click.command(context_settings=CONTEXT_SETTINGS)
@click.option("-f", "--file", type=click.Path(), metavar="", help="Filename and path.")
@click.option("--close-run", is_flag=True, help="Close the newly created run")
@click.option("--title", metavar="", help="Title of Test Run to be created in TestRail.")
@click.option(
    "--case-matcher",
    metavar="",
    default="auto",
    type=click.Choice(["auto", "name", "property"], case_sensitive=False),
    help="Mechanism to match cases between the JUnit report and TestRail."
)
@click.option(
    "--suite-id",
    type=click.IntRange(min=1),
    metavar="",
    help="Suite ID for the results they are reporting.",
)
@click.option(
    "--run-id",
    type=click.IntRange(min=1),
    metavar="",
    help="Run ID for the results they are reporting (otherwise the tool will attempt to create a new run).",
)
@click.option("--run-description", metavar="", default="", help="Summary text to be added to the test run.")
@click.option(
    "--case-fields",
    multiple=True,
    metavar="",
    default=[],
    help="List of case fields and values for new test cases creation. "
         "Usage: --case-fields type_id:1 --case-fields priority_id:3",
)
@click.option(
    "--result-fields",
    multiple=True,
    metavar="",
    default=[],
    help="List of result fields and values for test results creation. "
         "Usage: --result-fields custom_type_id:1 --result-fields custom_priority_id:3",
)
@click.pass_context
@pass_environment
def cli(environment: Environment, context: click.Context, *args, **kwargs):
    """Parse report files and upload results to TestRail"""
    environment.set_parameters(context)
    environment.check_for_required_parameters()
    print_config(environment)
    try:
        result_uploader = ResultsUploader(
            environment=environment, result_file_parser=JunitParser(environment)
        )
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
