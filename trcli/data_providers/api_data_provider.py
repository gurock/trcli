from beartype.typing import List, Dict, Optional

from serde.json import to_dict

from trcli.data_classes.dataclass_testrail import TestRailSuite


class ApiDataProvider:
    """
    ApiDataProvider is a place where you can convert TestRailSuite dataclass to bodies for API requests
    """

    def __init__(
        self,
        suites_input: TestRailSuite,
        case_fields: dict = None,
        run_description: str = None,
        result_fields: dict = None,
        parent_section_id: int = None
    ):
        self.suites_input = suites_input
        self.case_fields = case_fields
        self.run_description = run_description
        self.result_fields = result_fields
        self.update_data([{"suite_id": self.suites_input.suite_id}])
        self.__update_parent_section(parent_section_id)

    def add_suites_data(self) -> list:
        """Return list of bodies for adding suites"""
        return [to_dict(self.suites_input)]

    def add_sections_data(self, return_all_items=False) -> list:
        """Return list of bodies for adding sections.
        The ID of the test suite (ignored if the project is operating in single suite mode, required otherwise)
        """
        return [
            to_dict(section)
            for section in self.suites_input.testsections
            if section.section_id is None or return_all_items
        ]

    def add_cases(self, return_all_items=False) -> list:
        """Return list of bodies for adding test cases."""
        testcases = [sections.testcases for sections in self.suites_input.testsections]
        bodies = []
        for sublist in testcases:
            for case in sublist:
                if case.case_id is None or return_all_items:
                    case.add_global_case_fields(self.case_fields)
                    bodies.append(case)
        return bodies

    def existing_cases(self):
        """Return list of bodies for existing test cases."""
        testcases = [sections.testcases for sections in self.suites_input.testsections]
        bodies = []
        for sublist in testcases:
            for case in sublist:
                if case.case_id is not None:
                    case.add_global_case_fields(self.case_fields)
                    bodies.append(case)
        return bodies

    def add_run(
            self,
            run_name: Optional[str],
            case_ids=None,
            milestone_id=None,
            assigned_to_id=None,
            include_all=None,
            refs=None,
    ):
        """Return body for adding or updating a run."""
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
        if self.run_description:
            properties.insert(0, f"{self.run_description}\n")
        body = {
            "suite_id": self.suites_input.suite_id,
            "description": "\n".join(properties),
            "milestone_id": milestone_id,
            "case_ids": case_ids
        }
        if include_all is not None:
            body["include_all"] = include_all
        if assigned_to_id is not None:
            body["assignedto_id"] = assigned_to_id
        if refs is not None:
            body["refs"] = refs
        if run_name is not None:
            body["name"] = run_name
        return body

    def add_results_for_cases(self, bulk_size):
        """Return bodies for adding results for cases. Returns bodies for results that already have case ID."""
        testcases = [sections.testcases for sections in self.suites_input.testsections]

        bodies = []

        for sublist in testcases:
            for case in sublist:
                if case.case_id is not None:
                    case.result.add_global_result_fields(self.result_fields)
                    bodies.append(case.result.to_dict())

        result_bulks = ApiDataProvider.divide_list_into_bulks(
            bodies,
            bulk_size=bulk_size,
        )
        return [{"results": result_bulk} for result_bulk in result_bulks]

    def update_data(
        self,
        suite_data: List[Dict] = None,
        section_data: List[Dict] = None,
        case_data: List[Dict] = None,
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

    def __update_suite_data(self, suite_data: List[Dict]):
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

    def __update_section_data(self, section_data: List[Dict]):
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

    def __update_parent_section(self, parent_section_id: int):
        for section in self.suites_input.testsections:
            section.parent_id = parent_section_id

    def __update_case_data(self, case_data: List[Dict]):
        """case_data comes from add_case API response
        example:
            {
                "case_id": 1,
                "section_id": 1
                "title": "testCase1",
                "custom_automation_id": "className.testCase1"
            }

        """
        testcases = [sections.testcases for sections in self.suites_input.testsections]
        for case_updater in case_data:
            matched_case = next(
                (
                    case
                    for sublist in testcases
                    for case in sublist
                    if case.custom_automation_id == case_updater["custom_automation_id"]
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
