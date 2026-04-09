import functools
from typing import Optional

import click
from click import BadParameter

from trcli.cli import Environment


def print_config(env: Environment):
    assign_info = (
        f"Yes ({env.assign_failed_to})"
        if hasattr(env, "assign_failed_to") and env.assign_failed_to and env.assign_failed_to.strip()
        else "No"
    )


def json_output_option(f):
    return click.option(
        "--json-output",
        "--json",
        "json_output",
        is_flag=True,
        help="Output structured results in JSON format.",
    )(f)
    env.log(
        f"Parser Results Execution Parameters"
        f"\n> Report file: {env.file}"
        f"\n> Config file: {env.config}"
        f"\n> TestRail instance: {env.host} (user: {env.username})"
        f"\n> Project: {env.project if env.project else env.project_id}"
        f"\n> Run title: {env.title}"
        f"\n> Update run: {env.run_id if env.run_id else 'No'}"
        f"\n> Add to milestone: {env.milestone_id if env.milestone_id else 'No'}"
        f"\n> Auto-assign failures: {assign_info}"
        f"\n> Auto-create entities: {env.auto_creation_response}"
    )


def resolve_comma_separated_list(ctx, param, value):
    if value:
        try:
            return [int(part.strip()) for part in value.split(",")]
        except:
            raise BadParameter("Invalid format, use a comma-separated list (i.e.: 43,19)")


def results_parser_options(f):
    @json_output_option
    @click.option("-f", "--file", type=click.Path(), metavar="", help="Filename and path.")
    @click.option("--close-run", is_flag=True, help="Close the newly created run")
    @click.option("--title", metavar="", help="Title of Test Run to be created or updated in TestRail.")
    @click.option(
        "--case-matcher",
        metavar="",
        default="auto",
        type=click.Choice(["auto", "name", "property"], case_sensitive=False),
        help="Mechanism to match cases between the report and TestRail.",
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


def bdd_parser_options(f):
    """Options decorator for BDD/Cucumber parsers that don't need case-matcher or section-id"""

    @json_output_option
    @click.option("-f", "--file", type=click.Path(), metavar="", help="Filename and path.")
    @click.option("--close-run", is_flag=True, help="Close the newly created run")
    @click.option("--title", metavar="", help="Title of Test Run to be created or updated in TestRail.")
    @click.option(
        "--suite-id",
        type=click.IntRange(min=1),
        metavar="",
        help="Suite ID to submit results to.",
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
    @click.option("--run-description", metavar="", default="", help="Summary text to be added to the test run.")
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
    def wrapper_bdd_options(*args, **kwargs):
        return f(*args, **kwargs)

    return wrapper_bdd_options


def summarize_parsed_suites(parsed_suites) -> dict:
    sections = 0
    cases = 0
    results = 0

    for suite in parsed_suites:
        sections += len(suite.testsections)
        for section in suite.testsections:
            cases += len(section.testcases)
            for test_case in section.testcases:
                if getattr(test_case, "result", None) is not None:
                    results += 1

    return {
        "suites": len(parsed_suites),
        "sections": sections,
        "cases": cases,
        "results": results,
    }


def build_command_json(
    command: str,
    *,
    ok: bool = True,
    dry_run: bool = False,
    data: Optional[dict] = None,
    warnings: Optional[list[str]] = None,
    errors: Optional[list[str]] = None,
) -> dict:
    return {
        "ok": ok,
        "command": command,
        "dry_run": dry_run,
        "data": data or {},
        "warnings": warnings or [],
        "errors": errors or [],
    }


def emit_parser_result_json(
    env: Environment,
    *,
    parsed_suites,
    run_id=None,
    warnings: Optional[list[str]] = None,
    errors: Optional[list[str]] = None,
    extra_data: Optional[dict] = None,
    ok: bool = True,
):
    payload = build_command_json(
        env.cmd,
        ok=ok,
        dry_run=bool(getattr(env, "dry_run", False)),
        data={
            "file": env.file,
            "title": env.title,
            "run_id": run_id,
            "project": env.project,
            "project_id": env.project_id,
            "suite_id": env.suite_id,
            "parsed": summarize_parsed_suites(parsed_suites),
            **(extra_data or {}),
        },
        warnings=warnings,
        errors=errors,
    )
    env.emit_json(payload)


def print_dry_run_preview(env: Environment, parsed_suites, action: str):
    summary = summarize_parsed_suites(parsed_suites)
    if env.wants_json_output:
        env.emit_json(
            build_command_json(
                env.cmd,
                dry_run=True,
                data={
                    "action": action,
                    "parsed": summary,
                    "target_run_id": env.run_id,
                    "title": env.title,
                    "close_run": bool(env.close_run),
                },
            )
        )
        return

    env.log(f"Dry run: would {action}.")
    env.log(f"  Parsed suites: {summary['suites']}")
    env.log(f"  Parsed sections: {summary['sections']}")
    env.log(f"  Parsed cases: {summary['cases']}")
    env.log(f"  Parsed results: {summary['results']}")

    if env.run_id:
        env.log(f"  Target run: {env.run_id}")
    else:
        env.log(f"  Run title: {env.title}")

    if env.close_run:
        env.log("  Close run: yes")
