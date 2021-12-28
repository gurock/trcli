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
        ["title"],
        "Please give your Test Run a title using the --title argument.\n",
        1,
    ),
    (
        ["username"],
        "Please provide a valid TestRail username using the -u argument.\n",
        1,
    ),
    (
        ["title"],
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
    "No title parameter provided",
    "No username parameter provided",
    "No test run name parameter provided",
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

RETURN_VALUE_FROM_DEFAULT_CONFIG_FILE = {
    "host": "host_from_default_config",
    "file": "file_from_default_config.xml",
    "project": "project_from_default_config",
    "title": "title_from_default_config",
    "username": "username_from_default_config",
    "password": "password_from_default_config",
    "key": "key_from_default_config",
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

trcli_description = f"TestRail Connect v0.1\n\
Copyright 2021 Gurock Software GmbH - www.gurock.com\n\
Supported and loaded modules:\n\
    - junit: JUnit XML Files (& Similar)\n"

trcli_help_description = "TestRail CLI"
