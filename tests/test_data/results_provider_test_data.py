from trcli.constants import FAULT_MAPPING, RevertMessages

TEST_UPLOAD_RESULTS_FLOW_TEST_DATA = [
    ("get_suite_id", None),
    ("check_for_missing_sections_and_add", None),
    ("check_for_missing_test_cases_and_add", None),
    ("add_run", None),
    ("add_results", None),
    ("add_results", 10),
    ("get_cases_from_run", 10),
    ("close_run", None),
]
TEST_UPLOAD_RESULTS_FLOW_IDS = [
    "failed_to_get_suite_id",
    "check_and_add_sections_failed",
    "check_and_add_test_cases_failed",
    "add_run_failed",
    "add_results_failed",
    "add_results_failed_existing_run",
    "add_missing_tests_to_run_failed",
    "close_run_failed",
]
TEST_GET_SUITE_ID_PROMPTS_USER_TEST_DATA = [
    (True, 10, 1, "Adding missing suites to project Fake project name.", False),
    (True, 10, -1, "Adding missing suites to project Fake project name.", True),
    (False, -1, -1, FAULT_MAPPING["no_user_agreement"].format(type="suite"), False),
]
TEST_GET_SUITE_ID_PROMPTS_USER_IDS = [
    "user agrees",
    "user agrees, fail to add suite",
    "used does not agree",
]
TEST_ADD_MISSING_SECTIONS_PROMPTS_USER_TEST_DATA = [
    (
        True,
        [10, 11, 12],
        "",
        [10, 11, 12],
        "Adding missing sections to the suite.",
        1,
    ),
    (
        True,
        [10, 11, 12],
        "Fail to add",
        [],
        "Adding missing sections to the suite.",
        -1,
    ),
    (
        False,
        [10, 11, 12],
        "",
        [],
        FAULT_MAPPING["no_user_agreement"].format(type="sections"),
        -1,
    ),
]
TEST_ADD_MISSING_SECTIONS_PROMPTS_USER_IDS = [
    "user agrees, sections added",
    "user agrees, sections not added",
    "used does not agree",
]
TEST_ADD_MISSING_TEST_CASES_PROMPTS_USER_TEST_DATA = [
    (
        True,
        [10, 11, 12],
        "",
        [10, 11, 12],
        "Adding missing test cases to the suite.",
        1,
        False,
    ),
    (
        True,
        [10, 11, 12],
        "Fail to add",
        [],
        "Adding missing test cases to the suite.",
        -1,
        False,
    ),
    (
        False,
        [10, 11, 12],
        "",
        [],
        FAULT_MAPPING["no_user_agreement"].format(type="test cases"),
        -1,
        True,
    ),
]
TEST_ADD_MISSING_TEST_CASES_PROMPTS_USER_IDS = [
    "user agrees, test cases added",
    "user agrees, test cases not added",
    "used does not agree",
]
TEST_GET_SUITE_ID_SINGLE_SUITE_MODE_BASELINES_TEST_DATA = [
    (([], "Could not get suites"), -1, -1, "Could not get suites"),
    (([10], ""), -1, 1, ""),
    (
        ([10, 11, 12], ""),
        -1,
        -1,
        FAULT_MAPPING["not_unique_suite_id_single_suite_baselines"].format(
            project_name="Fake project name"
        ),
    ),
]

TEST_GET_SUITE_ID_SINGLE_SUITE_MODE_BASELINES_IDS = [
    "get_suite_ids fails",
    "get_suite_ids returns one ID",
    "get_suite_ids returns more than one ID",
]

TEST_REVERT_FUNCTIONS_AND_EXPECTED = [
    (
        "delete_suite",
        [
            RevertMessages.run_deleted,
            RevertMessages.test_cases_deleted,
            RevertMessages.section_deleted,
            RevertMessages.suite_not_deleted.format(
                error="No permissions to delete suite."
            ),
        ],
        [],
    ),
    (
        "delete_sections",
        [
            RevertMessages.run_deleted,
            RevertMessages.test_cases_deleted,
            RevertMessages.section_not_deleted.format(
                error="No permissions to delete sections."
            ),
            RevertMessages.suite_deleted,
        ],
        [],
    ),
    (
        "delete_cases",
        [
            RevertMessages.run_deleted,
            RevertMessages.test_cases_not_deleted.format(
                error="No permissions to delete cases."
            ),
            RevertMessages.section_deleted,
            RevertMessages.suite_deleted,
        ],
        [],
    ),
    (
        "delete_run",
        [
            RevertMessages.run_not_deleted.format(
                error="No permissions to delete run."
            ),
            RevertMessages.test_cases_deleted,
            RevertMessages.section_deleted,
            RevertMessages.suite_deleted,
        ],
        [],
    ),
    (
        "update_run_with_test_cases",
        [
            RevertMessages.run_rollback_not_completed.format(
                error="Update run with test cases failed."
            ),
            RevertMessages.test_cases_deleted,
            RevertMessages.section_deleted,
            RevertMessages.suite_deleted,
        ],
        [1, 2],
    ),
]

TEST_REVERT_FUNCTIONS_IDS = [
    "unable_to_delete_suite",
    "unable_to_delete_sections",
    "unable_to_delete_cases",
    "unable_to_delete_run",
    "unable_to_update_run",
]

TEST_ADD_MISSING_TESTS_TO_RUN_PROMPTS_USER_TEST_DATA = [
    (True, "Updating test run. Adding missing test cases to the run.", 1),
    (True, "Updating test run. Adding missing test cases to the run.", 1),
    (False, FAULT_MAPPING["no_user_agreement_for_update_run"], -1),
]
TEST_ADD_MISSING_TESTS_TO_RUN_PROMPTS_USER_IDS = [
    "user agrees",
    "user agrees, fail to update run",
    "used does not agree",
]
