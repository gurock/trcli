import builtins
import click
import json

from trcli.api.project_based_client import ProjectBasedClient
from trcli.cli import pass_environment, CONTEXT_SETTINGS, Environment
from trcli.data_classes.dataclass_testrail import TestRailSuite


def print_config(env: Environment, action: str):
    env.log(
        f"Cases {action} Execution Parameters"
        f"\n> TestRail instance: {env.host} (user: {env.username})"
        f"\n> Project: {env.project if env.project else env.project_id}"
    )


@click.group(context_settings=CONTEXT_SETTINGS)
@click.pass_context
@pass_environment
def cli(environment: Environment, context: click.Context, *args, **kwargs):
    """Manage test cases in TestRail"""
    environment.cmd = "cases"
    environment.set_parameters(context)


@cli.command()
@click.option("--case-id", type=click.IntRange(min=1), required=True, metavar="", help="Case ID to retrieve.")
@click.option("--json-output", is_flag=True, help="Output case as raw JSON from API.")
@click.option("--show-all-fields", is_flag=True, help="Show all fields including custom fields in detail.")
@click.pass_context
@pass_environment
def get(
    environment: Environment,
    context: click.Context,
    case_id: int,
    json_output: bool,
    show_all_fields: bool,
    *args,
    **kwargs,
):
    """Get a single test case by ID"""
    environment.check_for_required_parameters()

    print_config(environment, "Get")

    # Create ProjectBasedClient to resolve project
    project_client = ProjectBasedClient(
        environment=environment,
        suite=TestRailSuite(name=environment.suite_name, suite_id=environment.suite_id),
    )

    # Resolve project (converts name to ID if needed)
    project_client.resolve_project()

    environment.log(f"Retrieving case ID {case_id}...")

    # Retrieve the case using CaseHandler from ProjectBasedClient
    case_data, error_message = project_client.api_request_handler.case_handler.get_case(case_id)

    if error_message:
        environment.elog(f"Error: Failed to retrieve case: {error_message}")
        raise SystemExit(1)

    # Verify case belongs to the specified project
    if case_data.get("suite_id"):
        # Cases with suite_id belong to multi-suite projects
        # We should verify project_id, but API doesn't return it directly
        # For now, we trust the user provided correct project_id
        pass

    # Handle output format
    if json_output:
        # Output prettified JSON response
        print(json.dumps(case_data, indent=2))
    else:
        # Display case details
        environment.log("")
        environment.log(f"Case ID: {case_data.get('id', 'N/A')}")
        environment.log(f"  Title: {case_data.get('title', 'N/A')}")
        environment.log(f"  Section ID: {case_data.get('section_id', 'N/A')}")
        environment.log(f"  Suite ID: {case_data.get('suite_id', 'N/A')}")
        environment.log(f"  Template ID: {case_data.get('template_id', 'N/A')}")
        environment.log(f"  Type ID: {case_data.get('type_id', 'N/A')}")
        environment.log(f"  Priority ID: {case_data.get('priority_id', 'N/A')}")

        if case_data.get("milestone_id"):
            environment.log(f"  Milestone ID: {case_data.get('milestone_id')}")

        if case_data.get("refs"):
            environment.log(f"  References: {case_data.get('refs')}")

        environment.log(f"  Created By: {case_data.get('created_by', 'N/A')}")
        environment.log(f"  Created On: {case_data.get('created_on', 'N/A')}")
        environment.log(f"  Updated By: {case_data.get('updated_by', 'N/A')}")
        environment.log(f"  Updated On: {case_data.get('updated_on', 'N/A')}")

        if case_data.get("estimate"):
            environment.log(f"  Estimate: {case_data.get('estimate')}")

        if case_data.get("estimate_forecast"):
            environment.log(f"  Estimate Forecast: {case_data.get('estimate_forecast')}")

        # Display labels
        labels = case_data.get("labels", [])
        if labels:
            if show_all_fields:
                environment.log(f"  Labels ({len(labels)}):")
                for label in labels:
                    environment.log(f"    - ID: {label.get('id')}, Title: {label.get('title')}")
            else:
                label_titles = ", ".join([label.get("title", "") for label in labels])
                environment.log(f"  Labels: {label_titles}")
        else:
            environment.log("  Labels: (none)")

        if show_all_fields:
            # Show all custom fields
            custom_fields = {k: v for k, v in case_data.items() if k.startswith("custom_")}
            if custom_fields:
                environment.log(f"  Custom Fields ({len(custom_fields)}):")
                for key, value in custom_fields.items():
                    display_name = key.replace("_", " ").title()
                    if value is None:
                        display_value = "N/A"
                    elif isinstance(value, builtins.list):
                        if value:
                            display_value = f"{len(value)} item(s): {value}"
                        else:
                            display_value = "[]"
                    else:
                        display_value = value
                    environment.log(f"    {display_name}: {display_value}")
        else:
            # Show count of custom fields
            custom_fields = {k: v for k, v in case_data.items() if k.startswith("custom_")}
            if custom_fields:
                environment.log(f"  Custom Fields: {len(custom_fields)} field(s)")


@cli.command()
@click.option("--suite-id", type=click.IntRange(min=1), metavar="", help="Filter by suite ID.")
@click.option("--priority-id", metavar="", help="Filter by priority ID (comma-separated for multiple, e.g., '3,4').")
@click.option("--filter", "filter_text", metavar="", help="Filter by text search (case title).")
@click.option("--offset", type=int, default=0, metavar="", help="Offset for pagination (default: 0).")
@click.option("--limit", type=int, default=250, metavar="", help="Limit for pagination (default: 250).")
@click.option("--json-output", is_flag=True, help="Output cases as raw JSON from API.")
@click.option("--show-all-fields", is_flag=True, help="Show all fields including custom fields in detail.")
@click.pass_context
@pass_environment
def list(
    environment: Environment,
    context: click.Context,
    suite_id: int,
    priority_id: str,
    filter_text: str,
    offset: int,
    limit: int,
    json_output: bool,
    show_all_fields: bool,
    *args,
    **kwargs,
):
    """List test cases from TestRail"""
    environment.check_for_required_parameters()

    print_config(environment, "List")

    # Create ProjectBasedClient to resolve project
    project_client = ProjectBasedClient(
        environment=environment,
        suite=TestRailSuite(name=environment.suite_name, suite_id=environment.suite_id),
    )

    # Resolve project (converts name to ID if needed)
    project_client.resolve_project()

    # Build filter description
    filters = []
    if suite_id:
        filters.append(f"suite_id={suite_id}")
    if priority_id:
        filters.append(f"priority_id={priority_id}")
    if filter_text:
        filters.append(f"filter='{filter_text}'")

    filter_desc = ", ".join(filters) if filters else "no filters"
    environment.log(f"Retrieving cases for project ID {project_client.project.project_id} ({filter_desc})...")

    # Retrieve cases using CaseHandler from ProjectBasedClient
    response_data, error_message = project_client.api_request_handler.case_handler.get_cases(
        project_id=project_client.project.project_id,
        suite_id=suite_id,
        priority_id=priority_id,
        filter_text=filter_text,
        limit=limit,
        offset=offset,
    )

    if error_message:
        environment.elog(f"Error: Failed to retrieve cases: {error_message}")
        raise SystemExit(1)

    # Handle output format
    if json_output:
        # Output prettified JSON response
        print(json.dumps(response_data, indent=2))
    else:
        # Display cases line by line
        cases = response_data.get("cases", [])
        response_offset = response_data.get("offset", 0)
        response_limit = response_data.get("limit", 250)
        response_size = response_data.get("size", 0)
        next_link = response_data.get("_links", {}).get("next")

        if not cases:
            environment.log("No cases found.")
        else:
            environment.log(
                f"Found {response_size} case(s) (showing {response_offset + 1}-{response_offset + len(cases)}):"
            )
            if next_link:
                environment.log("  (More results available - use --offset and --limit for pagination)")
            environment.log("")

            for case in cases:
                if show_all_fields:
                    # Show all fields from API response
                    environment.log(f"  Case ID: {case.get('id', 'N/A')}")

                    # Iterate through all fields in the case
                    for key, value in case.items():
                        if key == "id":
                            continue  # Already displayed as Case ID

                        # Format field name for display
                        display_name = key.replace("_", " ").title()

                        # Handle None values
                        if value is None:
                            display_value = "N/A"
                        elif isinstance(value, builtins.list):
                            # Handle list fields (like labels)
                            if key == "labels" and value:
                                label_titles = ", ".join([label.get("title", "") for label in value])
                                display_value = f"{len(value)} label(s): {label_titles}"
                            elif value:
                                display_value = f"{len(value)} item(s): {value}"
                            else:
                                display_value = "[]"
                        else:
                            display_value = value

                        environment.log(f"    {display_name}: {display_value}")

                    environment.log("")
                else:
                    # Display compact format
                    environment.log(f"  Case ID: {case.get('id', 'N/A')}")
                    environment.log(f"    Title: {case.get('title', 'N/A')}")
                    environment.log(f"    Section ID: {case.get('section_id', 'N/A')}")

                    if case.get("suite_id"):
                        environment.log(f"    Suite ID: {case.get('suite_id')}")

                    environment.log(f"    Priority ID: {case.get('priority_id', 'N/A')}")
                    environment.log(f"    Type ID: {case.get('type_id', 'N/A')}")

                    if case.get("refs"):
                        refs = case.get("refs", "")
                        if len(refs) > 50:
                            refs = refs[:50] + "..."
                        environment.log(f"    References: {refs}")

                    # Display labels
                    labels = case.get("labels", [])
                    if labels:
                        label_titles = ", ".join([label.get("title", "") for label in labels])
                        environment.log(f"    Labels: {label_titles}")

                    # Show custom fields count
                    custom_fields = {k: v for k, v in case.items() if k.startswith("custom_")}
                    if custom_fields:
                        environment.log(f"    Custom Fields: {len(custom_fields)} field(s)")

                    environment.log("")
