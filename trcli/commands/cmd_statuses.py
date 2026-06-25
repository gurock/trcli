import click
import json

from trcli.api.project_based_client import ProjectBasedClient
from trcli.cli import pass_environment, CONTEXT_SETTINGS, Environment
from trcli.data_classes.dataclass_testrail import TestRailSuite


def print_config(env: Environment, action: str):
    env.log(
        f"Statuses {action} Execution Parameters"
        f"\n> TestRail instance: {env.host} (user: {env.username})"
        f"\n> Project: {env.project if env.project else env.project_id}"
    )


@click.group(context_settings=CONTEXT_SETTINGS)
@click.pass_context
@pass_environment
def cli(environment: Environment, context: click.Context, *args, **kwargs):
    """Manage test statuses in TestRail"""
    environment.cmd = "statuses"
    environment.set_parameters(context)


@cli.command()
@click.option("--json-output", is_flag=True, help="Output statuses as raw JSON from API.")
@click.option("--show-all-fields", is_flag=True, help="Show all fields for each status.")
@click.pass_context
@pass_environment
def all(
    environment: Environment,
    context: click.Context,
    json_output: bool,
    show_all_fields: bool,
    *args,
    **kwargs,
):
    """List all test result statuses from TestRail"""
    environment.check_for_required_parameters()

    print_config(environment, "List (Test Result Statuses)")

    # Create ProjectBasedClient to resolve project
    project_client = ProjectBasedClient(
        environment=environment,
        suite=TestRailSuite(name=environment.suite_name, suite_id=environment.suite_id),
    )

    # Resolve project (converts name to ID if needed)
    project_client.resolve_project()

    environment.log(f"Retrieving test result statuses for project ID {project_client.project.project_id}...")

    # Retrieve statuses using StatusHandler from ProjectBasedClient
    statuses_data, error_message = project_client.api_request_handler.status_handler.get_statuses(
        project_id=project_client.project.project_id
    )

    if error_message:
        environment.elog(f"Error: Failed to retrieve statuses: {error_message}")
        raise SystemExit(1)

    # Handle output format
    if json_output:
        # Output prettified JSON response
        print(json.dumps(statuses_data, indent=2))
    else:
        # Display statuses line by line
        if not statuses_data:
            environment.log("No statuses found.")
        else:
            environment.log(f"Found {len(statuses_data)} test result status(es):")
            environment.log("")

            for status in statuses_data:
                status_id = status.get("id", "N/A")
                name = status.get("name", "N/A")
                label = status.get("label", "N/A")
                is_system = status.get("is_system", False)
                is_untested = status.get("is_untested", False)
                is_final = status.get("is_final", False)

                environment.log(f"Status ID: {status_id}")
                environment.log(f"  Name: {name}")
                environment.log(f"  Label: {label}")
                environment.log(f"  System Status: {'Yes' if is_system else 'No'}")
                environment.log(f"  Is Untested: {'Yes' if is_untested else 'No'}")
                environment.log(f"  Is Final: {'Yes' if is_final else 'No'}")

                if show_all_fields:
                    color_dark = status.get("color_dark", "N/A")
                    color_medium = status.get("color_medium", "N/A")
                    color_bright = status.get("color_bright", "N/A")
                    environment.log(f"  Colors: Dark={color_dark}, Medium={color_medium}, Bright={color_bright}")

                environment.log("")

    environment.log("")
    environment.log("Status listing completed successfully.")


@cli.command()
@click.option("--json-output", is_flag=True, help="Output case statuses as raw JSON from API.")
@click.option("--show-all-fields", is_flag=True, help="Show all fields for each case status.")
@click.pass_context
@pass_environment
def case(
    environment: Environment,
    context: click.Context,
    json_output: bool,
    show_all_fields: bool,
    *args,
    **kwargs,
):
    """List all case statuses from TestRail (Enterprise 7.3+)"""
    environment.check_for_required_parameters()

    print_config(environment, "List (Case Statuses)")

    # Create ProjectBasedClient (no need to resolve project for case statuses)
    project_client = ProjectBasedClient(
        environment=environment,
        suite=TestRailSuite(name=environment.suite_name, suite_id=environment.suite_id),
    )

    environment.log("Retrieving case statuses...")
    environment.log("Note: This command requires TestRail Enterprise 7.3 or later.")

    # Retrieve case statuses using StatusHandler from ProjectBasedClient
    case_statuses_data, error_message = project_client.api_request_handler.status_handler.get_case_statuses()

    if error_message:
        environment.elog(f"Error: Failed to retrieve case statuses: {error_message}")
        environment.elog(
            "Note: get_case_statuses requires TestRail Enterprise 7.3+. "
            "If you have an older version, this endpoint may not be available."
        )
        raise SystemExit(1)

    # Handle output format
    if json_output:
        # Output prettified JSON response
        print(json.dumps(case_statuses_data, indent=2))
    else:
        # Display case statuses line by line
        if not case_statuses_data:
            environment.log("No case statuses found.")
        else:
            environment.log(f"Found {len(case_statuses_data)} case status(es):")
            environment.log("")

            for case_status in case_statuses_data:
                case_status_id = case_status.get("case_status_id", "N/A")
                name = case_status.get("name", "N/A")
                is_default = case_status.get("is_default", False)
                is_approved = case_status.get("is_approved", False)

                environment.log(f"Case Status ID: {case_status_id}")
                environment.log(f"  Name: {name}")
                environment.log(f"  Is Default: {'Yes' if is_default else 'No'}")
                environment.log(f"  Is Approved: {'Yes' if is_approved else 'No'}")

                if show_all_fields:
                    abbreviation = case_status.get("abbreviation")
                    if abbreviation:
                        environment.log(f"  Abbreviation: {abbreviation}")
                    else:
                        environment.log("  Abbreviation: (none)")

                environment.log("")

    environment.log("")
    environment.log("Case status listing completed successfully.")
