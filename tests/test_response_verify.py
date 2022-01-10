import pytest
from trcli.api.api_response_verify import ApiResponseVerify
from trcli.data_classes.dataclass_testrail import TestRailSuite


@pytest.fixture(scope="function")
def api_response_verify():
    yield ApiResponseVerify(True)


class TestResponseVerify:
    def test_verify_add_suite(self, api_response_verify: ApiResponseVerify):
        send_to_api = TestRailSuite("Suite1", description="Some Description")
        returned_from_api = {"name": "Suite1", "description": "Some Description"}
        assert api_response_verify.verify_returned_data(send_to_api, returned_from_api)

    def test_verify_add_suite_not_equal(self, api_response_verify: ApiResponseVerify):
        send_to_api = TestRailSuite("Suite1", description="Some Description")
        returned_from_api = {"name": "Suite1", "description": "Some other description"}
        assert not api_response_verify.verify_returned_data(
            send_to_api, returned_from_api
        )

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
