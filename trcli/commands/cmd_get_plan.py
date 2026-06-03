import click

from trcli.cli import pass_environment, CONTEXT_SETTINGS, Environment
from trcli.commands.read_command_helpers import check_auth, create_api_client, emit_json, fail, fetch_single_resource


@click.command(context_settings=CONTEXT_SETTINGS)
@click.option(
    "--plan-id",
    type=click.IntRange(min=1),
    required=True,
    metavar="",
    help="ID of the test plan to retrieve.",
)
@click.pass_context
@pass_environment
def cli(environment: Environment, context: click.Context, *args, **kwargs):
    """Retrieve a single test plan by ID."""
    environment.cmd = "get_plan"
    environment.set_parameters(context)
    check_auth(environment)

    client = create_api_client(environment)
    data, error = fetch_single_resource(client, f"get_plan/{environment.plan_id}")
    if error:
        fail(error)
    emit_json(data)
