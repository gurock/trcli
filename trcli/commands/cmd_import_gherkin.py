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
    "-f",
    "--file",
    type=click.Path(exists=True),
    metavar="",
    required=True,
    help="Path to Gherkin .feature file to upload.",
)
@click.option(
    "--section-id",
    type=click.IntRange(min=1),
    metavar="",
    required=False,
    help="TestRail section ID where test cases will be created (required for create mode).",
)
@click.option(
    "--case-id",
    type=click.IntRange(min=1),
    metavar="",
    required=False,
    help="TestRail case ID to update (required with --update flag).",
)
@click.option("--json-output", is_flag=True, help="Output case IDs in JSON format.")
@click.option("--update", is_flag=True, help="Update existing BDD test case instead of creating new one.")
@click.pass_context
@pass_environment
def cli(environment: Environment, context: click.Context, file: str, section_id: int, case_id: int, **kwargs):
    """Upload or update Gherkin .feature file in TestRail

    This command uploads a Gherkin/BDD .feature file directly to TestRail,
    which will create or update test cases based on the scenarios in the file.

    Two modes:
    - Create mode (default): Requires --section-id, creates new test case(s)
    - Update mode (--update): Requires --case-id, updates existing test case

    TestRail will parse the .feature file and automatically create/update test cases
    for each scenario, maintaining the BDD structure in TestRail's native format.

    Mapping Rules (.feature to TestRail):
        - Feature: → Test Case name
        - Free text after Feature: → Preconditions field
        - Background:/Scenario:/Scenario Outline:/Rule: → BDD Scenario field
        - Examples: (under Scenario Outline/Rule) → Same BDD field as parent
        - @Tags before Feature: → Reference field (@ stripped)
        - @Tags before scenarios → BDD field

    Examples:
        # Create new test case (requires --section-id)
        trcli import_gherkin -f login.feature --section-id 123 --project-id 1

        # Update existing test case (requires --case-id)
        trcli import_gherkin -f login.feature --case-id 456 --update --project-id 1
    """
    environment.cmd = "import_gherkin"
    environment.set_parameters(context)
    environment.check_for_required_parameters()

    json_output = kwargs.get("json_output", False)
    update_mode = kwargs.get("update", False)

    # Validate mutually exclusive parameters
    if update_mode:
        if not case_id:
            environment.elog("Error: --case-id is required when using --update flag")
            exit(1)
        if section_id:
            environment.elog("Error: --section-id cannot be used with --update flag (use --case-id instead)")
            exit(1)
    else:
        if not section_id:
            environment.elog("Error: --section-id is required for create mode")
            exit(1)
        if case_id:
            environment.elog("Error: --case-id can only be used with --update flag")
            exit(1)

    try:
        # Read the feature file
        feature_path = Path(file)
        if environment.verbose:
            environment.log(f"Reading feature file: {feature_path}")

        with open(feature_path, "r", encoding="utf-8") as f:
            feature_content = f.read()

        if not feature_content.strip():
            environment.elog("Error: Feature file is empty")
            exit(1)

        endpoint_name = "update_bdd" if update_mode else "add_bdd"
        target_id = case_id if update_mode else section_id
        id_type = "case ID" if update_mode else "section ID"

        environment.vlog(f"Feature file size: {len(feature_content)} characters")
        environment.vlog(f"Target {id_type}: {target_id}")
        environment.vlog(f"API endpoint: POST /api/v2/{endpoint_name}/{target_id}")

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
        minimal_suite = TestRailSuite(name="BDD Import", testsections=[])

        # Create ApiRequestHandler
        api_request_handler = ApiRequestHandler(
            environment=environment,
            api_client=api_client,
            suites_data=minimal_suite,
        )

        # Upload or update feature file based on mode
        if update_mode:
            if not json_output:
                environment.log(f"Updating existing BDD test case (C{case_id}) in TestRail...")
            case_ids, error_message = api_request_handler.update_bdd(case_id, feature_content)
        else:
            if not json_output:
                environment.log(f"Uploading feature file to TestRail...")
            case_ids, error_message = api_request_handler.add_bdd(section_id, feature_content)

        if error_message:
            action = "updating" if update_mode else "uploading"
            environment.elog(f"Error {action} feature file: {error_message}")
            exit(1)

        if not case_ids:
            action = "updated" if update_mode else "uploaded"
            environment.log("Warning: No case IDs returned from TestRail")
            environment.log(f"Feature file was {action} but no cases were created/updated.")
            exit(0)

        # Display results
        if kwargs.get("json_output"):
            import json

            print(json.dumps({"case_ids": case_ids, "count": len(case_ids)}, indent=2))
        else:
            if update_mode:
                environment.log(f"\nSuccessfully updated feature file!")
                environment.log(f"  Updated {len(case_ids)} test case(s)")
            else:
                environment.log(f"\nSuccessfully uploaded feature file!")
                environment.log(f"  Created {len(case_ids)} test case(s)")
            environment.log(f"  Case IDs: {', '.join(map(str, case_ids))}")

    except FileNotFoundError:
        environment.elog(f"Error: Feature file not found: {file}")
        exit(1)
    except PermissionError:
        environment.elog(f"Error: Permission denied reading feature file: {file}")
        exit(1)
    except UnicodeDecodeError:
        environment.elog(f"Error: Feature file must be UTF-8 encoded: {file}")
        exit(1)
    except Exception as e:
        environment.elog(f"Unexpected error: {str(e)}")
        if environment.verbose:
            import traceback

            environment.elog(traceback.format_exc())
        exit(1)
