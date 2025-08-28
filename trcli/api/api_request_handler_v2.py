
from concurrent.futures import ThreadPoolExecutor

from typing import Optional,List, Tuple, Dict

from trcli.api.api_request_helpers import SectionHandler, CaseHandler, ProjectHandler, SuiteHandler, RunHandler, \
    PlanHandler, TestHandler, ResultHandler, AttachmentHandler, FuturesHandler, EntityException, FutureActions
from trcli.api.api_client import APIClient
from trcli.api.api_response_verify import ApiResponseVerify
from trcli.cli import Environment
from trcli.constants import ProjectErrors, RevertMessages, ProcessingMessages
from trcli.data_classes.dataclass_testrail import TestRailCase, ProjectData
from trcli.data_providers.api_data_provider_v2 import ApiDataProvider
from trcli.settings import MAX_WORKERS_ADD_RESULTS, MAX_WORKERS_ADD_CASE


class ApiRequestHandler:
    """
    Sends requests based on DataProvider data.
    Server as container for keeping all necessary handlers
    """
    def __init__(self, environment: Environment, api_client: APIClient, provider: ApiDataProvider):
        self._environment = environment
        self._client = api_client
        self._data_provider = provider
        self._response_verifier = ApiResponseVerify(self._environment.verify)
        self._section_handler = SectionHandler(environment, self._client, self._data_provider)
        self._case_handler = CaseHandler(environment, self._client, self._data_provider)
        self._project_handler = ProjectHandler(environment, self._client)
        self._suite_handler = SuiteHandler(environment, self._client, self._data_provider)
        self._run_handler = RunHandler(self._client, self._data_provider)
        self._plan_handler = PlanHandler(self._client, self._data_provider)
        self._test_handler = TestHandler(environment, self._client, self._data_provider)
        self._result_handler = ResultHandler(self._client, self._data_provider)
        self._attachment_handler = AttachmentHandler(self._client)
        self._futures_handler = FuturesHandler(environment)

    def get_project_data(self, project_name: Optional[str], project_id: Optional[int] = None) -> ProjectData:
        """
        Get project data by name or id.
        Return logic with setting error into id field is inherited from twilight genius,
        left as is. I apologize...
        :project_name: Project name
        :project_id: Project id
        :returns: ProjectData
        """
        try:
            if project_id is not None:
                return self._project_handler.get_project_data_by_id(project_id)
            return self._project_handler.get_project_data_by_name(project_name)
        except EntityException as e:
            return ProjectData(
                project_id=ProjectErrors.other_error,
                suite_mode=-1,
                error_message=e.message,
                name=project_name if project_name else "")

    def define_automation_id_field(self, project_id: int) -> Optional[str]:
        """
        Defines the automation_id field for the project.
        :project_id: The ID of the project
        :returns: The system name of the automation_id field if available, otherwise None.
        """
        return self._project_handler.define_automation_id_field(project_id)

    def resolve_suite_id_using_name(self) -> Tuple[Optional[int], str]:
        """
        Get suite ID matching suite name on data provider or returns None if unable to match any suite.
        :returns: tuple with id of the suite and error message
        """
        try:
            entities = self._section_handler.entities
            suite_name = self._data_provider.suites_input.name
            suite = next(filter(lambda x: x["name"] == suite_name, entities), None)
            if suite:
                suite_id = suite["id"]
                return suite_id, ""
            return None, ""
        except EntityException as e:
            return None, e.message
        except KeyError:
            return None, "Invalid response structure: missing 'name' or 'id' in suite data"


    def check_suite_id(self) -> Tuple[bool, str]:
        """
        Check if suite from DataProvider exist using get_suites endpoint
        :returns: True if exists in suites. False if not.
        """
        try:
            entities = self._suite_handler.entities
        except EntityException as e:
            return False, e.message
        suite_id = self._data_provider.suite_id
        matched = next((suite for suite in entities if suite["id"] == suite_id), None)
        if matched:
            return True, ""
        return False, ""

    def add_suite(self) -> Tuple[Optional[int], str]:
        """
        Adds suite that doesn't have ID's in DataProvider.
        :returns: Tuple with suite id and error string.
        """
        try:
            suite_id, error_message = self._suite_handler.add_suite()
            return suite_id, error_message
        except KeyError as e:
            return None, "Can not retrieve created suite id from response - " + str(e)

    def get_suites_ids(self) -> Tuple[List[int], str]:
        """
        Get suite IDs for requested project_id.
        : returns: tuple with list of suite ids and error string
        """
        try:
            entities = self._suite_handler.entities
        except EntityException as e:
            return [], e.message
        return [suite["id"] for suite in entities], ""

    def add_run(self) -> Tuple[Optional[int], str]:
        """
        Creates a new test run.
        :returns: Tuple with run id and error string.
        """
        try:
            return self._run_handler.add_run()
        except EntityException as e:
            return None, e.message

    def add_run_to_plan(self) -> Tuple[Optional[int], str]:
        """
        Adds a test run to a test plan.
        Returns a tuple of (run_id, error_message).
        """
        try:
            return self._plan_handler.add_run_to_plan(self._data_provider.test_plan_id)
        except (KeyError, IndexError, TypeError, ValueError):
            return None, "Invalid response structure: missing run ID"

    def get_cases_ids_in_run(self) -> Tuple[List[int], str]:
        """
        Get all tests ids in the run specified in data provider.
        :returns: Tuple with list of tests and error message
        """
        try:
            entities = self._test_handler.entities
            return [test["case_id"] for test in entities], ""
        except KeyError as e:
            return [], f"Invalid response structure getting all tests in run: missing case_id - {str(e)}"
        except EntityException as e:
            return [], e.message

    def get_run(self) -> Tuple[dict, str]:
        """
        :returns: Tuple with run (id specified in data provider) data and error message
        """
        return self._run_handler.get_run_by_id(self._data_provider.test_run_id)

    def get_run_entry_id_in_plan(self, plan_id: int) -> Tuple[Optional[str], str]:
        """
        Get entry ID of a run in a test plan.
        :plan_id: ID of the test plan
        :returns: Tuple with entry ID and error message
        """
        plan_entity, error_message = self._plan_handler.get_plan_by_id(plan_id)
        if error_message:
            return None, error_message
        run_id = self._data_provider.test_run_id
        try:
            entry_id = next(
                (
                    run["entry_id"]
                    for entry in plan_entity["entries"]
                    for run in entry["runs"]
                    if run["id"] == run_id), None)

        except (KeyError, IndexError, TypeError, ValueError):
            return None, "Invalid response structure: missing entry_id"

        if entry_id is None:
            return None, f"Entry id of run: {run_id} was not found in plan: {plan_id}.",
        return entry_id, ""

    def update_run_in_plan_entry(self) -> str:
        """
        Updates an existing run in a test plan entry.
        :returns: Tuple with updated run data and error message
        """
        return self._plan_handler.update_run_in_plan_entry(self._data_provider.test_run_id)

    def update_plan_entry(self, plan_id: int, entry_id: int) -> str:
        """
        Updates a test plan entry.
        :plan_id: ID of the test plan
        :entry_id: ID of the test plan entry
        :returns: Error message if any, otherwise an empty string.
        """
        return self._plan_handler.update_plan_entry(plan_id, entry_id)

    def update_run(self) -> str:
        """
        Updates an existing run.
        :returns: Error message if any, otherwise an empty string.
        """
        return self._run_handler.update_run(self._data_provider.test_run_id)

    def delete_created_run(self) -> str:
        """
        Deletes a created run specified in data provider.
        :returns: String indicating the result of the deletion attempt
        or empty string if no run to delete.
        """
        if created_run_id:= self._data_provider.created_test_run_id:
            error = self._run_handler.delete_run(created_run_id)
            if error:
                return  RevertMessages.RUN_NOT_DELETED_FF_RUN_ID_ERROR.format(run_id=created_run_id, error=error)
            return RevertMessages.RUN_DELETED
        return ""

    def close_run(self) -> str:
        """
        Closes an existing test run.
        :returns: Error message if any, otherwise empty string.
        """
        return self._run_handler.close_run(self._data_provider.test_run_id)

    def add_missing_sections(self) -> Tuple[List[int], str]:
        """
        Adds sections that are missing in TestRail.
        Runs update_data in data_provider for successfully created resources.
        :returns: Tuple with list of dict created resources and error string.
        """
        try:
            return self._section_handler.create_missing_sections()
        except EntityException as e:
            return [], e.message
        except KeyError as e:
            return [], f"Invalid response structure adding missing sections: {str(e)}"

    def sort_missing_and_existing_cases(self) -> str:
        """
        Collects existing test cases from TestRail and sort test cases from provided suite existing/missing.
        Update corresponding data provider fields with the results.
        """
        try:
            self._case_handler.sort_missing_and_existing_cases()
        except EntityException as e:
            return e.message
        except KeyError as e:
            return f"Invalid response structure adding missing sections: {str(e)}"
        return ""

    def delete_created_cases(self) -> str:
        """ Deletes created cases specified in data provider.
        :returns: String indicating the result of the deletion attempt,
        or empty string if no cases to delete.
        """
        if ids:=self._data_provider.created_cases_ids:
            error = self._case_handler.delete_cases(ids)
            if error:
                return RevertMessages.TEST_CASES_NOT_DELETED_F_ERROR.format(error=error)
            return RevertMessages.TEST_CASES_DELETED
        return ""

    def delete_created_sections(self) -> str:
        """ Deletes created sections specified in data provider.
        :returns: String indicating the result of the deletion attempt,
        or empty string if no sections to delete.
        """
        if added_sections_ids:= self._data_provider.created_sections_ids:
            for section_id in added_sections_ids:
                error = self._section_handler.delete_section(section_id)
                if error:
                   return (RevertMessages.
                           SECTION_NOT_DELETED_FF_SECTION_ID_ERROR.format(section_id=section_id, error=error))
            return RevertMessages.SECTION_DELETED
        return ""

    def delete_created_suite(self) -> str:
        """ Deletes created suite specified in data provider.
        :returns: String indicating the result of the deletion attempt.
        """
        if suite_id := self._data_provider.created_suite_id:
            error = self._suite_handler.delete_suite(suite_id)
            if error:
                return RevertMessages.SUITE_NOT_DELETED_FF_SUITE_ID_ERROR.format(error=error)
            return RevertMessages.SUITE_DELETED
        return ""

    def update_existing_cases(self, cases_to_update: List[TestRailCase]) -> str:
        """
        Update cases that have ID's in DataProvider.
        Runs update_data in data_provider for successfully created resources.
        :cases_to_update: List of TestRailCase objects to update
        :returns: Error string or empty if not error.
        """
        with self._environment.get_progress_bar(
                results_amount=len(cases_to_update), prefix="Updating test cases"
        ) as progress_bar, ThreadPoolExecutor(max_workers=MAX_WORKERS_ADD_CASE) as executor:
            futures = {
                executor.submit(
                    self._case_handler.update_case, case
                ): case for case in cases_to_update
            }
            error_message = self._futures_handler.handle_futures(
                futures=futures, action=FutureActions.UPDATE_CASE, progress_bar=progress_bar
            )

        return error_message


    def add_cases(self, cases_to_add: List[TestRailCase]) -> str:
        """
        Add cases that doesn't have ID in DataProvider.
        Runs update_data in data_provider for successfully created resources.
        :returns: Tuple with number of added cases and error string or empty if not error.
        """
        with self._environment.get_progress_bar(
                results_amount=len(cases_to_add), prefix="Adding test cases"
        ) as progress_bar, ThreadPoolExecutor(max_workers=MAX_WORKERS_ADD_CASE) as executor:
            futures = {
                executor.submit(
                    self._case_handler.add_case, case
                ): case for case in cases_to_add
            }
            error_message = self._futures_handler.handle_futures(
                futures=futures, action=FutureActions.ADD_CASE, progress_bar=progress_bar
            )

        return error_message

    def add_results(self) -> Tuple[int, str]:
        """
        Adds one or more new test results.
        :returns: Tuple with dict created resources and error string.
        """
        data_chunks = self._data_provider.get_results_for_cases()
        total_results = sum(len(chunk["results"]) for chunk in data_chunks)

        with self._environment.get_progress_bar(
                results_amount=total_results, prefix="Adding results"
        ) as progress_bar, ThreadPoolExecutor(max_workers=MAX_WORKERS_ADD_RESULTS) as executor:
            futures = {
                executor.submit(
                    self._result_handler.add_result_for_cases, body
                ): body for body in data_chunks
            }
            responses, error_message = self._futures_handler.handle_futures(
                futures=futures, action=FutureActions.ADD_RESULTS, progress_bar=progress_bar)

        flat_results = [r for chunk in responses for r in chunk]
        attachments = self._collect_results_with_attachments(data_chunks)
        if attachments:
            self._log_and_upload_attachments(attachments, flat_results)
        else:
            self._environment.log("No attachments found to upload.")

        return progress_bar.n, error_message

    @staticmethod
    def _collect_results_with_attachments(data_chunks: List[Dict]) -> List[Dict]:
        """Extract results that have attachments from result chunks."""
        return [
            result
            for chunk in data_chunks
            for result in chunk["results"]
            if result.get("attachments")
        ]

    def _log_and_upload_attachments(self, report_results: List[Dict], results: List[Dict]) -> None:
        """Log attachment summary and trigger upload."""
        attachment_count = sum(len(r["attachments"]) for r in report_results)
        self._environment.log(ProcessingMessages.UPLOADING_ATTACHMENTS_FF_ATTACHMENTS_RESULTS
                              .format(amount=attachment_count, results=len(report_results)))
        self._upload_attachments(report_results, results)

    def _upload_attachments(self, report_results: List[Dict], results: List[Dict]):
        """ Getting test result id and upload attachments for it. """
        try:
            self._test_handler.clean_cache() # Ensure we have the latest tests in run after adding results
            tests_in_run = self._test_handler.entities
        except EntityException as e:
            self._environment.elog(f"Unable to upload attachments due to API request error: {e.message}")
            return
        for report_result in report_results:
            case_id = report_result["case_id"]
            test_id = next((test["id"] for test in tests_in_run if test["case_id"] == case_id), None)
            result_id = next((result["id"] for result in results if result["test_id"] == test_id), None)

            for file_path in report_result.get("attachments", []):
                try:
                    with open(file_path, "rb") as file:
                        error = self._attachment_handler.add_attachment_to_result(result_id, file)
                        if error:
                            self._environment.elog(
                                f"Error uploading attachment for case {case_id}: {error}"
                            )
                except Exception as e:
                    self._environment.elog(f"Error uploading attachment for case {case_id}: {e}")