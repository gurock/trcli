import click
from trcli.cli import pass_environment, Environment, CONTEXT_SETTINGS


@click.command(context_settings=CONTEXT_SETTINGS)
@click.option("-f", "--file", type=click.Path(), help="Filename and path.")
@click.pass_context
@pass_environment
def cli(env: Environment, ctx: click.Context, file):
    env.set_parameters(ctx)
    env.check_for_required_parameters()
