import click
import json

from trcli.api.results_uploader import ResultsUploader
from trcli.cli import pass_environment, Environment, CONTEXT_SETTINGS
from trcli.commands.results_parser_helpers import results_parser_options, print_config
from trcli.constants import FAULT_MAPPING, ProjectErrors
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
@click.option(
    "-v",
    "--verbose",
    is_flag=True,
    help="Enable verbose logging output.",
)
@click.pass_context
@pass_environment
def cli(environment: Environment, context: click.Context, *args, **kwargs):
    """Parse Cucumber JSON results and upload to TestRail

    This command parses Cucumber JSON test results and uploads them to TestRail.
    """
    environment.cmd = "parse_cucumber"
    environment.set_parameters(context)
    environment.check_for_required_parameters()

    # Set verbose mode if requested
    if kwargs.get("verbose"):
        environment.verbose = True

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
        # Only create test cases if auto-creation is enabled
        if upload_feature and environment.auto_creation_response:
            environment.log("\n=== Phase 1: Creating BDD Test Cases ===")

            # Setup API client
            from trcli.api.api_request_handler import ApiRequestHandler
            from trcli.api.api_client import APIClient
            import trcli

            environment.vlog("Initializing API client for BDD upload...")
            uploader_metadata = APIClient.build_uploader_metadata(version=trcli.__version__)
            api_client = APIClient(
                host_name=environment.host,
                verify=not environment.insecure,
                verbose_logging_function=environment.vlog,
                logging_function=environment.log,
                uploader_metadata=uploader_metadata,
            )

            # Set credentials
            api_client.username = environment.username
            api_client.password = environment.password
            api_client.api_key = environment.key

            # Create minimal suite for ApiRequestHandler
            minimal_suite = parsed_suites[0] if parsed_suites else None
            if not minimal_suite:
                from trcli.data_classes.dataclass_testrail import TestRailSuite

                minimal_suite = TestRailSuite(name="Cucumber BDD", testsections=[])

            # Set suite_id from environment if provided
            if environment.suite_id:
                minimal_suite.suite_id = environment.suite_id

            # Create ApiRequestHandler
            api_handler = ApiRequestHandler(
                environment=environment,
                api_client=api_client,
                suites_data=minimal_suite,
            )

            # Resolve project to get actual project_id
            environment.log("Checking project. ", new_line=False)
            project_data = api_handler.get_project_data(environment.project, environment.project_id)

            # Validate project was found
            if project_data.project_id == ProjectErrors.not_existing_project:
                environment.elog(f"\n{project_data.error_message}")
                exit(1)
            elif project_data.project_id == ProjectErrors.other_error:
                environment.elog(f"\nError checking project: {project_data.error_message}")
                exit(1)
            elif project_data.project_id == ProjectErrors.multiple_project_same_name:
                environment.elog(f"\nError checking project: {project_data.error_message}")
                exit(1)

            environment.log("Done.")
            resolved_project_id = project_data.project_id

            # Get BDD template ID
            environment.log("Getting BDD template ID...")
            bdd_template_id, error_message = api_handler.get_bdd_template_id(resolved_project_id)

            if error_message:
                environment.elog(f"Error getting BDD template: {error_message}")
                exit(1)

            environment.vlog(f"Using BDD template ID: {bdd_template_id}")

            # Load Cucumber JSON to access raw feature data
            parser = CucumberParser(environment)
            with open(environment.file, "r", encoding="utf-8") as f:
                cucumber_data = json.load(f)

            if not isinstance(cucumber_data, list) or not cucumber_data:
                environment.elog("Error: Invalid Cucumber JSON format")
                exit(1)

            # Create BDD test cases (one per feature)
            environment.log("Creating BDD test cases from features...")
            case_ids = []
            feature_scenario_counts = []  # Track how many scenarios per feature

            for feature in cucumber_data:
                feature_name = feature.get("name", "Untitled Feature")

                # Count scenarios in this feature (excluding backgrounds)
                scenario_count = sum(
                    1
                    for element in feature.get("elements", [])
                    if element.get("type", "") in ("scenario", "scenario_outline")
                )

                if scenario_count == 0:
                    environment.vlog(f"Skipping feature '{feature_name}' - no scenarios found")
                    continue

                # Generate complete .feature file content for this feature
                environment.vlog(f"Generating .feature file for feature: {feature_name}")
                feature_content = parser._generate_feature_content(feature)

                # Upload .feature file via add_bdd endpoint
                environment.vlog(f"Uploading feature '{feature_name}' with {scenario_count} scenario(s)")
                returned_case_ids, error_message = api_handler.add_bdd(
                    section_id=feature_section_id, feature_content=feature_content
                )

                if error_message:
                    environment.elog(f"Error creating BDD test case for feature '{feature_name}': {error_message}")
                    exit(1)

                if not returned_case_ids or len(returned_case_ids) == 0:
                    environment.elog(f"Error: add_bdd did not return a case ID for feature '{feature_name}'")
                    exit(1)

                case_id = returned_case_ids[0]  # add_bdd returns list with one case ID
                case_ids.append(case_id)
                feature_scenario_counts.append(scenario_count)
                environment.vlog(f"  Created case ID: {case_id} (covers {scenario_count} scenario(s))")

                # Set automation_id on the created test case for future matching
                # Use feature name as automation_id (one TestRail case = one feature)
                automation_id = feature_name
                success, error_message = api_handler.update_case_automation_id(case_id, automation_id)

                if not success:
                    environment.log(f"  Warning: Failed to set automation_id: {error_message}")
                else:
                    environment.vlog(f"  Set automation_id: '{automation_id}'")

            environment.log(f"✓ Successfully created {len(case_ids)} BDD test case(s)")
            environment.log(f"  Case IDs: {', '.join(map(str, case_ids))}")

            # Map returned case IDs to parsed test cases
            environment.vlog("\nMapping case IDs to test results...")

            # Map case IDs to sections (one case ID per feature/section)
            # Each feature creates one test case in TestRail but may have multiple scenario results
            total_mapped = 0
            if len(case_ids) != len(parsed_suites[0].testsections):
                environment.elog(
                    f"Error: Mismatch between features ({len(case_ids)}) and parsed sections ({len(parsed_suites[0].testsections)})"
                )
                exit(1)

            for section, case_id, scenario_count in zip(
                parsed_suites[0].testsections, case_ids, feature_scenario_counts
            ):
                environment.vlog(
                    f"Mapping case ID {case_id} to section '{section.name}' ({len(section.testcases)} scenario(s))"
                )

                # Assign the same case ID to ALL test cases (scenarios) in this section
                for test_case in section.testcases:
                    test_case.case_id = case_id
                    if test_case.result:
                        test_case.result.case_id = case_id
                    total_mapped += 1

            environment.vlog(f"Mapped {len(case_ids)} case ID(s) to {total_mapped} test result(s)")

            environment.log("\nProceeding to upload test results...")
        elif upload_feature and not environment.auto_creation_response:
            # Auto-creation is disabled, skip test case creation
            environment.log("\n=== Skipping BDD Test Case Creation ===")
            environment.log("Auto-creation disabled (-n flag). Will match scenarios using automation_id.")

        # Upload test results
        environment.log("\n=== Phase 2: Uploading Test Results ===")

        # Ensure all suites have suite_id set from environment
        for suite in parsed_suites:
            if environment.suite_id and not suite.suite_id:
                suite.suite_id = environment.suite_id

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
