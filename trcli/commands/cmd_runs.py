import builtins
import click
import json

from trcli.api.project_based_client import ProjectBasedClient
from trcli.cli import pass_environment, CONTEXT_SETTINGS, Environment
from trcli.data_classes.dataclass_testrail import TestRailSuite


def print_config(env: Environment, action: str):
    env.log(
        f"Runs {action} Execution Parameters"
        f"\n> TestRail instance: {env.host} (user: {env.username})"
        f"\n> Project: {env.project if env.project else env.project_id}"
    )


@click.group(context_settings=CONTEXT_SETTINGS)
@click.pass_context
@pass_environment
def cli(environment: Environment, context: click.Context, *args, **kwargs):
    """Manage test runs in TestRail"""
    environment.cmd = "runs"
    environment.set_parameters(context)


@cli.command()
@click.option("--run-id", type=click.IntRange(min=1), required=True, metavar="", help="Run ID to retrieve.")
@click.option("--json-output", is_flag=True, help="Output run as raw JSON from API.")
@click.option("--show-all-fields", is_flag=True, help="Show all fields including custom fields in detail.")
@click.pass_context
@pass_environment
def get(
    environment: Environment,
    context: click.Context,
    run_id: int,
    json_output: bool,
    show_all_fields: bool,
    *args,
    **kwargs,
):
    """Get a single test run by ID"""
    environment.check_for_required_parameters()

    print_config(environment, "Get")

    # Create ProjectBasedClient to resolve project
    project_client = ProjectBasedClient(
        environment=environment,
        suite=TestRailSuite(name=environment.suite_name, suite_id=environment.suite_id),
    )

    # Resolve project (converts name to ID if needed)
    project_client.resolve_project()

    environment.log(f"Retrieving run ID {run_id}...")

    # Retrieve the run using RunHandler from ProjectBasedClient
    run_data, error_message = project_client.api_request_handler.run_handler.get_run(run_id)

    if error_message:
        environment.elog(f"Error: Failed to retrieve run: {error_message}")
        raise SystemExit(1)

    # Handle output format
    if json_output:
        # Output prettified JSON response
        print(json.dumps(run_data, indent=2))
    else:
        # Display run details
        environment.log("")
        environment.log(f"Run ID: {run_data.get('id', 'N/A')}")
        environment.log(f"  Name: {run_data.get('name', 'N/A')}")

        if run_data.get("description"):
            description = run_data.get("description")
            # Truncate long descriptions in non-show-all-fields mode
            if not show_all_fields and len(description) > 100:
                description = description[:100] + "..."
            environment.log(f"  Description: {description}")
        else:
            environment.log("  Description: (none)")

        environment.log(f"  Suite ID: {run_data.get('suite_id', 'N/A')}")
        environment.log(f"  Project ID: {run_data.get('project_id', 'N/A')}")

        # Status information
        is_completed = run_data.get("is_completed", False)
        environment.log(f"  Status: {'Completed' if is_completed else 'Active'}")

        if is_completed and run_data.get("completed_on"):
            environment.log(f"  Completed On: {run_data.get('completed_on')}")

        # Test counts
        environment.log("  Test Status Counts:")
        environment.log(f"    Passed: {run_data.get('passed_count', 0)}")
        environment.log(f"    Failed: {run_data.get('failed_count', 0)}")
        environment.log(f"    Blocked: {run_data.get('blocked_count', 0)}")
        environment.log(f"    Retest: {run_data.get('retest_count', 0)}")
        environment.log(f"    Untested: {run_data.get('untested_count', 0)}")

        if show_all_fields:
            # Show additional fields
            if run_data.get("config"):
                environment.log(f"  Configuration: {run_data.get('config')}")

            if run_data.get("config_ids"):
                environment.log(f"  Configuration IDs: {run_data.get('config_ids')}")

            if run_data.get("milestone_id"):
                environment.log(f"  Milestone ID: {run_data.get('milestone_id')}")

            if run_data.get("plan_id"):
                environment.log(f"  Plan ID: {run_data.get('plan_id')}")

            if run_data.get("assignedto_id"):
                environment.log(f"  Assigned To ID: {run_data.get('assignedto_id')}")

            if run_data.get("refs"):
                environment.log(f"  References: {run_data.get('refs')}")

            environment.log(f"  Include All: {'Yes' if run_data.get('include_all') else 'No'}")
            environment.log(f"  Created By: {run_data.get('created_by', 'N/A')}")
            environment.log(f"  Created On: {run_data.get('created_on', 'N/A')}")

            if run_data.get("updated_on"):
                environment.log(f"  Updated On: {run_data.get('updated_on')}")

            if run_data.get("url"):
                environment.log(f"  URL: {run_data.get('url')}")

            # Show custom status counts
            custom_counts = {
                k: v for k, v in run_data.items() if k.startswith("custom_status") and k.endswith("_count")
            }
            if any(v > 0 for v in custom_counts.values()):
                environment.log("  Custom Status Counts:")
                for key, value in custom_counts.items():
                    if value > 0:
                        status_num = key.replace("custom_status", "").replace("_count", "")
                        environment.log(f"    Custom Status {status_num}: {value}")

            # Show all other fields
            standard_fields = [
                "id",
                "name",
                "description",
                "suite_id",
                "project_id",
                "is_completed",
                "completed_on",
                "passed_count",
                "failed_count",
                "blocked_count",
                "retest_count",
                "untested_count",
                "config",
                "config_ids",
                "milestone_id",
                "plan_id",
                "assignedto_id",
                "refs",
                "include_all",
                "created_by",
                "created_on",
                "updated_on",
                "url",
                "custom_status1_count",
                "custom_status2_count",
                "custom_status3_count",
                "custom_status4_count",
                "custom_status5_count",
                "custom_status6_count",
                "custom_status7_count",
            ]
            other_fields = {k: v for k, v in run_data.items() if k not in standard_fields}
            if other_fields:
                environment.log(f"\n  Additional Fields ({len(other_fields)}):")
                for key, value in other_fields.items():
                    display_name = key.replace("_", " ").title()
                    if value is None:
                        display_value = "N/A"
                    elif isinstance(value, builtins.list):
                        if value:
                            display_value = f"{len(value)} item(s): {value}"
                        else:
                            display_value = "[]"
                    else:
                        display_value = value
                    environment.log(f"    {display_name}: {display_value}")


@cli.command()
@click.option("--offset", type=int, default=0, metavar="", help="Offset for pagination (default: 0).")
@click.option("--limit", type=int, default=250, metavar="", help="Limit for pagination (default: 250).")
@click.option("--json-output", is_flag=True, help="Output runs as raw JSON from API.")
@click.option("--show-all-fields", is_flag=True, help="Show all fields including custom fields in detail.")
@click.pass_context
@pass_environment
def list(
    environment: Environment,
    context: click.Context,
    offset: int,
    limit: int,
    json_output: bool,
    show_all_fields: bool,
    *args,
    **kwargs,
):
    """List test runs from TestRail"""
    environment.check_for_required_parameters()

    print_config(environment, "List")

    # Create ProjectBasedClient to resolve project
    project_client = ProjectBasedClient(
        environment=environment,
        suite=TestRailSuite(name=environment.suite_name, suite_id=environment.suite_id),
    )

    # Resolve project (converts name to ID if needed)
    project_client.resolve_project()

    environment.log(f"Retrieving runs for project ID {project_client.project.project_id}...")
    environment.log("(Note: Only returns runs not part of test plans)")

    # Retrieve runs using RunHandler from ProjectBasedClient
    response_data, error_message = project_client.api_request_handler.run_handler.get_runs(
        project_id=project_client.project.project_id,
        limit=limit,
        offset=offset,
    )

    if error_message:
        environment.elog(f"Error: Failed to retrieve runs: {error_message}")
        raise SystemExit(1)

    # Handle output format
    if json_output:
        # Output prettified JSON response
        print(json.dumps(response_data, indent=2))
    else:
        # Display runs line by line
        runs = response_data.get("runs", [])
        response_offset = response_data.get("offset", 0)
        response_limit = response_data.get("limit", 250)
        response_size = response_data.get("size", 0)
        next_link = response_data.get("_links", {}).get("next")

        if not runs:
            environment.log("No runs found.")
        else:
            environment.log(
                f"Found {response_size} run(s) (showing {response_offset + 1}-{response_offset + len(runs)}):"
            )
            if next_link:
                environment.log("  (More results available - use --offset and --limit for pagination)")
            environment.log("")

            for run in runs:
                if show_all_fields:
                    # Show all fields from API response
                    environment.log(f"  Run ID: {run.get('id', 'N/A')}")

                    # Iterate through all fields in the run
                    for key, value in run.items():
                        if key == "id":
                            continue  # Already displayed as Run ID

                        # Format field name for display
                        display_name = key.replace("_", " ").title()

                        # Handle None values
                        if value is None:
                            display_value = "N/A"
                        elif isinstance(value, bool):
                            display_value = "Yes" if value else "No"
                        elif isinstance(value, builtins.list):
                            if value:
                                display_value = f"{len(value)} item(s): {value}"
                            else:
                                display_value = "[]"
                        else:
                            display_value = value

                        environment.log(f"    {display_name}: {display_value}")

                    environment.log("")
                else:
                    # Display compact format
                    environment.log(f"  Run ID: {run.get('id', 'N/A')}")
                    environment.log(f"    Name: {run.get('name', 'N/A')}")

                    if run.get("description"):
                        description = run.get("description")
                        # Truncate long descriptions in compact mode
                        if len(description) > 80:
                            description = description[:80] + "..."
                        environment.log(f"    Description: {description}")

                    is_completed = run.get("is_completed", False)
                    environment.log(f"    Status: {'Completed' if is_completed else 'Active'}")

                    # Show test counts
                    passed = run.get("passed_count", 0)
                    failed = run.get("failed_count", 0)
                    blocked = run.get("blocked_count", 0)
                    untested = run.get("untested_count", 0)
                    environment.log(
                        f"    Tests: Passed={passed}, Failed={failed}, Blocked={blocked}, Untested={untested}"
                    )

                    environment.log(f"    Suite ID: {run.get('suite_id', 'N/A')}")

                    environment.log("")
