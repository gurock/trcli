import html, json
from concurrent.futures import ThreadPoolExecutor, as_completed
from beartype.typing import List, Union, Tuple, Dict

from trcli.api.api_client import APIClient, APIClientResult
from trcli.api.api_response_verify import ApiResponseVerify
from trcli.cli import Environment
from trcli.constants import (
    ProjectErrors,
    FAULT_MAPPING, OLD_SYSTEM_NAME_AUTOMATION_ID, UPDATED_SYSTEM_NAME_AUTOMATION_ID,
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
        Checks if the automation_id field (custom_automation_id or custom_case_automation_id) is available for the project
        :param project_id: the id of the project
        :return: error message
        """
        response = self.client.send_get("get_case_fields")
        if not response.error_message:
            fields: List = response.response_text
            automation_id_field = next(
                    filter(
                    lambda x: x["system_name"] in [OLD_SYSTEM_NAME_AUTOMATION_ID, UPDATED_SYSTEM_NAME_AUTOMATION_ID],
                    fields
                ),
                None
            )
            if automation_id_field:
                if automation_id_field["is_active"] is False:
                    return FAULT_MAPPING["automation_id_unavailable"]
                if not automation_id_field["configs"]:
                    self._active_automation_id_field = automation_id_field["system_name"]
                    return None
                for config in automation_id_field["configs"]:
                    context = config["context"]
                    if context["is_global"] or project_id in context["project_ids"]:
                        self._active_automation_id_field = automation_id_field["system_name"]
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

    def check_suite_id(self, project_id: int) -> Tuple[bool, str]:
        """
        Check if suite from DataProvider exist using get_suites endpoint
        :project_id: project id
        :returns: True if exists in suites. False if not.
        """
        suite_id = self.suites_data_from_provider.suite_id
        suites_data, error = self.__get_all_suites(project_id)
        if not error:
            available_suites = [
                suite
                for suite in suites_data
                if suite["id"] == suite_id
            ]
            return (
                (True, "")
                if len(available_suites) > 0
                else (False, FAULT_MAPPING["missing_suite"].format(suite_id=suite_id))
            )
        else:
            return None, suites_data.error_message

    def resolve_suite_id_using_name(self, project_id: int) -> Tuple[int, str]:
        """Get suite ID matching suite name on data provider or returns -1 if unable to match any suite.
        :arg project_id: project id
        :returns: tuple with id of the suite and error message"""
        suite_id = -1
        suite_name = self.suites_data_from_provider.name
        suites_data, error = self.__get_all_suites(project_id)
        if not error:
            for suite in suites_data:
                if suite["name"] == suite_name:
                    suite_id = suite["id"]
                    self.data_provider.update_data([{"suite_id": suite["id"], "name": suite["name"]}])
                    break
            return (
                (suite_id, "")
                if suite_id != -1
                else (-1, FAULT_MAPPING["missing_suite_by_name"].format(suite_name=suite_name))
            )
        else:
            return -1, error

    def get_suite_ids(self, project_id: int) -> Tuple[List[int], str]:
        """Get suite IDs for requested project_id.
        : project_id: project id
        : returns: tuple with list of suite ids and error string"""
        available_suites = []
        returned_resources = []
        suites_data, error = self.__get_all_suites(project_id)
        if not error:
            for suite in suites_data:
                available_suites.append(suite["id"])
                returned_resources.append(
                    {
                        "suite_id": suite["id"],
                        "name": suite["name"],
                    }
                )
            if returned_resources:
                self.data_provider.update_data(suite_data=returned_resources)
            else:
                print("Update skipped")
            return (
                (available_suites, "")
                if len(available_suites) > 0
                else ([], FAULT_MAPPING["no_suites_found"].format(project_id=project_id))
            )
        else:
            return [], error

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
            sections_by_id = {section["id"]: section for section in returned_sections}
            sections_by_name = {section["name"]: section for section in returned_sections}
            section_data = []
            for section in self.suites_data_from_provider.testsections:
                if self.environment.section_id:
                    if section.section_id in sections_by_id.keys():
                        section_json = sections_by_id[section.section_id]
                        section_data.append({
                            "section_id": section_json["id"],
                            "suite_id": section_json["suite_id"],
                            "name": section_json["name"],
                        })
                    else:
                        missing_test_sections = True
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
                aut_case_id = case.get(OLD_SYSTEM_NAME_AUTOMATION_ID) or case.get(UPDATED_SYSTEM_NAME_AUTOMATION_ID)
                if aut_case_id:
                    aut_case_id = html.unescape(aut_case_id)
                    test_cases_by_aut_id[aut_case_id] = case
            test_case_data = []
            for section in self.suites_data_from_provider.testsections:
                for test_case in section.testcases:
                    aut_id = test_case.custom_automation_id
                    if aut_id in test_cases_by_aut_id.keys():
                        case = test_cases_by_aut_id[aut_id]
                        test_case_data.append({
                            "case_id": case["id"],
                            "section_id": case["section_id"],
                            "title": case["title"],
                            OLD_SYSTEM_NAME_AUTOMATION_ID: aut_id
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
            start_date: str = None,
            end_date: str = None,
            plan_id: int = None,
            config_ids: List[int] = None,
            assigned_to_id: int = None,
            include_all: bool = False,
            refs: str = None,
            case_ids: List[int] = None,
    ) -> Tuple[int, str]:
        """
        Creates a new test run.
        :project_id: project_id
        :run_name: run name
        :returns: Tuple with run id and error string.
        """
        add_run_data = self.data_provider.add_run(
            run_name,
            case_ids=case_ids,
            start_date=start_date,
            end_date=end_date,
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

    def update_run(self, run_id: int, run_name: str, start_date: str = None,
            end_date: str = None, milestone_id: int = None, refs: str = None, refs_action: str = 'add') -> Tuple[dict, str]:
        """
        Updates an existing run
        :run_id: run id
        :run_name: run name
        :refs: references to manage
        :refs_action: action to perform ('add', 'update', 'delete')
        :returns: Tuple with run and error string.
        """
        run_response = self.client.send_get(f"get_run/{run_id}")
        if run_response.error_message:
            return None, run_response.error_message
            
        existing_description = run_response.response_text.get("description", "")
        existing_refs = run_response.response_text.get("refs", "")

        add_run_data = self.data_provider.add_run(run_name, start_date=start_date,
            end_date=end_date, milestone_id=milestone_id)
        add_run_data["description"] = existing_description  # Retain the current description

        # Handle references based on action
        if refs is not None:
            updated_refs = self._manage_references(existing_refs, refs, refs_action)
            add_run_data["refs"] = updated_refs
        else:
            add_run_data["refs"] = existing_refs  # Keep existing refs if none provided

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

    def _manage_references(self, existing_refs: str, new_refs: str, action: str) -> str:
        """
        Manage references based on the specified action.
        :existing_refs: current references in the run
        :new_refs: new references to process
        :action: 'add', 'update', or 'delete'
        :returns: updated references string
        """
        if not existing_refs:
            existing_refs = ""
        
        if action == 'update':
            # Replace all references with new ones
            return new_refs
        elif action == 'delete':
            if not new_refs:
                # Delete all references
                return ""
            else:
                # Delete specific references
                existing_list = [ref.strip() for ref in existing_refs.split(',') if ref.strip()]
                refs_to_delete = [ref.strip() for ref in new_refs.split(',') if ref.strip()]
                updated_list = [ref for ref in existing_list if ref not in refs_to_delete]
                return ','.join(updated_list)
        else:  # action == 'add' (default)
            # Add new references to existing ones
            if not existing_refs:
                return new_refs
            existing_list = [ref.strip() for ref in existing_refs.split(',') if ref.strip()]
            new_list = [ref.strip() for ref in new_refs.split(',') if ref.strip()]
            # Avoid duplicates
            combined_list = existing_list + [ref for ref in new_list if ref not in existing_list]
            return ','.join(combined_list)

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
        active_field = getattr(self, "_active_automation_id_field", None)
        if active_field == UPDATED_SYSTEM_NAME_AUTOMATION_ID and OLD_SYSTEM_NAME_AUTOMATION_ID in case_body:
            case_body[UPDATED_SYSTEM_NAME_AUTOMATION_ID] = case_body.pop(OLD_SYSTEM_NAME_AUTOMATION_ID)
        if self.environment.case_matcher != MatchersParser.AUTO and OLD_SYSTEM_NAME_AUTOMATION_ID in case_body:
            case_body.pop(OLD_SYSTEM_NAME_AUTOMATION_ID)
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
        if suite_id is None:
            return self.__get_all_entities('cases', f"get_cases/{project_id}")
        else:
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
        Get all projects from all pages
        """
        return self.__get_all_entities('projects', f"get_projects")

    def __get_all_suites(self, project_id) -> Tuple[List[dict], str]:
        """
        Get all suites from all pages
        """
        return self.__get_all_entities('suites', f"get_suites/{project_id}")

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
                next_link = response.response_text["_links"]["next"].replace("limit=0", "limit=250")
                return self.__get_all_entities(entity, link=next_link, entities=entities)
            else:
                return entities, response.error_message
        else:
            return [], response.error_message

    # Label management methods
    def add_label(self, project_id: int, title: str) -> Tuple[dict, str]:
        """
        Add a new label to the project
        :param project_id: ID of the project
        :param title: Title of the label (max 20 characters)
        :returns: Tuple with created label data and error string
        """
        # Use multipart/form-data like the working CURL command
        files = {'title': (None, title)}
        response = self.client.send_post(f"add_label/{project_id}", payload=None, files=files)
        return response.response_text, response.error_message

    def update_label(self, label_id: int, project_id: int, title: str) -> Tuple[dict, str]:
        """
        Update an existing label
        :param label_id: ID of the label to update
        :param project_id: ID of the project
        :param title: New title for the label (max 20 characters)
        :returns: Tuple with updated label data and error string
        """
        # Use multipart/form-data like add_label
        files = {
            'project_id': (None, str(project_id)),
            'title': (None, title)  # Field name is 'title' (no colon) for form data
        }
        response = self.client.send_post(f"update_label/{label_id}", payload=None, files=files)
        return response.response_text, response.error_message

    def get_label(self, label_id: int) -> Tuple[dict, str]:
        """
        Get a specific label by ID
        :param label_id: ID of the label to retrieve
        :returns: Tuple with label data and error string
        """
        response = self.client.send_get(f"get_label/{label_id}")
        return response.response_text, response.error_message

    def get_labels(self, project_id: int, offset: int = 0, limit: int = 250) -> Tuple[dict, str]:
        """
        Get all labels for a project with pagination
        :param project_id: ID of the project
        :param offset: Offset for pagination
        :param limit: Limit for pagination
        :returns: Tuple with labels data (including pagination info) and error string
        """
        params = []
        if offset > 0:
            params.append(f"offset={offset}")
        if limit != 250:
            params.append(f"limit={limit}")
        
        url = f"get_labels/{project_id}"
        if params:
            url += "&" + "&".join(params)
            
        response = self.client.send_get(url)
        return response.response_text, response.error_message

    def delete_label(self, label_id: int) -> Tuple[bool, str]:
        """
        Delete a single label
        :param label_id: ID of the label to delete
        :returns: Tuple with success status and error string
        """
        response = self.client.send_post(f"delete_label/{label_id}")
        success = response.status_code == 200
        return success, response.error_message

    def delete_labels(self, label_ids: List[int]) -> Tuple[bool, str]:
        """
        Delete multiple labels
        :param label_ids: List of label IDs to delete
        :returns: Tuple with success status and error string
        """
        # Send as form data with JSON array format
        import json
        label_ids_json = json.dumps(label_ids)
        files = {"label_ids": (None, label_ids_json)}
        response = self.client.send_post("delete_labels", payload=None, files=files)
        success = response.status_code == 200
        return success, response.error_message

    def add_labels_to_cases(self, case_ids: List[int], title: str, project_id: int, suite_id: int = None) -> Tuple[dict, str]:
        """
        Add a label to multiple test cases
        
        :param case_ids: List of test case IDs
        :param title: Label title (max 20 characters)
        :param project_id: Project ID for validation
        :param suite_id: Suite ID (optional)
        :returns: Tuple with response data and error string
        """
        # Initialize results structure
        results = {
            'successful_cases': [], 
            'failed_cases': [], 
            'max_labels_reached': [],
            'case_not_found': []
        }
        
        # Check if project is multi-suite by getting all cases without suite_id
        all_cases_no_suite, error_message = self.__get_all_cases(project_id, None)
        if error_message:
            return results, error_message
            
        # Check if project has multiple suites
        suite_ids = set()
        for case in all_cases_no_suite:
            if 'suite_id' in case and case['suite_id']:
                suite_ids.add(case['suite_id'])
        
        # If project has multiple suites and no suite_id provided, require it
        if len(suite_ids) > 1 and suite_id is None:
            return results, "This project is multisuite, suite id is required"
        
        # Get all cases to validate that the provided case IDs exist
        all_cases, error_message = self.__get_all_cases(project_id, suite_id)
        if error_message:
            return results, error_message
        
        # Create a set of existing case IDs for quick lookup
        existing_case_ids = {case['id'] for case in all_cases}
        
        # Validate case IDs and separate valid from invalid ones
        invalid_case_ids = [case_id for case_id in case_ids if case_id not in existing_case_ids]
        valid_case_ids = [case_id for case_id in case_ids if case_id in existing_case_ids]
        
        # Record invalid case IDs
        for case_id in invalid_case_ids:
            results['case_not_found'].append(case_id)
        
        # If no valid case IDs, return early
        if not valid_case_ids:
            return results, ""
        
        # Check if label exists or create it
        existing_labels, error_message = self.get_labels(project_id)
        if error_message:
            return results, error_message
            
        # Find existing label with the same title
        label_id = None
        for label in existing_labels.get('labels', []):
            if label.get('title') == title:
                label_id = label.get('id')
                break
        
        # Create label if it doesn't exist
        if label_id is None:
            label_data, error_message = self.add_label(project_id, title)
            if error_message:
                return results, error_message
            label_info = label_data.get('label', label_data)
            label_id = label_info.get('id')
        
        # Collect case data and validate constraints
        cases_to_update = []
        for case_id in valid_case_ids:
            # Get current case to check existing labels
            case_response = self.client.send_get(f"get_case/{case_id}")
            if case_response.status_code != 200:
                results['failed_cases'].append({
                    'case_id': case_id,
                    'error': f"Could not retrieve case {case_id}: {case_response.error_message}"
                })
                continue
            
            case_data = case_response.response_text
            current_labels = case_data.get('labels', [])
            
            # Check if label already exists on this case
            if any(label.get('id') == label_id for label in current_labels):
                results['successful_cases'].append({
                    'case_id': case_id,
                    'message': f"Label '{title}' already exists on case {case_id}"
                })
                continue
            
            # Check maximum labels limit (10)
            if len(current_labels) >= 10:
                results['max_labels_reached'].append(case_id)
                continue
            
            # Prepare case for update
            existing_label_ids = [label.get('id') for label in current_labels if label.get('id')]
            updated_label_ids = existing_label_ids + [label_id]
            cases_to_update.append({
                'case_id': case_id,
                'labels': updated_label_ids
            })
        
        # Update cases using appropriate endpoint
        if len(cases_to_update) == 1:
            # Single case: use update_case/{case_id}
            case_info = cases_to_update[0]
            case_update_data = {'labels': case_info['labels']}
            
            update_response = self.client.send_post(f"update_case/{case_info['case_id']}", payload=case_update_data)
            
            if update_response.status_code == 200:
                results['successful_cases'].append({
                    'case_id': case_info['case_id'],
                    'message': f"Successfully added label '{title}' to case {case_info['case_id']}"
                })
            else:
                results['failed_cases'].append({
                    'case_id': case_info['case_id'],
                    'error': update_response.error_message
                })
        elif len(cases_to_update) > 1:
            # Multiple cases: use update_cases/{suite_id}
            # Need to determine suite_id from the cases
            case_suite_id = suite_id
            if not case_suite_id:
                # Get suite_id from the first case if not provided
                first_case = all_cases[0] if all_cases else None
                case_suite_id = first_case.get('suite_id') if first_case else None
            
            if not case_suite_id:
                # Fall back to individual updates if no suite_id available
                for case_info in cases_to_update:
                    case_update_data = {'labels': case_info['labels']}
                    update_response = self.client.send_post(f"update_case/{case_info['case_id']}", payload=case_update_data)
                    
                    if update_response.status_code == 200:
                        results['successful_cases'].append({
                            'case_id': case_info['case_id'],
                            'message': f"Successfully added label '{title}' to case {case_info['case_id']}"
                        })
                    else:
                        results['failed_cases'].append({
                            'case_id': case_info['case_id'],
                            'error': update_response.error_message
                        })
            else:
                # Batch update using update_cases/{suite_id}
                batch_update_data = {
                    'case_ids': [case_info['case_id'] for case_info in cases_to_update],
                    'labels': cases_to_update[0]['labels']  # Assuming same labels for all cases
                }
                
                batch_response = self.client.send_post(f"update_cases/{case_suite_id}", payload=batch_update_data)
                
                if batch_response.status_code == 200:
                    for case_info in cases_to_update:
                        results['successful_cases'].append({
                            'case_id': case_info['case_id'],
                            'message': f"Successfully added label '{title}' to case {case_info['case_id']}"
                        })
                else:
                    # If batch update fails, fall back to individual updates
                    for case_info in cases_to_update:
                        case_update_data = {'labels': case_info['labels']}
                        update_response = self.client.send_post(f"update_case/{case_info['case_id']}", payload=case_update_data)
                        
                        if update_response.status_code == 200:
                            results['successful_cases'].append({
                                'case_id': case_info['case_id'],
                                'message': f"Successfully added label '{title}' to case {case_info['case_id']}"
                            })
                        else:
                            results['failed_cases'].append({
                                'case_id': case_info['case_id'],
                                'error': update_response.error_message
                            })
        
        return results, ""

    def get_cases_by_label(self, project_id: int, suite_id: int = None, label_ids: List[int] = None, label_title: str = None) -> Tuple[List[dict], str]:
        """
        Get test cases filtered by label ID or title
        
        :param project_id: Project ID
        :param suite_id: Suite ID (optional)
        :param label_ids: List of label IDs to filter by
        :param label_title: Label title to filter by
        :returns: Tuple with list of matching cases and error string
        """
        # Get all cases first
        all_cases, error_message = self.__get_all_cases(project_id, suite_id)
        if error_message:
            return [], error_message
        
        # If filtering by title, first get the label ID
        target_label_ids = label_ids or []
        if label_title and not target_label_ids:
            labels_data, error_message = self.get_labels(project_id)
            if error_message:
                return [], error_message
            
            for label in labels_data.get('labels', []):
                if label.get('title') == label_title:
                    target_label_ids.append(label.get('id'))
            
            if not target_label_ids:
                return [], ""  # No label found is a valid case with 0 results
        
        # Filter cases that have any of the target labels
        matching_cases = []
        for case in all_cases:
            case_labels = case.get('labels', [])
            case_label_ids = [label.get('id') for label in case_labels]
            
            # Check if any of the target label IDs are present in this case
            if any(label_id in case_label_ids for label_id in target_label_ids):
                matching_cases.append(case)
        
        return matching_cases, ""

    def add_labels_to_tests(self, test_ids: List[int], titles: Union[str, List[str]], project_id: int) -> Tuple[dict, str]:
        """
        Add labels to multiple tests
        
        :param test_ids: List of test IDs
        :param titles: Label title(s) - can be a single string or list of strings (max 20 characters each)
        :param project_id: Project ID for validation
        :returns: Tuple with response data and error string
        """
        # Initialize results structure
        results = {
            'successful_tests': [], 
            'failed_tests': [], 
            'max_labels_reached': [],
            'test_not_found': []
        }
        
        # Normalize titles to a list
        if isinstance(titles, str):
            title_list = [titles]
        else:
            title_list = titles
        
        # At this point, title_list should already be validated by the CLI
        # Just ensure we have clean titles
        title_list = [title.strip() for title in title_list if title.strip()]
        
        if not title_list:
            return {}, "No valid labels provided"
        
        # Validate test IDs by getting run information for each test
        valid_test_ids = []
        for test_id in test_ids:
            # Get test information to validate it exists
            test_response = self.client.send_get(f"get_test/{test_id}")
            if test_response.status_code != 200:
                results['test_not_found'].append(test_id)
                continue
            
            test_data = test_response.response_text
            # Validate that the test belongs to the correct project
            run_id = test_data.get('run_id')
            if run_id:
                run_response = self.client.send_get(f"get_run/{run_id}")
                if run_response.status_code == 200:
                    run_data = run_response.response_text
                    if run_data.get('project_id') == project_id:
                        valid_test_ids.append(test_id)
                    else:
                        results['test_not_found'].append(test_id)
                else:
                    results['test_not_found'].append(test_id)
            else:
                results['test_not_found'].append(test_id)
        
        # If no valid test IDs, return early
        if not valid_test_ids:
            return results, ""
        
        # Check if labels exist or create them
        existing_labels, error_message = self.get_labels(project_id)
        if error_message:
            return results, error_message
        
        # Process each title to get/create label IDs
        label_ids = []
        label_id_to_title = {}  # Map label IDs to their titles
        for title in title_list:
            # Find existing label with the same title
            label_id = None
            for label in existing_labels.get('labels', []):
                if label.get('title') == title:
                    label_id = label.get('id')
                    break
            
            # Create label if it doesn't exist
            if label_id is None:
                label_data, error_message = self.add_label(project_id, title)
                if error_message:
                    return results, error_message
                label_info = label_data.get('label', label_data)
                label_id = label_info.get('id')
            
            if label_id:
                label_ids.append(label_id)
                label_id_to_title[label_id] = title
        
        # Collect test data and validate constraints
        tests_to_update = []
        for test_id in valid_test_ids:
            # Get current test to check existing labels
            test_response = self.client.send_get(f"get_test/{test_id}")
            if test_response.status_code != 200:
                results['failed_tests'].append({
                    'test_id': test_id,
                    'error': f"Could not retrieve test {test_id}: {test_response.error_message}"
                })
                continue
            
            test_data = test_response.response_text
            current_labels = test_data.get('labels', [])
            current_label_ids = [label.get('id') for label in current_labels if label.get('id')]
            
            new_label_ids = []
            already_exists_titles = []
            
            for label_id in label_ids:
                if label_id not in current_label_ids:
                    new_label_ids.append(label_id)
                else:
                    if label_id in label_id_to_title:
                        already_exists_titles.append(label_id_to_title[label_id])
            
            if not new_label_ids:
                results['successful_tests'].append({
                    'test_id': test_id,
                    'message': f"All labels already exist on test {test_id}: {', '.join(already_exists_titles)}"
                })
                continue
            
            # Check maximum labels limit (10)
            if len(current_label_ids) + len(new_label_ids) > 10:
                results['max_labels_reached'].append(test_id)
                continue
            
            # Prepare test for update
            updated_label_ids = current_label_ids + new_label_ids
            
            new_label_titles = []
            for label_id in new_label_ids:
                if label_id in label_id_to_title:
                    new_label_titles.append(label_id_to_title[label_id])
            
            tests_to_update.append({
                'test_id': test_id,
                'labels': updated_label_ids,
                'new_labels': new_label_ids,
                'new_label_titles': new_label_titles
            })
        
        # Update tests using appropriate endpoint
        if len(tests_to_update) == 1:
            # Single test: use update_test/{test_id}
            test_info = tests_to_update[0]
            test_update_data = {'labels': test_info['labels']}
            
            update_response = self.client.send_post(f"update_test/{test_info['test_id']}", payload=test_update_data)
            
            if update_response.status_code == 200:
                new_label_titles = test_info.get('new_label_titles', [])
                new_label_count = len(new_label_titles)
                
                if new_label_count == 1:
                    message = f"Successfully added label '{new_label_titles[0]}' to test {test_info['test_id']}"
                elif new_label_count > 1:
                    message = f"Successfully added {new_label_count} labels ({', '.join(new_label_titles)}) to test {test_info['test_id']}"
                else:
                    message = f"No new labels added to test {test_info['test_id']}"
                
                results['successful_tests'].append({
                    'test_id': test_info['test_id'],
                    'message': message
                })
            else:
                results['failed_tests'].append({
                    'test_id': test_info['test_id'],
                    'error': update_response.error_message
                })
        else:
            # Multiple tests: use individual updates to ensure each test gets its specific labels
            for test_info in tests_to_update:
                test_update_data = {'labels': test_info['labels']}
                update_response = self.client.send_post(f"update_test/{test_info['test_id']}", payload=test_update_data)
                
                if update_response.status_code == 200:
                    new_label_titles = test_info.get('new_label_titles', [])
                    new_label_count = len(new_label_titles)
                    
                    if new_label_count == 1:
                        message = f"Successfully added label '{new_label_titles[0]}' to test {test_info['test_id']}"
                    elif new_label_count > 1:
                        message = f"Successfully added {new_label_count} labels ({', '.join(new_label_titles)}) to test {test_info['test_id']}"
                    else:
                        message = f"No new labels added to test {test_info['test_id']}"
                    
                    results['successful_tests'].append({
                        'test_id': test_info['test_id'],
                        'message': message
                    })
                else:
                    results['failed_tests'].append({
                        'test_id': test_info['test_id'],
                        'error': update_response.error_message
                    })
        
        return results, ""

    def get_tests_by_label(self, project_id: int, label_ids: List[int] = None, label_title: str = None, run_ids: List[int] = None) -> Tuple[List[dict], str]:
        """
        Get tests filtered by label ID or title from specific runs
        
        :param project_id: Project ID
        :param label_ids: List of label IDs to filter by
        :param label_title: Label title to filter by
        :param run_ids: List of run IDs to filter tests from (optional, defaults to all runs)
        :returns: Tuple with list of matching tests and error string
        """
        # If filtering by title, first get the label ID
        target_label_ids = label_ids or []
        if label_title and not target_label_ids:
            labels_data, error_message = self.get_labels(project_id)
            if error_message:
                return [], error_message
            
            for label in labels_data.get('labels', []):
                if label.get('title') == label_title:
                    target_label_ids.append(label.get('id'))
            
            if not target_label_ids:
                return [], ""  # No label found is a valid case with 0 results
        
        # Get runs for the project (either all runs or specific run IDs)
        if run_ids:
            # Use specific run IDs - validate they exist by getting run details
            runs = []
            for run_id in run_ids:
                run_response = self.client.send_get(f"get_run/{run_id}")
                if run_response.status_code == 200:
                    runs.append(run_response.response_text)
                else:
                    return [], f"Run ID {run_id} not found or inaccessible"
        else:
            # Get all runs for the project
            runs_response = self.client.send_get(f"get_runs/{project_id}")
            if runs_response.status_code != 200:
                return [], runs_response.error_message
            
            runs_data = runs_response.response_text
            runs = runs_data.get('runs', []) if isinstance(runs_data, dict) else runs_data
        
        # Collect all tests from all runs
        matching_tests = []
        for run in runs:
            run_id = run.get('id')
            if not run_id:
                continue
                
            # Get tests for this run
            tests_response = self.client.send_get(f"get_tests/{run_id}")
            if tests_response.status_code != 200:
                continue  # Skip this run if we can't get tests
                
            tests_data = tests_response.response_text
            tests = tests_data.get('tests', []) if isinstance(tests_data, dict) else tests_data
            
            # Filter tests that have any of the target labels
            for test in tests:
                test_labels = test.get('labels', [])
                test_label_ids = [label.get('id') for label in test_labels]
                
                # Check if any of the target label IDs are present in this test
                if any(label_id in test_label_ids for label_id in target_label_ids):
                    matching_tests.append(test)
        
        return matching_tests, ""

    def get_test_labels(self, test_ids: List[int]) -> Tuple[List[dict], str]:
        """
        Get labels for specific tests
        
        :param test_ids: List of test IDs to get labels for
        :returns: Tuple with list of test label information and error string
        """
        results = []
        
        for test_id in test_ids:
            # Get test information
            test_response = self.client.send_get(f"get_test/{test_id}")
            if test_response.status_code != 200:
                results.append({
                    'test_id': test_id,
                    'error': f"Test {test_id} not found or inaccessible",
                    'labels': []
                })
                continue
            
            test_data = test_response.response_text
            test_labels = test_data.get('labels', [])
            
            results.append({
                'test_id': test_id,
                'title': test_data.get('title', 'Unknown'),
                'status_id': test_data.get('status_id'),
                'labels': test_labels,
                'error': None
            })
        
        return results, ""

    # Test case reference management methods
    def add_case_references(self, case_id: int, references: List[str]) -> Tuple[bool, str]:
        """
        Add references to a test case
        :param case_id: ID of the test case
        :param references: List of references to add
        :returns: Tuple with success status and error string
        """
        # First get the current test case to retrieve existing references
        case_response = self.client.send_get(f"get_case/{case_id}")
        if case_response.status_code != 200:
            return False, f"Failed to retrieve test case {case_id}: {case_response.error_message}"
        
        case_data = case_response.response_text
        existing_refs = case_data.get('refs', '') or ''
        
        # Parse existing references
        existing_ref_list = []
        if existing_refs:
            existing_ref_list = [ref.strip() for ref in existing_refs.split(',') if ref.strip()]
        
        # Add new references (avoid duplicates)
        all_refs = existing_ref_list.copy()
        for ref in references:
            if ref not in all_refs:
                all_refs.append(ref)
        
        # Join all references
        new_refs_string = ','.join(all_refs)
        
        # Validate total character limit
        if len(new_refs_string) > 2000:
            return False, f"Total references length ({len(new_refs_string)} characters) exceeds 2000 character limit"
        
        # Update the test case with new references
        update_data = {'refs': new_refs_string}
        update_response = self.client.send_post(f"update_case/{case_id}", update_data)
        
        if update_response.status_code == 200:
            return True, ""
        else:
            return False, update_response.error_message

    def update_case_references(self, case_id: int, references: List[str]) -> Tuple[bool, str]:
        """
        Update references on a test case by replacing existing ones
        :param case_id: ID of the test case
        :param references: List of references to replace existing ones
        :returns: Tuple with success status and error string
        """
        # Join references
        new_refs_string = ','.join(references)
        
        # Validate total character limit
        if len(new_refs_string) > 2000:
            return False, f"Total references length ({len(new_refs_string)} characters) exceeds 2000 character limit"
        
        # Update the test case with new references
        update_data = {'refs': new_refs_string}
        update_response = self.client.send_post(f"update_case/{case_id}", update_data)
        
        if update_response.status_code == 200:
            return True, ""
        else:
            return False, update_response.error_message

    def delete_case_references(self, case_id: int, specific_references: List[str] = None) -> Tuple[bool, str]:
        """
        Delete all or specific references from a test case
        :param case_id: ID of the test case
        :param specific_references: List of specific references to delete (None to delete all)
        :returns: Tuple with success status and error string
        """
        if specific_references is None:
            # Delete all references by setting refs to empty string
            update_data = {'refs': ''}
        else:
            # First get the current test case to retrieve existing references
            case_response = self.client.send_get(f"get_case/{case_id}")
            if case_response.status_code != 200:
                return False, f"Failed to retrieve test case {case_id}: {case_response.error_message}"
            
            case_data = case_response.response_text
            existing_refs = case_data.get('refs', '') or ''
            
            if not existing_refs:
                # No references to delete
                return True, ""
            
            # Parse existing references
            existing_ref_list = [ref.strip() for ref in existing_refs.split(',') if ref.strip()]
            
            # Remove specific references
            remaining_refs = [ref for ref in existing_ref_list if ref not in specific_references]
            
            # Join remaining references
            new_refs_string = ','.join(remaining_refs)
            update_data = {'refs': new_refs_string}
        
        # Update the test case
        update_response = self.client.send_post(f"update_case/{case_id}", update_data)
        
        if update_response.status_code == 200:
            return True, ""
        else:
            return False, update_response.error_message
