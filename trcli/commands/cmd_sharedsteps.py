import builtins
import click
import json
from datetime import datetime
from pathlib import Path

from trcli.api.project_based_client import ProjectBasedClient
from trcli.cli import pass_environment, CONTEXT_SETTINGS, Environment
from trcli.data_classes.dataclass_testrail import TestRailSuite


def print_config(env: Environment, action: str):
    env.log(f"Shared Steps {action} Execution Parameters" f"\n> TestRail instance: {env.host} (user: {env.username})")


def format_timestamp(timestamp: int) -> str:
    """Convert UNIX timestamp to readable format."""
    if timestamp:
        return datetime.fromtimestamp(timestamp).strftime("%Y-%m-%d %H:%M:%S")
    return "N/A"


def display_sharedstep(env: Environment, sharedstep: dict, show_details: bool = False):
    """Helper function to display a single shared step's information."""
    env.log(f"Shared Step ID: {sharedstep.get('id')}")
    env.log(f"  Title: {sharedstep.get('title', 'N/A')}")
    env.log(f"  Project ID: {sharedstep.get('project_id', 'N/A')}")

    if show_details:
        # Show detailed information
        env.log(f"  Created By: {sharedstep.get('created_by', 'N/A')}")
        env.log(f"  Created On: {format_timestamp(sharedstep.get('created_on'))}")
        env.log(f"  Updated By: {sharedstep.get('updated_by', 'N/A')}")
        env.log(f"  Updated On: {format_timestamp(sharedstep.get('updated_on'))}")

        # Display steps
        steps = sharedstep.get("custom_steps_separated", [])
        if steps:
            env.log(f"  Steps ({len(steps)}):")
            for idx, step in enumerate(steps, 1):
                env.log(f"    Step {idx}:")
                if step.get("content"):
                    env.log(f"      Content: {step.get('content')}")
                if step.get("expected"):
                    env.log(f"      Expected: {step.get('expected')}")
                if step.get("additional_info"):
                    env.log(f"      Additional Info: {step.get('additional_info')}")
                if step.get("refs"):
                    env.log(f"      References: {step.get('refs')}")
        else:
            env.log("  Steps: None")

        # Display case IDs that use this shared step
        case_ids = sharedstep.get("case_ids", [])
        if case_ids:
            env.log(f"  Used in {len(case_ids)} test case(s): {', '.join(map(str, case_ids))}")
        else:
            env.log("  Used in: No test cases")


def load_steps_from_file(file_path: str) -> dict:
    """
    Load shared step data from a JSON file.

    Expected format:
    {
        "title": "Step Title",
        "custom_steps_separated": [
            {
                "content": "Step description",
                "expected": "Expected result",
                "additional_info": "Additional info",
                "refs": "TR-123"
            }
        ]
    }

    Args:
        file_path: Path to JSON file

    Returns:
        Dictionary with title and custom_steps_separated

    Raises:
        SystemExit: If file cannot be read or parsed
    """
    path = Path(file_path)

    if not path.exists():
        raise click.ClickException(f"File not found: {file_path}")

    if not path.is_file():
        raise click.ClickException(f"Not a file: {file_path}")

    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        raise click.ClickException(f"Invalid JSON in file {file_path}: {e}")
    except Exception as e:
        raise click.ClickException(f"Error reading file {file_path}: {e}")

    # Validate structure
    if not isinstance(data, dict):
        raise click.ClickException("JSON file must contain a JSON object (not array or other type)")

    if "custom_steps_separated" not in data:
        raise click.ClickException("JSON file must contain 'custom_steps_separated' field")

    if not isinstance(data["custom_steps_separated"], builtins.list):
        raise click.ClickException("'custom_steps_separated' must be an array")

    if not data["custom_steps_separated"]:
        raise click.ClickException("'custom_steps_separated' array cannot be empty")

    return data


@click.group(context_settings=CONTEXT_SETTINGS)
@click.pass_context
@pass_environment
def cli(environment: Environment, context: click.Context, *args, **kwargs):
    """Manage shared steps in TestRail"""
    environment.cmd = "sharedsteps"
    environment.set_parameters(context)


@cli.command()
@click.option(
    "--project-id",
    type=click.IntRange(min=1),
    metavar="<id>",
    help="List shared steps for a specific project ID (uses project from config if not specified).",
)
@click.option("--json-output", is_flag=True, help="Output shared steps as raw JSON from API.")
@click.option("--created-by", type=str, metavar="<user_ids>", help="Comma-separated list of creator user IDs.")
@click.option("--refs", type=str, metavar="<reference>", help="Filter by reference ID (e.g., TR-123).")
@click.option("--limit", type=click.IntRange(min=1), metavar="<n>", help="Limit number of results (max 250).")
@click.option("--offset", type=click.IntRange(min=0), metavar="<n>", help="Skip N records.")
@click.pass_context
@pass_environment
def list(
    environment: Environment,
    context: click.Context,
    project_id: int,
    json_output: bool,
    created_by: str,
    refs: str,
    limit: int,
    offset: int,
    *args,
    **kwargs,
):
    """List all shared steps in a project"""
    environment.check_for_required_parameters()

    print_config(environment, "List")

    # Create ProjectBasedClient for consistent API access
    project_client = ProjectBasedClient(
        environment=environment,
        suite=TestRailSuite(name=environment.suite_name, suite_id=environment.suite_id),
    )

    # Resolve project name to project_id if needed
    if not project_id and environment.project:
        project_client.resolve_project()
        project_id = project_client.project.project_id if project_client.project else None

    if not project_id:
        project_id = environment.project_id

    if not project_id:
        environment.elog("Error: --project-id is required for listing shared steps.")
        environment.elog("Please specify --project-id or configure project in your config file.")
        raise SystemExit(1)

    # Retrieve shared steps
    environment.log(f"Retrieving shared steps for project {project_id}...")

    sharedsteps, error_message = project_client.api_request_handler.sharedstep_handler.get_shared_steps(
        project_id=project_id, created_by=created_by, refs=refs, limit=limit, offset=offset
    )

    if error_message:
        environment.elog(f"Error: Failed to retrieve shared steps: {error_message}")
        raise SystemExit(1)

    if json_output:
        print(json.dumps(sharedsteps, indent=2))
        return

    # Display results
    environment.log(f"Found {len(sharedsteps)} shared step(s).")
    environment.log("")

    for sharedstep in sharedsteps:
        display_sharedstep(environment, sharedstep, show_details=False)
        environment.log("")

    environment.log("Shared steps listing completed successfully.")


@cli.command()
@click.option(
    "--sharedstep-id",
    type=click.IntRange(min=1),
    required=True,
    metavar="<id>",
    help="The ID of the shared step to display.",
)
@click.option("--json-output", is_flag=True, help="Output shared step as raw JSON from API.")
@click.pass_context
@pass_environment
def show(
    environment: Environment,
    context: click.Context,
    sharedstep_id: int,
    json_output: bool,
    *args,
    **kwargs,
):
    """Show details for a specific shared step"""
    environment.check_for_required_parameters()

    print_config(environment, "Show")

    # Create ProjectBasedClient for consistent API access
    project_client = ProjectBasedClient(
        environment=environment,
        suite=TestRailSuite(name=environment.suite_name, suite_id=environment.suite_id),
    )

    # Retrieve shared step details
    environment.log(f"Retrieving shared step {sharedstep_id}...")

    sharedstep, error_message = project_client.api_request_handler.sharedstep_handler.get_shared_step(sharedstep_id)

    if error_message:
        environment.elog(f"Error: Failed to retrieve shared step: {error_message}")
        raise SystemExit(1)

    if json_output:
        print(json.dumps(sharedstep, indent=2))
        return

    # Display detailed information
    environment.log("")
    display_sharedstep(environment, sharedstep, show_details=True)
    environment.log("")
    environment.log("Shared step retrieval completed successfully.")


@cli.command()
@click.option(
    "--project-id",
    type=click.IntRange(min=1),
    metavar="<id>",
    help="Create shared step in a specific project ID (uses project from config if not specified).",
)
@click.option("--name", type=str, required=True, metavar="<title>", help="Title for the shared step.")
@click.option(
    "--steps-file",
    type=str,
    required=True,
    metavar="<file>",
    help="Path to JSON file containing step definitions.",
)
@click.option("--json-output", is_flag=True, help="Output created shared step as raw JSON from API.")
@click.pass_context
@pass_environment
def create(
    environment: Environment,
    context: click.Context,
    project_id: int,
    name: str,
    steps_file: str,
    json_output: bool,
    *args,
    **kwargs,
):
    """Create a new shared step from a file"""
    environment.check_for_required_parameters()

    print_config(environment, "Create")

    # Create ProjectBasedClient for consistent API access
    project_client = ProjectBasedClient(
        environment=environment,
        suite=TestRailSuite(name=environment.suite_name, suite_id=environment.suite_id),
    )

    # Resolve project name to project_id if needed
    if not project_id and environment.project:
        project_client.resolve_project()
        project_id = project_client.project.project_id if project_client.project else None

    if not project_id:
        project_id = environment.project_id

    if not project_id:
        environment.elog("Error: --project-id is required for creating shared steps.")
        environment.elog("Please specify --project-id or configure project in your config file.")
        raise SystemExit(1)

    # Load steps from file
    environment.log(f"Loading steps from file: {steps_file}")
    try:
        steps_data = load_steps_from_file(steps_file)
    except click.ClickException as e:
        environment.elog(f"Error: {e.message}")
        raise SystemExit(1)

    custom_steps = steps_data["custom_steps_separated"]
    environment.log(f"Loaded {len(custom_steps)} step(s) from file.")

    # Create shared step
    environment.log(f"Creating shared step '{name}' in project {project_id}...")

    sharedstep, error_message = project_client.api_request_handler.sharedstep_handler.add_shared_step(
        project_id=project_id, title=name, custom_steps_separated=custom_steps
    )

    if error_message:
        environment.elog(f"Error: Failed to create shared step: {error_message}")
        raise SystemExit(1)

    if json_output:
        print(json.dumps(sharedstep, indent=2))
        return

    # Display success message
    environment.log("")
    environment.log(f"Successfully created shared step!")
    environment.log("")
    display_sharedstep(environment, sharedstep, show_details=True)
    environment.log("")
    environment.log("Shared step creation completed successfully.")


@cli.command()
@click.option(
    "--sharedstep-id",
    type=click.IntRange(min=1),
    required=True,
    metavar="<id>",
    help="The ID of the shared step to update.",
)
@click.option("--name", type=str, metavar="<title>", help="New title for the shared step (optional).")
@click.option(
    "--steps-file",
    type=str,
    metavar="<file>",
    help="Path to JSON file containing step definitions (optional). ALL existing steps will be replaced.",
)
@click.option("--json-output", is_flag=True, help="Output updated shared step as raw JSON from API.")
@click.pass_context
@pass_environment
def update(
    environment: Environment,
    context: click.Context,
    sharedstep_id: int,
    name: str,
    steps_file: str,
    json_output: bool,
    *args,
    **kwargs,
):
    """Update an existing shared step"""
    environment.check_for_required_parameters()

    print_config(environment, "Update")

    # Validate that at least one field is provided
    if not name and not steps_file:
        environment.elog("Error: Either --name or --steps-file must be specified.")
        raise SystemExit(1)

    # Create ProjectBasedClient for consistent API access
    project_client = ProjectBasedClient(
        environment=environment,
        suite=TestRailSuite(name=environment.suite_name, suite_id=environment.suite_id),
    )

    # Load steps from file if provided
    custom_steps = None
    if steps_file:
        environment.log(f"Loading steps from file: {steps_file}")
        try:
            steps_data = load_steps_from_file(steps_file)
            custom_steps = steps_data["custom_steps_separated"]
            environment.log(f"Loaded {len(custom_steps)} step(s) from file.")
        except click.ClickException as e:
            environment.elog(f"Error: {e.message}")
            raise SystemExit(1)

    # Update shared step
    environment.log(f"Updating shared step {sharedstep_id}...")

    sharedstep, error_message = project_client.api_request_handler.sharedstep_handler.update_shared_step(
        shared_step_id=sharedstep_id, title=name, custom_steps_separated=custom_steps
    )

    if error_message:
        environment.elog(f"Error: Failed to update shared step: {error_message}")
        raise SystemExit(1)

    if json_output:
        print(json.dumps(sharedstep, indent=2))
        return

    # Display success message
    environment.log("")
    environment.log(f"Successfully updated shared step!")
    environment.log("")
    display_sharedstep(environment, sharedstep, show_details=True)
    environment.log("")
    environment.log("Shared step update completed successfully.")


@cli.command()
@click.option(
    "--sharedstep-id",
    type=click.IntRange(min=1),
    required=True,
    metavar="<id>",
    help="The ID of the shared step to delete.",
)
@click.option(
    "--no-keep-in-cases",
    "keep_in_cases",
    is_flag=True,
    flag_value=False,
    default=True,
    help="Delete steps from test cases as well as the shared step repository. "
    "By default (without this flag), steps are kept in test cases.",
)
@click.pass_context
@pass_environment
def delete(
    environment: Environment,
    context: click.Context,
    sharedstep_id: int,
    keep_in_cases: bool,
    *args,
    **kwargs,
):
    """Delete an existing shared step (WARNING: cannot be undone)"""
    environment.check_for_required_parameters()

    print_config(environment, "Delete")

    # Create ProjectBasedClient for consistent API access
    project_client = ProjectBasedClient(
        environment=environment,
        suite=TestRailSuite(name=environment.suite_name, suite_id=environment.suite_id),
    )

    # Display warning
    environment.log("")
    environment.log("WARNING: Deleting shared test steps cannot be undone!")
    if keep_in_cases:
        environment.log("The shared step will be deleted, but steps will be kept in test cases.")
    else:
        environment.log("The shared step AND all instances in test cases will be deleted.")
    environment.log("")

    # Delete shared step
    environment.log(f"Deleting shared step {sharedstep_id}...")

    success, error_message = project_client.api_request_handler.sharedstep_handler.delete_shared_step(
        shared_step_id=sharedstep_id, keep_in_cases=keep_in_cases
    )

    if error_message:
        environment.elog(f"Error: Failed to delete shared step: {error_message}")
        raise SystemExit(1)

    if not success:
        environment.elog("Error: Failed to delete shared step (unknown error)")
        raise SystemExit(1)

    # Display success message
    environment.log("")
    environment.log(f"Successfully deleted shared step {sharedstep_id}!")
    environment.log("")
    environment.log("Shared step deletion completed successfully.")
