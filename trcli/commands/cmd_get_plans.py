import click

from trcli.cli import pass_environment, CONTEXT_SETTINGS, Environment
from trcli.commands.read_command_helpers import check_auth, create_api_client, emit_json, fail, fetch_all_pages


@click.command(context_settings=CONTEXT_SETTINGS)
@click.option(
    "--project-id",
    type=click.IntRange(min=1),
    required=True,
    metavar="",
    help="Project ID to list plans for.",
)
@click.pass_context
@pass_environment
def cli(environment: Environment, context: click.Context, *args, **kwargs):
    """List all test plans for a project."""
    environment.cmd = "get_plans"
    environment.set_parameters(context)
    check_auth(environment)

    client = create_api_client(environment)
    data, error = fetch_all_pages(client, "plans", f"get_plans/{environment.project_id}")
    if error:
        fail(error)
    emit_json(data)
