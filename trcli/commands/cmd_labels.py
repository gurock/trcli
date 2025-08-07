import click

from trcli.api.project_based_client import ProjectBasedClient
from trcli.cli import pass_environment, CONTEXT_SETTINGS, Environment
from trcli.data_classes.dataclass_testrail import TestRailSuite


def print_config(env: Environment, action: str):
    env.log(f"Labels {action} Execution Parameters"
            f"\n> TestRail instance: {env.host} (user: {env.username})"
            f"\n> Project: {env.project if env.project else env.project_id}")


@click.group(context_settings=CONTEXT_SETTINGS)
@click.pass_context
@pass_environment
def cli(environment: Environment, context: click.Context, *args, **kwargs):
    """Manage labels in TestRail"""
    environment.cmd = "labels"
    environment.set_parameters(context)


@cli.command()
@click.option("--title", required=True, metavar="", help="Title of the label to add (max 20 characters).")
@click.pass_context
@pass_environment
def add(environment: Environment, context: click.Context, title: str, *args, **kwargs):
    """Add a new label in TestRail"""
    environment.check_for_required_parameters()
    print_config(environment, "Add")
    
    if len(title) > 20:
        environment.elog("Error: Label title must be 20 characters or less.")
        exit(1)
    
    project_client = ProjectBasedClient(
        environment=environment,
        suite=TestRailSuite(name=environment.suite_name, suite_id=environment.suite_id),
    )
    project_client.resolve_project()
    
    environment.log(f"Adding label '{title}'...")
    
    label_data, error_message = project_client.api_request_handler.add_label(
        project_id=project_client.project.project_id,
        title=title
    )
    
    if error_message:
        environment.elog(f"Failed to add label: {error_message}")
        exit(1)
    else:
        # API response has nested structure: {'label': {'id': 5, 'title': 'hello', ...}}
        label_info = label_data.get('label', label_data)  # Handle both nested and flat responses
        environment.log(f"Successfully added label: ID={label_info['id']}, Title='{label_info['title']}'")


@cli.command()
@click.option("--id", "label_id", required=True, type=int, metavar="", help="ID of the label to update.")
@click.option("--title", required=True, metavar="", help="New title for the label (max 20 characters).")
@click.pass_context
@pass_environment
def update(environment: Environment, context: click.Context, label_id: int, title: str, *args, **kwargs):
    """Update an existing label in TestRail"""
    environment.check_for_required_parameters()
    print_config(environment, "Update")
    
    if len(title) > 20:
        environment.elog("Error: Label title must be 20 characters or less.")
        exit(1)
    
    project_client = ProjectBasedClient(
        environment=environment,
        suite=TestRailSuite(name=environment.suite_name, suite_id=environment.suite_id),
    )
    project_client.resolve_project()
    
    environment.log(f"Updating label with ID {label_id}...")
    
    label_data, error_message = project_client.api_request_handler.update_label(
        label_id=label_id,
        project_id=project_client.project.project_id,
        title=title
    )
    
    if error_message:
        environment.elog(f"Failed to update label: {error_message}")
        exit(1)
    else:
        # Handle both nested and flat API responses
        label_info = label_data.get('label', label_data)
        environment.log(f"Successfully updated label: ID={label_info['id']}, Title='{label_info['title']}'")


@cli.command()
@click.option("--ids", required=True, metavar="", help="Comma-separated list of label IDs to delete (e.g., 1,2,3).")
@click.confirmation_option(prompt="Are you sure you want to delete these labels?")
@click.pass_context
@pass_environment
def delete(environment: Environment, context: click.Context, ids: str, *args, **kwargs):
    """Delete labels from TestRail"""
    environment.check_for_required_parameters()
    print_config(environment, "Delete")
    
    try:
        label_ids = [int(id.strip()) for id in ids.split(",")]
    except ValueError:
        environment.elog("Error: Invalid label IDs format. Use comma-separated integers (e.g., 1,2,3).")
        exit(1)
    
    project_client = ProjectBasedClient(
        environment=environment,
        suite=TestRailSuite(name=environment.suite_name, suite_id=environment.suite_id),
    )
    project_client.resolve_project()
    
    environment.log(f"Deleting labels with IDs: {', '.join(map(str, label_ids))}...")
    
    # Use single delete endpoint for one label, batch endpoint for multiple
    if len(label_ids) == 1:
        success, error_message = project_client.api_request_handler.delete_label(label_ids[0])
    else:
        success, error_message = project_client.api_request_handler.delete_labels(label_ids)
    
    if error_message:
        environment.elog(f"Failed to delete labels: {error_message}")
        exit(1)
    else:
        environment.log(f"Successfully deleted {len(label_ids)} label(s)")


@cli.command()
@click.option("--offset", type=int, default=0, metavar="", help="Offset for pagination (default: 0).")
@click.option("--limit", type=int, default=250, metavar="", help="Limit for pagination (default: 250).")
@click.pass_context
@pass_environment
def list(environment: Environment, context: click.Context, offset: int, limit: int, *args, **kwargs):
    """List all labels in the project"""
    environment.check_for_required_parameters()
    print_config(environment, "List")
    
    project_client = ProjectBasedClient(
        environment=environment,
        suite=TestRailSuite(name=environment.suite_name, suite_id=environment.suite_id),
    )
    project_client.resolve_project()
    
    environment.log("Retrieving labels...")
    
    labels_data, error_message = project_client.api_request_handler.get_labels(
        project_id=project_client.project.project_id,
        offset=offset,
        limit=limit
    )
    
    if error_message:
        environment.elog(f"Failed to retrieve labels: {error_message}")
        exit(1)
    else:
        labels = labels_data.get('labels', [])
        total_size = labels_data.get('size', len(labels))
        
        environment.log(f"Found {len(labels)} labels (showing {offset + 1}-{offset + len(labels)} of {total_size}):")
        environment.log("")
        
        if labels:
            for label in labels:
                environment.log(f"  ID: {label['id']}, Title: '{label['title']}', Created by: {label.get('created_by', 'N/A')}")
        else:
            environment.log("  No labels found.")


@cli.command()
@click.option("--id", "label_id", required=True, type=int, metavar="", help="ID of the label to retrieve.")
@click.pass_context
@pass_environment
def get(environment: Environment, context: click.Context, label_id: int, *args, **kwargs):
    """Get a specific label by ID"""
    environment.check_for_required_parameters()
    print_config(environment, "Get")
    
    project_client = ProjectBasedClient(
        environment=environment,
        suite=TestRailSuite(name=environment.suite_name, suite_id=environment.suite_id),
    )
    project_client.resolve_project()
    
    environment.log(f"Retrieving label with ID {label_id}...")
    
    label_data, error_message = project_client.api_request_handler.get_label(label_id)
    
    # Debug: Log what we received
    if environment.verbose:
        environment.log(f"Debug: API response: {label_data}")
        environment.log(f"Debug: Error message: {error_message}")
    
    if error_message:
        environment.elog(f"Failed to retrieve label: {error_message}")
        exit(1)
    elif not label_data:
        environment.elog(f"No data received for label ID {label_id}")
        exit(1)
    else:
        environment.log(f"Label details:")
        
        # Handle different possible response structures
        if isinstance(label_data, dict):
            # Check if it's a nested response like add_label
            if 'label' in label_data:
                label_info = label_data['label']
            else:
                label_info = label_data
            
            # Ensure we have the basic required fields
            if not label_info or not isinstance(label_info, dict):
                environment.elog(f"Invalid label data received: {label_info}")
                exit(1)
            
            environment.log(f"  ID: {label_info.get('id', label_id)}")  # Fallback to requested ID
            environment.log(f"  Title: '{label_info.get('title', label_info.get('name', 'N/A'))}'")
            environment.log(f"  Created by: {label_info.get('created_by', 'N/A')}")
            environment.log(f"  Created on: {label_info.get('created_on', 'N/A')}")
        else:
            environment.elog(f"Unexpected response format: {label_data}")
            exit(1) 