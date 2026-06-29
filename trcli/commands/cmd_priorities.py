import builtins
import click
import json

from trcli.api.project_based_client import ProjectBasedClient
from trcli.cli import pass_environment, CONTEXT_SETTINGS, Environment
from trcli.data_classes.dataclass_testrail import TestRailSuite


def print_config(env: Environment, action: str):
    env.log(f"Priorities {action} Execution Parameters" f"\n> TestRail instance: {env.host} (user: {env.username})")


@click.group(context_settings=CONTEXT_SETTINGS)
@click.pass_context
@pass_environment
def cli(environment: Environment, context: click.Context, *args, **kwargs):
    """Manage test case priorities in TestRail"""
    environment.cmd = "priorities"
    environment.set_parameters(context)


@cli.command()
@click.option("--json-output", is_flag=True, help="Output priorities as raw JSON from API.")
@click.option("--show-all-fields", is_flag=True, help="Show all fields including priority order and default flag.")
@click.pass_context
@pass_environment
def list(
    environment: Environment,
    context: click.Context,
    json_output: bool,
    show_all_fields: bool,
    *args,
    **kwargs,
):
    """List all test case priorities from TestRail"""
    environment.check_for_required_parameters()

    print_config(environment, "List")

    # Create ProjectBasedClient (priorities are global, but we use this for consistent API access)
    project_client = ProjectBasedClient(
        environment=environment,
        suite=TestRailSuite(name=environment.suite_name, suite_id=environment.suite_id),
    )

    environment.log("Retrieving priorities...")

    # Retrieve priorities using PriorityHandler
    priorities, error_message = project_client.api_request_handler.priority_handler.get_priorities()

    if error_message:
        environment.elog(f"Error: Failed to retrieve priorities: {error_message}")
        raise SystemExit(1)

    if json_output:
        # Output prettified JSON response
        print(json.dumps(priorities, indent=2))
    else:
        environment.log(f"Found {len(priorities)} priority level(s).")
        environment.log("")

        if not priorities:
            environment.log("No priorities found.")
        else:
            # Display priorities in a table-like format
            for priority in priorities:
                priority_id = priority.get("id")
                name = priority.get("name", "N/A")
                short_name = priority.get("short_name", "N/A")
                is_default = priority.get("is_default", False)
                priority_order = priority.get("priority", "N/A")

                default_marker = " [DEFAULT]" if is_default else ""

                if show_all_fields:
                    environment.log(
                        f"ID: {priority_id} | Name: {name} | Short: {short_name} | "
                        f"Order: {priority_order}{default_marker}"
                    )
                else:
                    environment.log(f"ID: {priority_id} | Name: {name} | Short: {short_name}{default_marker}")

        environment.log("")

    environment.log("Priority listing completed successfully.")
