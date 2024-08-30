import json
from pathlib import Path
from trcli.data_classes.dataclass_testrail import TestRailSuite
from serde.json import from_json

file_json = open(Path(__file__).parent / "json/data_provider.json")
json_string = json.dumps(json.load(file_json))
test_input = from_json(TestRailSuite, json_string)

file_json = open(Path(__file__).parent / "json/update_case_result_single_with_id.json")
json_string = json.dumps(json.load(file_json))
test_input_single_result_with_id = from_json(TestRailSuite, json_string)

file_json = open(
    Path(__file__).parent / "json/update_case_result_single_without_id.json"
)
json_string = json.dumps(json.load(file_json))
test_input_single_result_without_id = from_json(TestRailSuite, json_string)

file_json = open(
    Path(__file__).parent / "json/data_provider_duplicated_case_names.json"
)
json_string = json.dumps(json.load(file_json))
test_input_duplicated_case_names = from_json(TestRailSuite, json_string)


post_suite_bodies = [{"name": "Suite1"}]

post_section_bodies = [
    {"name": "Skipped test", "suite_id": 123},
    {"name": "Passed test", "suite_id": 123},
]

post_cases_bodies = [
    {"section_id": 12345, "title": "testCase2", "custom_automation_id": "className.testCase2abc"}
]

post_run_bodies = {
    "description": "logging: True\ndebug: False",
    "name": "test run",
    "suite_id": 123,
    "case_ids": [60, 4],
    "milestone_id": None
}

post_run_full_body = {
    "description": "logging: True\ndebug: False",
    "name": "test run",
    "suite_id": 123,
    "case_ids": [60, 4],
    "milestone_id": None,
    "assignedto_id": 1,
    "include_all": True,
    "refs": "SAN-1, SAN-2"
}

post_results_for_cases_body = [
    {
        "results": [
            {
                "case_id": 60,
                "comment": "Type: pytest.skip\\nMessage: Please skip\\nText: skipped by user",
                "attachments": [],
                "status_id": 4,
                'custom_step_results': []
            },
            {"case_id": 1234567, "comment": "", "attachments": [], "status_id": 1, 'custom_step_results': []},
            {"case_id": 4, "comment": "", "attachments": [], "status_id": 1, 'custom_step_results': []},
        ]
    }
]

result_for_update_case = {
    "case_id": 10,
    "comment": "Type: pytest.skip\\nMessage: Please skip\\nText: skipped by user",
    "status_id": 4,
    "attachments": [],
}
