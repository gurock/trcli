from tests.test_data.data_provider_post import *
from trcli.data_providers.api_data_provider import ApiPostProvider
import pytest


@pytest.fixture()
def post_data_provider():
    yield ApiPostProvider(env, test_input)


class TestApiDataProvider:
    def test_post_suite(self, post_data_provider):
        assert post_data_provider.suite == post_suite_bodies

    def test_post_section(self, post_data_provider):
        assert post_data_provider.sections == post_section_bodies

    def test_post_cases(self, post_data_provider):
        assert post_data_provider.cases == post_cases_bodies

    def test_post_run(self, post_data_provider):
        assert post_data_provider.run == post_run_bodies

    def test_post_results_for_cases(self, post_data_provider):
        assert post_data_provider.results_for_cases == post_results_for_cases_bodies
