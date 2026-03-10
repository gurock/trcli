import json
import sys

import click

import trcli
from trcli.api.api_client import APIClient
from trcli.cli import pass_environment, CONTEXT_SETTINGS, Environment


def _create_api_client(environment: Environment) -> APIClient:
    """Create an APIClient from the environment settings."""
    client_kwargs = {
        "verbose_logging_function": environment.vlog,
        "logging_function": environment.log,
        "verify": not environment.insecure,
        "proxy": environment.proxy,
        "proxy_user": environment.proxy_user,
        "noproxy": environment.noproxy,
        "uploader_metadata": APIClient.build_uploader_metadata(version=trcli.__version__),
    }
    if environment.timeout:
        client_kwargs["timeout"] = environment.timeout

    api_client = APIClient(environment.host, **client_kwargs)
    api_client.username = environment.username
    api_client.password = environment.password
    api_client.api_key = environment.key
    return api_client


@click.command(context_settings=CONTEXT_SETTINGS)
@click.option(
    "--project-id",
    type=click.IntRange(min=1),
    required=True,
    metavar="",
    help="Project ID to list suites for.",
)
@click.pass_context
@pass_environment
def cli(environment: Environment, context: click.Context, **kwargs):
    """List all test suites for a project."""
    environment.cmd = "get_suites"
    environment.set_parameters(context)

    if not environment.host:
        click.echo("Error: --host is required.", err=True)
        sys.exit(1)
    if not environment.username:
        click.echo("Error: --username is required.", err=True)
        sys.exit(1)
    if not environment.password and not environment.key:
        click.echo("Error: --password or --key is required.", err=True)
        sys.exit(1)

    client = _create_api_client(environment)
    response = client.send_get(f"get_suites/{environment.project_id}")

    if response.error_message:
        click.echo(f"Error: {response.error_message}", err=True)
        sys.exit(1)

    if response.status_code != 200:
        click.echo(f"Error: API returned status {response.status_code}", err=True)
        sys.exit(1)

    click.echo(json.dumps(response.response_text, indent=2))
