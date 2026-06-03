import click

from trcli.cli import CONTEXT_SETTINGS, Environment, pass_environment
from trcli.commands.read_command_helpers import (
    build_endpoint,
    check_auth,
    create_api_client,
    emit_json,
    fail,
    fetch_all_pages,
)


@click.command("get_sections", context_settings=CONTEXT_SETTINGS)
@click.option(
    "--project-id",
    type=click.IntRange(min=1),
    required=True,
    metavar="",
    help="Project ID to list sections for.",
)
@click.option(
    "--suite-id",
    type=click.IntRange(min=1),
    default=None,
    metavar="",
    help="Optional suite ID to list sections for.",
)
@click.pass_context
@pass_environment
def cli(environment: Environment, context: click.Context, **kwargs):
    """List sections for a project."""
    environment.cmd = "get_sections"
    environment.set_parameters(context)
    check_auth(environment)

    client = create_api_client(environment)
    link = build_endpoint("get_sections", environment.project_id, suite_id=environment.suite_id)
    data, error = fetch_all_pages(client, "sections", link)
    if error:
        fail(error)
    emit_json(data)
