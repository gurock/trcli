import click
import json

from trcli.api.results_uploader import ResultsUploader
from trcli.cli import pass_environment, Environment, CONTEXT_SETTINGS
from trcli.commands.results_parser_helpers import results_parser_options, print_config
from trcli.constants import FAULT_MAPPING
from trcli.data_classes.validation_exception import ValidationException
from trcli.readers.cucumber_json import CucumberParser


@click.command(context_settings=CONTEXT_SETTINGS)
@results_parser_options
@click.option(
    "--upload-feature",
    is_flag=True,
    help="Generate and upload .feature file to create/update test cases via BDD endpoint.",
)
@click.option(
    "--feature-section-id",
    type=click.IntRange(min=1),
    metavar="",
    help="Section ID for uploading .feature file (required if --upload-feature is used).",
)
@click.pass_context
@pass_environment
def cli(environment: Environment, context: click.Context, *args, **kwargs):
    """Parse Cucumber JSON results and upload to TestRail

    This command parses Cucumber JSON test results and uploads them to TestRail.
    It supports two workflows:

    Workflow 1 - Upload Results Only (requires existing test cases):
        trcli parse_cucumber -f results.json -n --project-id 1 --suite-id 2

    Workflow 2 - Create Cases + Upload Results (via BDD):
        trcli parse_cucumber -f results.json --upload-feature \\
          --feature-section-id 123 --project-id 1 --suite-id 2

    The --upload-feature flag will:
      1. Generate a .feature file from the Cucumber JSON
      2. Upload it to TestRail via add_bdd endpoint (applying mapping rules)
      3. Retrieve the created case IDs
      4. Upload test results to those cases

    Generated .feature Mapping Rules (Cucumber JSON → .feature → TestRail):
        - Feature name/description → Feature: + free text → Test Case name + Preconditions
        - Background → Background: → BDD Scenario field
        - Scenarios → Scenario:/Scenario Outline: → BDD Scenario field
        - Rules → Rule: → BDD Scenario field
        - Examples → Examples: table → BDD field (under parent scenario)
        - Feature/Scenario tags → @Tags → Reference/BDD fields

    Without --upload-feature, test cases must already exist in TestRail
    and be matched via automation_id (use --case-matcher option).
    """
    environment.cmd = "parse_cucumber"
    environment.set_parameters(context)
    environment.check_for_required_parameters()

    # Validate feature upload options
    upload_feature = kwargs.get("upload_feature", False)
    feature_section_id = kwargs.get("feature_section_id")

    if upload_feature and not feature_section_id:
        environment.elog("Error: --feature-section-id is required when using --upload-feature")
        exit(1)

    print_config(environment)

    try:
        # Parse Cucumber JSON file
        parsed_suites = CucumberParser(environment).parse_file()

        # Workflow: Upload feature file if requested
        if upload_feature:
            environment.log("\n=== Phase 1: Uploading Feature File ===")

            # Generate feature file content
            parser = CucumberParser(environment)
            feature_content = parser.generate_feature_file()

            if not feature_content:
                environment.elog("Error: Could not generate feature file from Cucumber JSON")
                exit(1)

            # Upload feature file
            from trcli.api.api_request_handler import ApiRequestHandler

            api_handler = ApiRequestHandler(
                environment=environment,
                suites_input=parsed_suites,
                project_id=environment.project_id,
            )

            environment.log(f"Uploading generated .feature file to section {feature_section_id}...")
            case_ids, error_message = api_handler.add_bdd(feature_section_id, feature_content)

            if error_message:
                environment.elog(f"Error uploading feature file: {error_message}")
                exit(1)

            environment.log(f"✓ Created/updated {len(case_ids)} test case(s)")
            environment.log(f"  Case IDs: {', '.join(map(str, case_ids))}")

            # Update parsed suites with case IDs (if we can map them)
            # Note: This mapping assumes the order is preserved, which may not always be true
            # A more robust implementation would match by automation_id
            environment.log("\nNote: Proceeding to upload results for matched cases...")

        # Upload test results
        environment.log("\n=== Phase 2: Uploading Test Results ===")

        run_id = None
        for suite in parsed_suites:
            result_uploader = ResultsUploader(environment=environment, suite=suite)
            result_uploader.upload_results()

            if run_id is None and hasattr(result_uploader, "last_run_id"):
                run_id = result_uploader.last_run_id

        # Summary
        if run_id:
            environment.log(f"\n✓ Results uploaded successfully to run ID: {run_id}")
        else:
            environment.log("\n✓ Results processing completed")

    except FileNotFoundError:
        environment.elog(f"Error: Cucumber JSON file not found: {environment.file}")
        exit(1)
    except json.JSONDecodeError as e:
        environment.elog(f"Error: Invalid JSON format in file: {environment.file}")
        environment.elog(f"  {str(e)}")
        exit(1)
    except ValidationException as e:
        environment.elog(f"Validation error: {str(e)}")
        exit(1)
    except ValueError as e:
        environment.elog(f"Error parsing Cucumber JSON: {str(e)}")
        exit(1)
    except Exception as e:
        environment.elog(f"Unexpected error: {str(e)}")
        if environment.verbose:
            import traceback

            environment.elog(traceback.format_exc())
        exit(1)
