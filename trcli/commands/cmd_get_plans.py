import json
import sys

import click

import trcli
from trcli.api.api_client import APIClient
from trcli.api.api_request_handler import ApiRequestHandler
from trcli.cli import pass_environment, CONTEXT_SETTINGS, Environment
from trcli.data_classes.dataclass_testrail import TestRailSuite


@click.command(context_settings=CONTEXT_SETTINGS)
@click.pass_context
@pass_environment
def cli(environment: Environment, context: click.Context, *args, **kwargs):
    """List all test plans for a project."""
    environment.cmd = "get_plans"
    environment.set_parameters(context)

    if not environment.host:
        click.echo("Please provide a TestRail server address with the -h argument.", err=True)
        sys.exit(1)
    if not environment.username:
        click.echo("Please provide a valid TestRail username using the -u argument.", err=True)
        sys.exit(1)
    if not environment.password and not environment.key:
        click.echo("Please provide either a password using the -p argument or an API key using the -k argument.", err=True)
        sys.exit(1)
    if not environment.project_id:
        click.echo("Please provide a project ID using the --project-id argument.", err=True)
        sys.exit(1)

    uploader_metadata = APIClient.build_uploader_metadata(version=trcli.__version__)
    api_client = APIClient(
        host_name=environment.host,
        verify=not environment.insecure,
        verbose_logging_function=environment.vlog,
        logging_function=environment.log,
        uploader_metadata=uploader_metadata,
    )
    api_client.username = environment.username
    api_client.password = environment.password
    api_client.api_key = environment.key

    minimal_suite = TestRailSuite(name="Plans Query", testsections=[])
    api_request_handler = ApiRequestHandler(
        environment=environment,
        api_client=api_client,
        suites_data=minimal_suite,
    )

    data, error_message = api_request_handler.get_plans(environment.project_id)
    if error_message:
        click.echo(error_message, err=True)
        sys.exit(1)

    click.echo(json.dumps(data, indent=2))
