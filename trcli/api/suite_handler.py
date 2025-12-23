"""
SuiteHandler - Handles all suite-related operations for TestRail

It manages all suite operations including:
- Checking if suites exist
- Resolving suite IDs by name
- Getting suite IDs for projects
- Adding new suites
- Deleting suites
"""

from beartype.typing import List, Tuple, Dict

from trcli.api.api_client import APIClient
from trcli.cli import Environment
from trcli.constants import FAULT_MAPPING
from trcli.data_providers.api_data_provider import ApiDataProvider


class SuiteHandler:
    """Handles all suite-related operations for TestRail"""

    def __init__(
        self,
        client: APIClient,
        environment: Environment,
        data_provider: ApiDataProvider,
        get_all_suites_callback,
    ):
        """
        Initialize the SuiteHandler

        :param client: APIClient instance for making API calls
        :param environment: Environment configuration
        :param data_provider: Data provider for updating suite data
        :param get_all_suites_callback: Callback to fetch all suites from TestRail
        """
        self.client = client
        self.environment = environment
        self.data_provider = data_provider
        self.__get_all_suites = get_all_suites_callback

    def check_suite_id(self, project_id: int, suite_id: int) -> Tuple[bool, str]:
        """
        Check if suite exists using get_suites endpoint

        :param project_id: project id
        :param suite_id: suite id to check
        :returns: Tuple (exists, error_message)
        """
        suites_data, error = self.__get_all_suites(project_id)
        if not error:
            available_suites = [suite for suite in suites_data if suite["id"] == suite_id]
            return (
                (True, "")
                if len(available_suites) > 0
                else (False, FAULT_MAPPING["missing_suite"].format(suite_id=suite_id))
            )
        else:
            return None, error

    def resolve_suite_id_using_name(self, project_id: int, suite_name: str) -> Tuple[int, str]:
        """
        Get suite ID matching suite name or returns -1 if unable to match any suite.

        :param project_id: project id
        :param suite_name: suite name to match
        :returns: tuple with id of the suite and error message
        """
        suite_id = -1
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
        """
        Get suite IDs for requested project_id.

        :param project_id: project id
        :returns: tuple with list of suite ids and error string
        """
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

    def add_suites(self, project_id: int, verify_callback) -> Tuple[List[Dict], str]:
        """
        Adds suites that doesn't have ID's in DataProvider.
        Runs update_data in data_provider for successfully created resources.

        :param project_id: project_id
        :param verify_callback: callback to verify returned data matches request
        :returns: Tuple with list of dict created resources and error string.
        """
        add_suite_data = self.data_provider.add_suites_data()
        responses = []
        error_message = ""
        for body in add_suite_data:
            response = self.client.send_post(f"add_suite/{project_id}", body)
            if not response.error_message:
                responses.append(response)
                if not verify_callback(body, response.response_text):
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
        (
            self.data_provider.update_data(suite_data=returned_resources)
            if len(returned_resources) > 0
            else "Update skipped"
        )
        return returned_resources, error_message

    def delete_suite(self, suite_id: int) -> Tuple[dict, str]:
        """
        Delete suite given suite id

        :param suite_id: suite id
        :returns: Tuple with dict created resources and error string.
        """
        response = self.client.send_post(f"delete_suite/{suite_id}", payload={})
        return response.response_text, response.error_message
