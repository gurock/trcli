import click
import yaml

from trcli.api.project_based_client import ProjectBasedClient
from trcli.cli import pass_environment, CONTEXT_SETTINGS, Environment
from trcli.data_classes.dataclass_testrail import TestRailSuite


def print_config(env: Environment):
    env.log(f"Parser Results Execution Parameters"
            f"\n> TestRail instance: {env.host} (user: {env.username})"
            f"\n> Project: {env.project if env.project else env.project_id}"
            f"\n> Run title: {env.title}"
            f"\n> Suite ID: {env.suite_id}"
            f"\n> Description: {env.run_description}"
            f"\n> Milestone ID: {env.milestone_id}"
            f"\n> Start Date: {env.run_start_date}"
            f"\n> End Date: {env.run_end_date}"
            f"\n> Assigned To ID: {env.run_assigned_to_id}"
            f"\n> Include All: {env.run_include_all}"
            f"\n> Case IDs: {env.run_case_ids}"
            f"\n> Refs: {env.run_refs}"
            f"\n> Refs Action: {env.run_refs_action if hasattr(env, 'run_refs_action') else 'add'}")


def write_run_to_file(environment: Environment, run_id: int):
    """Write the created run id and title to a yaml file that can be included in the configuration of later runs."""
    environment.log(f"Writing test run data to file ({environment.file}). ", new_line=False)
    data = dict(title=environment.title, run_id=run_id)
    if environment.run_description:
        data['run_description'] = environment.run_description
    if environment.run_refs:
        data['run_refs'] = environment.run_refs
    if environment.run_include_all:
        data['run_include_all'] = environment.run_include_all
    if environment.run_case_ids:
        data['run_case_ids'] = environment.run_case_ids
    if environment.run_assigned_to_id:
        data['run_assigned_to_id'] = environment.run_assigned_to_id
    with open(environment.file, "a") as f:
        f.write(yaml.dump(data, default_flow_style=False))
    environment.log("Done.")


@click.command(context_settings=CONTEXT_SETTINGS)
@click.option("--title", metavar="", help="Title of Test Run to be created or updated in TestRail.")
@click.option(
    "--run-id",
    type=click.IntRange(min=1),
    metavar="",
    help="ID of existing test run to update. If not provided, a new run will be created.",
)
@click.option(
    "--suite-id",
    type=click.IntRange(min=1),
    metavar="",
    help="Suite ID to submit results to.",
)
@click.option("--run-description", metavar="", default="", help="Summary text to be added to the test run.")
@click.option(
    "--milestone-id",
    type=click.IntRange(min=1),
    metavar="",
    help="Milestone ID to which the Test Run should be associated to.",
)
@click.option(
    "--run-start-date",
    metavar="",
    default=None,
    type=lambda x: [int(i) for i in x.split("/") if len(x.split("/")) == 3], 
    help="The expected or scheduled start date of this test run in MM/DD/YYYY format"
)
@click.option(
    "--run-end-date",
    metavar="",
    default=None,
    type=lambda x: [int(i) for i in x.split("/") if len(x.split("/")) == 3], 
    help="The expected or scheduled end date of this test run in MM/DD/YYYY format"
)
@click.option(
    "--run-assigned-to-id",
    type=click.IntRange(min=1),
    metavar="",
    help="The ID of the user the test run should be assigned to."
)
@click.option(
    "--run-include-all",
    is_flag=True,
    default=False,
    help="Use this option to include all test cases in this test run."
)
@click.option(
    "--auto-close-run",
    is_flag=True,
    default=False,
    help="Use this option to automatically close the created run."
)
@click.option(
    "--run-case-ids",
    metavar="",
    type=lambda x: [int(i) for i in x.split(",")], 
    help="Comma separated list of test case IDs to include in the test run (i.e.: 1,2,3,4)."
)
@click.option(
    "--run-refs",
    metavar="",
    help="A comma-separated list of references/requirements (up to 250 characters)"
)
@click.option(
    "--run-refs-action",
    type=click.Choice(['add', 'update', 'delete'], case_sensitive=False),
    default='add',
    metavar="",
    help="Action to perform on references: 'add' (default), 'update' (replace all), or 'delete' (remove all or specific)"
)
@click.option("-f", "--file", type=click.Path(), metavar="", help="Write run data to file.")
@click.pass_context
@pass_environment
def cli(environment: Environment, context: click.Context, *args, **kwargs):
    """Add a new test run in TestRail"""
    environment.cmd = "add_run"
    environment.set_parameters(context)
    environment.check_for_required_parameters()
    
    if environment.run_refs and len(environment.run_refs) > 250:
        environment.elog("Error: References field cannot exceed 250 characters.")
        exit(1)
    
    if environment.run_refs_action and environment.run_refs_action != 'add' and not environment.run_id:
        environment.elog("Error: --run-refs-action 'update' and 'delete' can only be used when updating an existing run (--run-id required).")
        exit(1)
    
    if environment.run_refs_action == 'delete' and not environment.run_refs and environment.run_id:
        environment.run_refs = ""
    
    print_config(environment)

    project_client = ProjectBasedClient(
        environment=environment,
        suite=TestRailSuite(name=environment.suite_name, suite_id=environment.suite_id),
    )
    project_client.resolve_project()
    project_client.resolve_suite()
    run_id, error_message = project_client.create_or_update_test_run()
    if error_message:
        exit(1)

    environment.run_id = run_id
    environment.log(f"title: {environment.title}")
    environment.log(f"run_id: {run_id}")
    if environment.file is not None:
        write_run_to_file(environment, run_id)
