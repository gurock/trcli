import json
import pytest
from junitparser import Element
from tests.test_data.dataclass_creation import *
from trcli.data_classes.dataclass_testrail import (
    TestRailResult,
    TestRailProperty,
    TestRailSuite,
    TestRailCase,
)
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

    def test_generate_suite_name(self, freezer):
        freezer.move_to("2020-01-10")
        suite = TestRailSuite(name=None, source="file.xml")
        assert suite.name == "file.xml 10-01-20 01:00:00", "Name not generated properly"

    @pytest.mark.parametrize(
        "input_time, output_time",
        [
            ("1m 40s", "1m 40s"),
            ("40s", "40s"),
            ("119.99", "2m 0s"),
            (0, "0m 0s"),
            (50.4, "0m 50s"),
            (-100, None),
            ("181.0", "3m 1s"),
        ],
    )
    def test_estimated_time_calc_in_testcase(self, input_time, output_time):
        test_case = TestRailCase(section_id=1, title="Some Title", estimate=input_time)
        assert test_case.estimate == output_time, "Estimate not parsed properly"

    def test_estimated_time_calc_in_testcase_none(self):
        test_case = TestRailCase(section_id=1, title="Some Title", estimate=None)
        assert test_case.estimate == None, "Estimate is not None"
        assert "estimate" not in to_json(
            test_case
        ), "Estimate should be skipped by serde"
