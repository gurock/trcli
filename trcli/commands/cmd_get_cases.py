import click

from trcli.cli import pass_environment, CONTEXT_SETTINGS, Environment
from trcli.commands.read_command_helpers import (
    build_endpoint,
    check_auth,
    create_api_client,
    emit_json,
    fail,
    fetch_all_pages,
)


@click.command("get_cases", context_settings=CONTEXT_SETTINGS)
@click.option(
    "--project-id",
    type=click.IntRange(min=1),
    required=True,
    metavar="",
    help="Project ID to list cases for.",
)
@click.option(
    "--suite-id",
    type=click.IntRange(min=1),
    required=True,
    metavar="",
    help="Suite ID to list cases for.",
)
@click.option(
    "--section-id",
    type=click.IntRange(min=1),
    default=None,
    metavar="",
    help="Optional section ID to filter cases.",
)
@click.pass_context
@pass_environment
def cli(environment: Environment, context: click.Context, **kwargs):
    """List test cases for a project and suite."""
    environment.cmd = "get_cases"
    environment.set_parameters(context)
    check_auth(environment)

    client = create_api_client(environment)
    link = build_endpoint(
        "get_cases",
        environment.project_id,
        suite_id=environment.suite_id,
        section_id=environment.section_id,
    )

    data, error = fetch_all_pages(client, "cases", link)
    if error:
        fail(error)

    emit_json(data)
