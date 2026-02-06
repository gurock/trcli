import click
import json

from trcli.api.results_uploader import ResultsUploader
from trcli.cli import pass_environment, Environment, CONTEXT_SETTINGS
from trcli.commands.results_parser_helpers import bdd_parser_options, print_config
from trcli.constants import FAULT_MAPPING, ProjectErrors
from trcli.data_classes.validation_exception import ValidationException
from trcli.readers.cucumber_json import CucumberParser


@click.command(context_settings=CONTEXT_SETTINGS)
@bdd_parser_options
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

    This command parses Cucumber JSON test results and uploads them to TestRail
    using BDD matching mode. Features are matched to TestRail BDD test cases by
    feature name only (case-insensitive, whitespace-normalized).

    BDD Matching:
    - Matches Cucumber features to TestRail BDD test cases by feature name
    - Auto-creates missing BDD test cases by default (use -n to disable)
    - Sections are auto-created based on feature names
    - Does not use automation_id or case-matcher (BDD uses feature name matching only)
    """
    environment.cmd = "parse_cucumber"
    environment.set_parameters(context)
    environment.check_for_required_parameters()

    # Set verbose mode if requested
    if kwargs.get("verbose"):
        environment.verbose = True

    print_config(environment)

    try:
        # Setup API client and handler (needed for both modes)
        from trcli.api.api_request_handler import ApiRequestHandler
        from trcli.api.api_client import APIClient
        import trcli

        environment.vlog("Initializing API client...")
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
        from trcli.data_classes.dataclass_testrail import TestRailSuite

        minimal_suite = TestRailSuite(name="Cucumber BDD", testsections=[])
        if environment.suite_id:
            minimal_suite.suite_id = environment.suite_id

        # Create ApiRequestHandler
        api_handler = ApiRequestHandler(
            environment=environment,
            api_client=api_client,
            suites_data=minimal_suite,
        )

        # Resolve project to get actual project_id (for use in BDD parsing)
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

        # BDD Matching Mode: Set API handler for validation and caching
        parser = CucumberParser(environment)
        parser.set_api_handler(api_handler)

        # Determine auto-creation behavior:
        # - With -n flag (auto_creation_response == False): Only match existing features
        # - With -y flag (auto_creation_response == True): Auto-create missing features
        # - Without flag (auto_creation_response == None): Auto-create by default for BDD
        auto_create = environment.auto_creation_response != False

        if environment.auto_creation_response == False:
            environment.vlog("Auto-creation disabled: Will only match existing BDD test cases")
        else:
            environment.vlog("Auto-creation enabled: Will create missing BDD test cases")

        parsed_suites = parser.parse_file(
            bdd_matching_mode=True,
            project_id=resolved_project_id,
            suite_id=environment.suite_id,
            auto_create=auto_create,
        )

        # Handle auto-creation of features in BDD matching mode
        # auto_creation_response != False means: -y flag OR no flag (default to auto-create)
        if environment.auto_creation_response != False:
            # Check if there are any features that need to be created (case_id=-1)
            features_to_create = []
            for suite in parsed_suites:
                for section in suite.testsections:
                    for test_case in section.testcases:
                        if test_case.case_id == -1:
                            features_to_create.append({"section": section, "test_case": test_case})

            if features_to_create:
                environment.log(f"\n=== Auto-Creating {len(features_to_create)} Missing BDD Test Case(s) ===")

                # Load Cucumber JSON to access raw feature data
                with open(environment.file, "r", encoding="utf-8") as f:
                    cucumber_data = json.load(f)

                # Get BDD template ID
                environment.log("Getting BDD template ID...")
                bdd_template_id, error_message = api_handler.get_bdd_template_id(resolved_project_id)

                if error_message:
                    environment.elog(f"Error getting BDD template: {error_message}")
                    exit(1)

                environment.vlog(f"Using BDD template ID: {bdd_template_id}")

                # Create each missing feature
                created_case_ids = {}  # Map feature name -> case_id

                for feature in cucumber_data:
                    feature_name = feature.get("name", "Untitled Feature")
                    normalized_name = parser._normalize_title(feature_name)

                    # Check if this feature needs creation
                    needs_creation = any(
                        parser._normalize_title(item["section"].name) == normalized_name for item in features_to_create
                    )

                    if not needs_creation:
                        continue

                    # Auto-create or fetch section for this feature
                    # Use feature name as section name (matching parse behavior)
                    section_name = feature_name
                    section_id = None

                    # Try to find existing section by name
                    environment.vlog(f"Looking for section '{section_name}'...")
                    sections, error = api_handler._ApiRequestHandler__get_all_sections(
                        project_id=resolved_project_id, suite_id=environment.suite_id
                    )

                    if error:
                        environment.elog(f"Error fetching sections: {error}")
                        exit(1)

                    for s in sections:
                        if s.get("name") == section_name:
                            section_id = s.get("id")
                            environment.vlog(f"  Found existing section ID: {section_id}")
                            break

                    # Create section if not found
                    if section_id is None:
                        environment.log(f"Creating section '{section_name}'...")

                        # Use send_post to create section directly
                        section_body = {"suite_id": environment.suite_id, "name": section_name}
                        response = api_handler.client.send_post(f"add_section/{resolved_project_id}", section_body)

                        if response.error_message:
                            environment.elog(f"Error creating section: {response.error_message}")
                            exit(1)

                        section_id = response.response_text.get("id")
                        environment.vlog(f"  Created section ID: {section_id}")

                    # Generate feature content
                    environment.vlog(f"Generating .feature file for '{feature_name}'")
                    feature_content = parser._generate_feature_content(feature)

                    # Upload feature via add_bdd endpoint
                    environment.log(f"Uploading feature '{feature_name}'...")
                    returned_case_ids, error_message = api_handler.add_bdd(
                        section_id=section_id, feature_content=feature_content
                    )

                    if error_message:
                        environment.elog(f"Error creating BDD test case: {error_message}")
                        exit(1)

                    if not returned_case_ids or len(returned_case_ids) == 0:
                        environment.elog(f"Error: add_bdd did not return a case ID")
                        exit(1)

                    case_id = returned_case_ids[0]
                    created_case_ids[normalized_name] = case_id
                    environment.log(f"Created case ID: C{case_id}")

                environment.log(f"Successfully created {len(created_case_ids)} BDD test case(s)")
                environment.vlog("Clearing BDD cache to include newly created cases...")
                api_handler._bdd_case_cache.clear()

                # Also clear the RequestCache for get_cases so fresh data is fetched
                # The RequestCache caches get_cases API responses, so newly created cases
                # won't be visible until we invalidate this cache
                api_handler._cache.invalidate_pattern(f"get_cases/{resolved_project_id}")

                # Re-parse with the newly created case IDs
                environment.vlog("Re-parsing to match newly created cases...")
                parser_for_results = CucumberParser(environment)
                parser_for_results.set_api_handler(api_handler)

                # Re-parse in BDD matching mode (cache will rebuild with new cases)
                parsed_suites = parser_for_results.parse_file(
                    bdd_matching_mode=True,
                    project_id=resolved_project_id,
                    suite_id=environment.suite_id,
                    auto_create=False,  # No need to mark for creation again
                )

                environment.vlog(f"Re-parsed successfully with {len(created_case_ids)} newly created case(s)")

        # Ensure all suites have suite_id set from environment
        for suite in parsed_suites:
            if environment.suite_id and not suite.suite_id:
                suite.suite_id = environment.suite_id

        run_id = None
        for suite in parsed_suites:
            result_uploader = ResultsUploader(environment=environment, suite=suite)
            # Set project to avoid duplicate "Checking project" call
            result_uploader.project = project_data
            result_uploader.upload_results()

            if run_id is None and hasattr(result_uploader, "last_run_id"):
                run_id = result_uploader.last_run_id

        # Summary
        if run_id:
            environment.log(f"Results uploaded successfully to run ID: {run_id}")
        else:
            environment.log("Results processing completed")

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
