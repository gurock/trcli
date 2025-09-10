import click

from trcli.api.project_based_client import ProjectBasedClient
from trcli.cli import pass_environment, CONTEXT_SETTINGS, Environment
from trcli.data_classes.dataclass_testrail import TestRailSuite


def print_config(env: Environment, action: str):
    env.log(f"References {action} Execution Parameters"
            f"\n> TestRail instance: {env.host} (user: {env.username})"
            f"\n> Project: {env.project if env.project else env.project_id}")


@click.group(context_settings=CONTEXT_SETTINGS)
@click.pass_context
@pass_environment
def cli(environment: Environment, context: click.Context, *args, **kwargs):
    """Manage references in TestRail"""
    environment.cmd = "references"
    environment.set_parameters(context)


@cli.group()
@click.pass_context
@pass_environment
def cases(environment: Environment, context: click.Context, *args, **kwargs):
    """Manage references for test cases"""
    pass


@cases.command(name='add')
@click.option("--case-ids", required=True, metavar="", help="Comma-separated list of test case IDs (e.g., 1,2,3).")
@click.option("--refs", required=True, metavar="", help="Comma-separated list of references to add (e.g., REQ-1,REQ-2).")
@click.pass_context
@pass_environment
def add_references(environment: Environment, context: click.Context, case_ids: str, refs: str, *args, **kwargs):
    """Add references to test cases"""
    environment.check_for_required_parameters()
    print_config(environment, "Add References")
    
    # Parse test case IDs
    try:
        test_case_ids = [int(id.strip()) for id in case_ids.split(",")]
    except ValueError:
        environment.elog("Error: Invalid test case IDs format. Use comma-separated integers (e.g., 1,2,3).")
        exit(1)
    
    # Parse references - allow up to 2000 characters total
    references = [ref.strip() for ref in refs.split(",") if ref.strip()]
    if not references:
        environment.elog("Error: No valid references provided.")
        exit(1)
    
    # Validate total character limit
    total_refs_length = len(",".join(references))
    if total_refs_length > 2000:
        environment.elog(f"Error: Total references length ({total_refs_length} characters) exceeds 2000 character limit.")
        exit(1)
    
    project_client = ProjectBasedClient(
        environment=environment,
        suite=TestRailSuite(name=environment.suite_name, suite_id=environment.suite_id),
    )
    project_client.resolve_project()
    
    environment.log(f"Adding references to {len(test_case_ids)} test case(s)...")
    environment.log(f"References: {', '.join(references)}")
    
    # Process each test case
    success_count = 0
    failed_cases = []
    
    for case_id in test_case_ids:
        success, error_message = project_client.api_request_handler.add_case_references(
            case_id=case_id,
            references=references
        )
        
        if success:
            success_count += 1
            environment.log(f"  ✓ Test case {case_id}: References added successfully")
        else:
            failed_cases.append({"case_id": case_id, "error": error_message})
            environment.elog(f"  ✗ Test case {case_id}: {error_message}")
    
    # Summary
    if success_count > 0:
        environment.log(f"Successfully added references to {success_count} test case(s)")
    
    if failed_cases:
        environment.elog(f"Failed to add references to {len(failed_cases)} test case(s)")
        exit(1)


@cases.command(name='update')
@click.option("--case-ids", required=True, metavar="", help="Comma-separated list of test case IDs (e.g., 1,2,3).")
@click.option("--refs", required=True, metavar="", help="Comma-separated list of references to replace existing ones (e.g., REQ-1,REQ-2).")
@click.pass_context
@pass_environment
def update_references(environment: Environment, context: click.Context, case_ids: str, refs: str, *args, **kwargs):
    """Update references on test cases by replacing existing ones"""
    environment.check_for_required_parameters()
    print_config(environment, "Update References")
    
    # Parse test case IDs
    try:
        test_case_ids = [int(id.strip()) for id in case_ids.split(",")]
    except ValueError:
        environment.elog("Error: Invalid test case IDs format. Use comma-separated integers (e.g., 1,2,3).")
        exit(1)
    
    # Parse references - allow up to 2000 characters total
    references = [ref.strip() for ref in refs.split(",") if ref.strip()]
    if not references:
        environment.elog("Error: No valid references provided.")
        exit(1)
    
    # Validate total character limit
    total_refs_length = len(",".join(references))
    if total_refs_length > 2000:
        environment.elog(f"Error: Total references length ({total_refs_length} characters) exceeds 2000 character limit.")
        exit(1)
    
    project_client = ProjectBasedClient(
        environment=environment,
        suite=TestRailSuite(name=environment.suite_name, suite_id=environment.suite_id),
    )
    project_client.resolve_project()
    
    environment.log(f"Updating references for {len(test_case_ids)} test case(s)...")
    environment.log(f"New references: {', '.join(references)}")
    
    # Process each test case
    success_count = 0
    failed_cases = []
    
    for case_id in test_case_ids:
        success, error_message = project_client.api_request_handler.update_case_references(
            case_id=case_id,
            references=references
        )
        
        if success:
            success_count += 1
            environment.log(f"  ✓ Test case {case_id}: References updated successfully")
        else:
            failed_cases.append({"case_id": case_id, "error": error_message})
            environment.elog(f"  ✗ Test case {case_id}: {error_message}")
    
    # Summary
    if success_count > 0:
        environment.log(f"Successfully updated references for {success_count} test case(s)")
    
    if failed_cases:
        environment.elog(f"Failed to update references for {len(failed_cases)} test case(s)")
        exit(1)


@cases.command(name='delete')
@click.option("--case-ids", required=True, metavar="", help="Comma-separated list of test case IDs (e.g., 1,2,3).")
@click.option("--refs", metavar="", help="Comma-separated list of specific references to delete. If not provided, all references will be deleted.")
@click.confirmation_option(prompt="Are you sure you want to delete these references?")
@click.pass_context
@pass_environment
def delete_references(environment: Environment, context: click.Context, case_ids: str, refs: str = None, *args, **kwargs):
    """Delete all or specific references from test cases"""
    environment.check_for_required_parameters()
    print_config(environment, "Delete References")
    
    # Parse test case IDs
    try:
        test_case_ids = [int(id.strip()) for id in case_ids.split(",")]
    except ValueError:
        environment.elog("Error: Invalid test case IDs format. Use comma-separated integers (e.g., 1,2,3).")
        exit(1)
    
    # Parse specific references if provided
    specific_refs = None
    if refs:
        specific_refs = [ref.strip() for ref in refs.split(",") if ref.strip()]
        if not specific_refs:
            environment.elog("Error: No valid references provided.")
            exit(1)
    
    project_client = ProjectBasedClient(
        environment=environment,
        suite=TestRailSuite(name=environment.suite_name, suite_id=environment.suite_id),
    )
    project_client.resolve_project()
    
    if specific_refs:
        environment.log(f"Deleting specific references from {len(test_case_ids)} test case(s)...")
        environment.log(f"References to delete: {', '.join(specific_refs)}")
    else:
        environment.log(f"Deleting all references from {len(test_case_ids)} test case(s)...")
    
    # Process each test case
    success_count = 0
    failed_cases = []
    
    for case_id in test_case_ids:
        success, error_message = project_client.api_request_handler.delete_case_references(
            case_id=case_id,
            specific_references=specific_refs
        )
        
        if success:
            success_count += 1
            if specific_refs:
                environment.log(f"  ✓ Test case {case_id}: Specific references deleted successfully")
            else:
                environment.log(f"  ✓ Test case {case_id}: All references deleted successfully")
        else:
            failed_cases.append({"case_id": case_id, "error": error_message})
            environment.elog(f"  ✗ Test case {case_id}: {error_message}")
    
    # Summary
    if success_count > 0:
        environment.log(f"Successfully deleted references from {success_count} test case(s)")
    
    if failed_cases:
        environment.elog(f"Failed to delete references from {len(failed_cases)} test case(s)")
        exit(1)

