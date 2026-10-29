import click
import json

from trcli.api.project_based_client import ProjectBasedClient
from trcli.cli import pass_environment, CONTEXT_SETTINGS, Environment
from trcli.data_classes.dataclass_testrail import TestRailSuite
from trcli.api.dynamic_filters_utils import FIELD_TYPES


def print_config(env: Environment, action: str):
    env.log(
        f"Fields {action} Execution Parameters"
        f"\n> TestRail instance: {env.host} (user: {env.username})"
        f"\n> Project: {env.project if env.project else env.project_id}"
    )


@click.group(context_settings=CONTEXT_SETTINGS)
@click.pass_context
@pass_environment
def cli(environment: Environment, context: click.Context, *args, **kwargs):
    """Manage fields in TestRail"""
    environment.cmd = "fields"
    environment.set_parameters(context)


@cli.command(name="list-dynamic")
@click.option("--json-output", is_flag=True, help="Output fields as raw JSON from API.")
@click.pass_context
@pass_environment
def list_dynamic(
    environment: Environment,
    context: click.Context,
    json_output: bool,
    *args,
    **kwargs,
):
    """List available dynamic filter fields for a project"""
    environment.check_for_required_parameters()

    print_config(environment, "List-Dynamic")

    # Create ProjectBasedClient to resolve project
    project_client = ProjectBasedClient(
        environment=environment,
        suite=TestRailSuite(name=environment.suite_name, suite_id=environment.suite_id),
    )

    # Resolve project (converts name to ID if needed)
    project_client.resolve_project()

    environment.log(f"Retrieving dynamic filter fields for project ID {project_client.project.project_id}...")

    # Retrieve fields using DynamicFilterHandler
    fields, error_message = project_client.api_request_handler.dynamic_filter_handler.get_dynamic_filter_fields(
        project_id=project_client.project.project_id
    )

    if error_message:
        environment.elog(f"Error: Failed to retrieve fields: {error_message}")
        raise SystemExit(1)

    # Handle output format
    if json_output:
        # Output prettified JSON response
        print(json.dumps(fields, indent=2))
    else:
        # Display fields in human-readable format
        if not fields:
            environment.log("No dynamic filter fields found.")
        else:
            environment.log(f"\nFound {len(fields)} available field(s) for dynamic filtering:\n")

            for field in fields:
                type_id = field.get("type_id", "Unknown")
                type_name = FIELD_TYPES.get(type_id, f"Type {type_id}")
                system_name = field.get("system_name", "N/A")
                label = field.get("label", "N/A")

                environment.log(f"Field: {label}")
                environment.log(f"  System Name: {system_name}")
                environment.log(f"  Type: {type_name} (ID: {type_id})")

                # Show operators if available (for fields that support operator-based filtering)
                sub_filters = field.get("sub_filters")
                if sub_filters:
                    environment.log(f"  Available Operators:")
                    for op in sub_filters:
                        op_id = op.get("op", "N/A")
                        op_label = op.get("label", "N/A")
                        environment.log(f"    - {op_label} (op: {op_id})")

                # Show options if available (for dropdown/multi-select fields)
                options = field.get("options")
                if options:
                    # Parse options - can be a string format "ID,Label\nID,Label" or a list
                    parsed_options = []
                    if isinstance(options, str):
                        # Parse string format: "1,GPT-5\n2,Gemini 3\n3,Sonnet 3.5"
                        for line in options.strip().split("\n"):
                            if line.strip():
                                parts = line.split(",", 1)  # Split on first comma only
                                if len(parts) == 2:
                                    opt_id = parts[0].strip()
                                    opt_label = parts[1].strip()
                                    parsed_options.append({"id": opt_id, "label": opt_label})
                                else:
                                    # Fallback for malformed lines
                                    parsed_options.append({"id": "N/A", "label": line.strip()})
                    elif isinstance(options, list):
                        # Already a list of dicts or strings
                        parsed_options = options

                    if parsed_options:
                        environment.log(f"  Available Options ({len(parsed_options)}):")
                        # Show first 5 options, then indicate if there are more
                        display_options = parsed_options[:5]
                        for option in display_options:
                            if isinstance(option, dict):
                                opt_id = option.get("id", "N/A")
                                opt_label = option.get("label", "N/A")
                                environment.log(f"    - {opt_label} (ID: {opt_id})")
                            else:
                                # Option is a plain string
                                environment.log(f"    - {option}")
                        if len(parsed_options) > 5:
                            environment.log(
                                f"    ... and {len(parsed_options) - 5} more (use --json-output to see all)"
                            )

                environment.log("")  # Blank line between fields
