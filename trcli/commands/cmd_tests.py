import builtins
import click
import json

from trcli.api.project_based_client import ProjectBasedClient
from trcli.cli import pass_environment, CONTEXT_SETTINGS, Environment
from trcli.data_classes.dataclass_testrail import TestRailSuite


def print_config(env: Environment, action: str):
    env.log(f"Tests {action} Execution Parameters" f"\n> TestRail instance: {env.host} (user: {env.username})")


def display_test(env: Environment, test: dict, show_all_fields: bool = False):
    """Helper function to display a single test's information."""
    env.log(f"Test ID: {test.get('id')}")
    env.log(f"  Title: {test.get('title', 'N/A')}")
    env.log(f"  Case ID: {test.get('case_id', 'N/A')}")
    env.log(f"  Run ID: {test.get('run_id', 'N/A')}")
    env.log(f"  Status ID: {test.get('status_id', 'N/A')}")

    if show_all_fields:
        env.log(f"  Assigned To ID: {test.get('assignedto_id', 'N/A')}")
        env.log(f"  Priority ID: {test.get('priority_id', 'N/A')}")
        env.log(f"  Type ID: {test.get('type_id', 'N/A')}")
        env.log(f"  Estimate: {test.get('estimate', 'N/A')}")
        env.log(f"  Estimate Forecast: {test.get('estimate_forecast', 'N/A')}")

        # Display labels if available
        labels = test.get("labels", [])
        if labels:
            env.log(f"  Labels: {len(labels)} label(s)")
            for label in labels:
                label_id = label.get("id")
                label_title = label.get("title", "N/A")
                env.log(f"    - Label ID: {label_id}, Title: {label_title}")

        # Display custom fields
        custom_fields = {k: v for k, v in test.items() if k.startswith("custom_")}
        if custom_fields:
            env.log(f"  Custom Fields: {len(custom_fields)} field(s)")
            custom_items = [item for item in custom_fields.items()]
            for field_name, field_value in custom_items:
                # Handle list values (like custom_steps_separated)
                if isinstance(field_value, builtins.list):
                    env.log(f"    - {field_name}: {len(field_value)} item(s)")
                else:
                    # Truncate long values
                    value_str = str(field_value)
                    if len(value_str) > 50:
                        value_str = value_str[:47] + "..."
                    env.log(f"    - {field_name}: {value_str}")

        # Display results if available (when using --with-data 1)
        results = test.get("results", [])
        if results:
            env.log(f"  Results: {len(results)} result(s)")
            for result in results:
                result_id = result.get("id")
                result_status = result.get("status_id")
                env.log(f"    - Result ID: {result_id}, Status ID: {result_status}")

        # Display attachments if available (when using --with-data 1)
        attachments = test.get("attachments", [])
        if attachments:
            env.log(f"  Attachments: {len(attachments)} attachment(s)")
            for attachment in attachments:
                attachment_id = attachment.get("id")
                attachment_name = attachment.get("name", "N/A")
                env.log(f"    - Attachment ID: {attachment_id}, Name: {attachment_name}")


@click.group(context_settings=CONTEXT_SETTINGS)
@click.pass_context
@pass_environment
def cli(environment: Environment, context: click.Context, *args, **kwargs):
    """Manage tests in TestRail"""
    environment.cmd = "tests"
    environment.set_parameters(context)


@cli.command()
@click.option("--test-id", type=click.IntRange(min=1), metavar="<id>", required=True, help="Get test by test ID.")
@click.option(
    "--with-data",
    type=click.Choice(["0", "1"]),
    metavar="<0|1>",
    help="Include test results and attachments (0=no, 1=yes).",
)
@click.option("--json-output", is_flag=True, help="Output test as raw JSON from API.")
@click.option("--show-all-fields", is_flag=True, help="Show all fields including custom fields and labels.")
@click.pass_context
@pass_environment
def get(
    environment: Environment,
    context: click.Context,
    test_id: int,
    with_data: str,
    json_output: bool,
    show_all_fields: bool,
    *args,
    **kwargs,
):
    """Get a specific test from TestRail"""
    environment.check_for_required_parameters()

    print_config(environment, "Get")

    # Create ProjectBasedClient for consistent API access
    project_client = ProjectBasedClient(
        environment=environment,
        suite=TestRailSuite(name=environment.suite_name, suite_id=environment.suite_id),
    )

    # Retrieve test
    environment.log(f"Retrieving test with ID {test_id}...")
    test, error_message = project_client.api_request_handler.test_handler.get_test(test_id, with_data)

    if error_message:
        environment.elog(f"Error: Failed to retrieve test: {error_message}")
        raise SystemExit(1)

    if not test:
        environment.log("No test found.")
        return

    if json_output:
        print(json.dumps(test, indent=2))
    else:
        environment.log("")
        display_test(environment, test, show_all_fields)
        environment.log("")

    environment.log("Test retrieval completed successfully.")


@cli.command()
@click.option("--run-id", type=click.IntRange(min=1), metavar="<id>", required=True, help="Get tests for run ID.")
@click.option("--status-id", type=str, metavar="<ids>", help="Comma-separated list of status IDs to filter by.")
@click.option("--limit", type=int, metavar="<limit>", help="Limit number of tests returned (default: 250).")
@click.option("--offset", type=int, metavar="<offset>", help="Offset for pagination (default: 0).")
@click.option("--label-id", type=str, metavar="<ids>", help="Comma-separated list of label IDs to filter by.")
@click.option("--json-output", is_flag=True, help="Output tests as raw JSON from API.")
@click.option("--show-all-fields", is_flag=True, help="Show all fields for each test.")
@click.pass_context
@pass_environment
def list(
    environment: Environment,
    context: click.Context,
    run_id: int,
    status_id: str,
    limit: int,
    offset: int,
    label_id: str,
    json_output: bool,
    show_all_fields: bool,
    *args,
    **kwargs,
):
    """List all tests for a test run"""
    environment.check_for_required_parameters()

    print_config(environment, "List")

    # Create ProjectBasedClient for consistent API access
    project_client = ProjectBasedClient(
        environment=environment,
        suite=TestRailSuite(name=environment.suite_name, suite_id=environment.suite_id),
    )

    # Build description of filters
    filters = []
    if status_id is not None:
        filters.append(f"status_id={status_id}")
    if limit is not None:
        filters.append(f"limit={limit}")
    if offset is not None:
        filters.append(f"offset={offset}")
    if label_id is not None:
        filters.append(f"label_id={label_id}")

    filter_desc = f" with filters: {', '.join(filters)}" if filters else ""
    environment.log(f"Retrieving tests for run ID {run_id}{filter_desc}...")

    # Retrieve tests
    tests, error_message = project_client.api_request_handler.test_handler.get_tests(
        run_id=run_id, status_id=status_id, limit=limit, offset=offset, label_id=label_id
    )

    if error_message:
        environment.elog(f"Error: Failed to retrieve tests: {error_message}")
        raise SystemExit(1)

    if json_output:
        print(json.dumps(tests, indent=2))
        return

    # Display results
    environment.log(f"Found {len(tests)} test(s).")
    environment.log("")

    for test in tests:
        display_test(environment, test, show_all_fields)
        environment.log("")

    environment.log("Test listing completed successfully.")
