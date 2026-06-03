import click

from trcli.cli import pass_environment, CONTEXT_SETTINGS, Environment
from trcli.commands.read_command_helpers import check_auth, create_api_client, emit_json, fail, fetch_single_resource


@click.command(context_settings=CONTEXT_SETTINGS)
@click.option(
    "--case-id",
    type=click.IntRange(min=1),
    required=True,
    metavar="",
    help="Test case ID to fetch.",
)
@click.pass_context
@pass_environment
def cli(environment: Environment, context: click.Context, **kwargs):
    """Fetch a single test case by ID."""
    environment.cmd = "get_case"
    environment.set_parameters(context)
    check_auth(environment)

    client = create_api_client(environment)
    data, error = fetch_single_resource(client, f"get_case/{environment.case_id}")
    if error:
        fail(error)
    emit_json(data)
