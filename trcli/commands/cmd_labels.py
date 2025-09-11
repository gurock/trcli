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
@click.option("--title", required=True, metavar="", help="Title of the label to add (max 20 characters).")
@click.pass_context
@pass_environment
def add_to_cases(environment: Environment, context: click.Context, case_ids: str, title: str, *args, **kwargs):
    """Add a label to test cases"""
    environment.check_for_required_parameters()
    print_config(environment, "Add Cases")
    
    if len(title) > 20:
        environment.elog("Error: Label title must be 20 characters or less.")
        exit(1)
    
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
    
    environment.log(f"Adding label '{title}' to {len(case_id_list)} test case(s)...")
    
    results, error_message = project_client.api_request_handler.add_labels_to_cases(
        case_ids=case_id_list,
        title=title,
        project_id=project_client.project.project_id,
        suite_id=environment.suite_id
    )
    
    if error_message:
        environment.elog(f"Failed to add labels to cases: {error_message}")
        exit(1)
    else:
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
    
    # Validate that either ids or title is provided
    if not ids and not title:
        environment.elog("Error: Either --ids or --title must be provided.")
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


@cli.group()
@click.pass_context
@pass_environment
def tests(environment: Environment, context: click.Context, *args, **kwargs):
    """Manage labels for tests"""
    pass


@tests.command(name='add')
@click.option("--test-ids", metavar="", help="Comma-separated list of test IDs (e.g., 1,2,3).")
@click.option("--test-id-file", metavar="", help="CSV file containing test IDs.")
@click.option("--title", required=True, metavar="", help="Label title(s) to add (max 20 characters each). Use comma separation for multiple labels (e.g., 'label1,label2').")
@click.pass_context
@pass_environment
def add_to_tests(environment: Environment, context: click.Context, test_ids: str, test_id_file: str, title: str, *args, **kwargs):
    """Add label(s) to tests"""
    environment.check_for_required_parameters()
    print_config(environment, "Add Tests")
    
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
    
    # Validate maximum number of valid labels (TestRail limit is 10 labels per test)
    if len(valid_titles) > 10:
        environment.elog(f"Error: Cannot add more than 10 labels at once. You provided {len(valid_titles)} valid labels.")
        exit(1)
    
    # Use only valid titles for processing
    title_list = valid_titles
    
    # Validate that either test_ids or test_id_file is provided
    if not test_ids and not test_id_file:
        environment.elog("Error: Either --test-ids or --test-id-file must be provided.")
        exit(1)
    
    if test_ids and test_id_file:
        environment.elog("Error: Cannot use both --test-ids and --test-id-file. Choose one.")
        exit(1)
    
    test_id_list = []
    
    # Parse test IDs from command line
    if test_ids:
        try:
            test_id_list = [int(id.strip()) for id in test_ids.split(",")]
        except ValueError:
            environment.elog("Error: Invalid test IDs format. Use comma-separated integers (e.g., 1,2,3).")
            exit(1)
    
    # Parse test IDs from CSV file
    if test_id_file:
        import csv
        import os
        
        if not os.path.exists(test_id_file):
            environment.elog(f"Error: File '{test_id_file}' not found.")
            exit(1)
        
        try:
            with open(test_id_file, 'r', newline='', encoding='utf-8') as csvfile:
                # Try to detect delimiter
                sample = csvfile.read(1024)
                csvfile.seek(0)
                sniffer = csv.Sniffer()
                
                single_column_mode = False
                try:
                    delimiter = sniffer.sniff(sample).delimiter
                except csv.Error:
                    # If delimiter detection fails, check for common delimiters
                    if ',' in sample:
                        delimiter = ','
                    elif ';' in sample:
                        delimiter = ';'
                    elif '\t' in sample:
                        delimiter = '\t'
                    else:
                        # Single column file - use line-by-line reading
                        single_column_mode = True
                
                if single_column_mode:
                    # Handle single column files (no delimiters)
                    csvfile.seek(0)
                    lines = csvfile.readlines()
                    for line in lines:
                        line = line.strip()
                        if line and not line.lower().startswith('test'):  # Skip likely headers
                            try:
                                test_id_list.append(int(line))
                            except ValueError:
                                environment.log(f"Warning: Ignoring invalid test ID '{line}' in file")
                else:
                    # Handle CSV files with delimiters
                    reader = csv.reader(csvfile, delimiter=delimiter)
                    
                    # Skip header if it exists (check if first row contains non-numeric values)
                    first_row = next(reader, None)
                    if first_row:
                        # Check if first row looks like a header
                        try:
                            # If we can convert all values to int, it's likely data, not header
                            [int(val.strip()) for val in first_row if val.strip()]
                            # Reset to beginning and don't skip
                            csvfile.seek(0)
                            reader = csv.reader(csvfile, delimiter=delimiter)
                        except ValueError:
                            # First row contains non-numeric data, likely header, so we skip it
                            pass
                    
                    for row in reader:
                        for cell in row:
                            cell_value = cell.strip()
                            if cell_value:  # Skip empty cells
                                try:
                                    test_id_list.append(int(cell_value))
                                except ValueError:
                                    environment.log(f"Warning: Ignoring invalid test ID '{cell_value}' in file")
                                
        except Exception as e:
            environment.elog(f"Error reading CSV file: {e}")
            exit(1)
        
        if not test_id_list:
            environment.elog("Error: No valid test IDs found in the CSV file.")
            exit(1)
        
        environment.log(f"Loaded {len(test_id_list)} test ID(s) from file '{test_id_file}'")
    
    project_client = ProjectBasedClient(
        environment=environment,
        suite=TestRailSuite(name=environment.suite_name, suite_id=environment.suite_id),
    )
    project_client.resolve_project()
    
    # Log message adjusted for single/multiple labels
    if len(title_list) == 1:
        environment.log(f"Adding label '{title_list[0]}' to {len(test_id_list)} test(s)...")
    else:
        environment.log(f"Adding {len(title_list)} labels ({', '.join(title_list)}) to {len(test_id_list)} test(s)...")
    
    results, error_message = project_client.api_request_handler.add_labels_to_tests(
        test_ids=test_id_list,
        titles=title_list,
        project_id=project_client.project.project_id
    )
    
    # Handle validation errors (warnings, not fatal)
    if error_message:
        environment.elog(f"Warning: {error_message}")
    
    # Process results
    # Report results
    successful_tests = results.get('successful_tests', [])
    failed_tests = results.get('failed_tests', [])
    max_labels_reached = results.get('max_labels_reached', [])
    test_not_found = results.get('test_not_found', [])
    
    if test_not_found:
        environment.log(f"Warning: {len(test_not_found)} test(s) not found or not accessible:")
        for test_id in test_not_found:
            environment.log(f"  Test ID {test_id} does not exist or is not accessible")
    
    if successful_tests:
        environment.log(f"Successfully processed {len(successful_tests)} test(s):")
        for test_result in successful_tests:
            environment.log(f"  Test {test_result['test_id']}: {test_result['message']}")
    
    if max_labels_reached:
        environment.log(f"Warning: {len(max_labels_reached)} test(s) already have maximum labels (10):")
        for test_id in max_labels_reached:
            environment.log(f"  Test {test_id}: Maximum labels reached")
    
    if failed_tests:
        environment.log(f"Failed to process {len(failed_tests)} test(s):")
        for test_result in failed_tests:
            environment.log(f"  Test {test_result['test_id']}: {test_result['error']}")


@tests.command(name='list')
@click.option("--run-id", required=True, metavar="", help="Comma-separated list of run IDs to filter tests from (e.g., 1,2,3).")
@click.option("--ids", required=True, metavar="", help="Comma-separated list of label IDs to filter by (e.g., 1,2,3).")
@click.pass_context
@pass_environment
def list_tests(environment: Environment, context: click.Context, run_id: str, ids: str, *args, **kwargs):
    """List tests filtered by label ID from specific runs"""
    environment.check_for_required_parameters()
    print_config(environment, "List Tests by Label")
    
    try:
        run_ids = [int(id.strip()) for id in run_id.split(",")]
    except ValueError:
        environment.elog("Error: Invalid run IDs format. Use comma-separated integers (e.g., 1,2,3).")
        exit(1)
    
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
    
    environment.log(f"Retrieving tests from run IDs: {', '.join(map(str, run_ids))} with label IDs: {', '.join(map(str, label_ids))}...")
    
    matching_tests, error_message = project_client.api_request_handler.get_tests_by_label(
        project_id=project_client.project.project_id,
        label_ids=label_ids,
        run_ids=run_ids
    )
    
    if error_message:
        environment.elog(f"Failed to retrieve tests: {error_message}")
        exit(1)
    else:
        environment.log(f"Found {len(matching_tests)} matching test(s):")
        environment.log("")
        
        if matching_tests:
            for test in matching_tests:
                test_labels = test.get('labels', [])
                label_info = []
                for label in test_labels:
                    label_info.append(f"ID:{label.get('id')},Title:'{label.get('title')}'")
                
                labels_str = f" [Labels: {'; '.join(label_info)}]" if label_info else " [No labels]"
                status_name = test.get('status_id', 'Unknown')
                environment.log(f"  Test ID: {test['id']}, Title: '{test.get('title', 'Unknown')}', Status: {status_name}{labels_str}")
        else:
            environment.log(f"  No tests found with the specified label IDs.")


@tests.command(name='get')
@click.option("--test-ids", required=True, metavar="", help="Comma-separated list of test IDs (e.g., 1,2,3).")
@click.pass_context
@pass_environment
def get_test_labels(environment: Environment, context: click.Context, test_ids: str, *args, **kwargs):
    """Get the labels of tests using test IDs"""
    environment.check_for_required_parameters()
    print_config(environment, "Get Test Labels")
    
    try:
        test_id_list = [int(id.strip()) for id in test_ids.split(",")]
    except ValueError:
        environment.elog("Error: Invalid test IDs format. Use comma-separated integers (e.g., 1,2,3).")
        exit(1)
    
    project_client = ProjectBasedClient(
        environment=environment,
        suite=TestRailSuite(name=environment.suite_name, suite_id=environment.suite_id),
    )
    project_client.resolve_project()
    
    environment.log(f"Retrieving labels for {len(test_id_list)} test(s)...")
    
    test_labels, error_message = project_client.api_request_handler.get_test_labels(test_id_list)
    
    if error_message:
        environment.elog(f"Failed to retrieve test labels: {error_message}")
        exit(1)
    else:
        environment.log(f"Test label information:")
        environment.log("")
        
        for test_info in test_labels:
            test_id = test_info['test_id']
            
            if test_info.get('error'):
                environment.log(f"  Test ID: {test_id} - Error: {test_info['error']}")
            else:
                test_labels = test_info.get('labels', [])
                title = test_info.get('title', 'Unknown')
                status_id = test_info.get('status_id', 'Unknown')
                
                environment.log(f"  Test ID: {test_id}")
                environment.log(f"    Title: '{title}'")
                environment.log(f"    Status: {status_id}")
                
                if test_labels:
                    environment.log(f"    Labels ({len(test_labels)}):")
                    for label in test_labels:
                        environment.log(f"      - ID: {label.get('id')}, Title: '{label.get('title')}'")
                else:
                    environment.log(f"    Labels: No labels assigned")
                environment.log("") 