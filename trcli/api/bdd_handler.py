"""
BddHandler - Handles all BDD (Behavior-Driven Development) related operations for TestRail

It manages all BDD operations including:
- Uploading .feature files
- Retrieving BDD test cases
- Getting BDD template IDs
- Creating BDD test cases
"""

from beartype.typing import List, Tuple

from trcli.api.api_client import APIClient
from trcli.cli import Environment


class BddHandler:
    """Handles all BDD-related operations for TestRail"""

    def __init__(self, client: APIClient, environment: Environment):
        """
        Initialize the BddHandler

        :param client: APIClient instance for making API calls
        :param environment: Environment configuration
        """
        self.client = client
        self.environment = environment

    def add_bdd(self, section_id: int, feature_content: str) -> Tuple[List[int], str]:
        """
        Upload .feature file to TestRail BDD endpoint

        Creates TestRail test case from Gherkin .feature content.
        The Gherkin content is sent in the request body as plain text.

        Args:
            section_id: TestRail section ID where test case will be created
            feature_content: Raw .feature file content (Gherkin syntax)

        Returns:
            Tuple of (case_ids, error_message)
            - case_ids: List containing the created test case ID
            - error_message: Empty string on success, error details on failure
        """
        # Send Gherkin content as file upload (multipart/form-data)
        # TestRail expects the .feature file as an attachment
        self.environment.vlog(f"Uploading .feature file to add_bdd/{section_id}")

        files = {"attachment": ("feature.feature", feature_content, "text/plain")}

        response = self.client.send_post(f"add_bdd/{section_id}", payload=None, files=files)

        if response.status_code == 200:
            # Response is a test case object with 'id' field
            if isinstance(response.response_text, dict):
                case_id = response.response_text.get("id")
                if case_id:
                    return [case_id], ""
                else:
                    return [], "Response missing 'id' field"
            else:
                return [], "Unexpected response format"
        else:
            error_msg = response.error_message or f"Failed to upload feature file (HTTP {response.status_code})"
            return [], error_msg

    def get_bdd(self, case_id: int) -> Tuple[str, str]:
        """
        Retrieve BDD test case as .feature file content

        Args:
            case_id: TestRail test case ID

        Returns:
            Tuple of (feature_content, error_message)
            - feature_content: .feature file content (Gherkin syntax)
            - error_message: Empty string on success, error details on failure
        """
        self.environment.vlog(f"Retrieving BDD test case from get_bdd/{case_id}")
        response = self.client.send_get(f"get_bdd/{case_id}")

        if response.status_code == 200:
            # TestRail returns raw Gherkin text (not JSON)
            # APIClient treats non-JSON as error and stores str(response.content)
            if isinstance(response.response_text, dict):
                # Some versions might return JSON with 'feature' field
                feature_content = response.response_text.get("feature", "")
            elif isinstance(response.response_text, str) and response.response_text.startswith("b'"):
                # APIClient converted bytes to string representation: "b'text'"
                # Need to extract the actual content
                try:
                    # Remove b' prefix and ' suffix, then decode escape sequences
                    feature_content = response.response_text[2:-1].encode().decode("unicode_escape")
                except (ValueError, AttributeError):
                    feature_content = response.response_text
            else:
                # Plain text response
                feature_content = response.response_text

            return feature_content, ""
        else:
            error_msg = response.error_message or f"Failed to retrieve BDD test case (HTTP {response.status_code})"
            return "", error_msg

    def get_bdd_template_id(self, project_id: int) -> Tuple[int, str]:
        """
        Get the BDD template ID for a project

        Args:
            project_id: TestRail project ID

        Returns:
            Tuple of (template_id, error_message)
            - template_id: BDD template ID if found, None otherwise
            - error_message: Empty string on success, error details on failure

        API Endpoint: GET /api/v2/get_templates/{project_id}
        """
        self.environment.vlog(f"Getting templates for project {project_id}")
        response = self.client.send_get(f"get_templates/{project_id}")

        if response.status_code == 200:
            templates = response.response_text
            if isinstance(templates, list):
                self.environment.vlog(f"Retrieved {len(templates)} template(s) from TestRail")

                # Log all available templates for debugging
                if templates:
                    self.environment.vlog("Available templates:")
                    for template in templates:
                        template_id = template.get("id")
                        template_name = template.get("name", "")
                        self.environment.vlog(f"  - ID {template_id}: '{template_name}'")

                # Look for BDD template by name
                for template in templates:
                    template_name = template.get("name", "").strip()
                    template_name_lower = template_name.lower()
                    template_id = template.get("id")

                    self.environment.vlog(f"Checking template '{template_name}' (ID: {template_id})")
                    self.environment.vlog(f"  Lowercase: '{template_name_lower}'")

                    # Check for BDD template (support both US and UK spellings)
                    if (
                        "behavior" in template_name_lower
                        or "behaviour" in template_name_lower
                        or "bdd" in template_name_lower
                    ):
                        self.environment.vlog(f"  ✓ MATCH: This is the BDD template!")
                        self.environment.log(f"Found BDD template: '{template_name}' (ID: {template_id})")
                        return template_id, ""
                    else:
                        self.environment.vlog(f"  ✗ No match: Does not contain 'behavior', 'behaviour', or 'bdd'")

                # Build detailed error message with available templates
                error_parts = ["BDD template not found. Please enable BDD template in TestRail project settings."]
                if templates:
                    template_list = ", ".join([f"'{t.get('name', 'Unknown')}'" for t in templates])
                    error_parts.append(f"Available templates: {template_list}")
                    error_parts.append("The BDD template name should contain 'behavior', 'behaviour', or 'bdd'.")
                else:
                    error_parts.append("No templates are available in this project.")

                return None, "\n".join(error_parts)
            else:
                return None, "Unexpected response format from get_templates"
        else:
            error_msg = response.error_message or f"Failed to get templates (HTTP {response.status_code})"
            return None, error_msg

    def add_case_bdd(
        self, section_id: int, title: str, bdd_content: str, template_id: int, tags: List[str] = None
    ) -> Tuple[int, str]:
        """
        Create a BDD test case with Gherkin content

        Args:
            section_id: TestRail section ID where test case will be created
            title: Test case title (scenario name)
            bdd_content: Gherkin scenario content
            template_id: BDD template ID
            tags: Optional list of tags (for refs field)

        Returns:
            Tuple of (case_id, error_message)
            - case_id: Created test case ID if successful, None otherwise
            - error_message: Empty string on success, error details on failure
        """
        self.environment.vlog(f"Creating BDD test case '{title}' in section {section_id}")

        # Build request body
        # Note: custom_testrail_bdd_scenario expects an array of lines, not a single string
        bdd_lines = bdd_content.split("\n") if bdd_content else []

        body = {
            "title": title,
            "template_id": template_id,
            "custom_testrail_bdd_scenario": bdd_lines,
        }

        # Add tags as references if provided
        if tags:
            # Filter out @C tags (case IDs) and format others
            ref_tags = [tag for tag in tags if not tag.upper().startswith("@C")]
            if ref_tags:
                body["refs"] = ", ".join(ref_tags)

        response = self.client.send_post(f"add_case/{section_id}", body)

        if response.status_code == 200:
            if isinstance(response.response_text, dict):
                case_id = response.response_text.get("id")
                if case_id:
                    self.environment.vlog(f"Created BDD test case ID: {case_id}")
                    return case_id, ""
                else:
                    return None, "Response missing 'id' field"
            else:
                return None, "Unexpected response format"
        else:
            error_msg = response.error_message or f"Failed to create BDD test case (HTTP {response.status_code})"
            return None, error_msg
