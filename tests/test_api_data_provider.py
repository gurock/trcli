from tests.test_data.api_data_provider_test_data import *
from trcli.data_providers.api_data_provider import ApiDataProvider
import pytest


@pytest.fixture(scope="function")
def post_data_provider():
    env = Environment()
    yield ApiDataProvider(env, test_input)


class TestApiDataProvider:
    def test_post_suite(self, post_data_provider):
        assert (
            post_data_provider.add_suites_data() == post_suite_bodies
        ), "Adding suite data doesn't match expected"

    def test_check_if_returns_items_witout_id(self, post_data_provider):
        """Check if data providers returns data only for items with missing IDs. Numbers correspond to data in
        test_data"""
        missing_sections = 2
        missing_cases = 1
        all_cases = 2
        assert (
            len(post_data_provider.add_sections_data()["bodies"]) == missing_sections
        ), f"Adding suite data doesn't match expected {missing_sections}"
        assert (
            len(post_data_provider.add_cases()["bodies"]) == 1
        ), f"Adding cases data doesn't match expected {missing_cases}"
        assert (
            len(post_data_provider.add_cases(return_all_items=True)["bodies"]) == 2
        ), f"Adding cases with return_all_items flag should match {all_cases}"

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

    def test_post_cases(self, post_data_provider):
        """Check body for adding cases"""
        section_updater = [
            {"name": "Passed test", "section_id": 12345},
        ]
        post_data_provider.update_data(section_data=section_updater)
        assert (
            post_data_provider.add_cases() == post_cases_bodies
        ), "Adding cases data doesn't match expected body"

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
            post_data_provider.add_results_for_cases() == post_results_for_cases_body
        ), "Adding results data doesn't match expected body"
