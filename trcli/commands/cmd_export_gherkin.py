import click
from pathlib import Path

from trcli.cli import pass_environment, Environment, CONTEXT_SETTINGS
from trcli.constants import FAULT_MAPPING
from trcli.api.api_client import APIClient
from trcli.api.api_request_handler import ApiRequestHandler
from trcli.data_classes.dataclass_testrail import TestRailSuite
import trcli


@click.command(context_settings=CONTEXT_SETTINGS)
@click.option(
    "--case-id",
    type=click.IntRange(min=1),
    metavar="",
    required=True,
    help="TestRail test case ID to export as .feature file.",
)
@click.option(
    "--output",
    type=click.Path(),
    metavar="",
    help="Output path for the .feature file. If not specified, prints to stdout.",
)
@click.option("-v", "--verbose", is_flag=True, help="Enable verbose logging output.")
@click.pass_context
@pass_environment
def cli(environment: Environment, context: click.Context, case_id: int, output: str, **kwargs):
    """Export BDD test case from TestRail as .feature file

    This command retrieves a test case from TestRail's BDD endpoint
    and exports it as a Gherkin .feature file.

    The test case must have been created via the BDD import functionality
    for this command to work.

    Mapping Rules (TestRail to .feature):
        - Test Case name → Feature:
        - Preconditions field → Free text after Feature:
        - BDD Scenario field → Background:/Scenario:/Scenario Outline:/Rule:
        - Reference field → @Tags before Feature: (@ added)
        - BDD field tags → @Tags before scenarios

    Examples:
        # Export to file
        trcli export_gherkin --case-id 456 --output login.feature --project-id 1

        # Print to stdout
        trcli export_gherkin --case-id 456 --project-id 1
    """
    environment.cmd = "export_gherkin"
    environment.set_parameters(context)
    environment.check_for_required_parameters()

    # Set up logging
    if kwargs.get("verbose"):
        environment.verbose = True

    try:
        environment.vlog(f"Target case ID: {case_id}")
        environment.vlog(f"API endpoint: GET /api/v2/get_bdd/{case_id}")

        # Initialize API client
        environment.log("Connecting to TestRail...")

        # Create APIClient
        uploader_metadata = APIClient.build_uploader_metadata(version=trcli.__version__)
        api_client = APIClient(
            host_name=environment.host,
            verify=not environment.insecure,
            verbose_logging_function=environment.vlog,
            logging_function=environment.log,
            uploader_metadata=uploader_metadata,
        )

        # Set credentials after initialization
        api_client.username = environment.username
        api_client.password = environment.password
        api_client.api_key = environment.key

        # Create minimal suite for ApiRequestHandler (BDD operations don't need suite data)
        minimal_suite = TestRailSuite(name="BDD Export", testsections=[])

        # Create ApiRequestHandler
        api_request_handler = ApiRequestHandler(
            environment=environment,
            api_client=api_client,
            suites_data=minimal_suite,
        )

        # Get BDD test case
        environment.log(f"Retrieving BDD test case {case_id}...")
        feature_content, error_message = api_request_handler.get_bdd(case_id)

        if error_message:
            environment.elog(f"Error retrieving test case: {error_message}")
            exit(1)

        if not feature_content or not feature_content.strip():
            environment.elog(f"Error: No BDD content found for case ID {case_id}")
            environment.elog("This test case may not have been created via BDD import.")
            exit(1)

        # Output results
        if output:
            output_path = Path(output)

            if environment.verbose:
                environment.log(f"Writing feature file to: {output_path}")

            # Create parent directory if it doesn't exist
            output_path.parent.mkdir(parents=True, exist_ok=True)

            with open(output_path, "w", encoding="utf-8") as f:
                f.write(feature_content)

            environment.log(f"\n✓ Successfully exported test case {case_id}")
            environment.log(f"  File: {output_path}")
            environment.log(f"  Size: {len(feature_content)} characters")
        else:
            # Print to stdout
            print(feature_content)

    except PermissionError:
        environment.elog(f"Error: Permission denied writing to file: {output}")
        exit(1)
    except IOError as e:
        environment.elog(f"Error writing file: {str(e)}")
        exit(1)
    except Exception as e:
        environment.elog(f"Unexpected error: {str(e)}")
        if environment.verbose:
            import traceback

            environment.elog(traceback.format_exc())
        exit(1)
