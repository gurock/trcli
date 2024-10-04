import trcli
import enum

PARSE_COMMON_FAULT_MAPPING = dict(
    missing_file="Please provide a valid path to your results file with the -f argument.",
)

PARSE_JUNIT_OR_ROBOT_FAULT_MAPPING = dict(
    missing_title="Please give your Test Run a title using the --title argument."
)

ADD_RUN_FAULT_MAPPING = dict(
    missing_title="Please give your Test Run a title using the --title argument.",
)

FAULT_MAPPING = dict(
    invalid_file="Provided file is not a valid file.",
    missing_host="Please provide a TestRail server address with the -h argument.",
    missing_project="Please specify the project name using the --project argument.",
    missing_username="Please provide a valid TestRail username using the -u argument.",
    more_than_one_project="Given project name matches more than one result."
    "Please specify which should be used using the --project-id argument",
    project_doesnt_exists="Please specify a valid project name using the --project argument",
    missing_password_and_key="Please provide either a password using the -p "
    "argument or an API key using the -k argument.",
    no_response_from_host="Your upload to TestRail did not receive a successful response from your TestRail Instance. "
    "Please check your settings and try again.",
    connection_error="Upload to TestRail failed due to a network error. Please make sure you have a "
    "valid network connection then try again.",
    host_issues="Please provide a valid TestRail server address.",
    yaml_file_parse_issue="Error occurred while parsing yaml file ({file_path}). "
    "Make sure that structure of a file is correct.\nWe expect only `key: value`, `---` and `...`. Please check README file for more details.",
    file_open_issue="Error occurred while opening the file ({file_path}). "
    "Make sure that the file exists or the path is correct.",
    missing_suite="Suite with ID '{suite_id}' does not exist in TestRail.",
    no_user_agreement="User did not agree to create '{type}' automatically. Exiting.",
    error_checking_project="Error detected while checking a project: '{error_message}'",
    error_while_adding_suite="Error detected while adding suite: '{error_message}'",
    not_unique_suite_id_single_suite_baselines="One or more baselines created under '{project_name}' (single suite "
    "with baseline project). Please provide suite ID by "
    "specifying --suite-id.",
    unknown_suite_mode="Suite mode: '{suite_mode}' not recognised.",
    error_checking_missing_item="Error occurred while checking for '{missing_item}': '{error_message}'",
    data_verification_error="Data verification failed. Server added different resource than expected.",
    unknown_test_case_id="There are some test cases that have IDs and not exist in Test Rail.",
    dataclass_validation_error="Unable to parse field {field} in {class_name} tag. {reason}",
    unknown_section_id="There are some sections that have IDs and not exist in Test Rail.",
    missing_run_id_when_case_id_present="--case-id needs to be passed together with --run-id parameter.",
    mismatch_between_case_id_and_result_file="Could not match --case-id with result file. "
    "Please make sure that:\n--case-id matches ID "
    "(if present) under `testcase` tag in result xml file\nand\n"
    "only one result is present in result xml file.",
    unexpected_error_during_request_send="Unexpected error occurred during sending request: {request}",
    automation_id_unavailable=f"The automation_id field is not properly configured. "
    f"Please configure it in the TestRail Administration under Customizations > Case Fields.\n"
    f"The field should have the following mandatory details:\n"
    f"  - System Name: automation_id\n"
    f"  - Type: Text (or String)\n"
    f"  - Is Active: True",
    proxy_connection_error= "Failed to connect to the proxy server. Please check the proxy settings and ensure the server is available.",
    proxy_authentication_failed= "Proxy authentication failed for proxy. Please verify the username and password.",
    proxy_timeout= "The connection to the proxy server timed out. Please try again later or check the proxy server's availability.",
    proxy_bypass_error= "Failed to bypass the proxy for host. Please check the settings.",
    proxy_invalid_configuration= "The provided proxy configuration is invalid. Please check the proxy URL and format.",
    ssl_error_on_proxy= "SSL error encountered while using the HTTPS proxy. Please check the proxy's SSL certificate.",
    no_proxy_match_error= "The host {host} does not match any NO_PROXY rules. Ensure the correct domains or IP addresses are specified for bypassing the proxy."
)

COMMAND_FAULT_MAPPING = dict(
    add_run=dict(**FAULT_MAPPING, **ADD_RUN_FAULT_MAPPING),
    parse_junit=dict(**FAULT_MAPPING, **PARSE_COMMON_FAULT_MAPPING, **PARSE_JUNIT_OR_ROBOT_FAULT_MAPPING),
    parse_openapi=dict(**FAULT_MAPPING, **PARSE_COMMON_FAULT_MAPPING),
    parse_robot=dict(**FAULT_MAPPING, **PARSE_COMMON_FAULT_MAPPING, **PARSE_JUNIT_OR_ROBOT_FAULT_MAPPING),
)

PROMPT_MESSAGES = dict(
    create_new_suite="Suite ID was not provided in either the result file or the command line.\n"
    "Would you like to create suite with name '{suite_name}' under project: "
    "'{project_name}'?'",
    create_missing_sections="Some of the sections in provided result file are missing "
    "in TestRail or the IDs are not specified.\n"
    "Would you like to create missing sections under project '{project_name}'?",
    create_missing_test_cases="Some of the test cases in provided file are missing "
    "in TestRail or the IDs are not specified.\n"
    "Would you like to create missing test cases under project: '{project_name}'?",
)

TOOL_VERSION = f"""TestRail CLI v{trcli.__version__}
Copyright 2024 Gurock Software GmbH - www.gurock.com"""
TOOL_USAGE = f"""Supported and loaded modules:
    - parse_junit: JUnit XML Files (& Similar)
    - parse_robot: Robot Framework XML Files
    - parse_openapi: OpenAPI YML Files
    - add_run: Create a new test run"""

MISSING_COMMAND_SLOGAN = """Usage: trcli [OPTIONS] COMMAND [ARGS]...\nTry 'trcli --help' for help.
\nError: Missing command."""


class ProjectErrors(enum.IntEnum):
    multiple_project_same_name = -1
    not_existing_project = -2
    other_error = -3


class SuiteModes(enum.IntEnum):
    single_suite = 1
    single_suite_baselines = 2
    multiple_suites = 3


class RevertMessages:
    suite_deleted = "Deleted created suite"
    suite_not_deleted = "Unable to delete created suite: {error}"
    section_deleted = "Deleted created section"
    section_not_deleted = "Unable to delete created section: {error}"
    test_cases_deleted = "Deleted created test cases"
    test_cases_not_deleted = "Unable to delete created test cases: {error}"
    run_deleted = "Deleted created run"
    run_not_deleted = "Unable to delete created run: {error}"
