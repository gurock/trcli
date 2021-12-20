from tests.test_data.data_provider_post import *
from trcli.data_providers.api_data_provider import ApiPostProvider
import pytest


@pytest.fixture(scope="function")
def post_data_provider():
    yield ApiPostProvider(env, test_input)


class TestApiDataProvider:
    def test_post_suite(self, post_data_provider):
        assert post_data_provider.add_suites_data() == post_suite_bodies

    def test_check_if_returns_items_witout_id(self, post_data_provider):

        assert len(post_data_provider.add_sections_data()["bodies"]) == 2
        assert len(post_data_provider.add_cases()["bodies"]) == 1
        assert len(post_data_provider.add_cases(return_all_items=True)["bodies"]) == 2

    def test_post_section(self, post_data_provider):
        updater = [
            {
                "suite_id": 123,
            }
        ]

        post_data_provider.update_data(suite_data=updater)
        assert post_data_provider.add_sections_data() == post_section_bodies

    def test_post_cases(self, post_data_provider):
        section_updater = [
            {"name": "Passed test", "section_id": 12345},
        ]
        post_data_provider.update_data(section_data=section_updater)
        assert post_data_provider.add_cases() == post_cases_bodies

    def test_post_run(self, post_data_provider):
        suite_updater = [
            {
                "suite_id": 123,
            }
        ]
        case_updater = [
            {
                "case_id": 1234567,
                "section_id": 12345,
                "title": "testCase2",
            }
        ]
        post_data_provider.update_data(suite_data=suite_updater, case_data=case_updater)
        assert post_data_provider.add_run() == post_run_bodies

    def test_post_results_for_cases(self, post_data_provider):
        case_updater = [
            {
                "case_id": 1234567,
                "section_id": 12345,
                "title": "testCase2",
            }
        ]
        post_data_provider.update_data(case_data=case_updater)

        assert (
            post_data_provider.add_results_for_cases() == post_results_for_cases_bodies
        )
