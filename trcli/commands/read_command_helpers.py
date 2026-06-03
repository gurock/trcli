import json
import sys
from urllib.parse import urlencode

import click

import trcli
from trcli.api.api_client import APIClient, APIClientResult
from trcli.cli import Environment


def create_api_client(environment: Environment) -> APIClient:
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


def check_auth(environment: Environment):
    if not environment.host:
        click.echo("Error: --host is required.", err=True)
        sys.exit(1)
    if not environment.username:
        click.echo("Error: --username is required.", err=True)
        sys.exit(1)
    if not environment.password and not environment.key:
        click.echo("Error: --password or --key is required.", err=True)
        sys.exit(1)


def build_endpoint(endpoint: str, resource_id: int, **params) -> str:
    query = urlencode({key: value for key, value in params.items() if value is not None})
    link = f"{endpoint}/{resource_id}"
    if query:
        link = f"{link}&{query}"
    return link


def response_error(response: APIClientResult) -> str:
    if response.error_message:
        return response.error_message
    if response.status_code != 200:
        return f"API returned status {response.status_code}"
    return ""


def fetch_single_resource(client: APIClient, link: str):
    response = client.send_get(link)
    error = response_error(response)
    if error:
        return None, error
    return response.response_text, ""


def fetch_all_pages(client: APIClient, entity_key: str, initial_link: str):
    response = client.send_get(initial_link)
    error = response_error(response)
    if error:
        return None, error

    if isinstance(response.response_text, list):
        return response.response_text, ""

    entities = response.response_text.get(entity_key, [])
    links = response.response_text.get("_links", {})
    while links.get("next") is not None:
        response = client.send_get(links["next"])
        error = response_error(response)
        if error:
            return None, error

        if isinstance(response.response_text, list):
            entities.extend(response.response_text)
            break

        entities.extend(response.response_text.get(entity_key, []))
        links = response.response_text.get("_links", {})

    return entities, ""


def emit_json(data):
    click.echo(json.dumps(data, indent=2))


def fail(error: str):
    click.echo(f"Error: {error}", err=True)
    sys.exit(1)
