from trcli.api.api_client import APIClient, APIClientResult
from trcli.cli import Environment
from trcli.api.api_response_verify import ApiResponseVerify
from trcli.data_classes.dataclass_testrail import TestRailSuite
from trcli.data_providers.api_data_provider import ApiDataProvider
from trcli.constants import (
    ProjectErrors,
    FAULT_MAPPING,
)
from trcli.settings import MAX_WORKERS_ADD_RESULTS, MAX_WORKERS_ADD_CASE
from typing import List, Any
from dataclasses import dataclass
from concurrent.futures import ThreadPoolExecutor, as_completed


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

    def get_project_id(self, project_name: str, project_id: int = None) -> ProjectData:
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
                if project_id in [project["id"] for project in available_projects]:
                    project_index = [
                        index
                        for index, project in enumerate(available_projects)
                        if project["id"] == project_id
                    ][0]
                    return ProjectData(
                        project_id=int(available_projects[project_index]["id"]),
                        suite_mode=int(available_projects[project_index]["suite_mode"]),
                        error_message=response.error_message,
                    )
                else:
                    return ProjectData(
                        project_id=ProjectErrors.multiple_project_same_name,
                        suite_mode=-1,
                        error_message=FAULT_MAPPING["more_than_one_project"],
                    )
            else:
                return ProjectData(
                    project_id=ProjectErrors.not_existing_project,
                    suite_mode=-1,
                    error_message=FAULT_MAPPING["project_doesnt_exists"],
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
            missing_sections = list(
                set(sections)
                - set(
                    [
                        section.get("id")
                        for section in response.response_text["sections"]
                    ]
                )
            )
            if any(missing_sections):
                return False, FAULT_MAPPING["unknown_section_id"]
            elif len(missing_sections) == 1:
                return True, response.error_message
            else:
                return False, response.error_message
        else:
            return False, response.error_message

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

        returned_cases, error_message = self.__get_all_items(
            f"get_cases/{project_id}&suite_id={suite_id}", "cases"
        )
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
        with self.environment.get_progress_bar(
            results_amount=len(add_case_data["bodies"]), prefix="Adding test cases"
        ) as progress_bar:
            with ThreadPoolExecutor(max_workers=MAX_WORKERS_ADD_CASE) as executor:
                futures = {
                    executor.submit(
                        self.client.send_post,
                        f"add_case/{body.pop('section_id')}",
                        body,
                    ): body
                    for body in add_case_data["bodies"]
                }
                responses, error_message = self.handle_futures(
                    futures=futures, action_string="add_case", progress_bar=progress_bar
                )
            if error_message:
                # When error_message is present we cannot be sure that responses contains all added items.
                # Iterate through futures to get all responses from done tasks (not cancelled)
                responses = ApiRequestHandler.retrieve_results_after_cancelling(futures)
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

    def update_case_result(self, run_id, case_id):
        """
        Updates result for case.
        :run_id: run id
        :case_id: case id
        :returns: Tuple with dict (updated resource) and error string.
        """
        update_case_data = self.data_provider.add_result_for_case(case_id=case_id)
        response_text = ""
        if update_case_data:
            response = self.client.send_post(
                f"add_result_for_case/{run_id}/{update_case_data.pop('case_id')}",
                update_case_data,
            )
            response_text = response.response_text
            error_message = response.error_message
        else:
            error_message = FAULT_MAPPING["mismatch_between_case_id_and_result_file"]
        return response_text, error_message

    def add_run(self, project_id: int, run_name: str) -> (List[dict], str):
        """
        Creates a new test run.
        :project_id: project_id
        :run_name: run name
        :returns: Tuple with run id and error string.
        """
        add_run_data = self.data_provider.add_run(run_name)
        response = self.client.send_post(f"add_run/{project_id}", add_run_data)
        return response.response_text.get("id"), response.error_message

    def get_cases_from_run(self, run_id: int) -> (List[int], str):
        """
        Return all test cases IDs attached to run.
        :run_id: run id
        :returns: List with cases ids
        """
        returned_tests, error_message = self.__get_all_items(
            f"get_tests/{run_id}", "tests"
        )
        if error_message:
            returned_cases = []
            error_message = FAULT_MAPPING["error_during_get_cases_from_run"]
        else:
            if len(returned_tests) > 0:
                returned_cases = [test.get("case_id") for test in returned_tests]
            else:
                returned_cases = []
        return returned_cases, error_message

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

        with self.environment.get_progress_bar(
            results_amount=results_amount, prefix="Adding results"
        ) as progress_bar:
            with ThreadPoolExecutor(max_workers=MAX_WORKERS_ADD_RESULTS) as executor:
                futures = {
                    executor.submit(
                        self.client.send_post, f"add_results_for_cases/{run_id}", body
                    ): body
                    for body in add_results_data_chunks
                }
                responses, error_message = self.handle_futures(
                    futures=futures,
                    action_string="add_results",
                    progress_bar=progress_bar,
                )
            if error_message:
                # When error_message is present we cannot be sure that responses contains all added items.
                # Iterate through futures to get all responses from done tasks (not cancelled)
                responses = ApiRequestHandler.retrieve_results_after_cancelling(futures)
        responses = [response.response_text for response in responses]
        return responses, error_message, progress_bar.n

    def handle_futures(self, futures, action_string, progress_bar):
        responses = []
        error_message = ""
        try:
            for future in as_completed(futures):
                arguments = futures[future]
                response = future.result()
                if not response.error_message:
                    responses.append(response)
                    if action_string == "add_results":
                        progress_bar.update(len(arguments["results"]))
                    else:
                        if not self.response_verifier.verify_returned_data(
                            arguments, response.response_text
                        ):
                            responses.append(response)
                            error_message = FAULT_MAPPING["data_verification_error"]
                            self.__cancel_running_futures(futures, action_string)
                            break
                        progress_bar.update(1)
                else:
                    error_message = response.error_message
                    self.environment.log(
                        f"\nError during {action_string}. Trying to cancel scheduled tasks."
                    )
                    self.__cancel_running_futures(futures, action_string)
                    break
            else:
                progress_bar.set_postfix_str(s="Done.")
        except KeyboardInterrupt:
            self.__cancel_running_futures(futures, action_string)
            raise KeyboardInterrupt
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

    def delete_suite(self, suite_id: int) -> (dict, str):
        """
        Delete suite given suite id
        :suite_id: suite id
        :returns: Tuple with dict created resources and error string.
        """
        response = self.client.send_post(f"delete_suite/{suite_id}", payload={})
        return response.response_text, response.error_message

    def delete_sections(self, added_sections: List[dict]) -> (dict, str):
        """
        Delete section given add_sections response
        :suite_id: section id
        :returns: Tuple with dict created resources and error string.
        """
        responses = []
        error_message = ""
        for section in added_sections:
            response = self.client.send_post(
                f"delete_section/{section['section_id']}", payload={}
            )
            if not response.error_message:
                responses.append(response.response_text)
            else:
                error_message = response.error_message
                break
        return responses, error_message

    def delete_cases(self, suite_id: int, added_cases: List[dict]) -> (dict, str):
        """
        Delete cases given add_cases response
        :suite_id: section id
        :returns: Tuple with dict created resources and error string.
        """
        body = {"case_ids": [case["case_id"] for case in added_cases]}
        response = self.client.send_post(f"delete_cases/{suite_id}", payload=body)
        return response.response_text, response.error_message

    def delete_run(self, run_id) -> (dict, str):
        """
        Delete run given add_run response
        :suite_id: section id
        :returns: Tuple with dict created resources and error string.
        """
        response = self.client.send_post(f"delete_run/{run_id}", payload={})
        return response.response_text, response.error_message

    @staticmethod
    def retrieve_results_after_cancelling(futures):
        responses = []
        for future in as_completed(futures):
            if not future.cancelled():
                response = future.result()
                if not response.error_message:
                    responses.append(response)
        return responses

    def __cancel_running_futures(self, futures, action_string):
        self.environment.log(
            f"\nAborting: {action_string}. Trying to cancel scheduled tasks."
        )
        for future in futures:
            future.cancel()

    def __get_all_items(
        self, url: str, key_to_get: str, link=None, items=[]
    ) -> (List[Any], str):
        """
        Get all items from all pages if number of items is too big to return in single response.
        Function using next page field in API response.
        """
        if link is None:
            response = self.client.send_get(url)
        else:
            response = self.client.send_get(link.replace(self.suffix, ""))
        if not response.error_message:
            items = items + response.response_text[key_to_get]
            if response.response_text["_links"]["next"] is not None:
                return self.__get_all_items(
                    url=url,
                    link=response.response_text["_links"]["next"],
                    key_to_get=key_to_get,
                    items=items,
                )
            else:
                return items, response.error_message
        else:
            return [], response.error_message
