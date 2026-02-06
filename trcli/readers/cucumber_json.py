import json
from pathlib import Path
from beartype.typing import List, Dict, Any, Optional, Tuple

from trcli.cli import Environment
from trcli.data_classes.data_parsers import MatchersParser, TestRailCaseFieldsOptimizer
from trcli.data_classes.dataclass_testrail import (
    TestRailCase,
    TestRailSuite,
    TestRailSection,
    TestRailResult,
    TestRailSeparatedStep,
)
from trcli.readers.file_parser import FileParser


class CucumberParser(FileParser):
    """Parser for Cucumber JSON results format"""

    def __init__(self, environment: Environment):
        super().__init__(environment)
        self.case_matcher = environment.case_matcher
        self._bdd_case_cache = None  # Cache for BDD cases (populated on first use)
        self._api_handler = None  # Will be set when BDD matching mode is needed

    def parse_file(
        self,
        bdd_matching_mode: bool = False,
        project_id: Optional[int] = None,
        suite_id: Optional[int] = None,
        auto_create: bool = False,
    ) -> List[TestRailSuite]:
        """Parse Cucumber JSON results file and convert to TestRailSuite structure

        Args:
            bdd_matching_mode: If True, use BDD matching mode (group scenarios under existing BDD cases)
            project_id: TestRail project ID (required for BDD matching mode)
            suite_id: TestRail suite ID (required for BDD matching mode)
            auto_create: If True, mark features for auto-creation when not found (BDD matching mode only)

        Returns:
            List of TestRailSuite objects with test cases and results
        """
        self.env.log(f"Parsing Cucumber JSON file: {self.filename}")

        if bdd_matching_mode:
            self.env.log("Using BDD matching mode (matching against existing BDD test cases)")
            if not project_id or not suite_id:
                raise ValueError("project_id and suite_id are required for BDD matching mode")

        # Read and parse the JSON file
        with open(self.filepath, "r", encoding="utf-8") as f:
            cucumber_data = json.load(f)

        # Cucumber JSON is typically an array of features
        if not isinstance(cucumber_data, list):
            raise ValueError("Cucumber JSON must be an array of features")

        # Parse features into TestRail structure
        sections = []
        for feature in cucumber_data:
            feature_sections = self._parse_feature(feature, bdd_matching_mode, project_id, suite_id, auto_create)
            sections.extend(feature_sections)

        # Generate appropriate message based on mode
        if bdd_matching_mode:
            # In BDD matching mode: count scenarios from original data
            scenario_count = sum(
                sum(
                    1
                    for element in feature.get("elements", [])
                    if element.get("type", "") in ("scenario", "scenario_outline")
                )
                for feature in cucumber_data
            )
            feature_word = "feature file" if len(cucumber_data) == 1 else "feature files"
            self.env.log(f"Processed {scenario_count} scenarios in {len(cucumber_data)} {feature_word}.")
        else:
            # Standard mode: count test cases and sections
            cases_count = sum(len(section.testcases) for section in sections)
            self.env.log(f"Processed {cases_count} test cases in {len(sections)} sections.")

        # Create suite
        suite_name = self.env.suite_name if self.env.suite_name else "Cucumber Test Results"
        testrail_suite = TestRailSuite(
            name=suite_name,
            testsections=sections,
            source=self.filename,
        )

        return [testrail_suite]

    def _parse_feature(
        self,
        feature: Dict[str, Any],
        bdd_matching_mode: bool = False,
        project_id: Optional[int] = None,
        suite_id: Optional[int] = None,
        auto_create: bool = False,
    ) -> List[TestRailSection]:
        """Parse a single Cucumber feature into TestRail sections

        Args:
            feature: Feature object from Cucumber JSON
            bdd_matching_mode: If True, parse as single BDD case (group scenarios)
            project_id: TestRail project ID (required for BDD matching mode)
            suite_id: TestRail suite ID (required for BDD matching mode)
            auto_create: If True, mark cases for auto-creation when not found

        Returns:
            List of TestRailSection objects
        """
        feature_name = feature.get("name", "Untitled Feature")
        feature_tags = self._extract_tags(feature.get("tags", []))

        # Create a section for this feature
        section = TestRailSection(name=feature_name, testcases=[])

        # Branch: BDD matching mode vs. standard mode
        if bdd_matching_mode:
            # BDD Matching Mode: Parse feature as single BDD case with grouped scenarios
            test_case = self._parse_feature_as_bdd_case(feature, project_id, suite_id, auto_create)
            if test_case:
                section.testcases.append(test_case)
        else:
            # Standard Mode: Parse each scenario as separate test case
            for element in feature.get("elements", []):
                element_type = element.get("type", "")

                if element_type in ("scenario", "scenario_outline"):
                    test_case = self._parse_scenario(element, feature_name, feature_tags)
                    if test_case:
                        section.testcases.append(test_case)

        return [section] if section.testcases else []

    def _parse_scenario(
        self, scenario: Dict[str, Any], feature_name: str, feature_tags: List[str]
    ) -> Optional[TestRailCase]:
        """Parse a Cucumber scenario into TestRailCase

        Args:
            scenario: Scenario object from Cucumber JSON
            feature_name: Name of the parent feature
            feature_tags: Tags from the parent feature

        Returns:
            TestRailCase object or None
        """
        scenario_name = scenario.get("name", "Untitled Scenario")
        scenario_tags = self._extract_tags(scenario.get("tags", []))
        all_tags = feature_tags + scenario_tags

        # Build automation ID
        automation_id = self._build_automation_id(feature_name, all_tags, scenario_name)

        # Extract case ID if using matcher
        case_id = None
        if self.case_matcher == MatchersParser.NAME:
            case_id, scenario_name = MatchersParser.parse_name_with_id(scenario_name)
        elif self.case_matcher == MatchersParser.PROPERTY:
            # Look for @C<id> tag pattern
            for tag in all_tags:
                if tag.startswith("@C") or tag.startswith("@c"):
                    try:
                        case_id = int(tag[2:])
                        break
                    except ValueError:
                        pass

        # Parse steps and determine overall status
        steps = scenario.get("steps", [])
        step_results, overall_status = self._parse_steps(steps)

        # Calculate elapsed time
        elapsed_time = self._calculate_elapsed_time(steps)

        # Build comment from failures
        comment = self._build_comment_from_failures(steps)

        # Create result object
        result = TestRailResult(
            case_id=case_id,
            status_id=overall_status,
            comment=comment,
            elapsed=elapsed_time,
            custom_step_results=step_results,
        )

        # Create test case
        test_case = TestRailCase(
            title=TestRailCaseFieldsOptimizer.extract_last_words(
                scenario_name, TestRailCaseFieldsOptimizer.MAX_TESTCASE_TITLE_LENGTH
            ),
            case_id=case_id,
            result=result,
            custom_automation_id=automation_id,
            case_fields={"tags": ", ".join(all_tags)} if all_tags else {},
        )

        return test_case

    def _parse_steps(self, steps: List[Dict[str, Any]]) -> tuple:
        """Parse Cucumber steps into TestRail step results

        Args:
            steps: List of step objects from Cucumber JSON

        Returns:
            Tuple of (list of TestRailSeparatedStep, overall_status_id)
        """
        step_results = []
        overall_status = 1  # Passed by default

        for step in steps:
            keyword = step.get("keyword", "").strip()
            step_name = step.get("name", "")
            step_content = f"{keyword} {step_name}".strip()

            # Determine step status
            result = step.get("result", {})
            result_status = result.get("status", "").lower()

            # Map Cucumber status to TestRail status ID
            # 1=Passed, 3=Untested, 4=Skipped, 5=Failed
            if result_status == "passed":
                step_status_id = 1
            elif result_status == "failed":
                step_status_id = 5
                overall_status = 5  # Test failed
            elif result_status == "skipped":
                step_status_id = 4
                if overall_status == 1:  # Only update if not already failed
                    overall_status = 4
            elif result_status == "pending":
                step_status_id = 3
                if overall_status == 1:
                    overall_status = 3
            elif result_status == "undefined":
                step_status_id = 3
                if overall_status == 1:
                    overall_status = 3
            else:
                step_status_id = 3

            # Create step result
            tr_step = TestRailSeparatedStep(content=step_content)
            tr_step.status_id = step_status_id
            step_results.append(tr_step)

        return step_results, overall_status

    def _calculate_elapsed_time(self, steps: List[Dict[str, Any]]) -> Optional[str]:
        """Calculate total elapsed time from steps

        Args:
            steps: List of step objects

        Returns:
            Elapsed time string or None
        """
        total_duration = 0
        for step in steps:
            result = step.get("result", {})
            duration = result.get("duration", 0)
            if duration:
                total_duration += duration

        if total_duration > 0:
            # Convert nanoseconds to seconds
            total_seconds = total_duration / 1_000_000_000
            # Always return at least 1s if there was any duration
            if total_seconds >= 1:
                return f"{round(total_seconds)}s"
            else:
                return "1s"

        return None

    def _build_comment_from_failures(self, steps: List[Dict[str, Any]]) -> str:
        """Build comment string from failed steps

        Args:
            steps: List of step objects

        Returns:
            Comment string describing failures
        """
        failures = []
        for step in steps:
            result = step.get("result", {})
            if result.get("status", "").lower() == "failed":
                keyword = step.get("keyword", "").strip()
                step_name = step.get("name", "")
                error_message = result.get("error_message", "")

                failure_text = f"Failed: {keyword} {step_name}"
                if error_message:
                    failure_text += f"\n  Error: {error_message}"

                failures.append(failure_text)

        return "\n\n".join(failures) if failures else ""

    def _extract_tags(self, tags: List[Dict[str, str]]) -> List[str]:
        """Extract tag names from Cucumber tag objects

        Args:
            tags: List of tag objects with 'name' field

        Returns:
            List of tag name strings
        """
        return [tag.get("name", "") for tag in tags if tag.get("name")]

    def _build_automation_id(self, feature_name: str, tags: List[str], scenario_name: str) -> str:
        """Build automation ID from feature, tags, and scenario name

        Args:
            feature_name: Feature name
            tags: List of tags
            scenario_name: Scenario name

        Returns:
            Automation ID string
        """
        parts = [feature_name]

        # Add tags if present
        if tags:
            parts.extend(tags)

        # Add scenario name
        parts.append(scenario_name)

        return ".".join(parts)

    def generate_feature_file(self) -> str:
        """Generate .feature file content from parsed Cucumber JSON

        This reconstructs Gherkin syntax from the Cucumber JSON results.
        Useful for creating/updating BDD test cases in TestRail.

        Returns:
            Feature file content as string
        """
        with open(self.filepath, "r", encoding="utf-8") as f:
            cucumber_data = json.load(f)

        if not isinstance(cucumber_data, list) or not cucumber_data:
            return ""

        # Generate feature files (one per feature in JSON)
        feature_files = []

        for feature in cucumber_data:
            feature_content = self._generate_feature_content(feature)
            if feature_content:
                feature_files.append(feature_content)

        return "\n\n".join(feature_files)

    def generate_scenario_gherkin(self, feature: Dict[str, Any], scenario: Dict[str, Any]) -> Tuple[str, List[str]]:
        """Generate Gherkin content for a single scenario with feature context

        This creates a complete .feature file containing just one scenario,
        including the feature header, tags, and description.

        Args:
            feature: Feature object from Cucumber JSON
            scenario: Scenario object from Cucumber JSON

        Returns:
            Tuple of (gherkin_content, all_tags)
            - gherkin_content: Complete Gherkin .feature file for single scenario
            - all_tags: List of all tags (feature + scenario)
        """
        lines = []

        # Collect all tags (feature + scenario)
        feature_tags = self._extract_tags(feature.get("tags", []))
        scenario_tags = self._extract_tags(scenario.get("tags", []))
        all_tags = feature_tags + scenario_tags

        # Feature tags
        if feature_tags:
            lines.append(" ".join(feature_tags))

        # Feature header
        feature_name = feature.get("name", "Untitled Feature")
        feature_description = feature.get("description", "")

        lines.append(f"Feature: {feature_name}")
        if feature_description:
            for desc_line in feature_description.split("\n"):
                if desc_line.strip():
                    lines.append(f"  {desc_line.strip()}")

        lines.append("")  # Empty line after feature header

        # Background (if exists in feature) - include for context
        background = None
        for element in feature.get("elements", []):
            if element.get("type") == "background":
                background = element
                break

        if background:
            background_content = self._generate_background_content(background)
            if background_content:
                lines.append(background_content)
                lines.append("")

        # Scenario tags
        if scenario_tags:
            lines.append("  " + " ".join(scenario_tags))

        # Scenario content
        scenario_type = scenario.get("type", "scenario")
        scenario_name = scenario.get("name", "Untitled Scenario")

        if scenario_type == "scenario_outline":
            lines.append(f"  Scenario Outline: {scenario_name}")
        else:
            lines.append(f"  Scenario: {scenario_name}")

        # Steps
        for step in scenario.get("steps", []):
            keyword = step.get("keyword", "").strip()
            step_name = step.get("name", "")
            lines.append(f"    {keyword} {step_name}")

        # Examples table (for Scenario Outline)
        if scenario_type == "scenario_outline":
            examples = scenario.get("examples", [])
            if examples:
                for example_group in examples:
                    lines.append("")  # Empty line before examples

                    # Examples tags (if any)
                    example_tags = self._extract_tags(example_group.get("tags", []))
                    if example_tags:
                        lines.append("    " + " ".join(example_tags))

                    # Examples keyword
                    lines.append("    Examples:")

                    # Examples table
                    rows = example_group.get("rows", [])
                    if rows:
                        for row in rows:
                            cells = row.get("cells", [])
                            if cells:
                                row_content = " | ".join(cells)
                                lines.append(f"      | {row_content} |")

        return "\n".join(lines), all_tags

    def _generate_feature_content(self, feature: Dict[str, Any]) -> str:
        """Generate Gherkin feature content from Cucumber feature object

        Args:
            feature: Feature object from Cucumber JSON

        Returns:
            Gherkin feature content as string
        """
        lines = []

        # Feature tags
        feature_tags = self._extract_tags(feature.get("tags", []))
        if feature_tags:
            lines.append(" ".join(feature_tags))

        # Feature header
        feature_name = feature.get("name", "Untitled Feature")
        feature_description = feature.get("description", "")

        lines.append(f"Feature: {feature_name}")
        if feature_description:
            for desc_line in feature_description.split("\n"):
                if desc_line.strip():
                    lines.append(f"  {desc_line.strip()}")

        lines.append("")  # Empty line after feature header

        # Process elements in order: Background first, then scenarios/rules
        for element in feature.get("elements", []):
            element_type = element.get("type", "")

            if element_type == "background":
                background_content = self._generate_background_content(element)
                if background_content:
                    lines.append(background_content)
                    lines.append("")  # Empty line after background

            elif element_type in ("scenario", "scenario_outline"):
                scenario_content = self._generate_scenario_content(element)
                if scenario_content:
                    lines.append(scenario_content)
                    lines.append("")  # Empty line between scenarios

            elif element_type == "rule":
                rule_content = self._generate_rule_content(element)
                if rule_content:
                    lines.append(rule_content)
                    lines.append("")  # Empty line after rule

        return "\n".join(lines)

    def _generate_scenario_content(self, scenario: Dict[str, Any]) -> str:
        """Generate Gherkin scenario content

        Args:
            scenario: Scenario object from Cucumber JSON

        Returns:
            Gherkin scenario content as string
        """
        lines = []

        # Scenario tags
        scenario_tags = self._extract_tags(scenario.get("tags", []))
        if scenario_tags:
            lines.append("  " + " ".join(scenario_tags))

        # Scenario header
        scenario_type = scenario.get("type", "scenario")
        scenario_name = scenario.get("name", "Untitled Scenario")

        if scenario_type == "scenario_outline":
            lines.append(f"  Scenario Outline: {scenario_name}")
        else:
            lines.append(f"  Scenario: {scenario_name}")

        # Steps
        for step in scenario.get("steps", []):
            keyword = step.get("keyword", "").strip()
            step_name = step.get("name", "")
            lines.append(f"    {keyword} {step_name}")

        # Examples table (for Scenario Outline)
        if scenario_type == "scenario_outline":
            examples = scenario.get("examples", [])
            if examples:
                for example_group in examples:
                    lines.append("")  # Empty line before examples

                    # Examples tags (if any)
                    example_tags = self._extract_tags(example_group.get("tags", []))
                    if example_tags:
                        lines.append("    " + " ".join(example_tags))

                    # Examples keyword
                    lines.append("    Examples:")

                    # Examples table
                    rows = example_group.get("rows", [])
                    if rows:
                        for row in rows:
                            cells = row.get("cells", [])
                            if cells:
                                row_content = " | ".join(cells)
                                lines.append(f"      | {row_content} |")

        return "\n".join(lines)

    def _generate_background_content(self, background: Dict[str, Any]) -> str:
        """Generate Gherkin background content

        Args:
            background: Background object from Cucumber JSON

        Returns:
            Gherkin background content as string
        """
        lines = []

        # Background header
        background_name = background.get("name", "")
        if background_name:
            lines.append(f"  Background: {background_name}")
        else:
            lines.append("  Background:")

        # Steps
        for step in background.get("steps", []):
            keyword = step.get("keyword", "").strip()
            step_name = step.get("name", "")
            lines.append(f"    {keyword} {step_name}")

        return "\n".join(lines)

    def _generate_rule_content(self, rule: Dict[str, Any]) -> str:
        """Generate Gherkin rule content

        Args:
            rule: Rule object from Cucumber JSON

        Returns:
            Gherkin rule content as string
        """
        lines = []

        # Rule tags (if any)
        rule_tags = self._extract_tags(rule.get("tags", []))
        if rule_tags:
            lines.append("  " + " ".join(rule_tags))

        # Rule header
        rule_name = rule.get("name", "Untitled Rule")
        lines.append(f"  Rule: {rule_name}")

        # Rule description (if any)
        rule_description = rule.get("description", "")
        if rule_description:
            for desc_line in rule_description.split("\n"):
                if desc_line.strip():
                    lines.append(f"    {desc_line.strip()}")

        # Process children in order: Background first, then scenarios
        for element in rule.get("children", []):
            element_type = element.get("type", "")

            if element_type == "background":
                lines.append("")
                background_content = self._generate_background_content(element)
                # Indent background under rule
                for line in background_content.split("\n"):
                    lines.append("  " + line if line else "")

            elif element_type in ("scenario", "scenario_outline"):
                lines.append("")
                scenario_content = self._generate_scenario_content(element)
                # Indent scenario under rule
                for line in scenario_content.split("\n"):
                    lines.append("  " + line if line else "")

        return "\n".join(lines)

    def _normalize_title(self, title: str) -> str:
        """Normalize title for robust matching (delegates to API handler for consistency)

        Converts to lowercase, strips whitespace, and removes special characters.
        Hyphens, underscores, and special chars are converted to spaces for word boundaries.

        Args:
            title: The title to normalize

        Returns:
            Normalized title string
        """
        # Use shared normalization from API handler for consistency
        from trcli.api.api_request_handler import ApiRequestHandler

        return ApiRequestHandler._normalize_feature_name(title)

    def set_api_handler(self, api_handler):
        """Set API handler for BDD matching mode

        Args:
            api_handler: ApiRequestHandler instance for API calls
        """
        self._api_handler = api_handler

    def _find_case_by_title(self, feature_name: str, project_id: int, suite_id: int) -> Optional[int]:
        """Find BDD case by feature name using cached index (delegates to API handler)

        Args:
            feature_name: Feature name from Cucumber JSON
            project_id: TestRail project ID
            suite_id: TestRail suite ID

        Returns:
            Case ID if found, None otherwise (also None if error or duplicates)
        """
        if self._api_handler is None:
            self.env.elog("Error: API handler not set. Cannot find case by title.")
            return None

        # Use shared API handler method for consistency
        case_id, error, duplicates = self._api_handler.find_bdd_case_by_name(
            feature_name=feature_name, project_id=project_id, suite_id=suite_id
        )

        # Handle errors
        if error:
            self.env.elog(f"Error finding case by title: {error}")
            return None

        # Handle duplicates
        if duplicates:
            case_ids_str = ", ".join([f"C{cid}" for cid in duplicates])
            self.env.elog(f"Warning: Multiple BDD cases found with title '{feature_name}': {case_ids_str}")
            self.env.elog(f"  Cannot proceed - please ensure unique feature names in TestRail")
            return None

        # Handle not found (case_id == -1)
        if case_id == -1:
            return None

        # Success
        return case_id

    def _extract_case_id_from_tags(self, feature_tags: List[str], scenario_tags: List[str]) -> Optional[int]:
        """Extract case ID from @C<id> tags

        Priority: Feature-level tags > Scenario-level tags
        This ensures feature-level @C123 tag applies to all scenarios.

        Args:
            feature_tags: Tags from feature level
            scenario_tags: Tags from scenario level

        Returns:
            Case ID if found, None otherwise
        """
        # Priority 1: Feature-level tags (applies to all scenarios)
        for tag in feature_tags:
            if tag.startswith("@C") or tag.startswith("@c"):
                try:
                    return int(tag[2:])
                except ValueError:
                    pass

        # Priority 2: Scenario-level tags (fallback)
        for tag in scenario_tags:
            if tag.startswith("@C") or tag.startswith("@c"):
                try:
                    return int(tag[2:])
                except ValueError:
                    pass

        return None

    def _validate_bdd_case_exists(self, case_id: int) -> Tuple[bool, Optional[str]]:
        """Validate that case exists and is a BDD template case

        Args:
            case_id: TestRail case ID to validate

        Returns:
            Tuple of (is_valid, error_message)
            - is_valid: True if case exists and is BDD template
            - error_message: Error description if validation fails, None otherwise
        """
        if self._api_handler is None:
            return False, "API handler not set"

        try:
            # Fetch case details from TestRail API (use api_handler's client)
            response = self._api_handler.client.send_get(f"get_case/{case_id}")

            # Check if request failed or returned no data
            if response.error_message or not response.response_text:
                error_msg = response.error_message if response.error_message else "Case not found"
                return False, f"Case C{case_id} not found: {error_msg}"

            case_data = response.response_text

            # Resolve BDD case field name dynamically
            bdd_field_name = self._api_handler.get_bdd_case_field_name()

            # Validate it's a BDD template case (has BDD scenarios field with content)
            if not case_data.get(bdd_field_name):
                return False, f"Case C{case_id} is not a BDD template case (missing field: {bdd_field_name})"

            return True, None

        except Exception as e:
            return False, f"Error validating case C{case_id}: {str(e)}"

    def _parse_feature_as_bdd_case(
        self, feature: Dict[str, Any], project_id: int, suite_id: int, auto_create: bool = False
    ) -> Optional[TestRailCase]:
        """Parse Cucumber feature as single BDD test case with multiple scenario results

        This method is used in BDD matching mode (WITHOUT --upload-feature).
        It groups all scenarios from a feature under a single BDD test case.

        Workflow:
        1. Extract case ID from @C<id> tags (feature > scenario priority)
        2. Fallback to feature name matching via cached lookup
        3. If not found and auto_create=True: Return special marker for auto-creation
        4. Validate case exists and is BDD template
        5. Parse all scenarios as BDD scenario results
        6. Aggregate status (fail-fast: any scenario failure → feature fails)
        7. Create single TestRailCase with custom_testrail_bdd_scenario_results

        Args:
            feature: Feature object from Cucumber JSON
            project_id: TestRail project ID
            suite_id: TestRail suite ID
            auto_create: If True, mark for auto-creation when not found

        Returns:
            TestRailCase with BDD scenario results, or None if case not found and auto_create=False
            Returns TestRailCase with case_id=-1 if not found and auto_create=True (marker for creation)
        """
        feature_name = feature.get("name", "Untitled Feature")
        feature_tags = self._extract_tags(feature.get("tags", []))

        # Step 1: Try to extract case ID from tags
        case_id = None
        for tag in feature_tags:
            if tag.startswith("@C") or tag.startswith("@c"):
                try:
                    case_id = int(tag[2:])
                    self.env.vlog(f"Found case ID from feature tag: C{case_id}")
                    break
                except ValueError:
                    pass

        # Step 2: Fallback to feature name matching (cached lookup)
        if case_id is None:
            case_id = self._find_case_by_title(feature_name, project_id, suite_id)
            if case_id:
                self.env.vlog(f"Found case ID from feature name '{feature_name}': C{case_id}")

        # Step 3: Handle case not found
        if case_id is None:
            if auto_create:
                self.env.log(f"Feature '{feature_name}' not found in TestRail - will auto-create")
                # Return special marker (case_id=-1) to indicate this needs creation
                # Store feature data for later creation
                case_id = -1  # Marker for auto-creation
            else:
                self.env.elog(f"Error: No BDD case found for feature '{feature_name}'")
                self.env.elog(f"  Add @C<id> tag to feature or ensure case exists with title '{feature_name}'")
                return None

        # Step 4: Validate case exists (skip validation if marked for creation)
        if case_id != -1:
            is_valid, error_message = self._validate_bdd_case_exists(case_id)
            if not is_valid:
                self.env.elog(f"Error validating case for feature '{feature_name}': {error_message}")
                return None

        # Step 4: Parse all scenarios as BDD scenario results
        bdd_scenario_results = []
        overall_status = 1  # Passed by default (fail-fast logic applied below)
        total_elapsed = 0

        for element in feature.get("elements", []):
            element_type = element.get("type", "")

            if element_type in ("scenario", "scenario_outline"):
                scenario_name = element.get("name", "Untitled Scenario")
                scenario_tags = self._extract_tags(element.get("tags", []))

                # Parse steps to determine scenario status
                steps = element.get("steps", [])
                _, scenario_status = self._parse_steps(steps)

                # Calculate elapsed time for this scenario
                scenario_elapsed = 0
                for step in steps:
                    result = step.get("result", {})
                    duration = result.get("duration", 0)
                    if duration:
                        scenario_elapsed += duration

                total_elapsed += scenario_elapsed

                # Create BDD scenario result (using TestRailSeparatedStep structure)
                bdd_scenario = TestRailSeparatedStep(content=scenario_name)
                bdd_scenario.status_id = scenario_status
                bdd_scenario_results.append(bdd_scenario)

                # Fail-fast: If any scenario fails, entire feature fails
                if scenario_status == 5:  # Failed
                    overall_status = 5
                elif scenario_status == 4 and overall_status != 5:  # Skipped
                    overall_status = 4
                elif scenario_status == 3 and overall_status == 1:  # Untested/Pending
                    overall_status = 3

        # Step 5: Calculate elapsed time (pass as numeric seconds, TestRailResult.__post_init__ will format)
        elapsed_time = None
        if total_elapsed > 0:
            total_seconds = total_elapsed / 1_000_000_000
            elapsed_time = str(total_seconds)  # Pass as string number, will be formatted by __post_init__

        # Step 6: Build comment from failures (aggregate all scenario failures)
        comment_parts = []
        for element in feature.get("elements", []):
            if element.get("type", "") in ("scenario", "scenario_outline"):
                scenario_name = element.get("name", "Untitled Scenario")
                steps = element.get("steps", [])

                # Check if scenario failed
                scenario_failed = False
                for step in steps:
                    result = step.get("result", {})
                    if result.get("status", "").lower() == "failed":
                        scenario_failed = True
                        break

                if scenario_failed:
                    failure_comment = self._build_comment_from_failures(steps)
                    if failure_comment:
                        comment_parts.append(f"Scenario: {scenario_name}\n{failure_comment}")

        comment = "\n\n".join(comment_parts) if comment_parts else ""

        # Step 7: Create result with BDD scenario results
        # Resolve BDD result field name dynamically
        bdd_result_field_name = self._api_handler.get_bdd_result_field_name()

        result = TestRailResult(
            case_id=case_id,
            status_id=overall_status,
            comment=comment,
            elapsed=elapsed_time,
        )

        # Add BDD scenario results to result_fields dict (for serialization)
        # Convert TestRailSeparatedStep objects to dicts for API
        result.result_fields[bdd_result_field_name] = [
            {"content": step.content, "status_id": step.status_id} for step in bdd_scenario_results
        ]

        # Step 8: Create test case
        test_case = TestRailCase(
            title=TestRailCaseFieldsOptimizer.extract_last_words(
                feature_name, TestRailCaseFieldsOptimizer.MAX_TESTCASE_TITLE_LENGTH
            ),
            case_id=case_id,
            result=result,
        )

        self.env.vlog(
            f"Parsed feature '{feature_name}' as BDD case C{case_id} "
            f"with {len(bdd_scenario_results)} scenarios (status: {overall_status})"
        )

        return test_case
