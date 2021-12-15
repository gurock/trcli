import json
from pathlib import Path
from trcli.data_classes.dataclass_testrail import TestRailSuite
from serde.json import from_json


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

file_json = open(Path(__file__).parent / "json/data_provider.json")
json_string = json.dumps(json.load(file_json))
test_input = from_json(TestRailSuite, json_string)


post_suite_bodies = {"bodies": [{"name": "Suite1"}]}

post_section_bodies = {
    "bodies": [
        {"name": "Skipped test", "suite_id": "123"},
        {"name": "Passed test", "suite_id": "123"},
    ]
}

post_cases_bodies = {
    "bodies": [
        {"section_id": "1234", "title": "testCase1"},
        {"section_id": "12345", "title": "testCase2"},
    ]
}

post_run_bodies = {
    "bodies": [
        {
            "case_ids": [666],
            "description": "[logging: True, debug: False]",
            "suite_id": "123",
        },
        {"case_ids": [777], "description": "[]", "suite_id": "123"},
    ]
}


post_results_for_cases_bodies = {
    "bodies": {
        "results": [
            {"case_id": "666", "comment": "", "status_id": 4},
            {"case_id": "777", "comment": "", "status_id": 1},
        ]
    },
    "run_id": "run id 1",
}
