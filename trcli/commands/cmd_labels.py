import click

from trcli.api.project_based_client import ProjectBasedClient
from trcli.cli import pass_environment, CONTEXT_SETTINGS, Environment
from trcli.data_classes.dataclass_testrail import TestRailSuite


def print_config(env: Environment, action: str):
    env.log(f"Labels {action} Execution Parameters"
            f"\n> TestRail instance: {env.host} (user: {env.username})"
            f"\n> Project: {env.project if env.project else env.project_id}")


@click.group(context_settings=CONTEXT_SETTINGS)
@click.pass_context
@pass_environment
def cli(environment: Environment, context: click.Context, *args, **kwargs):
    """Manage labels in TestRail"""
    environment.cmd = "labels"
    environment.set_parameters(context)


@cli.command()
@click.option("--title", required=True, metavar="", help="Title of the label to add (max 20 characters).")
@click.pass_context
@pass_environment
def add(environment: Environment, context: click.Context, title: str, *args, **kwargs):
    """Add a new label in TestRail"""
    environment.check_for_required_parameters()
    print_config(environment, "Add")
    
    if len(title) > 20:
        environment.elog("Error: Label title must be 20 characters or less.")
        exit(1)
    
    project_client = ProjectBasedClient(
        environment=environment,
        suite=TestRailSuite(name=environment.suite_name, suite_id=environment.suite_id),
    )
    project_client.resolve_project()
    
    environment.log(f"Adding label '{title}'...")
    
    label_data, error_message = project_client.api_request_handler.add_label(
        project_id=project_client.project.project_id,
        title=title
    )
    
    if error_message:
        environment.elog(f"Failed to add label: {error_message}")
        exit(1)
    else:
        # API response has nested structure: {'label': {'id': 5, 'title': 'hello', ...}}
        label_info = label_data.get('label', label_data)  # Handle both nested and flat responses
        environment.log(f"Successfully added label: ID={label_info['id']}, Title='{label_info['title']}'")


@cli.command()
@click.option("--id", "label_id", required=True, type=int, metavar="", help="ID of the label to update.")
@click.option("--title", required=True, metavar="", help="New title for the label (max 20 characters).")
@click.pass_context
@pass_environment
def update(environment: Environment, context: click.Context, label_id: int, title: str, *args, **kwargs):
    """Update an existing label in TestRail"""
    environment.check_for_required_parameters()
    print_config(environment, "Update")
    
    if len(title) > 20:
        environment.elog("Error: Label title must be 20 characters or less.")
        exit(1)
    
    project_client = ProjectBasedClient(
        environment=environment,
        suite=TestRailSuite(name=environment.suite_name, suite_id=environment.suite_id),
    )
    project_client.resolve_project()
    
    environment.log(f"Updating label with ID {label_id}...")
    
    label_data, error_message = project_client.api_request_handler.update_label(
        label_id=label_id,
        project_id=project_client.project.project_id,
        title=title
    )
    
    if error_message:
        environment.elog(f"Failed to update label: {error_message}")
        exit(1)
    else:
        # Handle both nested and flat API responses
        label_info = label_data.get('label', label_data)
        environment.log(f"Successfully updated label: ID={label_info['id']}, Title='{label_info['title']}'")


@cli.command()
@click.option("--ids", required=True, metavar="", help="Comma-separated list of label IDs to delete (e.g., 1,2,3).")
@click.confirmation_option(prompt="Are you sure you want to delete these labels?")
@click.pass_context
@pass_environment
def delete(environment: Environment, context: click.Context, ids: str, *args, **kwargs):
    """Delete labels from TestRail"""
    environment.check_for_required_parameters()
    print_config(environment, "Delete")
    
    try:
        label_ids = [int(id.strip()) for id in ids.split(",")]
    except ValueError:
        environment.elog("Error: Invalid label IDs format. Use comma-separated integers (e.g., 1,2,3).")
        exit(1)
    
    project_client = ProjectBasedClient(
        environment=environment,
        suite=TestRailSuite(name=environment.suite_name, suite_id=environment.suite_id),
    )
    project_client.resolve_project()
    
    environment.log(f"Deleting labels with IDs: {', '.join(map(str, label_ids))}...")
    
    # Use single delete endpoint for one label, batch endpoint for multiple
    if len(label_ids) == 1:
        success, error_message = project_client.api_request_handler.delete_label(label_ids[0])
    else:
        success, error_message = project_client.api_request_handler.delete_labels(label_ids)
    
    if error_message:
        environment.elog(f"Failed to delete labels: {error_message}")
        exit(1)
    else:
        environment.log(f"Successfully deleted {len(label_ids)} label(s)")


@cli.command()
@click.option("--offset", type=int, default=0, metavar="", help="Offset for pagination (default: 0).")
@click.option("--limit", type=int, default=250, metavar="", help="Limit for pagination (default: 250).")
@click.pass_context
@pass_environment
def list(environment: Environment, context: click.Context, offset: int, limit: int, *args, **kwargs):
    """List all labels in the project"""
    environment.check_for_required_parameters()
    print_config(environment, "List")
    
    project_client = ProjectBasedClient(
        environment=environment,
        suite=TestRailSuite(name=environment.suite_name, suite_id=environment.suite_id),
    )
    project_client.resolve_project()
    
    environment.log("Retrieving labels...")
    
    labels_data, error_message = project_client.api_request_handler.get_labels(
        project_id=project_client.project.project_id,
        offset=offset,
        limit=limit
    )
    
    if error_message:
        environment.elog(f"Failed to retrieve labels: {error_message}")
        exit(1)
    else:
        labels = labels_data.get('labels', [])
        total_size = labels_data.get('size', len(labels))
        
        environment.log(f"Found {len(labels)} labels (showing {offset + 1}-{offset + len(labels)} of {total_size}):")
        environment.log("")
        
        if labels:
            for label in labels:
                environment.log(f"  ID: {label['id']}, Title: '{label['title']}', Created by: {label.get('created_by', 'N/A')}")
        else:
            environment.log("  No labels found.")


@cli.command()
@click.option("--id", "label_id", required=True, type=int, metavar="", help="ID of the label to retrieve.")
@click.pass_context
@pass_environment
def get(environment: Environment, context: click.Context, label_id: int, *args, **kwargs):
    """Get a specific label by ID"""
    environment.check_for_required_parameters()
    print_config(environment, "Get")
    
    project_client = ProjectBasedClient(
        environment=environment,
        suite=TestRailSuite(name=environment.suite_name, suite_id=environment.suite_id),
    )
    project_client.resolve_project()
    
    environment.log(f"Retrieving label with ID {label_id}...")
    
    label_data, error_message = project_client.api_request_handler.get_label(label_id)
    
    # Debug: Log what we received
    if environment.verbose:
        environment.log(f"Debug: API response: {label_data}")
        environment.log(f"Debug: Error message: {error_message}")
    
    if error_message:
        environment.elog(f"Failed to retrieve label: {error_message}")
        exit(1)
    elif not label_data:
        environment.elog(f"No data received for label ID {label_id}")
        exit(1)
    else:
        environment.log(f"Label details:")
        
        # Handle different possible response structures
        if isinstance(label_data, dict):
            # Check if it's a nested response like add_label
            if 'label' in label_data:
                label_info = label_data['label']
            else:
                label_info = label_data
            
            # Ensure we have the basic required fields
            if not label_info or not isinstance(label_info, dict):
                environment.elog(f"Invalid label data received: {label_info}")
                exit(1)
            
            environment.log(f"  ID: {label_info.get('id', label_id)}")  # Fallback to requested ID
            environment.log(f"  Title: '{label_info.get('title', label_info.get('name', 'N/A'))}'")
            environment.log(f"  Created by: {label_info.get('created_by', 'N/A')}")
            environment.log(f"  Created on: {label_info.get('created_on', 'N/A')}")
        else:
            environment.elog(f"Unexpected response format: {label_data}")
            exit(1)


@cli.group()
@click.pass_context
@pass_environment
def cases(environment: Environment, context: click.Context, *args, **kwargs):
    """Manage labels for test cases"""
    pass


@cases.command(name='add')
@click.option("--case-ids", required=True, metavar="", help="Comma-separated list of test case IDs (e.g., 1,2,3).")
@click.option("--title", required=True, metavar="", help="Label title(s) to add (max 20 characters each). Use comma separation for multiple labels (e.g., 'label1,label2').")
@click.pass_context
@pass_environment
def add_to_cases(environment: Environment, context: click.Context, case_ids: str, title: str, *args, **kwargs):
    """Add one or more labels to test cases"""
    environment.check_for_required_parameters()
    print_config(environment, "Add Cases")
    
    # Parse comma-separated titles
    title_list = [t.strip() for t in title.split(",") if t.strip()]
    
    # Filter valid and invalid labels
    valid_titles = []
    invalid_titles = []
    
    for t in title_list:
        if len(t) > 20:
            invalid_titles.append(t)
        else:
            valid_titles.append(t)
    
    # Show warnings for invalid labels but continue with valid ones
    if invalid_titles:
        for invalid_title in invalid_titles:
            environment.elog(f"Warning: Label title '{invalid_title}' exceeds 20 character limit and will be skipped.")
    
    # Check if we have any valid labels left
    if not valid_titles:
        environment.elog("Error: No valid label titles provided after filtering.")
        exit(1)
    
    # Validate maximum number of valid labels (TestRail limit is 10 labels per case)
    if len(valid_titles) > 10:
        environment.elog(f"Error: Cannot add more than 10 labels at once. You provided {len(valid_titles)} valid labels.")
        exit(1)
    
    # Use only valid titles for processing
    title_list = valid_titles
    
    try:
        case_id_list = [int(id.strip()) for id in case_ids.split(",")]
    except ValueError:
        environment.elog("Error: Invalid case IDs format. Use comma-separated integers (e.g., 1,2,3).")
        exit(1)
    
    project_client = ProjectBasedClient(
        environment=environment,
        suite=TestRailSuite(name=environment.suite_name, suite_id=environment.suite_id),
    )
    project_client.resolve_project()
    
    # Create appropriate log message
    if len(title_list) == 1:
        environment.log(f"Adding label '{title_list[0]}' to {len(case_id_list)} test case(s)...")
    else:
        environment.log(f"Adding {len(title_list)} labels ({', '.join(title_list)}) to {len(case_id_list)} test case(s)...")
    
    results, error_message = project_client.api_request_handler.add_labels_to_cases(
        case_ids=case_id_list,
        titles=title_list,
        project_id=project_client.project.project_id,
        suite_id=environment.suite_id
    )
    
    # Handle validation errors (but don't exit if there are successful cases)
    if error_message:
        environment.elog(f"Warning: {error_message}")
    
    # Always process results (even if there were validation errors)
    # Report results
    successful_cases = results.get('successful_cases', [])
    failed_cases = results.get('failed_cases', [])
    max_labels_reached = results.get('max_labels_reached', [])
    case_not_found = results.get('case_not_found', [])
    
    if case_not_found:
        environment.elog(f"Error: {len(case_not_found)} test case(s) not found:")
        for case_id in case_not_found:
            environment.elog(f"  Case ID {case_id} does not exist in the project")
    
    if successful_cases:
        environment.log(f"Successfully processed {len(successful_cases)} case(s):")
        for case_result in successful_cases:
            environment.log(f"  Case {case_result['case_id']}: {case_result['message']}")
    
    if max_labels_reached:
        environment.log(f"Warning: {len(max_labels_reached)} case(s) already have maximum labels (10):")
        for case_id in max_labels_reached:
            environment.log(f"  Case {case_id}: Maximum labels reached")
    
    if failed_cases:
        environment.log(f"Failed to process {len(failed_cases)} case(s):")
        for case_result in failed_cases:
            environment.log(f"  Case {case_result['case_id']}: {case_result['error']}")
    
    # Exit with error if there were invalid case IDs
    if case_not_found:
        exit(1)


@cases.command(name='list')
@click.option("--ids", metavar="", help="Comma-separated list of label IDs to filter by (e.g., 1,2,3).")
@click.option("--title", metavar="", help="Label title to filter by (max 20 characters).")
@click.pass_context
@pass_environment
def list_cases(environment: Environment, context: click.Context, ids: str, title: str, *args, **kwargs):
    """List test cases filtered by label ID or title"""
    environment.check_for_required_parameters()
    
    # Validate that either ids or title is provided, but not both
    if not ids and not title:
        environment.elog("Error: Either --ids or --title must be provided.")
        exit(1)
    
    if ids and title:
        environment.elog("Error: --ids and --title options are mutually exclusive. Use only one at a time.")
        exit(1)
    
    if title and len(title) > 20:
        environment.elog("Error: Label title must be 20 characters or less.")
        exit(1)
    
    print_config(environment, "List Cases by Label")
    
    label_ids = None
    if ids:
        try:
            label_ids = [int(id.strip()) for id in ids.split(",")]
        except ValueError:
            environment.elog("Error: Invalid label IDs format. Use comma-separated integers (e.g., 1,2,3).")
            exit(1)
    
    project_client = ProjectBasedClient(
        environment=environment,
        suite=TestRailSuite(name=environment.suite_name, suite_id=environment.suite_id),
    )
    project_client.resolve_project()
    
    if title:
        environment.log(f"Retrieving test cases with label title '{title}'...")
    else:
        environment.log(f"Retrieving test cases with label IDs: {', '.join(map(str, label_ids))}...")
    
    matching_cases, error_message = project_client.api_request_handler.get_cases_by_label(
        project_id=project_client.project.project_id,
        suite_id=environment.suite_id,
        label_ids=label_ids,
        label_title=title
    )
    
    if error_message:
        environment.elog(f"Failed to retrieve cases: {error_message}")
        exit(1)
    else:
        environment.log(f"Found {len(matching_cases)} matching test case(s):")
        environment.log("")
        
        if matching_cases:
            for case in matching_cases:
                case_labels = case.get('labels', [])
                label_info = []
                for label in case_labels:
                    label_info.append(f"ID:{label.get('id')},Title:'{label.get('title')}'")
                
                labels_str = f" [Labels: {'; '.join(label_info)}]" if label_info else " [No labels]"
                environment.log(f"  Case ID: {case['id']}, Title: '{case['title']}'{labels_str}")
        else:
            if title:
                environment.log(f"  No test cases found with label title '{title}'.")
            else:
                environment.log(f"  No test cases found with the specified label IDs.")


@cases.command(name='get')
@click.option("--case-ids", required=True, metavar="", help="Comma-separated list of test case IDs (e.g., 1,2,3).")
@click.pass_context
@pass_environment
def get_case_labels(environment: Environment, context: click.Context, case_ids: str, *args, **kwargs):
    """Get labels assigned to test cases"""
    environment.check_for_required_parameters()
    print_config(environment, "Get Case Labels")
    
    try:
        case_id_list = [int(id.strip()) for id in case_ids.split(",")]
    except ValueError:
        environment.elog("Error: Invalid case IDs format. Use comma-separated integers (e.g., 1,2,3).")
        exit(1)
    
    project_client = ProjectBasedClient(
        environment=environment,
        suite=TestRailSuite(name=environment.suite_name, suite_id=environment.suite_id),
    )
    project_client.resolve_project()
    
    environment.log(f"Retrieving labels for {len(case_id_list)} test case(s)...")
    
    cases_with_labels, error_messages = project_client.api_request_handler.get_case_labels(case_id_list)
    
    # Display errors for failed cases
    if error_messages:
        for error in error_messages:
            environment.elog(f"Failed to retrieve case labels: {error}")
    
    # Display results for successful cases
    if cases_with_labels:
        environment.log(f"Found {len(cases_with_labels)} test case(s):")
        environment.log("")
        
        for case in cases_with_labels:
            case_labels = case.get('labels', [])
            label_info = []
            for label in case_labels:
                label_info.append(f"ID:{label.get('id')},Title:'{label.get('title')}'")
            
            labels_str = f" [Labels: {'; '.join(label_info)}]" if label_info else " [No labels]"
            environment.log(f"  Case ID: {case['id']}, Title: '{case['title']}'{labels_str}")
    else:
        if not error_messages:
            environment.log("No test cases found.")
    
    # Only exit with error if all cases failed
    if error_messages and not cases_with_labels:
        exit(1)