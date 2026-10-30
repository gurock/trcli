"""
CaseFieldHandler - Handles all case field-related operations for TestRail

It manages case field query operations including:
- Retrieving all available test case custom fields
- Creating new test case custom fields (e.g. auto-creating a missing
  automation_id field - see ApiRequestHandler.add_automation_id_field)
"""

from beartype.typing import List, Optional, Tuple

from trcli.api.api_client import APIClient


class CaseFieldHandler:
    """Handles all case field-related operations for TestRail"""

    def __init__(self, client: APIClient):
        """
        Initialize the CaseFieldHandler

        :param client: APIClient instance for making API calls
        """
        self.client = client

    def get_case_fields(self) -> Tuple[list, str]:
        """
        Retrieve all available test case custom fields

        :returns: Tuple with (case_fields_list, error_message)
        """
        response = self.client.send_get("get_case_fields")
        if response.error_message:
            return [], response.error_message
        return response.response_text, ""

    def add_case_field(
        self,
        field_type: str,
        name: str,
        label: str,
        project_ids: Optional[List[int]] = None,
        is_global: bool = False,
    ) -> Tuple[dict, str, int]:
        """
        Create a new test case custom field via ``POST add_case_field``.

        This is an admin-level, instance-wide-visible action in TestRail (creating a
        custom field affects every project it's scoped to) - callers must only invoke
        this after explicit user confirmation (see
        ``ProjectBasedClient.resolve_project``'s automation_id auto-creation prompt),
        never silently.

        :param field_type: TestRail field type string. "String" confirmed valid against a
            live TestRail instance (trcliaieval staging, 2026-10-05 spike) - creates a
            working plain-text field.
        :param name: system name for the field (without the "custom_" prefix TestRail
            adds automatically), e.g. "automation_id".
        :param label: human-readable label shown in the TestRail UI, e.g. "Automation ID".
        :param project_ids: list of project IDs to scope this field to. Ignored when
            ``is_global`` is True. A project-scoped field (``is_global=False``) is the
            safer default - it only affects the specified project(s) rather than every
            project in the TestRail instance.
        :param is_global: when True, the field is created for every project instance-wide.
        :returns: Tuple with (created_field_dict, error_message, status_code). On
            failure, created_field_dict is {}. status_code lets callers distinguish a
            permission error (403 - field management requires TestRail admin rights)
            from other failures.
        """
        payload = {
            "type": field_type,
            "name": name,
            "label": label,
            "configs": [
                {
                    "context": {
                        "is_global": is_global,
                        "project_ids": [] if is_global else (project_ids or []),
                    },
                    "options": {"is_required": False},
                }
            ],
            # NOTE: must always be True, independent of is_global.
            "include_all": True,
        }
        response = self.client.send_post("add_case_field", payload)
        if response.error_message:
            return {}, response.error_message, response.status_code
        return response.response_text, "", response.status_code
