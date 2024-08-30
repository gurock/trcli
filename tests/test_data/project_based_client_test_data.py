from trcli.constants import FAULT_MAPPING

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
