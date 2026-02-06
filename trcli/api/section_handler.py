"""
SectionHandler - Handles all section-related operations for TestRail

It manages all section operations including:
- Checking for missing sections
- Adding new sections
- Deleting sections
"""

from beartype.typing import List, Tuple, Dict

from trcli.api.api_client import APIClient
from trcli.cli import Environment
from trcli.constants import FAULT_MAPPING
from trcli.data_classes.dataclass_testrail import TestRailSuite
from trcli.data_providers.api_data_provider import ApiDataProvider


class SectionHandler:
    """Handles all section-related operations for TestRail"""

    def __init__(
        self,
        client: APIClient,
        environment: Environment,
        data_provider: ApiDataProvider,
        get_all_sections_callback,
    ):
        """
        Initialize the SectionHandler

        :param client: APIClient instance for making API calls
        :param environment: Environment configuration
        :param data_provider: Data provider for updating section data
        :param get_all_sections_callback: Callback to fetch all sections from TestRail
        """
        self.client = client
        self.environment = environment
        self.data_provider = data_provider
        self.__get_all_sections = get_all_sections_callback

    def check_missing_section_ids(self, project_id: int, suite_id: int, suites_data: TestRailSuite) -> Tuple[bool, str]:
        """
        Check what section id's are missing in DataProvider.

        :param project_id: project_id
        :param suite_id: suite_id
        :param suites_data: Test suite data from provider
        :returns: Tuple with list missing section ID and error string.
        """
        returned_sections, error_message = self.__get_all_sections(project_id, suite_id)
        if not error_message:
            missing_test_sections = False
            sections_by_id = {section["id"]: section for section in returned_sections}
            sections_by_name = {section["name"]: section for section in returned_sections}
            section_data = []
            for section in suites_data.testsections:
                if self.environment.section_id:
                    if section.section_id in sections_by_id.keys():
                        section_json = sections_by_id[section.section_id]
                        section_data.append(
                            {
                                "section_id": section_json["id"],
                                "suite_id": section_json["suite_id"],
                                "name": section_json["name"],
                            }
                        )
                    else:
                        missing_test_sections = True
                if section.name in sections_by_name.keys():
                    section_json = sections_by_name[section.name]
                    section_data.append(
                        {
                            "section_id": section_json["id"],
                            "suite_id": section_json["suite_id"],
                            "name": section_json["name"],
                        }
                    )
                else:
                    missing_test_sections = True
            self.data_provider.update_data(section_data=section_data)
            return missing_test_sections, error_message
        else:
            return False, error_message

    def add_sections(self, project_id: int, verify_callback) -> Tuple[List[Dict], str]:
        """
        Add sections that doesn't have ID in DataProvider.
        Runs update_data in data_provider for successfully created resources.

        :param project_id: project_id
        :param verify_callback: callback to verify returned data matches request
        :returns: Tuple with list of dict created resources and error string.
        """
        add_sections_data = self.data_provider.add_sections_data()
        responses = []
        error_message = ""
        for body in add_sections_data:
            response = self.client.send_post(f"add_section/{project_id}", body)
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
                "section_id": response.response_text["id"],
                "suite_id": response.response_text["suite_id"],
                "name": response.response_text["name"],
            }
            for response in responses
        ]
        (
            self.data_provider.update_data(section_data=returned_resources)
            if len(returned_resources) > 0
            else "Update skipped"
        )
        return returned_resources, error_message

    def delete_sections(self, added_sections: List[Dict]) -> Tuple[List, str]:
        """
        Delete section given add_sections response

        :param added_sections: List of sections to delete
        :returns: Tuple with dict created resources and error string.
        """
        responses = []
        error_message = ""
        for section in added_sections:
            response = self.client.send_post(f"delete_section/{section['section_id']}", payload={})
            if not response.error_message:
                responses.append(response.response_text)
            else:
                error_message = response.error_message
                break
        return responses, error_message
