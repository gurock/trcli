from junitparser.junitparser import Skipped, Failure
from dataclasses import asdict
from junitparser import TestCase, TestSuite, JUnitXml, Attr

from trcli.data_classes.dataclass_testrail import (
    TestCaseDataclass,
    PropertiesDataclass,
    TestSuiteDataclass,
)

TestCase.id = Attr("id")
TestSuite.id = Attr("id")
JUnitXml.id = Attr("id")


class TestDataClasses:
    def test_testrail_test_case(self):
        test_case_xml = TestCase(name="testing")
        test_case_xml.result = [Skipped("This test is skipped")]
        test_case_xml.id = "12345"
        test_case_xml.time = 10
        result = asdict(
            TestCaseDataclass(
                test_case_xml.name,
                test_case_xml.id,
                test_case_xml.time,
                test_case_xml.result,
            )
        )
        expected = {
            "case_id": "12345",
            "name": "testing",
            "time": 10.0,
            "section_id": None,
            "status_id": 4,
            "results": [
                {
                    "message": "This test is skipped",
                    "tag": "skipped",
                    "text": None,
                    "type": None,
                }
            ],
        }
        assert result == expected

    def test_testrail_properties(self):
        test_suite = TestSuite("TestSuite1")
        test_suite.add_property("test_prop1", "value_1")

        prop = list(test_suite.properties())[0]

        result = asdict(PropertiesDataclass(prop.name, prop.value))
        expected = {
            "name": "test_prop1",
            "value": "value_1",
            "description": "test_prop1: value_1",
        }
        assert result == expected

    def test_testrail_test_suite(self):
        test_suite = TestSuite("TestSuite1")
        test_suite.id = "1"
        test_suite.time = 15
        test_suite.add_property("test_prop1", "value_1")
        test_case_xml = TestCase(name="testing")
        test_case_xml.id = "12345"
        test_case_xml.time = 10
        failed_result = Failure("This test is failed")
        failed_result.text = "Error reading file on line 0"
        test_case_xml.result = [failed_result]
        test_suite.add_testcase(test_case_xml)

        prop = list(test_suite.properties())[0]
        result_prop = [PropertiesDataclass(prop.name, prop.value)]
        test_case = [
            TestCaseDataclass(
                test_case_xml.name,
                test_case_xml.id,
                test_case_xml.time,
                test_case_xml.result,
            )
        ]

        result = asdict(
            TestSuiteDataclass(
                test_suite.name, test_suite.id, test_suite.time, test_case, result_prop
            )
        )
        expected = {
            "name": "TestSuite1",
            "suite_id": "1",
            "time": 10.0,
            "properties": [
                {
                    "description": "test_prop1: value_1",
                    "name": "test_prop1",
                    "value": "value_1",
                }
            ],
            "testcases": [
                {
                    "case_id": "12345",
                    "name": "testing",
                    "time": 10.0,
                    "section_id": "1",
                    "status_id": 5,
                    "results": [
                        {
                            "message": "This test is failed",
                            "tag": "failure",
                            "text": "Error reading file on line 0",
                            "type": None,
                        }
                    ],
                }
            ],
        }
        assert result == expected
