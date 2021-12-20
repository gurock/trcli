from serde.json import from_json, to_json
from typing import List
from trcli.data_classes.dataclass_testrail import TestRailSuite


class ApiPostProvider:
    def __init__(self, env, suites_input: TestRailSuite):
        self.env_input = env
        self.suites_input = suites_input
        self.filename = env.file

    def add_suites_data(self):
        """Return ID of project and list of bodies for adding suites"""
        return {
            "bodies": [{"name": f"{self.suites_input.name}"}],
        }

    def add_sections_data(self, return_all_items=False):
        """Return ID of project and list of bodies for adding suites
        project_id - The ID of the project
        description - The description of the section
        suite_id - The ID of the test suite (ignored if the project is operating in single suite mode, required otherwise)
        """
        return {
            "bodies": [
                {
                    "suite_id": f"{section.suite_id}",
                    "name": f"{section.name}",
                }
                for section in self.suites_input.testsections
                if section.section_id is None or return_all_items
            ],
        }

    def add_cases(self, return_all_items=False):
        """
        section_id - The ID of the section the test case should be added to
        title - string The title of the test case
        """
        testcases = [sections.testcases for sections in self.suites_input.testsections]
        return {
            "bodies": [
                {
                    "section_id": f"{case.section_id}",
                    "title": f"{case.title}",
                }
                for sublist in testcases
                for case in sublist
                if case.case_id is None or return_all_items
            ],
        }

    def add_run(self):
        """
        project_id - The ID of the project the test run should be added to
        suite_id - The ID of the test suite for the test run (optional if the project is operating in single suite mode, required otherwise)
        case_ids - An array of case IDs for the custom case selection
        """
        return {
            "bodies": [
                {
                    "suite_id": f"{section.suite_id}",
                    "description": f"{str(section.properties)}",
                    "case_ids": [*map(int, section.testcases)],
                }
                for section in self.suites_input.testsections
            ],
        }

    def add_results_for_cases(self):
        """
        run_id - The ID of the test run the results should be added to
        """
        testcases = [sections.testcases for sections in self.suites_input.testsections]
        return {
            "run_id": self.env_input.run_id,
            "bodies": {
                "results": [
                    {
                        "case_id": case.case_id,
                        "status_id": case.result.status_id,
                        "comment": "",
                    }
                    for sublist in testcases
                    for case in sublist
                ],
            },
        }

    def close_run(self):
        """
        run_id - The ID of the test run
        """
        return {"run_id": self.env_input.run_id}

    def update_data(
        self,
        suite_data: List[dict] = None,
        section_data: List[dict] = None,
        case_data: List[dict] = None,
    ):
        """Here you can provide responses from service after creating resources.
        This way TestRailSuite data will be updated by ID's of new created resources.
        """
        if suite_data is not None:
            self.__update_suite_data(suite_data)
        if section_data is not None:
            self.__update_section_data(section_data)
        if case_data is not None:
            self.__update_case_data(case_data)

    def __update_suite_data(self, suite_data: List[dict]):
        self.suites_input.suite_id = suite_data[0]["suite_id"]
        for section in self.suites_input.testsections:
            section.suite_id = self.suites_input.suite_id

    def __update_section_data(self, section_data: List[dict]):
        for section_updater in section_data:
            matched_section = next(
                section
                for section in self.suites_input.testsections
                if section["name"] == section_updater["name"]
            )
            matched_section.section_id = section_updater["section_id"]
            for case in matched_section.testcases:
                case.section_id = section_updater["section_id"]

    def __update_case_data(self, case_data: List[dict]):
        testcases = [sections.testcases for sections in self.suites_input.testsections]
        for case_updater in case_data:
            matched_case = next(
                case
                for sublist in testcases
                for case in sublist
                if case["title"] == case_updater["title"]
            )
            matched_case.case_id = case_updater["case_id"]
            matched_case.section_id = case_updater["section_id"]
