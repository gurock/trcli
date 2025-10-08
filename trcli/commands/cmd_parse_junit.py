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
@click.option(
    "-a", "--assign",
    "assign_failed_to",
    metavar="",
    help="Comma-separated list of user emails to assign failed test results to."
)
@click.option(
    "--test-run-ref",
    metavar="",
    help="Comma-separated list of reference IDs to append to the test run (up to 250 characters total)."
)
@click.option(
    "--json-output",
    is_flag=True,
    help="Output reference operation results in JSON format."
)
@click.pass_context
@pass_environment
def cli(environment: Environment, context: click.Context, *args, **kwargs):
    """Parse JUnit report and upload results to TestRail"""
    environment.cmd = "parse_junit"
    environment.set_parameters(context)
    environment.check_for_required_parameters()
    
    if environment.test_run_ref is not None:
        validation_error = _validate_test_run_ref(environment.test_run_ref)
        if validation_error:
            environment.elog(validation_error)
            exit(1)
    
    settings.ALLOW_ELAPSED_MS = environment.allow_ms
    print_config(environment)
    try:
        parsed_suites = JunitParser(environment).parse_file()
        run_id = None
        for suite in parsed_suites:
            result_uploader = ResultsUploader(environment=environment, suite=suite)
            result_uploader.upload_results()

            if run_id is None and hasattr(result_uploader, 'last_run_id'):
                run_id = result_uploader.last_run_id
        
        if environment.test_run_ref and run_id:
            _handle_test_run_references(environment, run_id)
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


def _validate_test_run_ref(test_run_ref: str) -> str:
    """
    Validate the test-run-ref input.
    Returns error message if invalid, None if valid.
    """
    if not test_run_ref or not test_run_ref.strip():
        return "Error: --test-run-ref cannot be empty or whitespace-only"
    
    refs = [ref.strip() for ref in test_run_ref.split(',') if ref.strip()]
    if not refs:
        return "Error: --test-run-ref contains no valid references (malformed input)"
    
    if len(test_run_ref) > 250:
        return f"Error: --test-run-ref exceeds 250 character limit ({len(test_run_ref)} characters)"
    
    return None


def _handle_test_run_references(environment: Environment, run_id: int):
    """
    Handle appending references to the test run.
    """
    from trcli.api.project_based_client import ProjectBasedClient
    from trcli.data_classes.dataclass_testrail import TestRailSuite
    import json

    refs = [ref.strip() for ref in environment.test_run_ref.split(',') if ref.strip()]
    
    project_client = ProjectBasedClient(
        environment=environment,
        suite=TestRailSuite(name="temp", suite_id=1)
    )
    project_client.resolve_project()
    
    environment.log(f"Appending references to test run {run_id}...")
    run_data, added_refs, skipped_refs, error_message = project_client.api_request_handler.append_run_references(
        run_id, refs
    )
    
    if error_message:
        environment.elog(f"Error: Failed to append references: {error_message}")
        exit(1)
    
    final_refs = run_data.get("refs", "") if run_data else ""
    
    if environment.json_output:
        # JSON output
        result = {
            "run_id": run_id,
            "added": added_refs,
            "skipped": skipped_refs,
            "total_references": final_refs
        }
        print(json.dumps(result, indent=2))
    else:
        environment.log(f"References appended successfully:")
        environment.log(f"  Run ID: {run_id}")
        environment.log(f"  Total references: {len(final_refs.split(',')) if final_refs else 0}")
        environment.log(f"  Newly added: {len(added_refs)} ({', '.join(added_refs) if added_refs else 'none'})")
        environment.log(f"  Skipped (duplicates): {len(skipped_refs)} ({', '.join(skipped_refs) if skipped_refs else 'none'})")
        if final_refs:
            environment.log(f"  All references: {final_refs}")
