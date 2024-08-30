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
            f"\n> Assigned To ID: {env.run_assigned_to_id}"
            f"\n> Include All: {env.run_include_all}"
            f"\n> Case IDs: {env.run_case_ids}"
            f"\n> Refs: {env.run_refs}")


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
    "--run-assigned-to-id",
    type=click.IntRange(min=1),
    metavar="",
    help="The ID of the user the test run should be assigned to."
)
@click.option(
    "--include-all",
    is_flag=True,
    default=False,
    help="Use this option to include all test cases in this test run."
)
@click.option(
    "--case-ids",
    metavar="",
    help="Comma separated list of test case IDs to include in the test run."
)
@click.option(
    "--run-refs",
    metavar="",
    help="A comma-separated list of references/requirements"
)
@click.option("-f", "--file", type=click.Path(), metavar="", help="Write run data to file.")
@click.pass_context
@pass_environment
def cli(environment: Environment, context: click.Context, *args, **kwargs):
    """Add a new test run in TestRail"""
    environment.cmd = "add_run"
    environment.set_parameters(context)
    environment.check_for_required_parameters()
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
