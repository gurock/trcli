import pytest
from trcli.api.api_response_verify import ApiResponseVerify
from trcli.data_classes.dataclass_testrail import TestRailSuite


@pytest.fixture(scope="function")
def api_response_verify():
    yield ApiResponseVerify(True)


class TestResponseVerify:
    @pytest.mark.verifier
    def test_verify_add_suite(self, api_response_verify: ApiResponseVerify):
        send_to_api = TestRailSuite("Suite1", description="Some Description")
        returned_from_api = {"name": "Suite1", "description": "Some Description"}
        assert api_response_verify.verify_returned_data(send_to_api, returned_from_api)

    @pytest.mark.verifier
    def test_verify_add_suite_not_equal(self, api_response_verify: ApiResponseVerify):
        send_to_api = TestRailSuite("Suite1", description="Some Description")
        returned_from_api = {"name": "Suite1", "description": "Some other description"}
        assert not api_response_verify.verify_returned_data(send_to_api, returned_from_api)

    @pytest.mark.verifier
    def test_verify_data_in_list(self, api_response_verify: ApiResponseVerify):
        added_data = [{}, {}]
        response_data = [{}, {}]

        assert api_response_verify.verify_returned_data_for_list(
            added_data, response_data
        ), "Added data and returned data should match"

        added_data = [{}, {}, {}]
        response_data = [{}, {}]

        assert not api_response_verify.verify_returned_data_for_list(
            added_data, response_data
        ), "Missing item in response data. Verification should fail."

        added_data = [{"Case_name": "Case1"}, {"Case_name": "Case2"}]
        response_data = [
            {"Case_name": "Case1", "id": 1},
            {"Case_name": "Case2", "id": 2},
        ]

        assert api_response_verify.verify_returned_data_for_list(
            added_data, response_data
        ), "Added data and returned data should match"

        added_data = [{"Case_name": "Case1"}, {"Case_name": "Case2"}]
        response_data = [
            {"Case_name": "Case1", "id": 1},
            {"Case_name": "Case44", "id": 44},
        ]

        assert not api_response_verify.verify_returned_data_for_list(
            added_data, response_data
        ), "Missing item in response data. Verification should fail."

    @pytest.mark.verifier
    @pytest.mark.parametrize(
        "input_data_estimate, response_data_estimate",
        [
            ({"estimate": "1m 40s"}, {"estimate": "1m 40s"}),
            ({"estimate": "1m 60s"}, {"estimate": "2m"}),
            ({"estimate": "120s"}, {"estimate": "2m"}),
            ({"estimate": "36000s"}, {"estimate": "10h"}),
            ({"time": "2m"}, {"time": "2m"}),
        ],
    )
    @pytest.mark.verifier
    def test_verify_estimate(
        self,
        api_response_verify: ApiResponseVerify,
        input_data_estimate: dict,
        response_data_estimate: dict,
    ):

        assert api_response_verify.verify_returned_data(
            input_data_estimate, response_data_estimate
        ), "Added data and returned data should match"

    @pytest.mark.verifier
    def test_verify_returned_data_missing_key_fails_gracefully(self, api_response_verify: ApiResponseVerify):
        """
        A key present in added_data but entirely absent from returned_data (e.g. because
        TestRail stored/returned a custom field under a different name than expected, such
        as the automation_id field name variants) must be treated as a verification failure
        rather than raising a KeyError.
        """
        added_data = {"custom_automation_id": "some.test.id", "title": "Case1"}
        returned_data = {"custom_case_automation_id": "some.test.id", "title": "Case1"}

        assert not api_response_verify.verify_returned_data(
            added_data, returned_data
        ), "A field missing from the response should fail verification, not raise."

    @pytest.mark.verifier
    @pytest.mark.parametrize(
        "input_data_estimate, response_data_estimate",
        [
            ({"description": ""}, {"description": None}),
            ({"description": None}, {"description": ""}),
            ({"comment": ""}, {"comment": None}),
            ({"comment": None}, {"comment": ""}),
        ],
    )
    def test_verify_strings(
        self,
        api_response_verify: ApiResponseVerify,
        input_data_estimate: dict,
        response_data_estimate: dict,
    ):

        assert api_response_verify.verify_returned_data(
            input_data_estimate, response_data_estimate
        ), "Added data and returned data should match"
