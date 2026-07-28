import click
import json

from trcli.api.project_based_client import ProjectBasedClient
from trcli.cli import pass_environment, CONTEXT_SETTINGS, Environment
from trcli.data_classes.dataclass_testrail import TestRailSuite


def print_config(env: Environment, action: str):
    env.log(
        f"Datasets {action} Execution Parameters"
        f"\n> TestRail instance: {env.host} (user: {env.username})"
        f"\n> Project: {env.project if env.project else env.project_id}"
    )


@click.group(context_settings=CONTEXT_SETTINGS)
@click.pass_context
@pass_environment
def cli(environment: Environment, context: click.Context, *args, **kwargs):
    """Manage test data datasets in TestRail"""
    environment.cmd = "datasets"
    environment.set_parameters(context)


@cli.command()
@click.option("--offset", type=int, default=0, metavar="", help="Offset for pagination (default: 0).")
@click.option("--limit", type=int, default=250, metavar="", help="Limit for pagination (default: 250).")
@click.option("--json-output", is_flag=True, help="Output datasets as raw JSON from API.")
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
    """List all datasets for a project"""
    environment.check_for_required_parameters()

    print_config(environment, "List")

    # Create ProjectBasedClient to resolve project
    project_client = ProjectBasedClient(
        environment=environment,
        suite=TestRailSuite(name=environment.suite_name, suite_id=environment.suite_id),
    )

    # Resolve project (converts name to ID if needed)
    project_client.resolve_project()

    environment.log(f"Retrieving datasets for project ID {project_client.project.project_id}...")

    # Retrieve datasets
    response_data, error_message = project_client.api_request_handler.datasets_handler.get_datasets(
        project_id=project_client.project.project_id,
        limit=limit,
        offset=offset,
    )

    if error_message:
        environment.elog(f"Error: Failed to retrieve datasets: {error_message}")
        raise SystemExit(1)

    # Handle output format
    if json_output:
        print(json.dumps(response_data, indent=2))
    else:
        datasets = response_data.get("datasets", [])
        response_offset = response_data.get("offset", 0)
        response_size = response_data.get("size", 0)
        next_link = response_data.get("_links", {}).get("next")

        if not datasets:
            environment.log("No datasets found.")
        else:
            environment.log(
                f"Found {response_size} dataset(s) (showing {response_offset + 1}-{response_offset + len(datasets)}):"
            )
            if next_link:
                environment.log("  (More results available - use --offset and --limit for pagination)")
            environment.log("")

            for dataset in datasets:
                environment.log(f"  Dataset ID: {dataset.get('id', 'N/A')}")
                environment.log(f"    Name: {dataset.get('name', 'N/A')}")
                variables = dataset.get("variables", [])
                environment.log(f"    Variables: {len(variables)} variable(s)")
                if variables:
                    # Show first few variables as preview
                    preview_count = min(3, len(variables))
                    for i, var in enumerate(variables[:preview_count]):
                        environment.log(f"      - {var.get('name')}: {var.get('value')}")
                    if len(variables) > preview_count:
                        environment.log(f"      ... and {len(variables) - preview_count} more")
                environment.log("")


@cli.command()
@click.option("--dataset-id", type=click.IntRange(min=1), required=True, metavar="<id>", help="Dataset ID to retrieve.")
@click.option("--json-output", is_flag=True, help="Output dataset as raw JSON from API.")
@click.pass_context
@pass_environment
def show(
    environment: Environment,
    context: click.Context,
    dataset_id: int,
    json_output: bool,
    *args,
    **kwargs,
):
    """View a specific dataset with all variable values"""
    environment.check_for_required_parameters()

    print_config(environment, "Show")

    # Create ProjectBasedClient
    project_client = ProjectBasedClient(
        environment=environment,
        suite=TestRailSuite(name=environment.suite_name, suite_id=environment.suite_id),
    )

    environment.log(f"Retrieving dataset ID {dataset_id}...")

    # Retrieve dataset
    dataset, error_message = project_client.api_request_handler.datasets_handler.get_dataset(dataset_id=dataset_id)

    if error_message:
        environment.elog(f"Error: Failed to retrieve dataset: {error_message}")
        raise SystemExit(1)

    # Handle output format
    if json_output:
        print(json.dumps(dataset, indent=2))
    else:
        environment.log("")
        environment.log(f"Dataset ID: {dataset.get('id', 'N/A')}")
        environment.log(f"  Name: {dataset.get('name', 'N/A')}")

        variables = dataset.get("variables", [])
        if variables:
            environment.log(f"\n  Variables ({len(variables)}):")
            for variable in variables:
                environment.log(f"    {variable.get('name', 'N/A')}: {variable.get('value', '')}")
        else:
            environment.log("\n  Variables: (none)")


@cli.command()
@click.option("--name", type=str, required=True, metavar="<name>", help="Name of the dataset (required).")
@click.option(
    "--variables",
    type=str,
    metavar="<json>",
    help='JSON object of variable_name: value pairs. Example: \'{"browser":"Chrome","version":"1.0"}\'',
)
@click.option("--json-output", is_flag=True, help="Output created dataset as raw JSON from API.")
@click.pass_context
@pass_environment
def add(
    environment: Environment,
    context: click.Context,
    name: str,
    variables: str,
    json_output: bool,
    *args,
    **kwargs,
):
    """Create a new dataset"""
    environment.check_for_required_parameters()

    print_config(environment, "Add")

    # Parse variables JSON if provided
    parsed_variables = None
    if variables:
        try:
            parsed_variables = json.loads(variables)
            if not isinstance(parsed_variables, dict):
                environment.elog('Error: --variables must be a JSON object (e.g., \'{"var1":"value1"}\')')
                raise SystemExit(1)
        except json.JSONDecodeError as e:
            environment.elog(f"Error: Invalid JSON in --variables: {e}")
            raise SystemExit(1)

    # Create ProjectBasedClient to resolve project
    project_client = ProjectBasedClient(
        environment=environment,
        suite=TestRailSuite(name=environment.suite_name, suite_id=environment.suite_id),
    )

    # Resolve project (converts name to ID if needed)
    project_client.resolve_project()

    environment.log(f"Creating dataset '{name}' in project ID {project_client.project.project_id}...")

    # Create the dataset
    dataset, error_message = project_client.api_request_handler.datasets_handler.add_dataset(
        project_id=project_client.project.project_id,
        name=name,
        variables=parsed_variables,
    )

    if error_message:
        environment.elog(f"Error: Failed to create dataset: {error_message}")
        raise SystemExit(1)

    if not dataset or not dataset.get("id"):
        environment.elog("Error: Dataset creation returned unexpected response")
        raise SystemExit(1)

    # Handle output format
    if json_output:
        print(json.dumps(dataset, indent=2))
    else:
        environment.log(f"\nDataset created successfully!")
        environment.log(f"  Dataset ID: {dataset.get('id')}")
        environment.log(f"  Name: {dataset.get('name')}")

        variables_list = dataset.get("variables", [])
        if variables_list:
            environment.log(f"  Variables: {len(variables_list)} variable(s)")
            for var in variables_list:
                environment.log(f"    - {var.get('name')}: {var.get('value')}")


@cli.command()
@click.option("--dataset-id", type=click.IntRange(min=1), required=True, metavar="<id>", help="Dataset ID to update.")
@click.option("--name", type=str, metavar="<name>", help="New name for the dataset.")
@click.option(
    "--variables",
    type=str,
    metavar="<json>",
    help='JSON object of variable_name: value pairs to update. Example: \'{"browser":"Firefox"}\'',
)
@click.option("--json-output", is_flag=True, help="Output updated dataset as raw JSON from API.")
@click.pass_context
@pass_environment
def update(
    environment: Environment,
    context: click.Context,
    dataset_id: int,
    name: str,
    variables: str,
    json_output: bool,
    *args,
    **kwargs,
):
    """Update an existing dataset"""
    environment.check_for_required_parameters()

    # Validate that at least one field is provided
    if not name and not variables:
        environment.elog("Error: At least one of --name or --variables must be provided")
        raise SystemExit(1)

    print_config(environment, "Update")

    # Parse variables JSON if provided
    parsed_variables = None
    if variables:
        try:
            parsed_variables = json.loads(variables)
            if not isinstance(parsed_variables, dict):
                environment.elog('Error: --variables must be a JSON object (e.g., \'{"var1":"value1"}\')')
                raise SystemExit(1)
        except json.JSONDecodeError as e:
            environment.elog(f"Error: Invalid JSON in --variables: {e}")
            raise SystemExit(1)

    # Create ProjectBasedClient
    project_client = ProjectBasedClient(
        environment=environment,
        suite=TestRailSuite(name=environment.suite_name, suite_id=environment.suite_id),
    )

    environment.log(f"Updating dataset ID {dataset_id}...")

    # Update the dataset
    dataset, error_message = project_client.api_request_handler.datasets_handler.update_dataset(
        dataset_id=dataset_id,
        name=name,
        variables=parsed_variables,
    )

    if error_message:
        environment.elog(f"Error: Failed to update dataset: {error_message}")
        raise SystemExit(1)

    if not dataset or not dataset.get("id"):
        environment.elog("Error: Dataset update returned unexpected response")
        raise SystemExit(1)

    # Handle output format
    if json_output:
        print(json.dumps(dataset, indent=2))
    else:
        environment.log(f"\nDataset updated successfully!")
        environment.log(f"  Dataset ID: {dataset.get('id')}")
        environment.log(f"  Name: {dataset.get('name')}")

        variables_list = dataset.get("variables", [])
        if variables_list:
            environment.log(f"  Variables: {len(variables_list)} variable(s)")
            for var in variables_list:
                environment.log(f"    - {var.get('name')}: {var.get('value')}")


@cli.command()
@click.option("--dataset-id", type=click.IntRange(min=1), required=True, metavar="<id>", help="Dataset ID to delete.")
@click.pass_context
@pass_environment
def delete(
    environment: Environment,
    context: click.Context,
    dataset_id: int,
    *args,
    **kwargs,
):
    """Delete a dataset

    Note: Cannot delete the Default dataset. Deleting a dataset will also remove the dataset's values.
    """
    environment.check_for_required_parameters()

    print_config(environment, "Delete")

    # Create ProjectBasedClient
    project_client = ProjectBasedClient(
        environment=environment,
        suite=TestRailSuite(name=environment.suite_name, suite_id=environment.suite_id),
    )

    environment.log(f"Deleting dataset ID {dataset_id}...")

    # Delete the dataset
    response, error_message = project_client.api_request_handler.datasets_handler.delete_dataset(
        dataset_id=dataset_id,
    )

    if error_message:
        environment.elog(f"Error: Failed to delete dataset: {error_message}")
        raise SystemExit(1)

    environment.log(f"\nDataset ID {dataset_id} deleted successfully.")
    environment.log("Note: The dataset's values have also been removed.")
