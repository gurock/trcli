import click
import json

from trcli.api.project_based_client import ProjectBasedClient
from trcli.cli import pass_environment, CONTEXT_SETTINGS, Environment
from trcli.data_classes.dataclass_testrail import TestRailSuite


# Map type IDs to field type names
FIELD_TYPE_NAMES = {
    1: "String",
    2: "Integer",
    3: "Text",
    4: "URL",
    5: "Checkbox",
    6: "Dropdown",
    7: "User",
    8: "Date",
    9: "Milestone",
    11: "Step Results",
    12: "Multi-select",
    13: "Scenarios",
    14: "Scenario Results",
    15: "AI Automation",
    16: "Rating",
}


def print_config(env: Environment, project_filtered: bool):
    env.log(f"Result Fields List Execution Parameters" f"\n> TestRail instance: {env.host} (user: {env.username})")
    if project_filtered:
        env.log(f"> Project: {env.project if env.project else f'ID {env.project_id}'}")
        env.log("> Filtering fields for this project")


def is_field_applicable_to_project(field: dict, project_id: int) -> bool:
    """
    Check if a result field is applicable to a specific project

    :param field: Field dictionary from API
    :param project_id: Project ID to check
    :returns: True if field is applicable to the project
    """
    configs = field.get("configs", [])
    if not configs:
        return False

    for config in configs:
        context = config.get("context", {})
        # Field is applicable if it's global or includes this project
        if context.get("is_global", False):
            return True
        project_ids = context.get("project_ids")
        if project_ids and project_id in project_ids:
            return True

    return False


@click.command(context_settings=CONTEXT_SETTINGS)
@click.option("--json-output", is_flag=True, help="Output result fields as raw JSON from API.")
@click.option("--show-all-fields", is_flag=True, help="Show all fields including configs and options.")
@click.pass_context
@pass_environment
def cli(
    environment: Environment,
    context: click.Context,
    json_output: bool,
    show_all_fields: bool,
):
    """List all result fields from TestRail"""
    environment.cmd = "resultfields"
    environment.set_parameters(context)
    environment.check_for_required_parameters()

    # Create ProjectBasedClient
    project_client = ProjectBasedClient(
        environment=environment,
        suite=TestRailSuite(name=environment.suite_name, suite_id=environment.suite_id),
    )

    # Check if project is specified (either from config or command line)
    project_specified = bool(environment.project or environment.project_id)
    project_id = None

    if project_specified:
        # Resolve project to get project ID
        project_client.resolve_project()
        project_id = project_client.project.project_id

    print_config(environment, project_specified)

    if project_specified:
        environment.log(f"Retrieving result fields for project ID {project_id}...")
    else:
        environment.log("Retrieving all result fields...")

    # Retrieve result fields using ResultFieldHandler
    result_fields_data, error_message = project_client.api_request_handler.result_field_handler.get_result_fields()

    if error_message:
        environment.elog(f"Error: Failed to retrieve result fields: {error_message}")
        raise SystemExit(1)

    # Filter by project if project is specified
    if project_specified and project_id:
        filtered_fields = [field for field in result_fields_data if is_field_applicable_to_project(field, project_id)]
        result_fields_data = filtered_fields

    # Handle output format
    if json_output:
        # Output prettified JSON response
        print(json.dumps(result_fields_data, indent=2))
    else:
        # Display result fields line by line
        if not result_fields_data:
            environment.log("No result fields found.")
        else:
            environment.log(f"Found {len(result_fields_data)} result field(s):")
            environment.log("")

            for field in result_fields_data:
                field_id = field.get("id", "N/A")
                label = field.get("label", "N/A")
                name = field.get("name", "N/A")
                system_name = field.get("system_name", "N/A")
                type_id = field.get("type_id", 0)
                type_name = FIELD_TYPE_NAMES.get(type_id, f"Unknown ({type_id})")
                is_active = field.get("is_active", True)

                environment.log(f"Field ID: {field_id}")
                environment.log(f"  Label: {label}")
                environment.log(f"  Name: {name}")
                environment.log(f"  System Name: {system_name}")
                environment.log(f"  Type: {type_name} (ID: {type_id})")
                environment.log(f"  Active: {'Yes' if is_active else 'No'}")

                if show_all_fields:
                    description = field.get("description")
                    if description:
                        # Truncate long descriptions
                        if len(description) > 100:
                            description = description[:100] + "..."
                        environment.log(f"  Description: {description}")

                    display_order = field.get("display_order")
                    if display_order is not None:
                        environment.log(f"  Display Order: {display_order}")

                    # Show template IDs if available
                    template_ids = field.get("template_ids")
                    if template_ids:
                        environment.log(f"  Template IDs: {template_ids}")

                    # Show configuration details
                    configs = field.get("configs", [])
                    if configs:
                        environment.log(f"  Configurations ({len(configs)}):")
                        for idx, config in enumerate(configs, 1):
                            context_info = config.get("context", {})
                            is_global = context_info.get("is_global", False)
                            project_ids = context_info.get("project_ids")

                            if is_global:
                                environment.log(f"    Config {idx}: Global")
                            elif project_ids:
                                environment.log(f"    Config {idx}: Projects {project_ids}")
                            else:
                                environment.log(f"    Config {idx}: No context")

                            options = config.get("options", {})
                            if options:
                                is_required = options.get("is_required", False)
                                environment.log(f"      Required: {'Yes' if is_required else 'No'}")
                                default_value = options.get("default_value")
                                if default_value:
                                    environment.log(f"      Default: {default_value}")

                environment.log("")

    environment.log("")
    environment.log("Result field listing completed successfully.")
