import json
import pytest
from junitparser import Element
from tests.test_data.dataclass_creation import *
from trcli.data_classes.dataclass_testrail import (
    TestRailResult,
    TestRailProperty,
    TestRailSuite,
    TestRailCase,
    TestRailSection,
)
from serde.json import to_json
from trcli.data_classes.validation_exception import ValidationException


class TestDataClassCreation:
    @pytest.mark.dataclass
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
    @pytest.mark.dataclass
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

    @pytest.mark.dataclass
    def test_create_property(self):
        result_dataclass = TestRailProperty("Some property", "True")
        result_json = json.loads(to_json(result_dataclass))
        assert (
            result_json["description"] == "Some property: True"
        ), "Property description doesn't mach expected values"

    @pytest.mark.dataclass
    def test_generate_suite_name(self, freezer):
        freezer.move_to("2020-01-10 01:00:00")
        suite = TestRailSuite(name=None, source="file.xml")
        assert suite.name == "file.xml 10-01-20 01:00:00", "Name not generated properly"

    @pytest.mark.dataclass
    @pytest.mark.parametrize(
        "input_time, output_time",
        [
            ("40", "40s"),
            ("119.99", "120s"),
            (0, None),
            (50.4, "50s"),
            (-100, None),
        ],
    )
    def test_elapsed_time_calc_in_testresult(self, input_time, output_time):
        test_result = TestRailResult(case_id=1, elapsed=input_time)
        assert test_result.elapsed == output_time, "Elapsed not parsed properly"

    @pytest.mark.dataclass
    def test_elapsed_time_calc_in_testresult_none(self):
        test_result = TestRailResult(case_id=1, elapsed=None)
        assert test_result.elapsed is None, "Elapsed is not None"
        assert "elapsed" not in to_json(
            test_result
        ), "Elapsed should be skipped by serde"

    @pytest.mark.dataclass
    def test_validation_error_for_case(self):
        with pytest.raises(ValidationException):
            TestRailCase(section_id=1, title="")

    @pytest.mark.dataclass
    def test_validation_error_for_section(self):
        with pytest.raises(ValidationException):
            TestRailSection(suite_id=1, name="")
