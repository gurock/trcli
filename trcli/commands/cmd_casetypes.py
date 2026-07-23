import builtins
import click
import json

from trcli.api.project_based_client import ProjectBasedClient
from trcli.cli import pass_environment, CONTEXT_SETTINGS, Environment
from trcli.data_classes.dataclass_testrail import TestRailSuite


def print_config(env: Environment, action: str):
    env.log(f"Case Types {action} Execution Parameters" f"\n> TestRail instance: {env.host} (user: {env.username})")


@click.group(context_settings=CONTEXT_SETTINGS)
@click.pass_context
@pass_environment
def cli(environment: Environment, context: click.Context, *args, **kwargs):
    """Manage test case types in TestRail"""
    environment.cmd = "casetypes"
    environment.set_parameters(context)


@cli.command()
@click.option("--json-output", is_flag=True, help="Output case types as raw JSON from API.")
@click.pass_context
@pass_environment
def list(
    environment: Environment,
    context: click.Context,
    json_output: bool,
    *args,
    **kwargs,
):
    """List all test case types from TestRail"""
    environment.check_for_required_parameters()

    print_config(environment, "List")

    # Create ProjectBasedClient (case types are global, but we use this for consistent API access)
    project_client = ProjectBasedClient(
        environment=environment,
        suite=TestRailSuite(name=environment.suite_name, suite_id=environment.suite_id),
    )

    environment.log("Retrieving case types...")

    # Retrieve case types using CaseTypeHandler
    case_types, error_message = project_client.api_request_handler.case_type_handler.get_case_types()

    if error_message:
        environment.elog(f"Error: Failed to retrieve case types: {error_message}")
        raise SystemExit(1)

    if json_output:
        # Output prettified JSON response
        print(json.dumps(case_types, indent=2))
    else:
        environment.log(f"Found {len(case_types)} case type(s).")
        environment.log("")

        if not case_types:
            environment.log("No case types found.")
        else:
            # Display case types in a simple format
            for case_type in case_types:
                case_type_id = case_type.get("id")
                name = case_type.get("name", "N/A")
                is_default = case_type.get("is_default", False)

                default_marker = " [DEFAULT]" if is_default else ""
                environment.log(f"ID: {case_type_id} | Name: {name}{default_marker}")

        environment.log("")

    environment.log("Case type listing completed successfully.")
