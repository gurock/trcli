import json
import pytest
from junitparser import Element
from tests.test_data.dataclass_creation import *
from trcli.data_classes.dataclass_testrail import TestRailResult, TestRailProperty
from serde.json import to_json


class TestDataClassCreation:
    @pytest.mark.parametrize(
        "junit_test_result, expected_result",
        [
            ([FAILED_RESULT_INPUT], FAILED_EXPECTED),
            ([SKIPPED_RESULT_INPUT], SKIPPED_EXPECTED),
            ([SKIPPED_RESULT_EMPTY_INPUT], SKIPPED_EMPTY_EXPECTED),
            ([ERROR_RESULT_INPUT], ERROR_EXPECTED),
            ([], PASSED_EXPECTED),
        ],
        ids=[
            "Test result with failure",
            "Test result with skipped",
            "Test result with skipped but no messages",
            "Test result with error",
            "Test result passed",
        ],
    )
    def test_create_test_result_from_junit_element(
        self, junit_test_result: Element, expected_result: dict
    ):
        result_dataclass = TestRailResult(1, junit_result_unparsed=junit_test_result)
        result_json = json.loads(to_json(result_dataclass))
        assert (
            result_json["status_id"] == expected_result["status_id"]
        ), "calculated status id doesn't mach expected id"
        assert (
            result_json["comment"] == expected_result["comment"]
        ), "Joined comment doesn't mach expected comment"

    def test_create_property(self):
        result_dataclass = TestRailProperty("Some property", "True")
        result_json = json.loads(to_json(result_dataclass))
        assert (
            result_json["description"] == "Some property: True"
        ), "Property description doesn't mach expected values"
