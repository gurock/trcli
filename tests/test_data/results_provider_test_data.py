from trcli.constants import FAULT_MAPPING, RevertMessages

TEST_UPLOAD_RESULTS_FLOW_TEST_DATA = [
    "get_suite_id",
    "check_for_missing_sections_and_add",
    "check_for_missing_test_cases_and_add",
    "add_run",
    "add_results",
    "close_run",
]
TEST_UPLOAD_RESULTS_FLOW_IDS = [
    "failed_to_get_suite_id",
    "check_and_add_sections_failed",
    "check_and_add_test_cases_failed",
    "add_run_failed",
    "add_results_failed",
    "close_run_failed",
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
    ),
    (
        True,
        [10, 11, 12],
        "Fail to add",
        [],
        "Adding missing test cases to the suite.",
        -1,
    ),
    (
        False,
        [10, 11, 12],
        "",
        [],
        FAULT_MAPPING["no_user_agreement"].format(type="test cases"),
        -1,
    ),
]
TEST_ADD_MISSING_TEST_CASES_PROMPTS_USER_IDS = [
    "user agrees, test cases added",
    "user agrees, test cases not added",
    "used does not agree",
]

TEST_REVERT_FUNCTIONS_AND_EXPECTED = [
    (
        "delete_suite",
        [
            RevertMessages.RUN_DELETED,
            RevertMessages.TEST_CASES_DELETED,
            RevertMessages.SECTION_DELETED,
            RevertMessages.SUITE_NOT_DELETED_FF_SUITE_ID_ERROR.format(
                error="No permissions to delete suite."
            ),
        ],
    ),
    (
        "delete_sections",
        [
            RevertMessages.RUN_DELETED,
            RevertMessages.TEST_CASES_DELETED,
            RevertMessages.SECTION_NOT_DELETED_FF_SECTION_ID_ERROR.format(
                error="No permissions to delete sections."
            ),
            RevertMessages.SUITE_DELETED,
        ],
    ),
    (
        "delete_cases",
        [
            RevertMessages.RUN_DELETED,
            RevertMessages.TEST_CASES_NOT_DELETED_F_ERROR.format(
                error="No permissions to delete cases."
            ),
            RevertMessages.SECTION_DELETED,
            RevertMessages.SUITE_DELETED,
        ],
    ),
    (
        "delete_run",
        [
            RevertMessages.RUN_NOT_DELETED_FF_RUN_ID_ERROR.format(
                error="No permissions to delete run."
            ),
            RevertMessages.TEST_CASES_DELETED,
            RevertMessages.SECTION_DELETED,
            RevertMessages.SUITE_DELETED,
        ],
    ),
]

TEST_REVERT_FUNCTIONS_IDS = [
    "unable_to_delete_suite",
    "unable_to_delete_sections",
    "unable_to_delete_cases",
    "unable_to_delete_run",
]

TEST_REVERT_FUNCTIONS_AND_EXPECTED_EXISTING_SUITE = [
    (   
        "delete_sections",
        [
            RevertMessages.RUN_DELETED,
            RevertMessages.TEST_CASES_DELETED,
            RevertMessages.SECTION_NOT_DELETED_FF_SECTION_ID_ERROR.format(
                error="No permissions to delete sections."
            ),
        ],
    ),
    (
        "delete_cases",
        [
            RevertMessages.RUN_DELETED,
            RevertMessages.TEST_CASES_NOT_DELETED_F_ERROR.format(
                error="No permissions to delete cases."
            ),
            RevertMessages.SECTION_DELETED,
        ],
    ),
    (
        "delete_run",
        [
            RevertMessages.RUN_NOT_DELETED_FF_RUN_ID_ERROR.format(
                error="No permissions to delete run."
            ),
            RevertMessages.TEST_CASES_DELETED,
            RevertMessages.SECTION_DELETED,
        ],
    ),
]

TEST_REVERT_FUNCTIONS_IDS_EXISTING_SUITE = [
    "unable_to_delete_sections",
    "unable_to_delete_cases",
    "unable_to_delete_run",
]
