import click
import json

from trcli.api.project_based_client import ProjectBasedClient
from trcli.cli import pass_environment, CONTEXT_SETTINGS, Environment
from trcli.data_classes.dataclass_testrail import TestRailSuite


def print_config(env: Environment, action: str):
    env.log(
        f"Variables {action} Execution Parameters"
        f"\n> TestRail instance: {env.host} (user: {env.username})"
        f"\n> Project: {env.project if env.project else env.project_id}"
    )


@click.group(context_settings=CONTEXT_SETTINGS)
@click.pass_context
@pass_environment
def cli(environment: Environment, context: click.Context, *args, **kwargs):
    """Manage test data variables in TestRail"""
    environment.cmd = "variables"
    environment.set_parameters(context)


@cli.command()
@click.option("--offset", type=int, default=0, metavar="", help="Offset for pagination (default: 0).")
@click.option("--limit", type=int, default=250, metavar="", help="Limit for pagination (default: 250).")
@click.option("--json-output", is_flag=True, help="Output variables as raw JSON from API.")
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
    """List all variables for a project"""
    environment.check_for_required_parameters()

    # Skip log output when JSON output is requested (for clean JSON-only output)
    if not json_output:
        print_config(environment, "List")

    # Create ProjectBasedClient to resolve project
    project_client = ProjectBasedClient(
        environment=environment,
        suite=TestRailSuite(name=environment.suite_name, suite_id=environment.suite_id),
    )

    # Resolve project (converts name to ID if needed)
    project_client.resolve_project()

    if not json_output:
        environment.log(f"Retrieving variables for project ID {project_client.project.project_id}...")

    # Retrieve variables
    response_data, error_message = project_client.api_request_handler.variables_handler.get_variables(
        project_id=project_client.project.project_id,
        limit=limit,
        offset=offset,
    )

    if error_message:
        environment.elog(f"Error: Failed to retrieve variables: {error_message}")
        raise SystemExit(1)

    # Handle output format
    if json_output:
        print(json.dumps(response_data, indent=2))
    else:
        variables = response_data.get("variables", [])
        response_offset = response_data.get("offset", 0)
        response_size = response_data.get("size", 0)
        next_link = response_data.get("_links", {}).get("next")

        if not variables:
            environment.log("No variables found.")
        else:
            environment.log(
                f"Found {response_size} variable(s) (showing {response_offset + 1}-{response_offset + len(variables)}):"
            )
            if next_link:
                environment.log("  (More results available - use --offset and --limit for pagination)")
            environment.log("")

            for variable in variables:
                environment.log(f"  Variable ID: {variable.get('id', 'N/A')}")
                environment.log(f"    Name: {variable.get('name', 'N/A')}")
                environment.log("")


@cli.command()
@click.option("--name", type=str, required=True, metavar="<name>", help="Name of the variable (required).")
@click.option("--json-output", is_flag=True, help="Output created variable as raw JSON from API.")
@click.pass_context
@pass_environment
def add(
    environment: Environment,
    context: click.Context,
    name: str,
    json_output: bool,
    *args,
    **kwargs,
):
    """Create a new variable"""
    environment.check_for_required_parameters()

    # Skip log output when JSON output is requested (for clean JSON-only output)
    if not json_output:
        print_config(environment, "Add")

    # Create ProjectBasedClient to resolve project
    project_client = ProjectBasedClient(
        environment=environment,
        suite=TestRailSuite(name=environment.suite_name, suite_id=environment.suite_id),
    )

    # Resolve project (converts name to ID if needed)
    project_client.resolve_project()

    if not json_output:
        environment.log(f"Creating variable '{name}' in project ID {project_client.project.project_id}...")

    # Create the variable
    variable, error_message = project_client.api_request_handler.variables_handler.add_variable(
        project_id=project_client.project.project_id,
        name=name,
    )

    if error_message:
        environment.elog(f"Error: Failed to create variable: {error_message}")
        raise SystemExit(1)

    if not variable or not variable.get("id"):
        environment.elog("Error: Variable creation returned unexpected response")
        raise SystemExit(1)

    # Handle output format
    if json_output:
        print(json.dumps(variable, indent=2))
    else:
        environment.log(f"\nVariable created successfully!")
        environment.log(f"  Variable ID: {variable.get('id')}")
        environment.log(f"  Name: {variable.get('name')}")


@cli.command()
@click.option("--variable-id", type=click.IntRange(min=1), required=True, metavar="<id>", help="Variable ID to update.")
@click.option("--name", type=str, required=True, metavar="<name>", help="New name for the variable (required).")
@click.option("--json-output", is_flag=True, help="Output updated variable as raw JSON from API.")
@click.pass_context
@pass_environment
def update(
    environment: Environment,
    context: click.Context,
    variable_id: int,
    name: str,
    json_output: bool,
    *args,
    **kwargs,
):
    """Update an existing variable"""
    environment.cmd = "variables_update"  # Use ID-based command (no project required)
    environment.check_for_required_parameters()

    # Skip log output when JSON output is requested (for clean JSON-only output)
    if not json_output:
        print_config(environment, "Update")

    # Create ProjectBasedClient (needed for environment setup)
    project_client = ProjectBasedClient(
        environment=environment,
        suite=TestRailSuite(name=environment.suite_name, suite_id=environment.suite_id),
    )

    if not json_output:
        environment.log(f"Updating variable ID {variable_id}...")

    # Update the variable
    variable, error_message = project_client.api_request_handler.variables_handler.update_variable(
        variable_id=variable_id,
        name=name,
    )

    if error_message:
        environment.elog(f"Error: Failed to update variable: {error_message}")
        raise SystemExit(1)

    if not variable or not variable.get("id"):
        environment.elog("Error: Variable update returned unexpected response")
        raise SystemExit(1)

    # Handle output format
    if json_output:
        print(json.dumps(variable, indent=2))
    else:
        environment.log(f"\nVariable updated successfully!")
        environment.log(f"  Variable ID: {variable.get('id')}")
        environment.log(f"  Name: {variable.get('name')}")


@cli.command()
@click.option("--variable-id", type=click.IntRange(min=1), required=True, metavar="<id>", help="Variable ID to delete.")
@click.pass_context
@pass_environment
def delete(
    environment: Environment,
    context: click.Context,
    variable_id: int,
    *args,
    **kwargs,
):
    """Delete a variable

    Note: Deleting a variable will also delete corresponding values from datasets.
    """
    environment.cmd = "variables_delete"  # Use ID-based command (no project required)
    environment.check_for_required_parameters()

    print_config(environment, "Delete")

    # Create ProjectBasedClient (needed for environment setup)
    project_client = ProjectBasedClient(
        environment=environment,
        suite=TestRailSuite(name=environment.suite_name, suite_id=environment.suite_id),
    )

    environment.log(f"Deleting variable ID {variable_id}...")

    # Delete the variable
    response, error_message = project_client.api_request_handler.variables_handler.delete_variable(
        variable_id=variable_id,
    )

    if error_message:
        environment.elog(f"Error: Failed to delete variable: {error_message}")
        raise SystemExit(1)

    environment.log(f"\nVariable ID {variable_id} deleted successfully.")
    environment.log("Note: Corresponding values from datasets have also been deleted.")
