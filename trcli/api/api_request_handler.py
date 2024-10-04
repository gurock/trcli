import html
from concurrent.futures import ThreadPoolExecutor, as_completed
from beartype.typing import List, Union, Tuple, Dict

from trcli.api.api_client import APIClient, APIClientResult
from trcli.api.api_response_verify import ApiResponseVerify
from trcli.cli import Environment
from trcli.constants import (
    ProjectErrors,
    FAULT_MAPPING,
)
from trcli.data_classes.data_parsers import MatchersParser
from trcli.data_classes.dataclass_testrail import TestRailSuite, TestRailCase, ProjectData
from trcli.data_providers.api_data_provider import ApiDataProvider
from trcli.settings import MAX_WORKERS_ADD_RESULTS, MAX_WORKERS_ADD_CASE


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
        self.data_provider = ApiDataProvider(
            suites_data,
            environment.case_fields,
            environment.run_description,
            environment.result_fields,
            environment.section_id
        )
        self.suites_data_from_provider = self.data_provider.suites_input
        self.response_verifier = ApiResponseVerify(verify)

    def check_automation_id_field(self, project_id: int) -> Union[str, None]:
        """
        Checks if the automation_id field (custom_automation_id) is available for the project
        :param project_id: the id of the project
        :return: error message
        """
        response = self.client.send_get("get_case_fields")
        if not response.error_message:
            fields: List = response.response_text
            automation_id_field = next(
                filter(lambda x: x["system_name"] == "custom_automation_id", fields),
                None
            )
            if automation_id_field:
                if automation_id_field["is_active"] is False:
                    return FAULT_MAPPING["automation_id_unavailable"]
                if not automation_id_field["configs"]:
                    return None
                for config in automation_id_field["configs"]:
                    context = config["context"]
                    if context["is_global"] or project_id in context["project_ids"]:
                        return None
                return FAULT_MAPPING["automation_id_unavailable"]
            else:
                return FAULT_MAPPING["automation_id_unavailable"]
        else:
            return response.error_message

    def get_project_data(self, project_name: str, project_id: int = None) -> ProjectData:
        """
        Send get_projects with project name
        :project_name: Project name
        :returns: ProjectData
        """
        projects_data, error = self.__get_all_projects()
        if not error:
            available_projects = [
                project
                for project in projects_data
                if project["name"] == project_name
            ]

            if len(available_projects) == 1:
                return ProjectData(
                    project_id=int(available_projects[0]["id"]),
                    suite_mode=int(available_projects[0]["suite_mode"]),
                    error_message=error,
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
                        error_message=error,
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
                error_message=error,
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

    def resolve_suite_id_using_name(self, project_id: int) -> Tuple[int, str]:
        """Get suite ID matching suite name on data provider or returns -1 if unable to match any suite.
        :arg project_id: project id
        :returns: tuple with id of the suite and error message"""
        suite_id = -1
        error_message = ""
        response = self.client.send_get(f"get_suites/{project_id}")
        if not response.error_message:
            suites = response.response_text
            suite = next(
                filter(lambda x: x["name"] == self.suites_data_from_provider.name, suites),
                None
            )
            if suite:
                suite_id = suite["id"]
                self.data_provider.update_data([{"suite_id": suite["id"], "name": suite["name"]}])
        else:
            error_message = response.error_message

        return suite_id, error_message

    def get_suite_ids(self, project_id: int) -> Tuple[List[int], str]:
        """Get suite IDs for requested project_id.
        : project_id: project id
        : returns: tuple with list of suite ids and error string"""
        available_suites = []
        returned_resources = []
        error_message = ""
        response = self.client.send_get(f"get_suites/{project_id}")
        if not response.error_message:
            for suite in response.response_text:
                available_suites.append(int(suite["id"]))
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

    def add_suites(self, project_id: int) -> Tuple[List[Dict], str]:
        """
        Adds suites that doesn't have ID's in DataProvider.
        Runs update_data in data_provider for successfully created resources.
        :project_id: project_id
        :returns: Tuple with list of dict created resources and error string.
        """
        add_suite_data = self.data_provider.add_suites_data()
        responses = []
        error_message = ""
        for body in add_suite_data:
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

    def check_missing_section_ids(self, project_id: int) -> Tuple[bool, str]:
        """
        Check what section id's are missing in DataProvider.
        :project_id: project_id
        :returns: Tuple with list missing section ID and error string.
        """
        suite_id = self.suites_data_from_provider.suite_id
        returned_sections, error_message = self.__get_all_sections(project_id, suite_id)
        if not error_message:
            missing_test_sections = False
            sections_by_name = {section["name"]: section for section in returned_sections}
            section_data = []
            for section in self.suites_data_from_provider.testsections:
                if section.name in sections_by_name.keys():
                    section_json = sections_by_name[section.name]
                    section_data.append({
                        "section_id": section_json["id"],
                        "suite_id": section_json["suite_id"],
                        "name": section_json["name"],
                    })
                else:
                    missing_test_sections = True
            self.data_provider.update_data(section_data=section_data)
            return missing_test_sections, error_message
        else:
            return False, error_message

    def add_sections(self, project_id: int) -> Tuple[List[Dict], str]:
        """
        Add sections that doesn't have ID in DataProvider.
        Runs update_data in data_provider for successfully created resources.
        :project_id: project_id
        :returns: Tuple with list of dict created resources and error string.
        """
        add_sections_data = self.data_provider.add_sections_data()
        responses = []
        error_message = ""
        for body in add_sections_data:
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

    def check_missing_test_cases_ids(self, project_id: int) -> Tuple[bool, str]:
        """
        Check what test cases id's are missing in DataProvider.
        :project_id: project_id
        :returns: Tuple with list test case ID missing and error string.
        """
        missing_cases_number = 0
        suite_id = self.suites_data_from_provider.suite_id
        returned_cases, error_message = self.__get_all_cases(project_id, suite_id)
        if error_message:
            return False, error_message
        if self.environment.case_matcher == MatchersParser.AUTO:
            test_cases_by_aut_id = {}
            for case in returned_cases:
                aut_case_id = case["custom_automation_id"]
                aut_case_id = aut_case_id if not aut_case_id else html.unescape(case["custom_automation_id"])
                test_cases_by_aut_id[aut_case_id] = case
            test_case_data = []
            for section in self.suites_data_from_provider.testsections:
                for test_case in section.testcases:
                    if test_case.custom_automation_id in test_cases_by_aut_id.keys():
                        case = test_cases_by_aut_id[test_case.custom_automation_id]
                        test_case_data.append({
                            "case_id": case["id"],
                            "section_id": case["section_id"],
                            "title": case["title"],
                            "custom_automation_id": test_case.custom_automation_id
                        })
                    else:
                        missing_cases_number += 1
            self.data_provider.update_data(case_data=test_case_data)
            if missing_cases_number:
                self.environment.log(f"Found {missing_cases_number} test cases not matching any TestRail case.")
        else:
            nonexistent_ids = []
            all_case_ids = [case["id"] for case in returned_cases]
            for section in self.suites_data_from_provider.testsections:
                for test_case in section.testcases:
                    if not test_case.case_id:
                        missing_cases_number += 1
                    elif int(test_case.case_id) not in all_case_ids:
                        nonexistent_ids.append(test_case.case_id)
            if missing_cases_number:
                self.environment.log(f"Found {missing_cases_number} test cases without case ID in the report file.")
            if nonexistent_ids:
                self.environment.elog(f"Nonexistent case IDs found in the report file: {nonexistent_ids}")
                return False, "Case IDs not in TestRail project or suite were detected in the report file."

        return missing_cases_number > 0, ""

    def add_cases(self) -> Tuple[List[dict], str]:
        """
        Add cases that doesn't have ID in DataProvider.
        Runs update_data in data_provider for successfully created resources.
        :returns: Tuple with list of dict created resources and error string.
        """
        add_case_data = self.data_provider.add_cases()
        responses = []
        error_message = ""
        with self.environment.get_progress_bar(
            results_amount=len(add_case_data), prefix="Adding test cases"
        ) as progress_bar:
            with ThreadPoolExecutor(max_workers=MAX_WORKERS_ADD_CASE) as executor:
                futures = {
                    executor.submit(
                        self._add_case_and_update_data,
                        body,
                    ): body
                    for body in add_case_data
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
                "title": response.response_text["title"]
            }
            for response in responses
        ]
        return returned_resources, error_message

    def add_run(
            self,
            project_id: int,
            run_name: str,
            milestone_id: int = None,
            plan_id: int = None,
            config_ids: List[int] = None,
            assigned_to_id: int = None,
            include_all: bool = False,
            refs: str = None,
    ) -> Tuple[int, str]:
        """
        Creates a new test run.
        :project_id: project_id
        :run_name: run name
        :returns: Tuple with run id and error string.
        """
        add_run_data = self.data_provider.add_run(
            run_name,
            milestone_id=milestone_id,
            assigned_to_id=assigned_to_id,
            include_all=include_all,
            refs=refs,
        )
        if not plan_id:
            response = self.client.send_post(f"add_run/{project_id}", add_run_data)
            run_id = response.response_text.get("id")
        else:
            if config_ids:
                add_run_data["config_ids"] = config_ids
                entry_data = {
                    "name": add_run_data["name"],
                    "suite_id": add_run_data["suite_id"],
                    "config_ids": config_ids,
                    "runs": [add_run_data]
                }
            else:
                entry_data = add_run_data
            response = self.client.send_post(f"add_plan_entry/{plan_id}", entry_data)
            run_id = response.response_text["runs"][0]["id"]
        return run_id, response.error_message

    def update_run(self, run_id: int, run_name: str, milestone_id: int = None) -> Tuple[dict, str]:
        """
        Updates an existing run
        :run_id: run id
        :run_name: run name
        :returns: Tuple with run and error string.
        """
        run_response = self.client.send_get(f"get_run/{run_id}")
        existing_description = run_response.response_text.get("description", "")

        add_run_data = self.data_provider.add_run(run_name, milestone_id=milestone_id)
        add_run_data["description"] = existing_description  # Retain the current description

        run_tests, error_message = self.__get_all_tests_in_run(run_id)
        run_case_ids = [test["case_id"] for test in run_tests]
        report_case_ids = add_run_data["case_ids"]
        joint_case_ids = list(set(report_case_ids + run_case_ids))
        add_run_data["case_ids"] = joint_case_ids
        
        plan_id = run_response.response_text["plan_id"]
        config_ids = run_response.response_text["config_ids"]
        if not plan_id:
            update_response = self.client.send_post(f"update_run/{run_id}", add_run_data)
        elif plan_id and config_ids:
            update_response = self.client.send_post(f"update_run_in_plan_entry/{run_id}", add_run_data)
        else:
            response = self.client.send_get(f"get_plan/{plan_id}")
            entry_id = next(
                (
                    run["entry_id"]
                    for entry in response.response_text["entries"]
                    for run in entry["runs"]
                    if run["id"] == run_id
                ),
                None,
            )
            update_response = self.client.send_post(f"update_plan_entry/{plan_id}/{entry_id}", add_run_data)
        run_response = self.client.send_get(f"get_run/{run_id}")
        return run_response.response_text, update_response.error_message

    def upload_attachments(self, report_results: [Dict], results: List[Dict], run_id: int):
        """ Getting test result id and upload attachments for it. """
        tests_in_run, error = self.__get_all_tests_in_run(run_id)
        if not error:
            for report_result in report_results:
                case_id = report_result["case_id"]
                test_id = next((test["id"] for test in tests_in_run if test["case_id"] == case_id), None)
                result_id = next((result["id"] for result in results if result["test_id"] == test_id), None)
                for file_path in report_result.get("attachments"):
                    try:
                        with open(file_path, "rb") as file:
                            self.client.send_post(f"add_attachment_to_result/{result_id}", files={"attachment": file})
                    except Exception as ex:
                        self.environment.elog(f"Error uploading attachment for case {case_id}: {ex}")
        else:
            self.environment.elog(f"Unable to upload attachments due to API request error: {error}")

    def add_results(self, run_id: int) -> Tuple[List, str, int]:
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
        results = [
            result
            for results_list in responses
            for result in results_list
        ]
        report_results_w_attachments = []
        for results_data_chunk in add_results_data_chunks:
            for test_result in results_data_chunk["results"]:
                if test_result["attachments"]:
                    report_results_w_attachments.append(test_result)
        if report_results_w_attachments:
            attachments_count = 0
            for result in report_results_w_attachments:
                attachments_count += len(result["attachments"])
            self.environment.log(f"Uploading {attachments_count} attachments "
                                 f"for {len(report_results_w_attachments)} test results.")
            self.upload_attachments(report_results_w_attachments, results, run_id)
        else:
            self.environment.log(f"No attachments found to upload.")
        return responses, error_message, progress_bar.n

    def handle_futures(self, futures, action_string, progress_bar) -> Tuple[list, str]:
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
                        if action_string == "add_case":
                            arguments = arguments.to_dict()
                            arguments.pop("case_id")
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

    def close_run(self, run_id: int) -> Tuple[dict, str]:
        """
        Closes an existing test run and archives its tests & results.
        :run_id: run id
        :returns: Tuple with dict created resources and error string.
        """
        body = {"run_id": run_id}
        response = self.client.send_post(f"close_run/{run_id}", body)
        return response.response_text, response.error_message

    def delete_suite(self, suite_id: int) -> Tuple[dict, str]:
        """
        Delete suite given suite id
        :suite_id: suite id
        :returns: Tuple with dict created resources and error string.
        """
        response = self.client.send_post(f"delete_suite/{suite_id}", payload={})
        return response.response_text, response.error_message

    def delete_sections(self, added_sections: List[Dict]) -> Tuple[List, str]:
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

    def delete_cases(self, suite_id: int, added_cases: List[Dict]) -> Tuple[Dict, str]:
        """
        Delete cases given add_cases response
        :suite_id: section id
        :returns: Tuple with dict created resources and error string.
        """
        body = {"case_ids": [case["case_id"] for case in added_cases]}
        response = self.client.send_post(f"delete_cases/{suite_id}", payload=body)
        return response.response_text, response.error_message

    def delete_run(self, run_id) -> Tuple[dict, str]:
        """
        Delete run given add_run response
        :suite_id: section id
        :returns: Tuple with dict created resources and error string.
        """
        response = self.client.send_post(f"delete_run/{run_id}", payload={})
        return response.response_text, response.error_message

    @staticmethod
    def retrieve_results_after_cancelling(futures) -> list:
        responses = []
        for future in as_completed(futures):
            if not future.cancelled():
                response = future.result()
                if not response.error_message:
                    responses.append(response)
        return responses

    def _add_case_and_update_data(self, case: TestRailCase) -> APIClientResult:
        case_body = case.to_dict()
        if self.environment.case_matcher != MatchersParser.AUTO and "custom_automation_id" in case_body:
            case_body.pop("custom_automation_id")
        response = self.client.send_post(f"add_case/{case_body.pop('section_id')}", case_body)
        if response.status_code == 200:
            case.case_id = response.response_text["id"]
            case.result.case_id = response.response_text["id"]
            case.section_id = response.response_text["section_id"]
        return response

    def __cancel_running_futures(self, futures, action_string):
        self.environment.log(
            f"\nAborting: {action_string}. Trying to cancel scheduled tasks."
        )
        for future in futures:
            future.cancel()

    def __get_all_cases(self, project_id=None, suite_id=None) -> Tuple[List[dict], str]:
        """
        Get all cases from all pages
        """
        return self.__get_all_entities('cases', f"get_cases/{project_id}&suite_id={suite_id}")

    def __get_all_sections(self, project_id=None, suite_id=None) -> Tuple[List[dict], str]:
        """
        Get all sections from all pages
        """
        return self.__get_all_entities('sections', f"get_sections/{project_id}&suite_id={suite_id}")

    def __get_all_tests_in_run(self, run_id=None) -> Tuple[List[dict], str]:
        """
        Get all tests from all pages
        """
        return self.__get_all_entities('tests', f"get_tests/{run_id}")

    def __get_all_projects(self) -> Tuple[List[dict], str]:
        """
        Get all cases from all pages
        """
        return self.__get_all_entities('projects', f"get_projects")

    def __get_all_entities(self, entity: str, link=None, entities=[]) -> Tuple[List[Dict], str]:
        """
        Get all entities from all pages if number of entities is too big to return in single response.
        Function using next page field in API response.
        Entity examples: cases, sections
        """
        if link.startswith(self.suffix):
            link = link.replace(self.suffix, "")
        response = self.client.send_get(link)
        if not response.error_message:
            # Endpoints without pagination (legacy)
            if isinstance(response.response_text, list):
                return response.response_text, response.error_message
            # Endpoints with pagination
            entities = entities + response.response_text[entity]
            if response.response_text["_links"]["next"] is not None:
                return self.__get_all_entities(entity, link=response.response_text["_links"]["next"], entities=entities)
            else:
                return entities, response.error_message
        else:
            return [], response.error_message
