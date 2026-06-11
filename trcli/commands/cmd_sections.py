import builtins
import click
import json

from trcli.api.project_based_client import ProjectBasedClient
from trcli.cli import pass_environment, CONTEXT_SETTINGS, Environment
from trcli.data_classes.dataclass_testrail import TestRailSuite


def print_config(env: Environment, action: str):
    env.log(
        f"Sections {action} Execution Parameters"
        f"\n> TestRail instance: {env.host} (user: {env.username})"
        f"\n> Project: {env.project if env.project else env.project_id}"
    )


@click.group(context_settings=CONTEXT_SETTINGS)
@click.pass_context
@pass_environment
def cli(environment: Environment, context: click.Context, *args, **kwargs):
    """Manage test sections in TestRail"""
    environment.cmd = "sections"
    environment.set_parameters(context)


@cli.command()
@click.option("--section-id", type=click.IntRange(min=1), required=True, metavar="", help="Section ID to retrieve.")
@click.option("--json-output", is_flag=True, help="Output section as raw JSON from API.")
@click.option("--show-all-fields", is_flag=True, help="Show all fields including custom fields in detail.")
@click.pass_context
@pass_environment
def get(
    environment: Environment,
    context: click.Context,
    section_id: int,
    json_output: bool,
    show_all_fields: bool,
    *args,
    **kwargs,
):
    """Get a single test section by ID"""
    environment.check_for_required_parameters()

    print_config(environment, "Get")

    # Create ProjectBasedClient to resolve project
    project_client = ProjectBasedClient(
        environment=environment,
        suite=TestRailSuite(name=environment.suite_name, suite_id=environment.suite_id),
    )

    # Resolve project (converts name to ID if needed)
    project_client.resolve_project()

    environment.log(f"Retrieving section ID {section_id}...")

    # Retrieve the section using SectionHandler from ProjectBasedClient
    section_data, error_message = project_client.api_request_handler.section_handler.get_section(section_id)

    if error_message:
        environment.elog(f"Error: Failed to retrieve section: {error_message}")
        raise SystemExit(1)

    # Handle output format
    if json_output:
        # Output prettified JSON response
        print(json.dumps(section_data, indent=2))
    else:
        # Display section details
        environment.log("")
        environment.log(f"Section ID: {section_data.get('id', 'N/A')}")
        environment.log(f"  Name: {section_data.get('name', 'N/A')}")

        if section_data.get("description"):
            description = section_data.get("description")
            # Truncate long descriptions in non-show-all-fields mode
            if not show_all_fields and len(description) > 100:
                description = description[:100] + "..."
            environment.log(f"  Description: {description}")
        else:
            environment.log("  Description: (none)")

        environment.log(f"  Suite ID: {section_data.get('suite_id', 'N/A')}")
        environment.log(f"  Depth: {section_data.get('depth', 0)}")

        if show_all_fields:
            environment.log(f"  Display Order: {section_data.get('display_order', 'N/A')}")

            parent_id = section_data.get("parent_id")
            if parent_id:
                environment.log(f"  Parent Section ID: {parent_id}")
            else:
                environment.log("  Parent Section ID: (root level)")

            standard_fields = ["id", "name", "description", "suite_id", "depth", "display_order", "parent_id"]
            other_fields = {k: v for k, v in section_data.items() if k not in standard_fields}
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
@click.option(
    "--suite-id", type=click.IntRange(min=1), required=True, metavar="", help="Suite ID to list sections from."
)
@click.option("--offset", type=int, default=0, metavar="", help="Offset for pagination (default: 0).")
@click.option("--limit", type=int, default=250, metavar="", help="Limit for pagination (default: 250).")
@click.option("--json-output", is_flag=True, help="Output sections as raw JSON from API.")
@click.option("--show-all-fields", is_flag=True, help="Show all fields including custom fields in detail.")
@click.pass_context
@pass_environment
def list(
    environment: Environment,
    context: click.Context,
    suite_id: int,
    offset: int,
    limit: int,
    json_output: bool,
    show_all_fields: bool,
    *args,
    **kwargs,
):
    """List test sections from TestRail"""
    environment.check_for_required_parameters()

    print_config(environment, "List")

    # Create ProjectBasedClient to resolve project
    project_client = ProjectBasedClient(
        environment=environment,
        suite=TestRailSuite(name=environment.suite_name, suite_id=environment.suite_id),
    )

    # Resolve project (converts name to ID if needed)
    project_client.resolve_project()

    environment.log(f"Retrieving sections for project ID {project_client.project.project_id}, suite ID {suite_id}...")

    # Retrieve sections using SectionHandler from ProjectBasedClient
    response_data, error_message = project_client.api_request_handler.section_handler.get_sections(
        project_id=project_client.project.project_id,
        suite_id=suite_id,
        limit=limit,
        offset=offset,
    )

    if error_message:
        environment.elog(f"Error: Failed to retrieve sections: {error_message}")
        raise SystemExit(1)

    # Handle output format
    if json_output:
        # Output prettified JSON response
        print(json.dumps(response_data, indent=2))
    else:
        # Display sections line by line
        sections = response_data.get("sections", [])
        response_offset = response_data.get("offset", 0)
        response_limit = response_data.get("limit", 250)
        response_size = response_data.get("size", 0)
        next_link = response_data.get("_links", {}).get("next")

        if not sections:
            environment.log("No sections found.")
        else:
            environment.log(
                f"Found {response_size} section(s) (showing {response_offset + 1}-{response_offset + len(sections)}):"
            )
            if next_link:
                environment.log("  (More results available - use --offset and --limit for pagination)")
            environment.log("")

            for section in sections:
                if show_all_fields:
                    # Show all fields from API response
                    environment.log(f"  Section ID: {section.get('id', 'N/A')}")

                    # Iterate through all fields in the section
                    for key, value in section.items():
                        if key == "id":
                            continue  # Already displayed as Section ID

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
                    # Display compact format with hierarchy indication
                    depth = section.get("depth", 0)
                    indent = "  " + ("  " * depth)  # Extra indentation for child sections

                    environment.log(f"{indent}Section ID: {section.get('id', 'N/A')}")
                    environment.log(f"{indent}  Name: {section.get('name', 'N/A')}")

                    if section.get("description"):
                        description = section.get("description")
                        # Truncate long descriptions in compact mode
                        if len(description) > 60:
                            description = description[:60] + "..."
                        environment.log(f"{indent}  Description: {description}")

                    environment.log(f"{indent}  Suite ID: {section.get('suite_id', 'N/A')}")
                    environment.log(f"{indent}  Depth: {depth}")

                    environment.log("")
