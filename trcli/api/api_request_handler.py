from trcli.api.api_client import APIClient, APIClientResult
from trcli.cli import Environment
from trcli.api.api_response_verify import ApiResponseVerify
from trcli.data_classes.dataclass_testrail import TestRailSuite
from trcli.data_providers.api_data_provider import ApiDataProvider
from trcli.constants import ProjectErrors, FAULT_MAPPING
from typing import List
from dataclasses import dataclass


@dataclass
class ProjectData:
    project_id: int
    suite_mode: int
    error_message: str


class ApiRequestHandler:
    """Sends requests based on DataProvider bodies"""

    def __init__(
        self,
        environment: Environment,
        api_client: APIClient,
        suites_data: TestRailSuite,
        verify: bool = False,
    ):
        self.environment = environment
        self.client = api_client
        self.suffix = api_client.VERSION
        self.data_provider = ApiDataProvider(suites_data)
        self.suites_data_from_provider = self.data_provider.suites_input
        self.response_verifier = ApiResponseVerify(verify)

    def get_project_id(self, project_name: str) -> ProjectData:
        """
        Send get_projects with project name
        :project_name: Project name
        :returns: ProjectData
        """
        response = self.client.send_get("get_projects")
        if not response.error_message:
            available_projects = [
                project
                for project in response.response_text["projects"]
                if project["name"] == project_name
            ]
            if len(available_projects) == 1:
                return ProjectData(
                    project_id=int(available_projects[0]["id"]),
                    suite_mode=int(available_projects[0]["suite_mode"]),
                    error_message=response.error_message,
                )
            elif len(available_projects) > 1:
                return ProjectData(
                    project_id=ProjectErrors.multiple_project_same_name,
                    suite_mode=-1,
                    error_message=FAULT_MAPPING["more_than_one_project"],
                )
            else:
                return ProjectData(
                    project_id=ProjectErrors.not_existing_project,
                    suite_mode=-1,
                    error_message=f"{project_name} {FAULT_MAPPING['project_doesnt_exists']}",
                )
        else:
            return ProjectData(
                project_id=ProjectErrors.other_error,
                suite_mode=-1,
                error_message=response.error_message,
            )

    def check_suite_id(self, project_id: int) -> (bool, str):
        """
        Check if suite from DataProvider exist using get_suites endpoint
        :project_id: project id
        :returns: True if exists in suites. False if not.
        """
        suite_id = self.suites_data_from_provider.suite_id
        response = self.client.send_get(f"get_suites/{project_id}")
        if not response.error_message:
            available_suites = [suite["id"] for suite in response.response_text]
            return (
                (True, "")
                if suite_id in available_suites
                else (False, FAULT_MAPPING["missing_suite"].format(suite_id=suite_id))
            )
        else:
            return None, response.error_message

    def get_suite_ids(self, project_id: int) -> (List[int], str):
        """Get suite IDs for requested project_id.
        : project_id: project id
        : returns: tuple with list of suite ids and error string"""
        available_suites = []
        returned_resources = []
        error_message = ""
        response = self.client.send_get(f"get_suites/{project_id}")
        if not response.error_message:
            for suite in response.response_text:
                available_suites.append(suite["id"])
                returned_resources.append(
                    {
                        "suite_id": suite["id"],
                        "name": suite["name"],
                    }
                )
        else:
            error_message = response.error_message

        self.data_provider.update_data(suite_data=returned_resources) if len(
            returned_resources
        ) > 0 else "Update skipped"
        return available_suites, error_message

    def add_suites(self, project_id: int) -> (List[dict], str):
        """
        Adds suites that doesn't have ID's in DataProvider.
        Runs update_data in data_provider for successfully created resources.
        :project_id: project_id
        :returns: Tuple with list of dict created resources and error string.
        """
        add_suite_data = self.data_provider.add_suites_data()
        responses = []
        error_message = ""
        for body in add_suite_data["bodies"]:
            response = self.client.send_post(f"add_suite/{project_id}", body)
            if not response.error_message:
                responses.append(response)
                if not self.response_verifier.verify_returned_data(
                    body, response.response_text
                ):
                    responses.append(response)
                    error_message = FAULT_MAPPING["data_verification_error"]
                    break
            else:
                error_message = response.error_message
                break

        returned_resources = [
            {
                "suite_id": response.response_text["id"],
                "name": response.response_text["name"],
            }
            for response in responses
        ]
        self.data_provider.update_data(suite_data=returned_resources) if len(
            returned_resources
        ) > 0 else "Update skipped"
        return returned_resources, error_message

    def check_missing_section_ids(self, project_id: int) -> (List[int], str):
        """
        Check what section id's are missing in DataProvider.
        :project_id: project_id
        :returns: Tuple with list missing section ID and error string.
        """
        suite_id = self.suites_data_from_provider.suite_id
        sections = [
            section.section_id
            for section in self.suites_data_from_provider.testsections
        ]
        response = self.client.send_get(
            f"get_sections/{project_id}&suite_id={suite_id}"
        )
        if not response.error_message:
            return (
                list(
                    set(sections)
                    - set(
                        [
                            section.get("id")
                            for section in response.response_text["sections"]
                        ]
                    )
                ),
                response.error_message,
            )
        else:
            return [], response.error_message

    def add_sections(self, project_id: int) -> (List[dict], str):
        """
        Add sections that doesn't have ID in DataProvider.
        Runs update_data in data_provider for successfully created resources.
        :project_id: project_id
        :returns: Tuple with list of dict created resources and error string.
        """
        add_sections_data = self.data_provider.add_sections_data()
        responses = []
        error_message = ""
        for body in add_sections_data["bodies"]:
            response = self.client.send_post(f"add_section/{project_id}", body)
            if not response.error_message:
                responses.append(response)
                if not self.response_verifier.verify_returned_data(
                    body, response.response_text
                ):
                    responses.append(response)
                    error_message = FAULT_MAPPING["data_verification_error"]
                    break
            else:
                error_message = response.error_message
                break
        returned_resources = [
            {
                "section_id": response.response_text["id"],
                "suite_id": response.response_text["suite_id"],
                "name": response.response_text["name"],
            }
            for response in responses
        ]
        self.data_provider.update_data(section_data=returned_resources) if len(
            returned_resources
        ) > 0 else "Update skipped"
        return returned_resources, error_message

    def check_missing_test_cases_ids(self, project_id: int) -> (bool, str):
        """
        Check what test cases id's are missing in DataProvider.
        :project_id: project_id
        :returns: Tuple with list test case ID missing and error string.
        """
        suite_id = self.suites_data_from_provider.suite_id
        test_cases = [
            test_case["case_id"]
            for sections in self.suites_data_from_provider.testsections
            for test_case in sections.testcases
        ]

        returned_cases, error_message = self.__get_all_cases(project_id, suite_id)
        if not error_message:
            missing_cases = list(
                set(test_cases)
                - set([test_case.get("id") for test_case in returned_cases])
            )
            if any(missing_cases):
                return False, FAULT_MAPPING["unknown_test_case_id"]
            elif len(missing_cases) == 1:
                return True, error_message
            else:
                return False, error_message
        else:
            return False, error_message

    def add_cases(self) -> (List[dict], str):
        """
        Add cases that doesn't have ID in DataProvider.
        Runs update_data in data_provider for successfully created resources.
        :returns: Tuple with list of dict created resources and error string.
        """
        add_case_data = self.data_provider.add_cases()
        responses = []
        error_message = ""
        for body in add_case_data["bodies"]:
            response = self.client.send_post(f"add_case/{body.pop('section_id')}", body)
            if not response.error_message:
                responses.append(response)
                if not self.response_verifier.verify_returned_data(
                    body, response.response_text
                ):
                    responses.append(response)
                    error_message = FAULT_MAPPING["data_verification_error"]
                    break
            else:
                error_message = response.error_message
                break

        returned_resources = [
            {
                "case_id": response.response_text["id"],
                "section_id": response.response_text["section_id"],
                "title": response.response_text["title"],
            }
            for response in responses
        ]
        self.data_provider.update_data(case_data=returned_resources) if len(
            returned_resources
        ) > 0 else "Update skipped"
        return returned_resources, error_message

    def add_run(self, project_id: int, run_name: str) -> (List[dict], str):
        """
        Creates a new test run.
        :project_id: project_id
        :run_name: run name
        :returns: Tuple with run id and error string.
        """
        add_run_data = self.data_provider.add_run(run_name)
        response = self.client.send_post(f"add_run/{project_id}", add_run_data)
        if not response.error_message:
            if not self.response_verifier.verify_returned_data(
                add_run_data, response.response_text
            ):
                response.error_message = FAULT_MAPPING["data_verification_error"]
        return response.response_text.get("id"), response.error_message

    def add_results(self, run_id: int) -> (dict, str):
        """
        Adds one or more new test results.
        :run_id: run id
        :returns: Tuple with dict created resources and error string.
        """
        responses = []
        error_message = ""
        add_results_data_chunks = self.data_provider.add_results_for_cases(
            self.environment.batch_size
        )
        results_amount = sum(
            [len(results["results"]) for results in add_results_data_chunks]
        )

        with self.environment.get_progress_bar(results_amount) as progress_bar:
            for add_results_data in add_results_data_chunks:
                response = self.client.send_post(
                    f"add_results_for_cases/{run_id}", add_results_data
                )
                if not response.error_message:
                    responses.append(response.response_text)
                    progress_bar.update(len(add_results_data["results"]))
                else:
                    error_message = response.error_message
                    break
            else:
                progress_bar.set_postfix_str(s="Done.")
        return responses, error_message

    def close_run(self, run_id: int) -> (dict, str):
        """
        Closes an existing test run and archives its tests & results.
        :run_id: run id
        :returns: Tuple with dict created resources and error string.
        """
        body = {"run_id": run_id}
        response = self.client.send_post(f"close_run/{run_id}", body)
        return response.response_text, response.error_message

    def __get_all_cases(
        self, project_id=None, suite_id=None, link=None, cases=[]
    ) -> (List[dict], str):
        """
        Get all cases from all pages if number of cases is too big to return in single response.
        Function using next page field in API response.
        """
        if link is None:
            response = self.client.send_get(
                f"get_cases/{project_id}&suite_id={suite_id}"
            )
        else:
            response = self.client.send_get(link.replace(self.suffix, ""))
        if not response.error_message:
            cases = cases + response.response_text["cases"]
            if response.response_text["_links"]["next"] is not None:
                return self.__get_all_cases(
                    link=response.response_text["_links"]["next"], cases=cases
                )
            else:
                return cases, response.error_message
        else:
            return [], response.error_message
