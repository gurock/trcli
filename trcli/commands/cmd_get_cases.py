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


def _check_auth(environment: Environment):
    """Validate required auth parameters are present."""
    if not environment.host:
        click.echo("Error: --host is required.", err=True)
        sys.exit(1)
    if not environment.username:
        click.echo("Error: --username is required.", err=True)
        sys.exit(1)
    if not environment.password and not environment.key:
        click.echo("Error: --password or --key is required.", err=True)
        sys.exit(1)


def _get_all_pages(client: APIClient, entity_key: str, initial_link: str):
    """Fetch all pages for a paginated endpoint.

    Returns (data_list, error_message).
    """
    response = client.send_get(initial_link)
    if response.error_message:
        return None, response.error_message
    if response.status_code != 200:
        return None, f"API returned status {response.status_code}"

    # Non-paginated (legacy): response is a plain list
    if isinstance(response.response_text, list):
        return response.response_text, None

    # Paginated: response is a dict with entity key and _links
    entities = response.response_text.get(entity_key, [])
    links = response.response_text.get("_links", {})
    while links.get("next") is not None:
        next_link = links["next"]
        response = client.send_get(next_link)
        if response.error_message:
            return None, response.error_message
        if isinstance(response.response_text, list):
            entities.extend(response.response_text)
            break
        entities.extend(response.response_text.get(entity_key, []))
        links = response.response_text.get("_links", {})

    return entities, None


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
    _check_auth(environment)

    client = _create_api_client(environment)

    link = f"get_cases/{environment.project_id}&suite_id={environment.suite_id}"
    if environment.section_id:
        link += f"&section_id={environment.section_id}"

    data, error = _get_all_pages(client, "cases", link)
    if error:
        click.echo(f"Error: {error}", err=True)
        sys.exit(1)

    click.echo(json.dumps(data, indent=2))
