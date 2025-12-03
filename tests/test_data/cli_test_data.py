from trcli import __version__

CHECK_ERROR_MESSAGE_FOR_REQUIRED_PARAMETERS_TEST_DATA = [
    (
        ["file"],
        "Please provide a valid path to your results file with the -f argument.\n",
        1,
    ),
    (
        ["host"],
        "Please provide a TestRail server address with the -h argument.\n",
        1,
    ),
    (
        ["project"],
        "Please specify the project name using the --project argument.\n",
        1,
    ),
    (
        ["username"],
        "Please provide a valid TestRail username using the -u argument.\n",
        1,
    ),
    (
        ["title", "run-id"],
        "Please give your Test Run a title using the --title argument.\n",
        1,
    ),
    (
        ["password", "key"],
        "Please provide either a password using the -p argument or an API key using the -k argument.\n",
        1,
    ),
]

CHECK_ERROR_MESSAGE_FOR_REQUIRED_PARAMETERS_TEST_IDS = [
    "No file parameter provided",
    "No host parameter provided",
    "No project parameter provided",
    "No username parameter provided",
    "No title or run-id parameter provided",
    "No password and API key parameter provided",
]

ENVIRONMENT_VARIABLES = {
    "TR_CLI_HOST": "host_name_from_env",
    "TR_CLI_FILE": "file_from_env",
    "TR_CLI_PROJECT": "project_from_env",
    "TR_CLI_TITLE": "title_from_env",
    "TR_CLI_USERNAME": "username_from_env",
    "TR_CLI_PASSWORD": "password_from_env",
    "TR_CLI_KEY": "key_from_env",
}

RETURN_VALUE_FROM_CUSTOM_CONFIG_FILE = {
    "host": "host_from_custom_config",
    "file": "file_from_custom_config",
    "project": "project_from_custom_config",
    "title": "title_from_custom_config",
    "username": "username_from_custom_config",
    "password": "password_from_custom_config",
    "key": "key_from_custom_config",
}

trcli_description = (
    "Supported and loaded modules:\n"
    "    - parse_junit: JUnit XML Files (& Similar)\n"
    "    - parse_cucumber: Cucumber JSON results (BDD)\n"
    "    - import_gherkin: Upload .feature files to TestRail BDD\n"
    "    - export_gherkin: Export BDD test cases as .feature files\n"
    "    - parse_gherkin: Parse Gherkin .feature file locally\n"
    "    - parse_robot: Robot Framework XML Files\n"
    "    - parse_openapi: OpenAPI YML Files\n"
    "    - add_run: Create a new test run\n"
    "    - labels: Manage labels (add, update, delete, list)\n"
    "    - references: Manage references (cases and runs)\n"
)

trcli_help_description = "TestRail CLI"
