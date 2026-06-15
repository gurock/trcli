import builtins
import click
import json

from trcli.api.project_based_client import ProjectBasedClient
from trcli.cli import pass_environment, CONTEXT_SETTINGS, Environment
from trcli.data_classes.dataclass_testrail import TestRailSuite


def print_config(env: Environment, action: str):
    env.log(
        f"Configurations {action} Execution Parameters"
        f"\n> TestRail instance: {env.host} (user: {env.username})"
        f"\n> Project: {env.project if env.project else env.project_id}"
    )


@click.group(context_settings=CONTEXT_SETTINGS)
@click.pass_context
@pass_environment
def cli(environment: Environment, context: click.Context, *args, **kwargs):
    """Manage configurations in TestRail"""
    environment.cmd = "configurations"
    environment.set_parameters(context)


@cli.command()
@click.option("--json-output", is_flag=True, help="Output configurations as raw JSON from API.")
@click.option("--show-all-fields", is_flag=True, help="Show all fields including group IDs for each configuration.")
@click.pass_context
@pass_environment
def list(
    environment: Environment,
    context: click.Context,
    json_output: bool,
    show_all_fields: bool,
    *args,
    **kwargs,
):
    """List configurations from TestRail"""
    environment.check_for_required_parameters()

    print_config(environment, "List")

    # Create ProjectBasedClient to resolve project
    project_client = ProjectBasedClient(
        environment=environment,
        suite=TestRailSuite(name=environment.suite_name, suite_id=environment.suite_id),
    )

    # Resolve project (converts name to ID if needed)
    project_client.resolve_project()

    environment.log(f"Retrieving configurations for project ID {project_client.project.project_id}...")

    # Retrieve configurations using ConfigurationHandler
    config_groups, error_message = project_client.api_request_handler.configuration_handler.get_configs(
        project_id=project_client.project.project_id
    )

    if error_message:
        environment.elog(f"Error: Failed to retrieve configurations: {error_message}")
        raise SystemExit(1)

    total_groups = len(config_groups)
    total_configs = sum(len(group.get("configs", [])) for group in config_groups)

    if json_output:
        # Output prettified JSON response
        print(json.dumps(config_groups, indent=2))
    else:
        environment.log(f"Found {total_groups} configuration group(s) with {total_configs} total configuration(s).")
        environment.log("")

        if not config_groups:
            environment.log("No configuration groups found.")
        else:
            for group in config_groups:
                # Display group information
                environment.log(f"Configuration Group ID: {group.get('id')}")
                environment.log(f"  Name: {group.get('name')}")
                environment.log(f"  Project ID: {group.get('project_id', 'N/A')}")

                configs = group.get("configs", [])
                if configs:
                    environment.log(f"  Configurations ({len(configs)}):")
                    for config in configs:
                        if show_all_fields:
                            environment.log(
                                f"    - ID: {config.get('id')}, Name: {config.get('name')}, Group ID: {config.get('group_id')}"
                            )
                        else:
                            environment.log(f"    - ID: {config.get('id')}, Name: {config.get('name')}")
                else:
                    environment.log("  Configurations: (none)")

                environment.log("")

    environment.log("")
    environment.log("Configuration listing completed successfully.")
