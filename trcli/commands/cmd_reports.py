import builtins
import click
import json
import re

from trcli.api.project_based_client import ProjectBasedClient
from trcli.cli import pass_environment, CONTEXT_SETTINGS, Environment
from trcli.data_classes.dataclass_testrail import TestRailSuite


def print_config(env: Environment, action: str):
    env.log(f"Reports {action} Execution Parameters" f"\n> TestRail instance: {env.host} (user: {env.username})")


def display_report(env: Environment, report: dict, show_all_fields: bool = False):
    """Helper function to display a single report's information."""
    env.log(f"Report ID: {report.get('id')}")
    env.log(f"  Name: {report.get('name', 'N/A')}")

    if not show_all_fields:
        # Basic display - only show description and project IDs
        if report.get("description"):
            env.log(f"  Description: {report.get('description')}")

        # Show project IDs for cross-project reports
        if "project_ids" in report:
            project_ids = report.get("project_ids", [])
            if project_ids:
                env.log(f"  Project IDs: {', '.join(map(str, project_ids))}")
            else:
                env.log(f"  Project IDs: All projects")
    else:
        # Show ALL fields from the API response
        # Skip 'id' and 'name' as they're already shown
        for key, value in sorted(report.items()):
            if key in ["id", "name"]:
                continue

            # Format the field name
            label = key.replace("_", " ").title()

            # Format the value based on type
            # Note: Check bool before other types as bool is a subclass of int
            # Use builtins.list and builtins.dict because 'list' is shadowed by the command function
            if value is None:
                formatted_value = "null"
            elif value is True or value is False:  # Explicit boolean check
                formatted_value = "Yes" if value else "No"
            elif isinstance(value, builtins.dict):
                formatted_value = json.dumps(value, indent=4)
            elif isinstance(value, builtins.list):
                if not value:
                    formatted_value = "[]"
                else:
                    # Check if all items are simple types (str or int, but not bool)
                    try:
                        simple_types = all(
                            (isinstance(item, str) or (isinstance(item, int) and not isinstance(item, bool)))
                            for item in value
                        )
                        if simple_types:
                            formatted_value = ", ".join(map(str, value))
                        else:
                            formatted_value = json.dumps(value, indent=4)
                    except (TypeError, ValueError):
                        formatted_value = json.dumps(value, indent=4)
            else:
                formatted_value = str(value)

            # Handle multiline values
            if "\n" in formatted_value or formatted_value.startswith("{") or formatted_value.startswith("["):
                env.log(f"  {label}:")
                for line in formatted_value.split("\n"):
                    env.log(f"    {line}")
            else:
                env.log(f"  {label}: {formatted_value}")


def find_reports_by_name(reports: list, name: str) -> list:
    """
    Find all reports matching a name (case-insensitive, partial match).

    Args:
        reports: List of report dictionaries
        name: Name or partial name to search for

    Returns:
        List of matching report dictionaries (may be empty)
    """
    name_lower = name.lower()
    matched_reports = []

    # First collect exact matches
    for report in reports:
        if report.get("name", "").lower() == name_lower:
            matched_reports.append(report)

    # If no exact matches, collect partial matches
    if not matched_reports:
        for report in reports:
            if name_lower in report.get("name", "").lower():
                matched_reports.append(report)

    return matched_reports


@click.group(context_settings=CONTEXT_SETTINGS)
@click.pass_context
@pass_environment
def cli(environment: Environment, context: click.Context, *args, **kwargs):
    """Manage reports in TestRail"""
    environment.cmd = "reports"
    environment.set_parameters(context)


@cli.command()
@click.option(
    "--project-id",
    type=click.IntRange(min=1),
    metavar="<id>",
    help="List reports for a specific project ID (uses project from config if not specified).",
)
@click.option("--json-output", is_flag=True, help="Output reports as raw JSON from API.")
@click.option("--show-all-fields", is_flag=True, help="Show all fields including notification settings.")
@click.option(
    "--cross-project",
    is_flag=True,
    help="List cross-project reports (Enterprise only, ignores --project-id).",
)
@click.pass_context
@pass_environment
def list(
    environment: Environment,
    context: click.Context,
    project_id: int,
    json_output: bool,
    show_all_fields: bool,
    cross_project: bool,
    *args,
    **kwargs,
):
    """List available report templates from TestRail"""
    environment.check_for_required_parameters()

    print_config(environment, "List")

    # Create ProjectBasedClient for consistent API access
    project_client = ProjectBasedClient(
        environment=environment,
        suite=TestRailSuite(name=environment.suite_name, suite_id=environment.suite_id),
    )

    # Resolve project name to project_id if needed (unless using cross-project)
    if not cross_project and not project_id and environment.project:
        project_client.resolve_project()
        project_id = project_client.project.project_id if project_client.project else None

    if cross_project:
        # Retrieve cross-project reports (Enterprise only)
        environment.log("Retrieving cross-project reports...")
        reports, error_message = project_client.api_request_handler.report_handler.get_cross_project_reports()

        if error_message:
            environment.elog(f"Error: Failed to retrieve cross-project reports: {error_message}")
            environment.elog("Note: Cross-project reports are only available on Enterprise license plans.")
            raise SystemExit(1)
    else:
        # Use project-id from parameter or environment
        if not project_id:
            project_id = environment.project_id

        if not project_id:
            environment.elog("Error: --project-id is required for single-project reports (or use --cross-project).")
            environment.elog("Please specify --project-id or configure project in your config file.")
            raise SystemExit(1)

        # Retrieve project reports
        environment.log(f"Retrieving reports for project {project_id}...")
        reports, error_message = project_client.api_request_handler.report_handler.get_reports(project_id)

        if error_message:
            environment.elog(f"Error: Failed to retrieve reports: {error_message}")
            raise SystemExit(1)

    if json_output:
        print(json.dumps(reports, indent=2))
        return

    # Display results
    environment.log(f"Found {len(reports)} report(s).")
    environment.log("")

    for report in reports:
        display_report(environment, report, show_all_fields)
        environment.log("")

    environment.log("Report listing completed successfully.")


@cli.command()
@click.option(
    "--project-id",
    type=click.IntRange(min=1),
    metavar="<id>",
    help="Generate report for a specific project ID (uses project from config if not specified).",
)
@click.option(
    "--report-id",
    type=click.IntRange(min=1),
    metavar="<id>",
    help="Report template ID to generate.",
)
@click.option(
    "--report",
    type=str,
    metavar="<name>",
    help="Report template name (or partial name) to generate. Generates all matching reports.",
)
@click.option("--json-output", is_flag=True, help="Output report URLs as raw JSON from API.")
@click.option(
    "--cross-project",
    is_flag=True,
    help="Generate cross-project report (Enterprise only, ignores --project-id).",
)
@click.pass_context
@pass_environment
def generate(
    environment: Environment,
    context: click.Context,
    project_id: int,
    report_id: int,
    report: str,
    json_output: bool,
    cross_project: bool,
    *args,
    **kwargs,
):
    """Generate a report in TestRail"""
    environment.check_for_required_parameters()

    print_config(environment, "Generate")

    # Validate that either report_id or report name is provided
    if not report_id and not report:
        environment.elog("Error: Either --report-id or --report must be specified.")
        raise SystemExit(1)

    if report_id and report:
        environment.elog("Error: Cannot specify both --report-id and --report. Use one or the other.")
        raise SystemExit(1)

    # Create ProjectBasedClient for consistent API access
    project_client = ProjectBasedClient(
        environment=environment,
        suite=TestRailSuite(name=environment.suite_name, suite_id=environment.suite_id),
    )

    # Resolve project name to project_id if needed (unless using cross-project)
    if not cross_project and not project_id and environment.project:
        project_client.resolve_project()
        project_id = project_client.project.project_id if project_client.project else None

    # Determine which reports to generate
    reports_to_generate = []

    if report_id:
        # Single report by ID - need to fetch report details for name
        if cross_project:
            reports_list, error_message = project_client.api_request_handler.report_handler.get_cross_project_reports()
            if error_message:
                environment.elog(f"Error: Failed to retrieve cross-project reports: {error_message}")
                raise SystemExit(1)
        else:
            # Use project-id from parameter or environment
            if not project_id:
                project_id = environment.project_id

            if not project_id:
                environment.elog("Error: --project-id is required for single-project reports (or use --cross-project).")
                environment.elog("Please specify --project-id or configure project in your config file.")
                raise SystemExit(1)

            reports_list, error_message = project_client.api_request_handler.report_handler.get_reports(project_id)
            if error_message:
                environment.elog(f"Error: Failed to retrieve reports: {error_message}")
                raise SystemExit(1)

        # Find the report with this ID
        matched_report = None
        for r in reports_list:
            if r.get("id") == report_id:
                matched_report = r
                break

        if not matched_report:
            environment.elog(f"Error: No report found with ID {report_id}.")
            raise SystemExit(1)

        reports_to_generate.append(matched_report)
        environment.log(f"Found report: {matched_report.get('name')} (ID: {report_id})")

    elif report:
        # Multiple reports by name - find all matching
        environment.log(f"Looking up report templates matching: {report}")

        if cross_project:
            reports_list, error_message = project_client.api_request_handler.report_handler.get_cross_project_reports()
            if error_message:
                environment.elog(f"Error: Failed to retrieve cross-project reports: {error_message}")
                raise SystemExit(1)
        else:
            # Use project-id from parameter or environment
            if not project_id:
                project_id = environment.project_id

            if not project_id:
                environment.elog("Error: --project-id is required when using --report (or use --cross-project).")
                environment.elog("Please specify --project-id or configure project in your config file.")
                raise SystemExit(1)

            reports_list, error_message = project_client.api_request_handler.report_handler.get_reports(project_id)
            if error_message:
                environment.elog(f"Error: Failed to retrieve reports: {error_message}")
                raise SystemExit(1)

        # Find all matching reports
        reports_to_generate = find_reports_by_name(reports_list, report)

        if not reports_to_generate:
            environment.elog(f"Error: No reports found matching '{report}'.")
            if reports_list:
                environment.log("\nAvailable reports:")
                for r in reports_list:
                    environment.log(f"  - {r.get('name')} (ID: {r.get('id')})")
            raise SystemExit(1)

        environment.log(f"Found {len(reports_to_generate)} matching report(s):")
        for r in reports_to_generate:
            environment.log(f"  - {r.get('name')} (ID: {r.get('id')})")

    # Generate all matched reports
    environment.log("")
    generated_reports = []

    for report_to_gen in reports_to_generate:
        report_name = report_to_gen.get("name")
        report_gen_id = report_to_gen.get("id")

        if cross_project:
            environment.log(f"Generating: {report_name} (ID: {report_gen_id})...")
            report_urls, error_message = project_client.api_request_handler.report_handler.run_cross_project_report(
                report_gen_id
            )
        else:
            environment.log(f"Generating: {report_name} (ID: {report_gen_id})...")
            report_urls, error_message = project_client.api_request_handler.report_handler.run_report(report_gen_id)

        if error_message:
            environment.elog(f"  Error: Failed to generate report: {error_message}")
            continue

        if not report_urls:
            environment.log("  No report URLs returned.")
            continue

        generated_reports.append({"name": report_name, "id": report_gen_id, "urls": report_urls})

    # Display results
    if not generated_reports:
        environment.elog("No reports were generated successfully.")
        raise SystemExit(1)

    if json_output:
        print(json.dumps(generated_reports, indent=2))
        return

    # Display summary
    environment.log("")
    environment.log(f"Successfully generated {len(generated_reports)} report(s)!")
    environment.log("")

    for gen_report in generated_reports:
        report_name = gen_report["name"]
        urls = gen_report["urls"]

        environment.log(f"{report_name}:")
        environment.log(f"  View:  {urls.get('report_url', 'N/A')}")
        environment.log(f"  HTML:  {urls.get('report_html', 'N/A')}")
        environment.log(f"  PDF:   {urls.get('report_pdf', 'N/A')}")
        environment.log("")

    environment.log("Note: Reports may not be available immediately after being generated.")
    environment.log("The time required can vary, especially for TestRail Server customers.")
    environment.log("")
    environment.log("Report generation completed successfully.")
