from dataclasses import asdict

from trcli.data_classes.dataclass_testrail import SuitesDataclass


class ApiPostProvider:
    def __init__(self, env, suites_input: SuitesDataclass):
        self.env_input = env
        self.suites_input = suites_input
        self.filename = env.file
        self.suite = self.add_suites_data()
        self.sections = self.add_sections_data()
        self.cases = self.add_cases()
        self.run = self.add_run()
        self.results_for_cases = self.add_results_for_cases()

    def add_suites_data(self):
        """Return ID of project and list of bodies for adding suites"""
        return {
            "bodies": [
                {
                    "name": f"{self.suites_input.name}",
                    "description": f"{self.suites_input.name} imported from {self.filename}",
                }
            ],
        }

    def add_sections_data(self):
        """Return ID of project and list of bodies for adding suites
        project_id - The ID of the project
        description - The description of the section
        suite_id - The ID of the test suite (ignored if the project is operating in single suite mode, required otherwise)
        """
        return {
            "bodies": [
                {
                    "suite_id": f"{self.suites_input.id}",
                    "name": f"{section.name}",
                }
                for section in self.suites_input.testsuites
            ],
        }

    def add_cases(self):
        """
        section_id - The ID of the section the test case should be added to
        title - string The title of the test case
        """
        sections = [sections.testcases for sections in self.suites_input.testsuites]
        return {
            "bodies": [
                {
                    "section_id": f"{item.section_id}",
                    "title": f"{item.name}",
                }
                for sublist in sections
                for item in sublist
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
                    "suite_id": f"{self.suites_input.id}",
                    "description": f"{str(section.properties)}",
                    "case_ids": [*map(int, section.testcases)],
                }
                for section in self.suites_input.testsuites
            ],
        }

    def add_results_for_cases(self):
        """
        run_id - The ID of the test run the results should be added to
        """
        sections = [sections.testcases for sections in self.suites_input.testsuites]
        return {
            "run_id": self.env_input.run_id,
            "bodies": {
                "results": [
                    {
                        "case_id": item.case_id,
                        "status_id": item.status_id,
                        "comment": "",
                    }
                    for sublist in sections
                    for item in sublist
                ],
            },
        }

    def close_run(self):
        """
        run_id - The ID of the test run
        """
        return {"run_id": self.env_input.run_id}
