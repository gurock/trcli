import click

from trcli.api.project_based_client import ProjectBasedClient
from trcli.cli import pass_environment, CONTEXT_SETTINGS, Environment
from trcli.data_classes.dataclass_testrail import TestRailSuite


def print_config(env: Environment):
    """Display update_run execution parameters"""
    env.log(
        f"Update Run Parameters"
        f"\n> TestRail instance: {env.host} (user: {env.username})"
        f"\n> Project: {env.project if env.project else env.project_id}"
        f"\n> Run ID: {env.run_id}"
        f"\n> Run title: {env.title if env.title else '(unchanged)'}"
        f"\n> Description: {env.run_description if env.run_description else '(unchanged)'}"
        f"\n> Assigned To ID: {env.assignedto_id if hasattr(env, 'assignedto_id') else '(unchanged)'}"
    )


@click.command(context_settings=CONTEXT_SETTINGS)
@click.option(
    "--run-id",
    type=click.IntRange(min=1),
    required=True,
    metavar="",
    help="ID of the test run to update.",
)
@click.option("--title", metavar="", help="New title for the test run.")
@click.option("--run-description", metavar="", default="", help="New description for the test run.")
@click.option(
    "--assignedto",
    type=click.IntRange(min=1),
    metavar="",
    help="Assign the test run to the given user ID. User must be active and have access to the project.",
)
@click.option(
    "--clear-assignee",
    is_flag=True,
    default=False,
    help="Clear the assignee of the test run.",
)
@click.pass_context
@pass_environment
def cli(environment: Environment, context: click.Context, *args, **kwargs):
    """Update an existing test run in TestRail"""
    environment.cmd = "update_run"
    environment.set_parameters(context)
    environment.check_for_required_parameters()

    if environment.assignedto and environment.clear_assignee:
        environment.elog("Error: --assignedto and --clear-assignee cannot be used together.")
        exit(1)

    # Handle assignee logic: set assignedto_id attribute only if user specified it
    if environment.clear_assignee:
        environment.assignedto_id = None
    elif environment.assignedto:
        environment.assignedto_id = environment.assignedto
    print_config(environment)

    project_client = ProjectBasedClient(
        environment=environment,
        suite=TestRailSuite(name=environment.suite_name, suite_id=environment.suite_id),
    )
    project_client.resolve_project()
    project_client.resolve_suite()
    run_id, error_message = project_client.create_or_update_test_run()
    if error_message:
        environment.elog(f"Error updating run: {error_message}")
        exit(1)

    environment.log(f"Test run updated successfully")
    environment.log(f"Run ID: {run_id}")
    environment.log(f"Test run: {environment.host}index.php?/runs/view/{run_id}")
