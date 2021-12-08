from trcli.data_classes.dataclass_testrail import (
    SuitesDataclass,
    TestSuiteDataclass,
    TestCaseDataclass,
    PropertiesDataclass,
)
from junitparser import Skipped, Failure, Error


class Environment:
    def __init__(self):
        self.file = "File.xml"
        self.project = "Project 1"
        self.project_id = "3"
        self.title = "Test run title"
        self.suite_id = "Suite id 1"
        self.run_id = "run id 1"
        self.case_id = [66, 77, 88]


env = Environment()
failed_result = Failure("This test is failed")
failed_result.text = "Error reading file on line 0"

skipped_result = Skipped("This test is skipped")
skipped_result.text = "skipped by user"

error_result = Error("Unbable to run test - error")
error_result.text = "Error in test setup line 10"

test_input = SuitesDataclass(
    name="Suites1",
    id=1,
    time="10",
    testsuites=[
        TestSuiteDataclass(
            name="TestSuite1",
            suite_id=2,
            time="5",
            testcases=[
                TestCaseDataclass(
                    name="testcase1",
                    case_id=3,
                    time="5",
                    results=[],
                ),
            ],
            properties=[
                PropertiesDataclass("logging", "true"),
                PropertiesDataclass("debug", "false"),
            ],
        ),
        TestSuiteDataclass(
            name="TestSuite2",
            suite_id=4,
            time="5",
            testcases=[
                TestCaseDataclass(
                    name="testcase21_skipped",
                    case_id=5,
                    time="5",
                    results=[skipped_result],
                ),
                TestCaseDataclass(
                    name="testcase22_failed",
                    case_id=6,
                    time="5",
                    results=[failed_result],
                ),
                TestCaseDataclass(
                    name="testcase23_error",
                    case_id=7,
                    time="5",
                    results=[error_result],
                ),
            ],
        ),
    ],
)

post_suite_bodies = {
    "bodies": [{"name": "Suites1", "description": "Suites1 imported from File.xml"}]
}

post_section_bodies = {
    "bodies": [
        {"suite_id": "1", "name": "TestSuite1"},
        {"suite_id": "1", "name": "TestSuite2"},
    ]
}

post_cases_bodies = {
    "bodies": [
        {"section_id": "2", "title": "testcase1"},
        {"section_id": "4", "title": "testcase21_skipped"},
        {"section_id": "4", "title": "testcase22_failed"},
        {"section_id": "4", "title": "testcase23_error"},
    ]
}

post_run_bodies = {
    "bodies": [
        {
            "suite_id": "1",
            "description": "[logging: true, debug: false]",
            "case_ids": [3],
        },
        {"suite_id": "1", "description": "[]", "case_ids": [5, 6, 7]},
    ]
}


post_results_for_cases_bodies = {
    "run_id": "run id 1",
    "bodies": {
        "results": [
            {"case_id": 3, "status_id": 1, "comment": ""},
            {"case_id": 5, "status_id": 4, "comment": ""},
            {"case_id": 6, "status_id": 5, "comment": ""},
            {"case_id": 7, "status_id": 5, "comment": ""},
        ]
    },
}
