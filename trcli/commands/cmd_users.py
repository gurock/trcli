import builtins
import click
import json

from trcli.api.project_based_client import ProjectBasedClient
from trcli.cli import pass_environment, CONTEXT_SETTINGS, Environment
from trcli.data_classes.dataclass_testrail import TestRailSuite


def print_config(env: Environment, action: str):
    env.log(f"Users {action} Execution Parameters" f"\n> TestRail instance: {env.host} (user: {env.username})")


def display_user(env: Environment, user: dict, show_all_fields: bool = False):
    """Helper function to display a single user's information."""
    env.log(f"User ID: {user.get('id')}")
    env.log(f"  Name: {user.get('name', 'N/A')}")
    env.log(f"  Email: {user.get('email', 'N/A')}")

    if show_all_fields:
        env.log(f"  Role: {user.get('role', 'N/A')}")
        env.log(f"  Role ID: {user.get('role_id', 'N/A')}")
        env.log(f"  Active: {'Yes' if user.get('is_active') else 'No'}")
        env.log(f"  Admin: {'Yes' if user.get('is_admin') else 'No'}")

        # Enterprise-specific fields
        if "sso_enabled" in user:
            env.log(f"  SSO Enabled: {'Yes' if user.get('sso_enabled') else 'No'}")
        if "assigned_projects" in user:
            env.log(f"  Assigned Projects: {user.get('assigned_projects', [])}")
        if "group_ids" in user:
            env.log(f"  Group IDs: {user.get('group_ids', [])}")
        if "mfa_required" in user:
            env.log(f"  MFA Required: {'Yes' if user.get('mfa_required') else 'No'}")
        if "email_notifications" in user:
            env.log(f"  Email Notifications: {'Yes' if user.get('email_notifications') else 'No'}")
    else:
        # Basic display
        if "role" in user:
            env.log(f"  Role: {user.get('role', 'N/A')}")
        if "is_active" in user:
            env.log(f"  Active: {'Yes' if user.get('is_active') else 'No'}")


@click.group(context_settings=CONTEXT_SETTINGS)
@click.pass_context
@pass_environment
def cli(environment: Environment, context: click.Context, *args, **kwargs):
    """Manage users in TestRail"""
    environment.cmd = "users"
    environment.set_parameters(context)


@cli.command()
@click.option("--current", is_flag=True, help="Get the current authenticated user.")
@click.option("--user-id", type=int, metavar="<id>", help="Get user by user ID.")
@click.option("--email", type=str, metavar="<email>", help="Get user by email address.")
@click.option("--json-output", is_flag=True, help="Output user as raw JSON from API.")
@click.option(
    "--show-all-fields", is_flag=True, help="Show all fields including admin status, groups, and enterprise fields."
)
@click.pass_context
@pass_environment
def get(
    environment: Environment,
    context: click.Context,
    current: bool,
    user_id: int,
    email: str,
    json_output: bool,
    show_all_fields: bool,
    *args,
    **kwargs,
):
    """Get a specific user from TestRail"""
    environment.check_for_required_parameters()

    # Validate mutually exclusive options
    options_provided = sum([current, user_id is not None, email is not None])
    if options_provided == 0:
        environment.elog("Error: Must specify one of --current, --user-id, or --email")
        raise SystemExit(1)
    if options_provided > 1:
        environment.elog("Error: Options --current, --user-id, and --email are mutually exclusive")
        raise SystemExit(1)

    print_config(environment, "Get")

    # Create ProjectBasedClient for consistent API access
    project_client = ProjectBasedClient(
        environment=environment,
        suite=TestRailSuite(name=environment.suite_name, suite_id=environment.suite_id),
    )

    # Retrieve user based on option
    user = None
    error_message = ""

    if current:
        environment.log("Retrieving current authenticated user...")
        user, error_message = project_client.api_request_handler.user_handler.get_current_user()
    elif user_id:
        environment.log(f"Retrieving user with ID {user_id}...")
        user, error_message = project_client.api_request_handler.user_handler.get_user(user_id)
    elif email:
        environment.log(f"Retrieving user with email {email}...")
        user, error_message = project_client.api_request_handler.user_handler.get_user_by_email(email)

    if error_message:
        environment.elog(f"Error: Failed to retrieve user: {error_message}")
        raise SystemExit(1)

    if not user:
        environment.log("No user found.")
        return

    if json_output:
        print(json.dumps(user, indent=2))
    else:
        environment.log("")
        display_user(environment, user, show_all_fields)
        environment.log("")

    environment.log("User retrieval completed successfully.")


@cli.command()
@click.option(
    "--project-id",
    type=int,
    metavar="<id>",
    help="Filter users by project ID (returns only users with access to the project).",
)
@click.option("--json-output", is_flag=True, help="Output users as raw JSON from API.")
@click.option("--show-all-fields", is_flag=True, help="Show all fields for each user.")
@click.pass_context
@pass_environment
def list(
    environment: Environment,
    context: click.Context,
    project_id: int,
    json_output: bool,
    show_all_fields: bool,
    *args,
    **kwargs,
):
    """List all users from TestRail"""
    environment.check_for_required_parameters()

    print_config(environment, "List")

    # Create ProjectBasedClient for consistent API access
    project_client = ProjectBasedClient(
        environment=environment,
        suite=TestRailSuite(name=environment.suite_name, suite_id=environment.suite_id),
    )

    if project_id:
        environment.log(f"Retrieving users for project ID {project_id}...")
    else:
        environment.log("Retrieving all users...")
        environment.log("Note: Listing all users requires administrator privileges.")

    # Retrieve users
    users, error_message = project_client.api_request_handler.user_handler.get_users(project_id)

    if error_message:
        environment.elog(f"Error: Failed to retrieve users: {error_message}")
        raise SystemExit(1)

    if json_output:
        print(json.dumps(users, indent=2))
    else:
        environment.log(f"Found {len(users)} user(s).")
        environment.log("")

        if not users:
            environment.log("No users found.")
        else:
            for user in users:
                display_user(environment, user, show_all_fields)
                environment.log("")

    environment.log("User listing completed successfully.")
