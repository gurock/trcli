import builtins
import click
import json

from trcli.api.project_based_client import ProjectBasedClient
from trcli.cli import pass_environment, CONTEXT_SETTINGS, Environment
from trcli.data_classes.dataclass_testrail import TestRailSuite


def print_config(env: Environment, action: str):
    env.log(
        f"Suites {action} Execution Parameters"
        f"\n> TestRail instance: {env.host} (user: {env.username})"
        f"\n> Project: {env.project if env.project else env.project_id}"
    )


@click.group(context_settings=CONTEXT_SETTINGS)
@click.pass_context
@pass_environment
def cli(environment: Environment, context: click.Context, *args, **kwargs):
    """Manage test suites in TestRail"""
    environment.cmd = "suites"
    environment.set_parameters(context)


@cli.command()
@click.option("--suite-id", type=click.IntRange(min=1), required=True, metavar="", help="Suite ID to retrieve.")
@click.option("--json-output", is_flag=True, help="Output suite as raw JSON from API.")
@click.option("--show-all-fields", is_flag=True, help="Show all fields including custom fields in detail.")
@click.pass_context
@pass_environment
def get(
    environment: Environment,
    context: click.Context,
    suite_id: int,
    json_output: bool,
    show_all_fields: bool,
    *args,
    **kwargs,
):
    """Get a single test suite by ID"""
    environment.check_for_required_parameters()

    print_config(environment, "Get")

    # Create ProjectBasedClient to resolve project
    project_client = ProjectBasedClient(
        environment=environment,
        suite=TestRailSuite(name=environment.suite_name, suite_id=environment.suite_id),
    )

    # Resolve project (converts name to ID if needed)
    project_client.resolve_project()

    environment.log(f"Retrieving suite ID {suite_id}...")

    # Retrieve the suite using SuiteHandler from ProjectBasedClient
    suite_data, error_message = project_client.api_request_handler.suite_handler.get_suite(suite_id)

    if error_message:
        environment.elog(f"Error: Failed to retrieve suite: {error_message}")
        raise SystemExit(1)

    # Handle output format
    if json_output:
        # Output prettified JSON response
        print(json.dumps(suite_data, indent=2))
    else:
        # Display suite details
        environment.log("")
        environment.log(f"Suite ID: {suite_data.get('id', 'N/A')}")
        environment.log(f"  Name: {suite_data.get('name', 'N/A')}")

        if suite_data.get("description"):
            description = suite_data.get("description")
            # Truncate long descriptions in non-show-all-fields mode
            if not show_all_fields and len(description) > 100:
                description = description[:100] + "..."
            environment.log(f"  Description: {description}")
        else:
            environment.log("  Description: (none)")

        environment.log(f"  Project ID: {suite_data.get('project_id', 'N/A')}")

        if suite_data.get("url"):
            environment.log(f"  URL: {suite_data.get('url')}")

        if show_all_fields:
            # Show all custom fields if any
            custom_fields = {
                k: v for k, v in suite_data.items() if k not in ["id", "name", "description", "project_id", "url"]
            }
            if custom_fields:
                environment.log(f"  Additional Fields ({len(custom_fields)}):")
                for key, value in custom_fields.items():
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
@click.option("--json-output", is_flag=True, help="Output suites as raw JSON from API.")
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
    """List test suites from TestRail"""
    environment.check_for_required_parameters()

    print_config(environment, "List")

    # Create ProjectBasedClient to resolve project
    project_client = ProjectBasedClient(
        environment=environment,
        suite=TestRailSuite(name=environment.suite_name, suite_id=environment.suite_id),
    )

    # Resolve project (converts name to ID if needed)
    project_client.resolve_project()

    environment.log(f"Retrieving suites for project ID {project_client.project.project_id}...")

    # Retrieve suites using SuiteHandler from ProjectBasedClient
    response_data, error_message = project_client.api_request_handler.suite_handler.get_suites(
        project_id=project_client.project.project_id,
        limit=limit,
        offset=offset,
    )

    if error_message:
        environment.elog(f"Error: Failed to retrieve suites: {error_message}")
        raise SystemExit(1)

    # Handle output format
    if json_output:
        # Output prettified JSON response
        print(json.dumps(response_data, indent=2))
    else:
        # Display suites line by line
        suites = response_data.get("suites", [])
        response_offset = response_data.get("offset", 0)
        response_limit = response_data.get("limit", 250)
        response_size = response_data.get("size", 0)
        next_link = response_data.get("_links", {}).get("next")

        if not suites:
            environment.log("No suites found.")
        else:
            environment.log(
                f"Found {response_size} suite(s) (showing {response_offset + 1}-{response_offset + len(suites)}):"
            )
            if next_link:
                environment.log("  (More results available - use --offset and --limit for pagination)")
            environment.log("")

            for suite in suites:
                if show_all_fields:
                    # Show all fields from API response
                    environment.log(f"  Suite ID: {suite.get('id', 'N/A')}")

                    # Iterate through all fields in the suite
                    for key, value in suite.items():
                        if key == "id":
                            continue  # Already displayed as Suite ID

                        # Format field name for display
                        display_name = key.replace("_", " ").title()

                        # Handle None values
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

                    environment.log("")
                else:
                    # Display compact format
                    environment.log(f"  Suite ID: {suite.get('id', 'N/A')}")
                    environment.log(f"    Name: {suite.get('name', 'N/A')}")

                    if suite.get("description"):
                        description = suite.get("description")
                        # Truncate long descriptions in compact mode
                        if len(description) > 80:
                            description = description[:80] + "..."
                        environment.log(f"    Description: {description}")

                    environment.log(f"    Project ID: {suite.get('project_id', 'N/A')}")

                    environment.log("")
