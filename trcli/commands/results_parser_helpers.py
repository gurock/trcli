import functools

import click
from click import BadParameter

from trcli.cli import Environment


def print_config(env: Environment):
    env.log(f"Parser Results Execution Parameters"
            f"\n> Report file: {env.file}"
            f"\n> Config file: {env.config}"
            f"\n> TestRail instance: {env.host} (user: {env.username})"
            f"\n> Project: {env.project if env.project else env.project_id}"
            f"\n> Run title: {env.title}"
            f"\n> Update run: {env.run_id if env.run_id else 'No'}"
            f"\n> Add to milestone: {env.milestone_id if env.milestone_id else 'No'}"
            f"\n> Auto-create entities: {env.auto_creation_response}")


def resolve_comma_separated_list(ctx, param, value):
    if value:
        try:
            return [int(part.strip()) for part in value.split(',')]
        except:
            raise BadParameter('Invalid format, use a comma-separated list (i.e.: 43,19)')


def results_parser_options(f):
    @click.option("-f", "--file", type=click.Path(), metavar="", help="Filename and path.")
    @click.option("--close-run", is_flag=True, help="Close the newly created run")
    @click.option("--title", metavar="", help="Title of Test Run to be created or updated in TestRail.")
    @click.option(
        "--case-matcher",
        metavar="",
        default="auto",
        type=click.Choice(["auto", "name", "property"], case_sensitive=False),
        help="Mechanism to match cases between the report and TestRail."
    )
    @click.option(
        "--suite-id",
        type=click.IntRange(min=1),
        metavar="",
        help="Suite ID to submit results to.",
    )
    @click.option(
        "--suite-name",
        metavar="",
        help="Suite name to submit results to.",
    )
    @click.option(
        "--run-id",
        type=click.IntRange(min=1),
        metavar="",
        help="Run ID for the results they are reporting (otherwise the tool will attempt to create a new run).",
    )
    @click.option(
        "--plan-id",
        type=click.IntRange(min=1),
        metavar="",
        help="Plan ID with which the Test Run will be associated.",
    )
    @click.option(
        "--config-ids",
        metavar="",
        callback=resolve_comma_separated_list,
        help="Comma-separated configuration IDs to use along with Test Plans (i.e.: 34,52).",
    )
    @click.option(
        "--milestone-id",
        type=click.IntRange(min=1),
        metavar="",
        help="Milestone ID to which the Test Run should be associated to.",
    )
    @click.option(
        "--section-id",
        type=click.IntRange(min=1),
        metavar="",
        help="Section ID to create new sections with test cases under (optional).",
    )
    @click.option("--run-description", metavar="", default="", help="Summary text to be added to the test run.")
    @click.option(
        "--case-fields",
        multiple=True,
        metavar="",
        default=[],
        help="List of case fields and values for new test cases creation. "
             "Usage: --case-fields type_id:1 --case-fields priority_id:3",
    )
    @click.option(
        "--result-fields",
        multiple=True,
        metavar="",
        default=[],
        help="List of result fields and values for test results creation. "
             "Usage: --result-fields custom_field_a:value1 --result-fields custom_field_b:3",
    )
    @click.option("--allow-ms", is_flag=True, help="Allows using milliseconds for elapsed times.")
    @functools.wraps(f)
    def wrapper_common_options(*args, **kwargs):
        return f(*args, **kwargs)

    return wrapper_common_options
