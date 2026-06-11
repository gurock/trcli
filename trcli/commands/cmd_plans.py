import builtins
import click
import json

from trcli.api.project_based_client import ProjectBasedClient
from trcli.cli import pass_environment, CONTEXT_SETTINGS, Environment
from trcli.data_classes.dataclass_testrail import TestRailSuite


def print_config(env: Environment, action: str):
    env.log(
        f"Plans {action} Execution Parameters"
        f"\n> TestRail instance: {env.host} (user: {env.username})"
        f"\n> Project: {env.project if env.project else env.project_id}"
    )


@click.group(context_settings=CONTEXT_SETTINGS)
@click.pass_context
@pass_environment
def cli(environment: Environment, context: click.Context, *args, **kwargs):
    """Manage test plans in TestRail"""
    environment.cmd = "plans"
    environment.set_parameters(context)


@cli.command()
@click.option("--plan-id", type=click.IntRange(min=1), required=True, metavar="", help="Plan ID to retrieve.")
@click.option("--json-output", is_flag=True, help="Output plan as raw JSON from API.")
@click.option("--show-all-fields", is_flag=True, help="Show all fields including custom fields in detail.")
@click.pass_context
@pass_environment
def get(
    environment: Environment,
    context: click.Context,
    plan_id: int,
    json_output: bool,
    show_all_fields: bool,
    *args,
    **kwargs,
):
    """Get a single test plan by ID"""
    environment.check_for_required_parameters()

    print_config(environment, "Get")

    # Create ProjectBasedClient to resolve project
    project_client = ProjectBasedClient(
        environment=environment,
        suite=TestRailSuite(name=environment.suite_name, suite_id=environment.suite_id),
    )

    # Resolve project (converts name to ID if needed)
    project_client.resolve_project()

    environment.log(f"Retrieving plan ID {plan_id}...")

    # Retrieve the plan using PlanHandler from ProjectBasedClient
    plan_data, error_message = project_client.api_request_handler.plan_handler.get_plan(plan_id)

    if error_message:
        environment.elog(f"Error: Failed to retrieve plan: {error_message}")
        raise SystemExit(1)

    # Handle output format
    if json_output:
        # Output prettified JSON response
        print(json.dumps(plan_data, indent=2))
    else:
        # Display plan details
        environment.log("")
        environment.log(f"Plan ID: {plan_data.get('id', 'N/A')}")
        environment.log(f"  Name: {plan_data.get('name', 'N/A')}")

        if plan_data.get("description"):
            description = plan_data.get("description")
            # Truncate long descriptions in non-show-all-fields mode
            if not show_all_fields and len(description) > 100:
                description = description[:100] + "..."
            environment.log(f"  Description: {description}")
        else:
            environment.log("  Description: (none)")

        environment.log(f"  Project ID: {plan_data.get('project_id', 'N/A')}")

        if plan_data.get("milestone_id"):
            environment.log(f"  Milestone ID: {plan_data.get('milestone_id')}")

        if plan_data.get("assignedto_id"):
            environment.log(f"  Assigned To ID: {plan_data.get('assignedto_id')}")

        # Status information
        is_completed = plan_data.get("is_completed", False)
        environment.log(f"  Status: {'Completed' if is_completed else 'Active'}")

        if is_completed and plan_data.get("completed_on"):
            environment.log(f"  Completed On: {plan_data.get('completed_on')}")

        # Test counts
        environment.log("  Test Status Counts:")
        environment.log(f"    Passed: {plan_data.get('passed_count', 0)}")
        environment.log(f"    Failed: {plan_data.get('failed_count', 0)}")
        environment.log(f"    Blocked: {plan_data.get('blocked_count', 0)}")
        environment.log(f"    Retest: {plan_data.get('retest_count', 0)}")
        environment.log(f"    Untested: {plan_data.get('untested_count', 0)}")

        if show_all_fields:
            # Show custom status counts
            custom_counts = {
                k: v for k, v in plan_data.items() if k.startswith("custom_status") and k.endswith("_count")
            }
            if any(v > 0 for v in custom_counts.values()):
                environment.log("    Custom Statuses:")
                for key, value in custom_counts.items():
                    if value > 0:
                        status_num = key.replace("custom_status", "").replace("_count", "")
                        environment.log(f"      Custom Status {status_num}: {value}")

        # Created and updated info
        environment.log(f"  Created By: {plan_data.get('created_by', 'N/A')}")
        environment.log(f"  Created On: {plan_data.get('created_on', 'N/A')}")

        if plan_data.get("url"):
            environment.log(f"  URL: {plan_data.get('url')}")

        # Entries (runs grouped by suite/config)
        entries = plan_data.get("entries", [])
        if entries:
            environment.log(f"\n  Entries ({len(entries)}):")
            for idx, entry in enumerate(entries, 1):
                environment.log(f"    Entry {idx}:")
                environment.log(f"      ID: {entry.get('id', 'N/A')}")
                environment.log(f"      Name: {entry.get('name', 'N/A')}")
                environment.log(f"      Suite ID: {entry.get('suite_id', 'N/A')}")

                if entry.get("description"):
                    desc = entry.get("description")
                    if not show_all_fields and len(desc) > 60:
                        desc = desc[:60] + "..."
                    environment.log(f"      Description: {desc}")

                runs = entry.get("runs", [])
                if runs:
                    environment.log(f"      Runs ({len(runs)}):")
                    for run in runs:
                        environment.log(f"        - Run ID {run.get('id')}: {run.get('name', 'N/A')}")
                        if run.get("config"):
                            environment.log(f"          Config: {run.get('config')}")
                        if show_all_fields:
                            environment.log(
                                f"          Passed: {run.get('passed_count', 0)}, Failed: {run.get('failed_count', 0)}, Blocked: {run.get('blocked_count', 0)}, Untested: {run.get('untested_count', 0)}"
                            )
        else:
            environment.log("\n  Entries: (none)")

        if show_all_fields:
            # Show all other fields
            standard_fields = [
                "id",
                "name",
                "description",
                "project_id",
                "milestone_id",
                "assignedto_id",
                "is_completed",
                "completed_on",
                "passed_count",
                "failed_count",
                "blocked_count",
                "retest_count",
                "untested_count",
                "created_by",
                "created_on",
                "url",
                "entries",
                "custom_status1_count",
                "custom_status2_count",
                "custom_status3_count",
                "custom_status4_count",
                "custom_status5_count",
                "custom_status6_count",
                "custom_status7_count",
            ]
            other_fields = {k: v for k, v in plan_data.items() if k not in standard_fields}
            if other_fields:
                environment.log(f"\n  Additional Fields ({len(other_fields)}):")
                for key, value in other_fields.items():
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


@cli.command()
@click.option("--offset", type=int, default=0, metavar="", help="Offset for pagination (default: 0).")
@click.option("--limit", type=int, default=250, metavar="", help="Limit for pagination (default: 250).")
@click.option("--json-output", is_flag=True, help="Output plans as raw JSON from API.")
@click.option("--show-all-fields", is_flag=True, help="Show all fields including custom fields in detail.")
@click.pass_context
@pass_environment
def list(
    environment: Environment,
    context: click.Context,
    offset: int,
    limit: int,
    json_output: bool,
    show_all_fields: bool,
    *args,
    **kwargs,
):
    """List test plans from TestRail"""
    environment.check_for_required_parameters()

    print_config(environment, "List")

    # Create ProjectBasedClient to resolve project
    project_client = ProjectBasedClient(
        environment=environment,
        suite=TestRailSuite(name=environment.suite_name, suite_id=environment.suite_id),
    )

    # Resolve project (converts name to ID if needed)
    project_client.resolve_project()

    environment.log(f"Retrieving plans for project ID {project_client.project.project_id}...")

    # Retrieve plans using PlanHandler from ProjectBasedClient
    response_data, error_message = project_client.api_request_handler.plan_handler.get_plans(
        project_id=project_client.project.project_id,
        limit=limit,
        offset=offset,
    )

    if error_message:
        environment.elog(f"Error: Failed to retrieve plans: {error_message}")
        raise SystemExit(1)

    # Handle output format
    if json_output:
        # Output prettified JSON response
        print(json.dumps(response_data, indent=2))
    else:
        # Display plans line by line
        plans = response_data.get("plans", [])
        response_offset = response_data.get("offset", 0)
        response_limit = response_data.get("limit", 250)
        response_size = response_data.get("size", 0)
        next_link = response_data.get("_links", {}).get("next")

        if not plans:
            environment.log("No plans found.")
        else:
            environment.log(
                f"Found {response_size} plan(s) (showing {response_offset + 1}-{response_offset + len(plans)}):"
            )
            if next_link:
                environment.log("  (More results available - use --offset and --limit for pagination)")
            environment.log("")

            for plan in plans:
                if show_all_fields:
                    # Show all fields from API response
                    environment.log(f"  Plan ID: {plan.get('id', 'N/A')}")

                    # Iterate through all fields in the plan
                    for key, value in plan.items():
                        if key == "id":
                            continue  # Already displayed as Plan ID

                        # Format field name for display
                        display_name = key.replace("_", " ").title()

                        # Handle None values
                        if value is None:
                            display_value = "N/A"
                        elif isinstance(value, bool):
                            display_value = "Yes" if value else "No"
                        elif isinstance(value, builtins.list):
                            if value:
                                display_value = f"{len(value)} item(s): {value}"
                            else:
                                display_value = "[]"
                        else:
                            display_value = value

                        environment.log(f"    {display_name}: {display_value}")

                    environment.log("")
                else:
                    # Display compact format
                    environment.log(f"  Plan ID: {plan.get('id', 'N/A')}")
                    environment.log(f"    Name: {plan.get('name', 'N/A')}")

                    if plan.get("description"):
                        description = plan.get("description")
                        # Truncate long descriptions in compact mode
                        if len(description) > 80:
                            description = description[:80] + "..."
                        environment.log(f"    Description: {description}")

                    is_completed = plan.get("is_completed", False)
                    environment.log(f"    Status: {'Completed' if is_completed else 'Active'}")

                    # Show test counts
                    passed = plan.get("passed_count", 0)
                    failed = plan.get("failed_count", 0)
                    blocked = plan.get("blocked_count", 0)
                    untested = plan.get("untested_count", 0)
                    environment.log(
                        f"    Tests: Passed={passed}, Failed={failed}, Blocked={blocked}, Untested={untested}"
                    )

                    if plan.get("milestone_id"):
                        environment.log(f"    Milestone ID: {plan.get('milestone_id')}")

                    environment.log("")
