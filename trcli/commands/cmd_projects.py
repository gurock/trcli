import builtins
import click
import json

from trcli.api.project_based_client import ProjectBasedClient
from trcli.cli import pass_environment, CONTEXT_SETTINGS, Environment
from trcli.data_classes.dataclass_testrail import TestRailSuite


def print_config(env: Environment, action: str):
    env.log(f"Projects {action} Execution Parameters" f"\n> TestRail instance: {env.host} (user: {env.username})")


def display_project(env: Environment, project: dict, show_all_fields: bool = False):
    """Helper function to display a single project's information."""
    env.log(f"Project ID: {project.get('id')}")
    env.log(f"  Name: {project.get('name', 'N/A')}")
    env.log(f"  Completed: {'Yes' if project.get('is_completed') else 'No'}")
    env.log(f"  Suite Mode: {project.get('suite_mode', 'N/A')}")

    if show_all_fields:
        env.log(f"  URL: {project.get('url', 'N/A')}")
        env.log(f"  Show Announcement: {'Yes' if project.get('show_announcement') else 'No'}")
        if project.get("announcement"):
            env.log(f"  Announcement: {project.get('announcement')}")
        if project.get("completed_on"):
            env.log(f"  Completed On: {project.get('completed_on')}")
        env.log(f"  Default Role: {project.get('default_role', 'N/A')} (ID: {project.get('default_role_id', 'N/A')})")

        # Display users if available
        users = project.get("users", [])
        if users:
            env.log(f"  Users: {len(users)} user(s)")
            for user in users[:5]:  # Show first 5 users
                user_id = user.get("user_id")
                global_role = user.get("global_role", "N/A")
                project_role = user.get("project_role", "N/A")
                env.log(f"    - User ID: {user_id}, Global Role: {global_role}, Project Role: {project_role}")
            if len(users) > 5:
                env.log(f"    ... and {len(users) - 5} more")

        # Display groups if available
        groups = project.get("groups", [])
        if groups:
            env.log(f"  Groups: {len(groups)} group(s)")


@click.group(context_settings=CONTEXT_SETTINGS)
@click.pass_context
@pass_environment
def cli(environment: Environment, context: click.Context, *args, **kwargs):
    """Manage projects in TestRail"""
    environment.cmd = "projects"
    environment.set_parameters(context)


@cli.command()
@click.option("--project-id", type=int, metavar="<id>", required=True, help="Get project by project ID.")
@click.option("--json-output", is_flag=True, help="Output project as raw JSON from API.")
@click.option("--show-all-fields", is_flag=True, help="Show all fields including announcement, users, and groups.")
@click.pass_context
@pass_environment
def get(
    environment: Environment,
    context: click.Context,
    project_id: int,
    json_output: bool,
    show_all_fields: bool,
    *args,
    **kwargs,
):
    """Get a specific project from TestRail"""
    environment.check_for_required_parameters()

    print_config(environment, "Get")

    # Create ProjectBasedClient for consistent API access
    project_client = ProjectBasedClient(
        environment=environment,
        suite=TestRailSuite(name=environment.suite_name, suite_id=environment.suite_id),
    )

    # Retrieve project
    environment.log(f"Retrieving project with ID {project_id}...")
    project, error_message = project_client.api_request_handler.project_handler.get_project(project_id)

    if error_message:
        environment.elog(f"Error: Failed to retrieve project: {error_message}")
        raise SystemExit(1)

    if not project:
        environment.log("No project found.")
        return

    if json_output:
        print(json.dumps(project, indent=2))
    else:
        environment.log("")
        display_project(environment, project, show_all_fields)
        environment.log("")

    environment.log("Project retrieval completed successfully.")


@cli.command()
@click.option(
    "--is-completed",
    type=int,
    metavar="<0|1>",
    help="Filter projects by completion status (0=active, 1=completed).",
)
@click.option("--limit", type=int, metavar="<limit>", help="Limit number of projects returned (default: 250).")
@click.option("--offset", type=int, metavar="<offset>", help="Offset for pagination (default: 0).")
@click.option("--json-output", is_flag=True, help="Output projects as raw JSON from API.")
@click.option("--show-all-fields", is_flag=True, help="Show all fields for each project.")
@click.pass_context
@pass_environment
def list(
    environment: Environment,
    context: click.Context,
    is_completed: int,
    limit: int,
    offset: int,
    json_output: bool,
    show_all_fields: bool,
    *args,
    **kwargs,
):
    """List all projects from TestRail"""
    environment.check_for_required_parameters()

    print_config(environment, "List")

    # Create ProjectBasedClient for consistent API access
    project_client = ProjectBasedClient(
        environment=environment,
        suite=TestRailSuite(name=environment.suite_name, suite_id=environment.suite_id),
    )

    # Build description of filters
    filters = []
    if is_completed is not None:
        filters.append(f"completed={is_completed}")
    if limit is not None:
        filters.append(f"limit={limit}")
    if offset is not None:
        filters.append(f"offset={offset}")

    filter_desc = f" with filters: {', '.join(filters)}" if filters else ""
    environment.log(f"Retrieving projects{filter_desc}...")

    # Retrieve projects
    projects, error_message = project_client.api_request_handler.project_handler.get_projects(
        is_completed=is_completed, limit=limit, offset=offset
    )

    if error_message:
        environment.elog(f"Error: Failed to retrieve projects: {error_message}")
        raise SystemExit(1)

    if json_output:
        print(json.dumps(projects, indent=2))
        return

    # Display results
    environment.log(f"Found {len(projects)} project(s).")
    environment.log("")

    for project in projects:
        display_project(environment, project, show_all_fields)
        environment.log("")

    environment.log("Project listing completed successfully.")
