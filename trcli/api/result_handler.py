"""
ResultHandler - Handles all test result-related operations for TestRail

It manages all test result operations including:
- Adding test results
- Uploading attachments to results
- Retrieving results after cancellation
"""

import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from beartype.typing import List, Tuple, Dict

from trcli.api.api_client import APIClient
from trcli.cli import Environment
from trcli.constants import FAULT_MAPPING
from trcli.data_providers.api_data_provider import ApiDataProvider
from trcli.settings import MAX_WORKERS_ADD_RESULTS


class ResultHandler:
    """Handles all test result-related operations for TestRail"""

    def __init__(
        self,
        client: APIClient,
        environment: Environment,
        data_provider: ApiDataProvider,
        get_all_tests_in_run_callback,
        handle_futures_callback,
    ):
        """
        Initialize the ResultHandler

        :param client: APIClient instance for making API calls
        :param environment: Environment configuration
        :param data_provider: Data provider for result data
        :param get_all_tests_in_run_callback: Callback to fetch all tests in a run
        :param handle_futures_callback: Callback to handle concurrent futures
        """
        self.client = client
        self.environment = environment
        self.data_provider = data_provider
        self.__get_all_tests_in_run = get_all_tests_in_run_callback
        self.handle_futures = handle_futures_callback

    def upload_attachments(self, report_results: List[Dict], results: List[Dict], run_id: int):
        """
        Getting test result id and upload attachments for it.

        :param report_results: List of test results with attachments from report
        :param results: List of created results from TestRail
        :param run_id: Run ID
        """
        tests_in_run, error = self.__get_all_tests_in_run(run_id)
        if not error:
            failed_uploads = []
            for report_result in report_results:
                case_id = report_result["case_id"]
                test_id = next((test["id"] for test in tests_in_run if test["case_id"] == case_id), None)
                result_id = next((result["id"] for result in results if result["test_id"] == test_id), None)
                for file_path in report_result.get("attachments"):
                    try:
                        with open(file_path, "rb") as file:
                            response = self.client.send_post(
                                f"add_attachment_to_result/{result_id}", files={"attachment": file}
                            )

                            # Check if upload was successful
                            if response.status_code != 200:
                                file_name = os.path.basename(file_path)

                                # Handle 413 Request Entity Too Large specifically
                                if response.status_code == 413:
                                    error_msg = FAULT_MAPPING["attachment_too_large"].format(
                                        file_name=file_name, case_id=case_id
                                    )
                                    self.environment.elog(error_msg)
                                    failed_uploads.append(f"{file_name} (case {case_id})")
                                else:
                                    # Handle other HTTP errors
                                    error_msg = FAULT_MAPPING["attachment_upload_failed"].format(
                                        file_path=file_name,
                                        case_id=case_id,
                                        error_message=response.error_message or f"HTTP {response.status_code}",
                                    )
                                    self.environment.elog(error_msg)
                                    failed_uploads.append(f"{file_name} (case {case_id})")
                    except FileNotFoundError:
                        self.environment.elog(f"Attachment file not found: {file_path} (case {case_id})")
                        failed_uploads.append(f"{file_path} (case {case_id})")
                    except Exception as ex:
                        file_name = os.path.basename(file_path) if os.path.exists(file_path) else file_path
                        self.environment.elog(f"Error uploading attachment '{file_name}' for case {case_id}: {ex}")
                        failed_uploads.append(f"{file_name} (case {case_id})")

            # Provide a summary if there were failed uploads
            if failed_uploads:
                self.environment.log(f"\nWarning: {len(failed_uploads)} attachment(s) failed to upload.")
        else:
            self.environment.elog(f"Unable to upload attachments due to API request error: {error}")

    def add_results(self, run_id: int) -> Tuple[List, str, int]:
        """
        Adds one or more new test results.

        :param run_id: run id
        :returns: Tuple with dict created resources, error string, and results count.
        """
        responses = []
        error_message = ""
        # Get pre-validated user IDs if available
        user_ids = getattr(self.environment, "_validated_user_ids", [])

        add_results_data_chunks = self.data_provider.add_results_for_cases(self.environment.batch_size, user_ids)
        # Get assigned count from data provider
        assigned_count = getattr(self.data_provider, "_assigned_count", 0)

        results_amount = sum([len(results["results"]) for results in add_results_data_chunks])

        with self.environment.get_progress_bar(results_amount=results_amount, prefix="Adding results") as progress_bar:
            with ThreadPoolExecutor(max_workers=MAX_WORKERS_ADD_RESULTS) as executor:
                futures = {
                    executor.submit(self.client.send_post, f"add_results_for_cases/{run_id}", body): body
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
                responses = ResultHandler.retrieve_results_after_cancelling(futures)
        responses = [response.response_text for response in responses]
        results = [result for results_list in responses for result in results_list]
        report_results_w_attachments = []
        for results_data_chunk in add_results_data_chunks:
            for test_result in results_data_chunk["results"]:
                if test_result["attachments"]:
                    report_results_w_attachments.append(test_result)
        if report_results_w_attachments:
            attachments_count = 0
            for result in report_results_w_attachments:
                attachments_count += len(result["attachments"])
            self.environment.log(
                f"Uploading {attachments_count} attachments " f"for {len(report_results_w_attachments)} test results."
            )
            self.upload_attachments(report_results_w_attachments, results, run_id)
        else:
            self.environment.log(f"No attachments found to upload.")

        # Log assignment results if assignment was performed
        if user_ids:
            total_failed = getattr(self.data_provider, "_total_failed_count", assigned_count)
            if assigned_count > 0:
                self.environment.log(f"Assigning failed results: {assigned_count}/{total_failed}, Done.")
            else:
                self.environment.log(f"Assigning failed results: 0/0, Done.")

        return responses, error_message, progress_bar.n

    @staticmethod
    def retrieve_results_after_cancelling(futures) -> list:
        """
        Retrieve results from futures after cancellation has been triggered.

        :param futures: Dictionary of futures
        :returns: List of successful responses
        """
        responses = []
        for future in as_completed(futures):
            if not future.cancelled():
                response = future.result()
                if not response.error_message:
                    responses.append(response)
        return responses
