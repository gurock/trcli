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

        Sections are matched against the sections already present on TestRail using both
        `name` and `parent_id` (rather than bare name alone), so that sections at different
        positions in a nested hierarchy which happen to share a name (e.g. two different
        suites each contributing a "Setup" sub-section) are not confused with one another.

        Local sections are walked in parent-before-child (topological) order, and every match
        is applied to the live section object immediately (via `apply_created_section`) rather
        than only through an aggregated `update_data()` call at the end - both so that any
        pending child already linked to it via `parent_section` can resolve its own expected
        `parent_id` from its parent's now-known, real `section_id` later in this same pass, and
        so that same-named sibling sections under different parents (e.g. two different suites
        each contributing a "Setup" sub-section) are never conflated with one another. The
        legacy `update_data(section_data=...)` call this method used to end with matched purely
        by bare `name` (via `ApiDataProvider.__update_section_data`) and would silently
        misassign such duplicate-named sections if used here; it has intentionally been dropped
        in favor of this immediate, hierarchy-aware application.

        :param project_id: project_id
        :param suite_id: suite_id
        :param suites_data: Test suite data from provider
        :returns: Tuple with list missing section ID and error string.
        """
        returned_sections, error_message = self.__get_all_sections(project_id, suite_id)
        if not error_message:
            missing_test_sections = False
            sections_by_id = {section["id"]: section for section in returned_sections}
            sections_by_parent_and_name = {
                (section.get("parent_id"), section["name"]): section for section in returned_sections
            }
            ordered_sections = self.data_provider.sections_in_creation_order(only_pending=False)
            for section in ordered_sections:
                if self.environment.section_id:
                    if section.section_id in sections_by_id.keys():
                        section_json = sections_by_id[section.section_id]
                        self.data_provider.apply_created_section(
                            section, section_json["id"], suite_id=section_json["suite_id"]
                        )
                    else:
                        missing_test_sections = True

                expected_parent_id = (
                    section.parent_section.section_id
                    if section.parent_section is not None
                    else self.environment.section_id
                )
                section_json = sections_by_parent_and_name.get((expected_parent_id, section.name))
                if section_json is not None:
                    # Apply immediately (see docstring) so that any pending children linked via
                    # `parent_section` can resolve their own `expected_parent_id` above, later
                    # in this very same loop.
                    self.data_provider.apply_created_section(
                        section, section_json["id"], suite_id=section_json["suite_id"]
                    )
                else:
                    missing_test_sections = True
            return missing_test_sections, error_message
        else:
            return False, error_message

    def add_sections(self, project_id: int, verify_callback) -> Tuple[List[Dict], str]:
        """
        Add sections that don't yet have an ID in DataProvider, one at a time, in
        parent-before-child (topological) order.

        TestRail has no bulk `add_section` endpoint, so sections are always created one at a
        time - but for nested hierarchies this ordering is also a correctness requirement, not
        just an API limitation: each section's real, newly-assigned `section_id` is written back
        onto the live section object immediately after its own request succeeds (via
        `apply_created_section`), *before* the next section's request body is built. This
        guarantees a pending child already linked via `parent_section` can resolve its own
        correct `parent_id` on its own turn, even though its parent may have only just been
        created earlier in this very call.

        :param project_id: project_id
        :param verify_callback: callback to verify returned data matches request
        :returns: Tuple with list of dict created resources and error string.
        """
        pending_sections = self.data_provider.sections_in_creation_order()
        responses = []
        error_message = ""
        for section in pending_sections:
            body = self.data_provider.build_section_body(section)
            response = self.client.send_post(f"add_section/{project_id}", body)
            if not response.error_message:
                if not verify_callback(body, response.response_text):
                    error_message = FAULT_MAPPING["data_verification_error"]
                    break
                responses.append(response)
                self.data_provider.apply_created_section(
                    section, response.response_text["id"], suite_id=response.response_text["suite_id"]
                )
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

    def get_section(self, section_id: int) -> Tuple[dict, str]:
        """
        Retrieve a single section by ID

        :param section_id: TestRail section ID
        :returns: Tuple with (section_data_dict, error_message)
        """
        response = self.client.send_get(f"get_section/{section_id}")
        if response.error_message:
            return {}, response.error_message
        return response.response_text, ""

    def get_sections(
        self,
        project_id: int,
        suite_id: int,
        limit: int = 250,
        offset: int = 0,
    ) -> Tuple[dict, str]:
        """
        Retrieve sections for a project and suite with pagination

        :param project_id: TestRail project ID
        :param suite_id: TestRail suite ID (required)
        :param limit: Maximum number of sections to return (default: 250)
        :param offset: Offset for pagination (default: 0)
        :returns: Tuple with (paginated_response_dict, error_message)
                  Response dict contains: sections, offset, limit, size, _links
        """
        # Build query parameters
        params = [f"suite_id={suite_id}"]  # suite_id is required
        if limit != 250:
            params.append(f"limit={limit}")
        if offset > 0:
            params.append(f"offset={offset}")

        # Build URL
        query_string = "&".join(params)
        url = f"get_sections/{project_id}&{query_string}"

        response = self.client.send_get(url)
        if response.error_message:
            return {}, response.error_message
        return response.response_text, ""
