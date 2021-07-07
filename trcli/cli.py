import os
import sys

import click

CONTEXT_SETTINGS = dict(auto_envvar_prefix="TR_CLI")

class Environment:
    def __init__(self):
        self.verbose = False
        self.home = os.getcwd()

    def log(self, msg, *args):
        """Logs a message to stderr."""
        if args:
            msg %= args
        click.echo(msg, file=sys.stderr)

    def vlog(self, msg, *args):
        """Logs a message to stderr only if the verbose option is enabled"""
        if self.verbose:
            self.log(msg, *args)


pass_environment = click.make_pass_decorator(Environment, ensure=True)
cmd_folder = os.path.abspath(os.path.join(os.path.dirname(__file__), "commands"))

class TRCLI(click.MultiCommand):
    def list_commands(self, ctx):
        rv = []
        for filename in os.listdir(cmd_folder):
            if filename.endswith(".py") and filename.startswith("cmd_"):
                rv.append(filename[4:-3])
        rv.sort()
        return rv

    def get_command(self, ctx, name):
        try:
            mod = __import__(f"trcli.commands.cmd_{name}", None, None, ["cli"])
        except ImportError:
            print('trcli failed to load')
            return
        return mod.cli


@click.command(cls=TRCLI, context_settings=CONTEXT_SETTINGS)
@click.option(
    "-v",
    "--verbose",
    is_flag=True,
    help="Enables verbose logging."
)
@pass_environment

def cli(ctx, verbose):
    """TestRail CLI"""
    ctx.verbose = verbose
