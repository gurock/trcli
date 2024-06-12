import click

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
@click.option("-f", "--file", type=click.Path(), metavar="", help="Filename and path.")
@click.pass_context
@pass_environment
def cli(environment: Environment, context: click.Context, *args, **kwargs):
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

    environment.log(f"Run id: {run_id}")
    if environment.file is not None:
        environment.log(f"Writing test run name and id to file ({environment.file}). ", new_line=False)
        with open(environment.file, "w") as f:
            f.write(f"{environment.title}\n{run_id}\n")
        environment.log("Done.")
