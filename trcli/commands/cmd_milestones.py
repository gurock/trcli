import builtins
import click
import json
from datetime import datetime

from trcli.api.project_based_client import ProjectBasedClient
from trcli.cli import pass_environment, CONTEXT_SETTINGS, Environment
from trcli.data_classes.dataclass_testrail import TestRailSuite


def print_config(env: Environment, action: str):
    env.log(
        f"Milestones {action} Execution Parameters"
        f"\n> TestRail instance: {env.host} (user: {env.username})"
        f"\n> Project: {env.project if env.project else env.project_id}"
    )


def format_timestamp(timestamp):
    """Format Unix timestamp to readable date, returns 'N/A' if None"""
    if timestamp:
        return datetime.fromtimestamp(timestamp).strftime("%Y-%m-%d %H:%M:%S")
    return "N/A"


@click.group(context_settings=CONTEXT_SETTINGS)
@click.pass_context
@pass_environment
def cli(environment: Environment, context: click.Context, *args, **kwargs):
    """Manage milestones in TestRail"""
    environment.cmd = "milestones"
    environment.set_parameters(context)


@cli.command()
@click.option("--milestone-id", type=click.IntRange(min=1), required=True, metavar="", help="Milestone ID to retrieve.")
@click.option("--json-output", is_flag=True, help="Output milestone as raw JSON from API.")
@click.option("--show-all-fields", is_flag=True, help="Show all fields including custom fields in detail.")
@click.pass_context
@pass_environment
def get(
    environment: Environment,
    context: click.Context,
    milestone_id: int,
    json_output: bool,
    show_all_fields: bool,
    *args,
    **kwargs,
):
    """Get a single milestone by ID"""
    environment.check_for_required_parameters()

    print_config(environment, "Get")

    # Create ProjectBasedClient to resolve project
    project_client = ProjectBasedClient(
        environment=environment,
        suite=TestRailSuite(name=environment.suite_name, suite_id=environment.suite_id),
    )

    # Resolve project (converts name to ID if needed)
    project_client.resolve_project()

    environment.log(f"Retrieving milestone ID {milestone_id}...")

    # Retrieve the milestone using MilestoneHandler from ProjectBasedClient
    milestone_data, error_message = project_client.api_request_handler.milestone_handler.get_milestone(milestone_id)

    if error_message:
        environment.elog(f"Error: Failed to retrieve milestone: {error_message}")
        raise SystemExit(1)

    # Handle output format
    if json_output:
        # Output prettified JSON response
        print(json.dumps(milestone_data, indent=2))
    else:
        # Display milestone details
        environment.log("")
        environment.log(f"Milestone ID: {milestone_data.get('id', 'N/A')}")
        environment.log(f"  Name: {milestone_data.get('name', 'N/A')}")

        if milestone_data.get("description"):
            description = milestone_data.get("description")
            # Truncate long descriptions in non-show-all-fields mode
            if not show_all_fields and len(description) > 100:
                description = description[:100] + "..."
            environment.log(f"  Description: {description}")
        else:
            environment.log("  Description: (none)")

        environment.log(f"  Project ID: {milestone_data.get('project_id', 'N/A')}")

        # Status information
        is_completed = milestone_data.get("is_completed", False)
        environment.log(f"  Status: {'Completed' if is_completed else 'Active'}")

        # Due date
        due_on = milestone_data.get("due_on")
        if due_on:
            environment.log(f"  Due On: {format_timestamp(due_on)}")
        else:
            environment.log("  Due On: (not set)")

        if show_all_fields:
            # Show additional fields
            if milestone_data.get("refs"):
                environment.log(f"  References: {milestone_data.get('refs')}")

            completed_on = milestone_data.get("completed_on")
            if completed_on:
                environment.log(f"  Completed On: {format_timestamp(completed_on)}")

            if milestone_data.get("url"):
                environment.log(f"  URL: {milestone_data.get('url')}")

            # Show all other fields (custom fields)
            standard_fields = [
                "id",
                "name",
                "description",
                "project_id",
                "is_completed",
                "due_on",
                "completed_on",
                "refs",
                "url",
            ]
            custom_fields = {k: v for k, v in milestone_data.items() if k not in standard_fields}
            if custom_fields:
                environment.log("  Custom Fields:")
                for key, value in sorted(custom_fields.items()):
                    environment.log(f"    {key}: {value}")

    environment.log("")
    environment.log("Milestone retrieval completed successfully.")


@cli.command()
@click.option(
    "--offset",
    type=click.IntRange(min=0),
    default=0,
    metavar="",
    help="Offset for pagination (default: 0).",
)
@click.option(
    "--limit",
    type=click.IntRange(min=1, max=250),
    default=250,
    metavar="",
    help="Maximum number of milestones to return (default: 250, max: 250).",
)
@click.option("--json-output", is_flag=True, help="Output milestones as raw JSON from API.")
@click.option("--show-all-fields", is_flag=True, help="Show all fields including custom fields for each milestone.")
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
    """List milestones from TestRail"""
    environment.check_for_required_parameters()

    print_config(environment, "List")

    # Create ProjectBasedClient to resolve project
    project_client = ProjectBasedClient(
        environment=environment,
        suite=TestRailSuite(name=environment.suite_name, suite_id=environment.suite_id),
    )

    # Resolve project (converts name to ID if needed)
    project_client.resolve_project()

    environment.log(
        f"Retrieving milestones for project ID {project_client.project.project_id} (offset: {offset}, limit: {limit})..."
    )

    # Retrieve milestones using MilestoneHandler
    milestones_data, error_message = project_client.api_request_handler.milestone_handler.get_milestones(
        project_id=project_client.project.project_id, limit=limit, offset=offset
    )

    if error_message:
        environment.elog(f"Error: Failed to retrieve milestones: {error_message}")
        raise SystemExit(1)

    milestones = milestones_data.get("milestones", [])
    total_count = milestones_data.get("size", 0)
    returned_count = len(milestones)

    if json_output:
        # Output prettified JSON response
        print(json.dumps(milestones_data, indent=2))
    else:
        environment.log(f"Found {total_count} milestone(s), displaying {returned_count}.")
        environment.log("")

        if not milestones:
            environment.log("No milestones found.")
        else:
            for milestone in milestones:
                # Compact format by default
                status = "✓ Completed" if milestone.get("is_completed") else "○ Active"
                due_on = format_timestamp(milestone.get("due_on")) if milestone.get("due_on") else "No due date"

                environment.log(f"Milestone ID: {milestone.get('id')}")
                environment.log(f"  Name: {milestone.get('name')}")

                # Show description if present
                if milestone.get("description"):
                    description = milestone.get("description")
                    if not show_all_fields and len(description) > 80:
                        description = description[:80] + "..."
                    environment.log(f"  Description: {description}")

                environment.log(f"  Status: {status}")
                environment.log(f"  Due On: {due_on}")
                environment.log(f"  Project ID: {milestone.get('project_id', 'N/A')}")

                if show_all_fields:
                    # Show additional fields in detailed view
                    if milestone.get("refs"):
                        environment.log(f"  References: {milestone.get('refs')}")

                    completed_on = milestone.get("completed_on")
                    if completed_on:
                        environment.log(f"  Completed On: {format_timestamp(completed_on)}")

                    if milestone.get("url"):
                        environment.log(f"  URL: {milestone.get('url')}")

                    # Show custom fields
                    standard_fields = [
                        "id",
                        "name",
                        "description",
                        "project_id",
                        "is_completed",
                        "due_on",
                        "completed_on",
                        "refs",
                        "url",
                    ]
                    custom_fields = {k: v for k, v in milestone.items() if k not in standard_fields}
                    if custom_fields:
                        environment.log("  Custom Fields:")
                        for key, value in sorted(custom_fields.items()):
                            environment.log(f"    {key}: {value}")

                environment.log("")

        # Pagination info
        next_link = milestones_data.get("_links", {}).get("next")
        if next_link:
            next_offset = offset + limit
            environment.log(f"More results available. Use --offset {next_offset} to retrieve next page.")

    environment.log("")
    environment.log("Milestone listing completed successfully.")
