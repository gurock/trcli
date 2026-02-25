"""
Update command for TRCLI.

Provides a convenient way to update TRCLI to the latest version from PyPI.
"""

import sys
import subprocess
import click

from trcli.cli import CONTEXT_SETTINGS
from trcli.version_checker import _query_pypi, _compare_and_format
from trcli import __version__


@click.command(context_settings=CONTEXT_SETTINGS)
@click.option(
    "--check-only",
    is_flag=True,
    help="Only check for updates without installing.",
)
@click.option(
    "--force",
    is_flag=True,
    help="Force reinstall even if already on latest version.",
)
def cli(check_only: bool, force: bool):
    """Update TRCLI to the latest version from PyPI.

    This command checks PyPI for the latest version and updates TRCLI
    using pip. It will show what version will be installed before proceeding.

    Examples:
        trcli update                # Update to latest version
        trcli update --check-only   # Only check for updates
        trcli update --force        # Force reinstall current version
    """
    click.echo(f"Current version: {__version__}")
    click.echo()

    # Query PyPI for latest version
    click.echo("Checking PyPI for latest version...")
    latest_version = _query_pypi()

    if latest_version is None:
        click.secho("✗ Failed to query PyPI. Check your network connection.", fg="red", err=True)
        sys.exit(1)

    click.echo(f"Latest version on PyPI: {latest_version}")
    click.echo()

    # Check if update is available
    update_message = _compare_and_format(__version__, latest_version)

    if update_message is None and not force:
        click.secho(f"✓ You are already on the latest version ({__version__})!", fg="green")
        click.echo()
        click.echo("Use --force to reinstall the current version.")
        sys.exit(0)

    # If check-only, just display the message and exit
    if check_only:
        if update_message:
            click.echo(update_message)
        else:
            click.secho(f"✓ You are already on the latest version ({__version__})!", fg="green")
        sys.exit(0)

    # Show what will be updated
    if force:
        click.secho(f"⚠️  Forcing reinstall of version {__version__}", fg="yellow")
    else:
        click.secho(f"→ Updating from {__version__} to {latest_version}", fg="blue")

    click.echo()

    # Confirm with user
    if not click.confirm("Do you want to proceed with the update?"):
        click.echo("Update cancelled.")
        sys.exit(0)

    click.echo()
    click.echo("Starting update...")
    click.echo("=" * 60)
    click.echo()

    # Prepare pip command
    pip_command = [sys.executable, "-m", "pip", "install", "--upgrade", "trcli"]

    if force:
        pip_command.append("--force-reinstall")

    # Run pip install
    try:
        result = subprocess.run(
            pip_command,
            capture_output=False,  # Show pip output directly
            text=True,
            check=False,  # Don't raise exception, we'll check returncode
        )

        click.echo()
        click.echo("=" * 60)
        click.echo()

        if result.returncode == 0:
            # Success
            click.secho("✓ Update completed successfully!", fg="green", bold=True)
            click.echo()
            click.echo("Run 'trcli' to verify the new version.")

            # Check if we need to inform about restart
            if sys.prefix != sys.base_prefix:  # In virtual environment
                click.echo()
                click.secho("Note: You may need to restart your virtual environment.", fg="yellow")

        else:
            # Failed
            click.secho("✗ Update failed!", fg="red", bold=True, err=True)
            click.echo()
            click.echo("Common issues and solutions:", err=True)
            click.echo("  • Permission denied: Try using --user flag", err=True)
            click.echo("    pip install --user --upgrade trcli", err=True)
            click.echo("  • Already satisfied: You may already have the latest version", err=True)
            click.echo("  • Network issues: Check your internet connection", err=True)
            sys.exit(result.returncode)

    except FileNotFoundError:
        click.secho("✗ Error: pip not found!", fg="red", bold=True, err=True)
        click.echo()
        click.echo("Please ensure pip is installed and available in your PATH.", err=True)
        sys.exit(1)

    except KeyboardInterrupt:
        click.echo()
        click.secho("✗ Update interrupted by user.", fg="yellow", err=True)
        sys.exit(130)

    except Exception as e:
        click.secho(f"✗ Unexpected error: {e}", fg="red", bold=True, err=True)
        sys.exit(1)
