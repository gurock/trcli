from typing import List
from trcli.data_classes.dataclass_testrail import TestRailSuite
from trcli.cli import Environment


class ApiDataProvider:
    """
    ApiPostProvider is a place where you can convert TestRailSuite dataclass to bodies for API requests
    """

    def __init__(self, env: Environment, suites_input: TestRailSuite):
        self.env_input = env
        self.suites_input = suites_input
        self.filename = env.file

    def add_suites_data(self):
        """Return list of bodies for adding suites"""
        return {
            "bodies": [{"name": f"{self.suites_input.name}"}],
        }

    def add_sections_data(self, return_all_items=False):
        """Return list of bodies for adding sections.
        The ID of the test suite (ignored if the project is operating in single suite mode, required otherwise)
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
        """Return list of bodies for adding test cases."""
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

    def add_run(self, run_name: str):
        """Return body for adding a run."""
        properties = [
            str(prop)
            for section in self.suites_input.testsections
            for prop in section.properties
        ]
        return {
            "name": run_name,
            "suite_id": f"{self.suites_input.suite_id}",
            "description": f"{' '.join(properties)}",
        }

    def add_results_for_cases(self):
        """Return bodies for adding results for cases. Returns bodies for results that already have case ID."""
        testcases = [sections.testcases for sections in self.suites_input.testsections]
        return {
            "results": [
                {
                    "case_id": case.case_id,
                    "status_id": case.result.status_id,
                    "comment": f"{case.result.comment}",
                }
                for sublist in testcases
                for case in sublist
                if case.case_id is not None
            ],
        }

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
        """suite_data comes from add_suite API response
        example:
            {
                "suite_id": 123,
            }

        """
        self.suites_input.suite_id = suite_data[0]["suite_id"]
        for section in self.suites_input.testsections:
            section.suite_id = self.suites_input.suite_id

    def __update_section_data(self, section_data: List[dict]):
        """section_data comes from add_section API response
        example:
            {
            "name": "Passed test",
             "section_id": 12345
            }

        """
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
        """case_data comes from add_case API response
        example:
            {
                "case_id": 1,
                "section_id": 1
                "title": "testCase1",
            }

        """
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
