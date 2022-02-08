from tests.test_data.api_data_provider_test_data import *
from trcli.data_providers.api_data_provider import ApiDataProvider
import pytest


@pytest.fixture(scope="function")
def post_data_provider():
    yield ApiDataProvider(test_input)


@pytest.fixture(scope="function")
def post_data_provider_single_result_with_id():
    yield ApiDataProvider(test_input_single_result_with_id)


@pytest.fixture(scope="function")
def post_data_provider_single_result_without_id():
    yield ApiDataProvider(test_input_single_result_without_id)


@pytest.fixture(scope="function")
def post_data_provider_duplicated_case_names():
    yield ApiDataProvider(test_input_duplicated_case_names)


class TestApiDataProvider:
    @pytest.mark.data_provider
    def test_post_suite(self, post_data_provider):
        assert (
            post_data_provider.add_suites_data() == post_suite_bodies
        ), "Adding suite data doesn't match expected"

    @pytest.mark.data_provider
    def test_data_provider_returns_items_without_id(self, post_data_provider):
        """Check if data providers returns data only for items with missing IDs. Numbers correspond to data in
        test_data"""
        missing_sections = 2
        missing_cases = 1
        assert (
            len(post_data_provider.add_sections_data()["bodies"]) == missing_sections
        ), f"Adding suite data doesn't match expected {missing_sections}"
        assert (
            len(post_data_provider.add_cases()["bodies"]) == missing_cases
        ), f"Adding cases data doesn't match expected {missing_cases}"

    @pytest.mark.data_provider
    def test_post_section(self, post_data_provider):
        """Check body for adding sections"""
        suite_updater = [
            {
                "suite_id": 123,
            }
        ]

        post_data_provider.update_data(suite_data=suite_updater)
        assert (
            post_data_provider.add_sections_data() == post_section_bodies
        ), "Adding sections data doesn't match expected body"

    @pytest.mark.data_provider
    def test_post_cases(self, post_data_provider):
        """Check body for adding cases"""
        section_updater = [
            {"name": "Passed test", "section_id": 12345},
        ]
        post_data_provider.update_data(section_data=section_updater)
        assert (
            post_data_provider.add_cases() == post_cases_bodies
        ), "Adding cases data doesn't match expected body"

    @pytest.mark.data_provider
    def test_post_run(self, post_data_provider):
        """Check body for adding run"""
        suite_updater = [
            {
                "suite_id": 123,
            }
        ]
        post_data_provider.update_data(suite_data=suite_updater)
        assert (
            post_data_provider.add_run("test run") == post_run_bodies
        ), "Adding run data doesn't match expected body"

    @pytest.mark.data_provider
    def test_post_results_for_cases(self, post_data_provider):
        """Check body for adding results"""
        case_updater = [
            {
                "case_id": 1234567,
                "section_id": 12345,
                "title": "testCase2",
            }
        ]
        post_data_provider.update_data(case_data=case_updater)
        assert (
            post_data_provider.add_results_for_cases(bulk_size=10)
            == post_results_for_cases_body
        ), "Adding results data doesn't match expected body"

    @pytest.mark.data_provider
    def test_return_all_items_flag(self, post_data_provider):
        all_sections = 3
        all_cases = 3
        assert (
            len(post_data_provider.add_sections_data(return_all_items=True)["bodies"])
            == all_sections
        ), f"Adding cases with return_all_items flag should match {all_sections}"
        assert (
            len(post_data_provider.add_cases(return_all_items=True)["bodies"])
            == all_cases
        ), f"Adding cases with return_all_items flag should match {all_cases}"

    @pytest.mark.data_provider
    @pytest.mark.parametrize(
        "list_to_divide, bulk_size, expected_result",
        [
            ([1, 2, 3, 4, 5, 6], 3, [[1, 2, 3], [4, 5, 6]]),
            ([1, 2, 3, 4, 5, 6], 4, [[1, 2, 3, 4], [5, 6]]),
            ([1, 2, 3, 4, 5, 6], 6, [[1, 2, 3, 4, 5, 6]]),
            ([1, 2, 3, 4, 5, 6], 7, [[1, 2, 3, 4, 5, 6]]),
            ([], 2, []),
        ],
    )
    def test_divide_list_into_bulks(self, list_to_divide, bulk_size, expected_result):
        result = ApiDataProvider.divide_list_into_bulks(list_to_divide, bulk_size)
        assert (
            result == expected_result
        ), f"Expected: {expected_result} but got {result} instead."

    @pytest.mark.data_provider
    @pytest.mark.parametrize(
        "case_id, expected_result",
        [(1, None), (10, None)],
        ids=["Existing case id", "Not existing case id"],
    )
    def test_add_result_for_case_multiple_results(
        self, case_id, expected_result, post_data_provider
    ):
        result = post_data_provider.add_result_for_case(case_id)
        assert result is expected_result, f"Expected None as a result. But got {result}"

    @pytest.mark.data_provider
    def test_add_result_for_case_single_result_with_id(
        self, post_data_provider_single_result_with_id
    ):
        case_id = 1
        result = post_data_provider_single_result_with_id.add_result_for_case(case_id)
        assert result is None, f"Expected None as a result. But got {result}"

        case_id = 10
        result = post_data_provider_single_result_with_id.add_result_for_case(case_id)
        assert (
            result == result_for_update_case
        ), f"Expected None as a result. But got {result}"

    @pytest.mark.data_provider
    def test_add_result_for_case_single_result_without_id(
        self, post_data_provider_single_result_without_id
    ):
        case_id = 10
        result = post_data_provider_single_result_without_id.add_result_for_case(
            case_id
        )
        assert (
            result == result_for_update_case
        ), f"Expected None as a result. But got {result}"

    @pytest.mark.data_provider
    def test_check_for_case_names_duplicates_found(
        self, post_data_provider_duplicated_case_names
    ):
        result = (
            post_data_provider_duplicated_case_names.check_for_case_names_duplicates()
        )

        assert result, "Expected True as a result."

    @pytest.mark.data_provider
    def test_check_for_case_names_duplicates_not_found(self, post_data_provider):
        result = post_data_provider.check_for_case_names_duplicates()

        assert not result, "Expected False as a result."

    @pytest.mark.data_provider
    @pytest.mark.parametrize(
        "input, expected_result",
        UPDATE_RUN_RETURNS_IDS_LIST_TEST_DATA,
        ids=UPDATE_RUN_RETURNS_IDS_LIST_TEST_IDS,
    )
    def test_update_run_returns_ids_list(
        self, input, expected_result, post_data_provider
    ):
        """Check list of ids will be returned when providing response add case response to
        update_run"""
        result = post_data_provider.update_run(input)

        assert (
            result == expected_result
        ), "Expected {expected_result} as a result but got {result} instead."
