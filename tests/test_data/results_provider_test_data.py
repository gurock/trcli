from trcli.constants import FAULT_MAPPING

TEST_UPLOAD_RESULTS_FLOW_TEST_DATA = [
    "get_suite_id_log_errors",
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
TEST_GET_SUITE_ID_LOG_ERRORS_PROMPTS_USER_TEST_DATA = [
    (True, 10, "Adding missing suites to project Fake project name.", False),
    (True, -1, "Adding missing suites to project Fake project name.", True),
    (False, -1, FAULT_MAPPING["no_user_agreement"].format(type="suite"), False),
]
TEST_GET_SUITE_ID_LOG_ERRORS_PROMPTS_USER_IDS = [
    "user agrees",
    "user agrees, fail to add suite",
    "used does not agree",
]
TEST_CHECK_FOR_MISSING_SECTIONS_PROMPTS_USER_TEST_DATA = [
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
TEST_CHECK_FOR_MISSING_SECTIONS_PROMPTS_USER_IDS = [
    "user agrees, sections added",
    "user agrees, sections not added",
    "used does not agree",
]
TEST_CHECK_FOR_MISSING_TEST_CASES_PROMPTS_USER_TEST_DATA = [
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
TEST_CHECK_FOR_MISSING_TEST_CATAS_PROMPTS_USER_IDS = [
    "user agrees, test cases added",
    "user agrees, test cases not added",
    "used does not agree",
]
TEST_GET_SUITE_ID_LOG_ERRORS_SINGLE_SUITE_MODE_BASELINES_TEST_DATA = [
    (([], "Could not get suites"), -1, "Could not get suites"),
    (([10], ""), 10, ""),
    (
        ([10, 11, 12], ""),
        -1,
        FAULT_MAPPING["not_unique_suite_id_single_suite_baselines"].format(
            project_name="Fake project name"
        ),
    ),
]

TEST_GET_SUITE_ID_LOG_ERRORS_SINGLE_SUITE_MODE_BASELINES_IDS = [
    "get_suite_ids fails",
    "get_suite_ids returns one ID",
    "get_suite_ids returns more than one ID",
]
