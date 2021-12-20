import itertools

from trcli.api.api_client import APIClient, APIClientResult
from trcli.cli import Environment
from trcli.data_classes.dataclass_testrail import TestRailSuite
from trcli.data_providers.api_data_provider import ApiPostProvider
from typing import List


class ApiRequestHandler:
    def __init__(
        self,
        env: Environment,
        api_client: APIClient,
        suites_data: TestRailSuite,
    ):
        self.env = env
        self.client = api_client
        self.data_provider = ApiPostProvider(env, suites_data)
        self.suites_data_from_provider = self.data_provider.suites_input

    def get_project_id(self, project_name: str) -> (int, str):
        """
        Send get_projects with project name
        :project_name: Project name
        :returns: Tuple with project id and error string. Project id will be set to -1 if fail.
        """

        response = self.client.send_get("get_projects")
        if not response.error_message:
            available_projects = [
                project["id"]
                for project in response.response_text["projects"]
                if project["name"] == project_name
            ]
            if len(available_projects) == 1:
                return available_projects[0], response.error_message
            elif len(available_projects) > 1:
                return -1, "Given project name matches more than one result."
            else:
                return -2, f"{project_name} project doesn't exists."
        else:
            return -3, response.error_message

    def check_suite_id(self, project_id: int) -> (bool, ""):
        """
        Check if suite from DataProvider exist using get_suites endpoint
        :project_id: project id
        :returns: True if exists in suites. False if not.
        """
        suite_id = self.suites_data_from_provider.suite_id
        response = self.client.send_get(f"get_suites/{project_id}")
        if not response.error_message:
            available_suites = [suite["id"] for suite in response.response_text]
            return (True, "") if suite_id in available_suites else (False, "")
        else:
            return None, response.error_message

    def add_suite(self, project_id: int) -> (List[dict], str):
        """
        Adds suites that doesn't have ID's in DataProvider.
        Runs update_data in data_provider for successfully created resources.
        :project_id: project_id
        :returns: Tuple with list of dict created resources and error string.
        """
        add_suite_data = self.data_provider.add_suites_data()
        responses = []
        error = ""
        for body in add_suite_data["bodies"]:
            response = self.client.send_post(f"add_suite/{project_id}", body)
            if not response.error_message:
                responses.append(response)
            else:
                error = response.error_message
                break

        returned_resources = [
            {
                "suite_id": response.response_text["id"],
                "name": response.response_text["name"],
            }
            for response in responses
        ]
        self.data_provider.update_data(suite_data=returned_resources)
        return returned_resources, error

    def check_missing_section_id(self, project_id: int) -> (List[dict], str):
        """
        Check what section id's are missing in DataProvider.
        :project_id: project_id
        :returns: Tuple with list of dict created resources and error string.
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
                    - set([section.get("id") for section in response.response_text])
                ),
                response.error_message,
            )
        else:
            return [], response.error_message

    def add_section(self, project_id: int) -> (List[dict], str):
        """
        Add sections that doesn't have ID in DataProvider.
        Runs update_data in data_provider for successfully created resources.
        :project_id: project_id
        :returns: Tuple with list of dict created resources and error string.
        """
        add_sections_data = self.data_provider.add_sections_data()
        responses = []
        error = ""
        for body in add_sections_data["bodies"]:
            response = self.client.send_post(f"add_section/{project_id}", body)
            if not response.error_message:
                responses.append(response)
            else:
                error = response.error_message
                break
        returned_resources = [
            {
                "section_id": response.response_text["id"],
                "suite_id": response.response_text["suite_id"],
                "name": response.response_text["name"],
            }
            for response in responses
        ]
        self.data_provider.update_data(section_data=returned_resources)
        return returned_resources, error

    def add_case(self) -> (List[dict], str):
        """
        Add cases that doesn't have ID in DataProvider.
        Runs update_data in data_provider for successfully created resources.
        :project_id: project_id
        :returns: Tuple with list of dict created resources and error string.
        """
        add_case_data = self.data_provider.add_cases()
        responses = []
        error = ""
        for body in add_case_data["bodies"]:
            response = self.client.send_post(f"add_case/{body.pop('section_id')}", body)
            if not response.error_message:
                responses.append(response)
            else:
                error = response.error_message
                break

        returned_resources = [
            {
                "case_id": response.response_text["id"],
                "section_id": response.response_text["section_id"],
                "title": response.response_text["title"],
            }
            for response in responses
        ]
        self.data_provider.update_data(case_data=returned_resources)
        return returned_resources, error

    def add_run(self, project_id: int) -> (List[dict], str):
        suite_id = self.suites_data_from_provider.suite_id
        # TODO proper body should be already returned by add_run in DataProvider - To fix in DataProvider
        # TODO DataProvider will set case_id to -1 if not found in test suite. In full flow this shouldn't happen but dataclass or dataprovider should handle this
        add_run_data = self.data_provider.add_run()
        body = {
            "suite_id": suite_id,
            "description": " ".join(
                [single_run["description"] for single_run in add_run_data["bodies"]]
            ),
            "case_ids": list(
                itertools.chain(
                    *[single_run["case_ids"] for single_run in add_run_data["bodies"]]
                )
            ),
        }
        response = self.client.send_post(f"add_run/{project_id}", body)
        return response.response_text.get("id"), response.error_message

    def add_results(self, run_id: int) -> (List[dict], str):
        # TODO proper body should be already returned by add_run in DataProvider - To fix in DataProvider
        # TODO DataProvider will set case_id to NONE if not found in test suite. In full flow this shouldn't happen but dataclass or dataprovider should handle this
        add_results_data = self.data_provider.add_results_for_cases()
        body = {"results": add_results_data["bodies"]["results"]}

        response = self.client.send_post(f"add_results_for_cases/{run_id}", body)
        return response.response_text, response.error_message

    def close_run(self, run_id: int):
        body = {"run_id": run_id}  # TODO handle by dataprovider?
        response = self.client.send_post(f"close_run/{run_id}", body)
        return response.response_text, response.error_message


# TODO add check mising test cases ids
