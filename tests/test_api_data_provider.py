from tests.test_data.data_provider_post import *
from trcli.data_providers.api_data_provider import ApiPostProvider


class TestApiDataProvider:
    def test_post_suite(self):
        result = ApiPostProvider(env, test_input).suite
        print(result)
        assert result == post_suite_bodies

    def test_post_section(self):
        result = ApiPostProvider(env, test_input).sections
        assert result == post_section_bodies

    def test_post_cases(self):
        result = ApiPostProvider(env, test_input).cases
        assert result == post_cases_bodies

    def test_post_run(self):
        result = ApiPostProvider(env, test_input).run
        assert result == post_run_bodies

    def test_post_results_for_cases(self):
        result = ApiPostProvider(env, test_input).results_for_cases
        assert result == post_results_for_cases_bodies
