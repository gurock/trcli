from typing import List
from trcli.data_classes.dataclass_testrail import TestRailSuite
from serde.json import to_dict


class ApiDataProvider:
    """
    ApiPostProvider is a place where you can convert TestRailSuite dataclass to bodies for API requests
    """

    def __init__(self, suites_input: TestRailSuite):
        self.suites_input = suites_input

    def add_suites_data(self):
        """Return list of bodies for adding suites"""
        return {
            "bodies": [to_dict(self.suites_input)],
        }

    def add_sections_data(self, return_all_items=False):
        """Return list of bodies for adding sections.
        The ID of the test suite (ignored if the project is operating in single suite mode, required otherwise)
        """
        return {
            "bodies": [
                to_dict(section)
                for section in self.suites_input.testsections
                if section.section_id is None or return_all_items
            ],
        }

    def add_cases(self, return_all_items=False):
        """Return list of bodies for adding test cases."""
        testcases = [sections.testcases for sections in self.suites_input.testsections]
        return {
            "bodies": [
                to_dict(case)
                for sublist in testcases
                for case in sublist
                if case.case_id is None or return_all_items
            ],
        }

    def add_run(self, run_name: str, case_ids=None):
        """Return body for adding a run."""
        if case_ids is None:
            case_ids = [
                int(case)
                for section in self.suites_input.testsections
                for case in section.testcases
                if int(case) > 0
            ]
        properties = [
            str(prop)
            for section in self.suites_input.testsections
            for prop in section.properties
            if prop.description is not None
        ]
        return {
            "name": run_name,
            "suite_id": self.suites_input.suite_id,
            "description": f"{' '.join(properties)}",
            "include_all": False,
            "case_ids": case_ids,
        }

    def add_result_for_case(self, case_id):
        """Return body for adding result for case with case_id."""
        results = []

        testcases = [sections.testcases for sections in self.suites_input.testsections]
        cases = [case for sublist in testcases for case in sublist]

        if len(cases) == 1:
            case_id_from_file = cases[0].case_id
            result = to_dict(cases[0].result)
            if case_id_from_file is None or case_id_from_file == case_id:
                result["case_id"] = case_id
                results = [result]
            else:
                results = []
        else:
            results = []
        return results[0] if results else None

    def add_results_for_cases(self, bulk_size):
        """Return bodies for adding results for cases. Returns bodies for results that already have case ID."""
        testcases = [sections.testcases for sections in self.suites_input.testsections]

        result_bulks = ApiDataProvider.divide_list_into_bulks(
            [
                to_dict(case.result)
                for sublist in testcases
                for case in sublist
                if case.case_id is not None
            ],
            bulk_size=bulk_size,
        )
        return [{"results": result_bulk} for result_bulk in result_bulks]

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

    def check_section_names_duplicates(self):
        """
        Check if section names in result xml file are duplicated.
        """
        sections_names = [sections.name for sections in self.suites_input.testsections]

        if len(sections_names) == len(set(sections_names)):
            return False
        else:
            return True

    def check_for_case_names_duplicates(self):
        """
        Check if cases names in result xml file are duplicated.
        """
        testcases = [sections.testcases for sections in self.suites_input.testsections]
        cases = [case for sublist in testcases for case in sublist]
        cases_names = [case.title for case in cases]

        if len(cases) == len(set(cases_names)):
            return False
        else:
            return True

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
                (
                    section
                    for section in self.suites_input.testsections
                    if section["name"] == section_updater["name"]
                ),
                None,
            )
            if matched_section is not None:
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
                (
                    case
                    for sublist in testcases
                    for case in sublist
                    if case["title"] == case_updater["title"]
                ),
                None,
            )
            if matched_case is not None:
                matched_case.case_id = case_updater["case_id"]
                matched_case.result.case_id = case_updater["case_id"]
                matched_case.section_id = case_updater["section_id"]

    @staticmethod
    def divide_list_into_bulks(input_list: List, bulk_size: int) -> List:
        return [
            input_list[i : i + bulk_size] for i in range(0, len(input_list), bulk_size)
        ]
