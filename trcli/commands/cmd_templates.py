import builtins
import click
import json

from trcli.api.project_based_client import ProjectBasedClient
from trcli.cli import pass_environment, CONTEXT_SETTINGS, Environment
from trcli.data_classes.dataclass_testrail import TestRailSuite


def print_config(env: Environment, action: str):
    env.log(f"Templates {action} Execution Parameters" f"\n> TestRail instance: {env.host} (user: {env.username})")


def display_template(env: Environment, template: dict):
    """Helper function to display a single template's information."""
    env.log(f"Template ID: {template.get('id')}")
    env.log(f"  Name: {template.get('name', 'N/A')}")
    env.log(f"  Default: {'Yes' if template.get('is_default') else 'No'}")
    env.log(f"  Custom ID: {template.get('i18n_custom_id', 'N/A')}")


@click.group(context_settings=CONTEXT_SETTINGS)
@click.pass_context
@pass_environment
def cli(environment: Environment, context: click.Context, *args, **kwargs):
    """Manage templates in TestRail"""
    environment.cmd = "templates"
    environment.set_parameters(context)


@cli.command()
@click.option(
    "--project-id", type=click.IntRange(min=1), metavar="<id>", required=True, help="Get templates for project ID."
)
@click.option("--json-output", is_flag=True, help="Output templates as raw JSON from API.")
@click.pass_context
@pass_environment
def list(
    environment: Environment,
    context: click.Context,
    project_id: int,
    json_output: bool,
    *args,
    **kwargs,
):
    """List all templates (field layouts) for a project"""
    environment.check_for_required_parameters()

    print_config(environment, "List")

    # Create ProjectBasedClient for consistent API access
    project_client = ProjectBasedClient(
        environment=environment,
        suite=TestRailSuite(name=environment.suite_name, suite_id=environment.suite_id),
    )

    # Retrieve templates
    environment.log(f"Retrieving templates for project ID {project_id}...")
    templates, error_message = project_client.api_request_handler.template_handler.get_templates(project_id)

    if error_message:
        environment.elog(f"Error: Failed to retrieve templates: {error_message}")
        raise SystemExit(1)

    if json_output:
        print(json.dumps(templates, indent=2))
        return

    # Display results
    environment.log(f"Found {len(templates)} template(s).")
    environment.log("")

    for template in templates:
        display_template(environment, template)
        environment.log("")

    environment.log("Template listing completed successfully.")
