import builtins
import click
import json

from trcli.api.api_client import APIClient
from trcli.api.result_handler import ResultHandler
from trcli.cli import pass_environment, CONTEXT_SETTINGS, Environment


def print_config(env: Environment, action: str):
    env.log(f"Results {action} Execution Parameters" f"\n> TestRail instance: {env.host} (user: {env.username})")


@click.group(context_settings=CONTEXT_SETTINGS)
@click.pass_context
@pass_environment
def cli(environment: Environment, context: click.Context, *args, **kwargs):
    """Manage test results in TestRail"""
    environment.cmd = "results"
    environment.set_parameters(context)


@cli.command()
@click.option("--test-id", type=click.IntRange(min=1), metavar="", help="Test ID to retrieve results for.")
@click.option("--run-id", type=click.IntRange(min=1), metavar="", help="Run ID to retrieve results for.")
@click.option(
    "--case-id", type=click.IntRange(min=1), metavar="", help="Case ID to retrieve results for (requires --run-id)."
)
@click.option("--offset", type=int, default=0, metavar="", help="Offset for pagination (default: 0).")
@click.option("--limit", type=int, default=250, metavar="", help="Limit for pagination (default: 250).")
@click.option("--json-output", is_flag=True, help="Output results as raw JSON from API.")
@click.option("--show-all-fields", is_flag=True, help="Show all fields including custom fields in detail.")
@click.pass_context
@pass_environment
def list(
    environment: Environment,
    context: click.Context,
    test_id: int,
    run_id: int,
    case_id: int,
    offset: int,
    limit: int,
    json_output: bool,
    show_all_fields: bool,
    *args,
    **kwargs,
):
    """List test results from TestRail"""
    print_config(environment, "List")

    # Validate mutually exclusive filters
    filters_provided = sum([test_id is not None, run_id is not None, case_id is not None])

    if filters_provided == 0:
        environment.elog("Error: One of --test-id, --run-id, or --case-id must be provided.")
        raise SystemExit(1)

    # Validate case-id requires run-id
    if case_id is not None and run_id is None:
        environment.elog("Error: --case-id requires --run-id to be specified.")
        raise SystemExit(1)

    # Validate test-id is mutually exclusive with run-id and case-id
    if test_id is not None and (run_id is not None or case_id is not None):
        environment.elog("Error: --test-id cannot be used with --run-id or --case-id.")
        raise SystemExit(1)

    # Validate run-id with case-id vs run-id alone
    if run_id is not None and case_id is not None and test_id is not None:
        environment.elog("Error: --test-id, --run-id, and --case-id cannot be used together.")
        raise SystemExit(1)

    # Create API client
    api_client = APIClient(
        host_name=environment.host,
        verbose_logging_function=environment.vlog,
        logging_function=environment.log,
        verify=environment.verify,
        timeout=environment.timeout,
    )

    # Set credentials
    api_client.username = environment.username
    api_client.password = environment.password
    api_client.api_key = environment.key

    # Create ResultHandler
    result_handler = ResultHandler(
        client=api_client,
        environment=environment,
        data_provider=None,
        get_all_tests_in_run_callback=None,
        handle_futures_callback=None,
    )

    # Retrieve results based on filter type
    if test_id is not None:
        environment.log(f"Retrieving results for test ID {test_id}...")
        results_data, error_message = result_handler.get_results(test_id, offset, limit)
    elif case_id is not None:  # case_id with run_id (validated above)
        environment.log(f"Retrieving results for case ID {case_id} in run ID {run_id}...")
        results_data, error_message = result_handler.get_results_for_case(run_id, case_id, offset, limit)
    else:  # run_id alone
        environment.log(f"Retrieving results for run ID {run_id}...")
        results_data, error_message = result_handler.get_results_for_run(run_id, offset, limit)

    if error_message:
        environment.elog(f"Error: Failed to retrieve results: {error_message}")
        raise SystemExit(1)

    # Handle output format
    if json_output:
        # Output raw API JSON response
        print(json.dumps(results_data, separators=(",", ":")))
    else:
        # Display results line by line with details
        results = results_data if isinstance(results_data, builtins.list) else []

        if not results:
            environment.log("No results found.")
        else:
            environment.log(f"Found {len(results)} result(s) (showing {offset + 1}-{offset + len(results)}):")
            environment.log("")

            for result in results:
                if show_all_fields:
                    # Show all fields from API response
                    environment.log(f"  Result ID: {result.get('id', 'N/A')}")

                    # Iterate through all fields in the result
                    for key, value in result.items():
                        if key == "id":
                            continue  # Already displayed as Result ID

                        # Format field name for display (remove underscores, title case)
                        display_name = key.replace("_", " ").title()

                        # Handle None values
                        if value is None:
                            display_value = "N/A"
                        elif isinstance(value, builtins.list):
                            # Handle list fields (like attachment_ids)
                            if value:
                                display_value = f"{len(value)} item(s): {value}"
                            else:
                                display_value = "[]"
                        else:
                            display_value = value

                        environment.log(f"    {display_name}: {display_value}")

                    environment.log("")
                else:
                    # Display standard fields with compact format
                    environment.log(f"  Result ID: {result.get('id', 'N/A')}")
                    environment.log(f"    Test ID: {result.get('test_id', 'N/A')}")
                    environment.log(f"    Status ID: {result.get('status_id', 'N/A')}")
                    environment.log(f"    Created On: {result.get('created_on', 'N/A')}")
                    environment.log(f"    Created By: {result.get('created_by', 'N/A')}")

                    if result.get("assignedto_id"):
                        environment.log(f"    Assigned To: {result.get('assignedto_id')}")

                    if result.get("comment"):
                        # Truncate long comments for readability
                        comment = result.get("comment", "")
                        if len(comment) > 100:
                            comment = comment[:100] + "..."
                        environment.log(f"    Comment: {comment}")

                    if result.get("version"):
                        environment.log(f"    Version: {result.get('version')}")

                    if result.get("elapsed"):
                        environment.log(f"    Elapsed: {result.get('elapsed')}")

                    if result.get("defects"):
                        environment.log(f"    Defects: {result.get('defects')}")

                    # Show custom fields if present
                    custom_fields = {k: v for k, v in result.items() if k.startswith("custom_")}
                    if custom_fields:
                        environment.log(f"    Custom Fields: {len(custom_fields)} field(s)")

                    environment.log("")


@cli.command()
@click.option(
    "--result-id",
    type=click.IntRange(min=1),
    required=True,
    metavar="",
    help="ID of the test result to edit.",
)
@click.option(
    "--status-id",
    type=click.IntRange(min=1, max=12),
    metavar="",
    help="Test status ID to set (1=Passed, 2=Blocked, 3=Untested, 4=Retest, 5=Failed).",
)
@click.option(
    "--comment",
    metavar="",
    help="Comment/notes to add or update for the result.",
)
@click.option(
    "--version",
    metavar="",
    help="Version or build tested against.",
)
@click.option(
    "--elapsed",
    metavar="",
    help="Time elapsed for the test (e.g., '1m 5s' or '65s').",
)
@click.option(
    "--defects",
    metavar="",
    help="Comma-separated list of defect/bug IDs.",
)
@click.option(
    "--assignedto-id",
    type=click.IntRange(min=1),
    metavar="",
    help="User ID to assign the test result to.",
)
@click.option(
    "--custom-fields",
    metavar="",
    help='Custom field values in JSON format (e.g., \'{"custom_field1": "value1"}\').',
)
@click.pass_context
@pass_environment
def update(
    environment: Environment,
    context: click.Context,
    result_id: int,
    status_id: int,
    comment: str,
    version: str,
    elapsed: str,
    defects: str,
    assignedto_id: int,
    custom_fields: str,
    *args,
    **kwargs,
):
    """
    Update an existing test result in TestRail.

    This command allows you to update fields of an existing test result, such as status,
    comment, elapsed time, defects, version, and custom fields.

    Example:
        trcli results update --result-id 12345 --status-id 5 --comment "Test failed due to timeout"
    """
    print_config(environment, "Update")

    environment.log("Updating test result...")

    # Validate that at least one field is provided
    if not any([status_id, comment, version, elapsed, defects, assignedto_id, custom_fields]):
        environment.elog("Error: At least one field must be provided to update.")
        raise SystemExit(1)

    # Parse custom fields if provided
    custom_fields_dict = None
    if custom_fields:
        try:
            custom_fields_dict = json.loads(custom_fields)
            if not isinstance(custom_fields_dict, dict):
                environment.elog("Error: --custom-fields must be a valid JSON object.")
                raise SystemExit(1)
        except json.JSONDecodeError as e:
            environment.elog(f"Error: Invalid JSON format for --custom-fields: {e}")
            raise SystemExit(1)

    # Create API client
    api_client = APIClient(
        host_name=environment.host,
        verbose_logging_function=environment.vlog,
        logging_function=environment.log,
        verify=environment.verify,
        timeout=environment.timeout,
    )

    # Set credentials
    api_client.username = environment.username
    api_client.password = environment.password
    api_client.api_key = environment.key

    # Create ResultHandler (minimal - only need client for edit_result)
    result_handler = ResultHandler(
        client=api_client,
        environment=environment,
        data_provider=None,
        get_all_tests_in_run_callback=None,
        handle_futures_callback=None,
    )

    # Print configuration
    environment.log(
        f"Update Result Parameters"
        f"\n> Result ID: {result_id}"
        + (f"\n> Status ID: {status_id}" if status_id else "")
        + (
            f"\n> Comment: {comment[:50]}..."
            if comment and len(comment) > 50
            else f"\n> Comment: {comment}" if comment else ""
        )
        + (f"\n> Version: {version}" if version else "")
        + (f"\n> Elapsed: {elapsed}" if elapsed else "")
        + (f"\n> Defects: {defects}" if defects else "")
        + (f"\n> Assigned To ID: {assignedto_id}" if assignedto_id else "")
        + (f"\n> Custom Fields: {custom_fields_dict}" if custom_fields_dict else "")
    )

    # Edit the result
    success, error_message = result_handler.edit_result(
        result_id=result_id,
        status_id=status_id,
        comment=comment,
        version=version,
        elapsed=elapsed,
        defects=defects,
        assignedto_id=assignedto_id,
        custom_fields=custom_fields_dict,
    )

    if success:
        environment.log(f"✓ Result {result_id} updated successfully.")
    else:
        environment.elog(f"Error: Failed to update result {result_id}: {error_message}")
        raise SystemExit(1)
