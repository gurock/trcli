import builtins
import click
import json

from trcli.api.project_based_client import ProjectBasedClient
from trcli.cli import pass_environment, CONTEXT_SETTINGS, Environment
from trcli.data_classes.dataclass_testrail import TestRailSuite


def print_config(env: Environment, action: str):
    env.log(f"Groups {action} Execution Parameters" f"\n> TestRail instance: {env.host} (user: {env.username})")


def display_group(env: Environment, group: dict):
    """Helper function to display a single group's information."""
    env.log(f"Group ID: {group.get('id')}")
    env.log(f"  Name: {group.get('name', 'N/A')}")

    user_ids = group.get("user_ids", [])
    if user_ids:
        env.log(f"  Members: {len(user_ids)} user(s)")
        env.log(f"  User IDs: {', '.join(str(uid) for uid in user_ids)}")
    else:
        env.log(f"  Members: 0 user(s)")


@click.group(context_settings=CONTEXT_SETTINGS)
@click.pass_context
@pass_environment
def cli(environment: Environment, context: click.Context, *args, **kwargs):
    """Manage groups in TestRail"""
    environment.cmd = "groups"
    environment.set_parameters(context)


@cli.command()
@click.option("--group-id", type=int, required=True, metavar="<id>", help="The ID of the group to retrieve.")
@click.option("--json-output", is_flag=True, help="Output group as raw JSON from API.")
@click.pass_context
@pass_environment
def show(
    environment: Environment,
    context: click.Context,
    group_id: int,
    json_output: bool,
    *args,
    **kwargs,
):
    """Get a specific group from TestRail"""
    environment.check_for_required_parameters()

    print_config(environment, "Show")

    # Create ProjectBasedClient for consistent API access
    project_client = ProjectBasedClient(
        environment=environment,
        suite=TestRailSuite(name=environment.suite_name, suite_id=environment.suite_id),
    )

    environment.log(f"Retrieving group with ID {group_id}...")
    group, error_message = project_client.api_request_handler.groups_handler.get_group(group_id)

    if error_message:
        environment.elog(f"Error: Failed to retrieve group: {error_message}")
        raise SystemExit(1)

    if not group:
        environment.log("No group found.")
        return

    if json_output:
        print(json.dumps(group, indent=2))
    else:
        environment.log("")
        display_group(environment, group)
        environment.log("")

    environment.log("Group retrieval completed successfully.")


@cli.command()
@click.option("--offset", type=int, default=0, metavar="<offset>", help="Offset for pagination (default: 0).")
@click.option(
    "--limit",
    type=int,
    default=250,
    metavar="<limit>",
    help="Maximum number of groups to return (default: 250).",
)
@click.option("--json-output", is_flag=True, help="Output groups as raw JSON from API.")
@click.pass_context
@pass_environment
def list(
    environment: Environment,
    context: click.Context,
    offset: int,
    limit: int,
    json_output: bool,
    *args,
    **kwargs,
):
    """List all groups from TestRail"""
    environment.check_for_required_parameters()

    print_config(environment, "List")

    # Create ProjectBasedClient for consistent API access
    project_client = ProjectBasedClient(
        environment=environment,
        suite=TestRailSuite(name=environment.suite_name, suite_id=environment.suite_id),
    )

    environment.log(f"Retrieving groups (limit: {limit}, offset: {offset})...")
    response, error_message = project_client.api_request_handler.groups_handler.get_groups(limit=limit, offset=offset)

    if error_message:
        environment.elog(f"Error: Failed to retrieve groups: {error_message}")
        raise SystemExit(1)

    groups = response.get("groups", [])

    if not groups:
        environment.log("No groups found.")
        return

    if json_output:
        print(json.dumps(response, indent=2))
    else:
        environment.log("")
        environment.log(f"Found {len(groups)} group(s):")
        environment.log("")

        for group in groups:
            display_group(environment, group)
            environment.log("")

        # Display pagination info
        total_size = response.get("size", len(groups))
        current_offset = response.get("offset", offset)
        current_limit = response.get("limit", limit)

        environment.log(f"Showing {len(groups)} of {total_size} group(s)")
        environment.log(f"Offset: {current_offset}, Limit: {current_limit}")

        # Show pagination hints
        links = response.get("_links", {})
        if links.get("next"):
            environment.log(f"More results available. Use --offset {current_offset + current_limit} to see next page.")

    environment.log("Groups retrieval completed successfully.")
