import json
from pathlib import Path
from beartype.typing import List, Dict, Any, Optional

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

    def parse_file(self) -> List[TestRailSuite]:
        """Parse Cucumber JSON results file and convert to TestRailSuite structure

        Returns:
            List of TestRailSuite objects with test cases and results
        """
        self.env.log(f"Parsing Cucumber JSON file: {self.filename}")

        # Read and parse the JSON file
        with open(self.filepath, "r", encoding="utf-8") as f:
            cucumber_data = json.load(f)

        # Cucumber JSON is typically an array of features
        if not isinstance(cucumber_data, list):
            raise ValueError("Cucumber JSON must be an array of features")

        # Parse features into TestRail structure
        sections = []
        for feature in cucumber_data:
            feature_sections = self._parse_feature(feature)
            sections.extend(feature_sections)

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

    def _parse_feature(self, feature: Dict[str, Any]) -> List[TestRailSection]:
        """Parse a single Cucumber feature into TestRail sections

        Args:
            feature: Feature object from Cucumber JSON

        Returns:
            List of TestRailSection objects
        """
        feature_name = feature.get("name", "Untitled Feature")
        feature_tags = self._extract_tags(feature.get("tags", []))

        # Create a section for this feature
        section = TestRailSection(name=feature_name, testcases=[])

        # Parse scenarios/scenario outlines
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

        # Background within rule (if any)
        for element in rule.get("children", []):
            element_type = element.get("type", "")
            if element_type == "background":
                lines.append("")
                background_content = self._generate_background_content(element)
                # Indent background under rule
                for line in background_content.split("\n"):
                    lines.append("  " + line if line else "")

        # Scenarios within rule
        for element in rule.get("children", []):
            element_type = element.get("type", "")
            if element_type in ("scenario", "scenario_outline"):
                lines.append("")
                scenario_content = self._generate_scenario_content(element)
                # Indent scenario under rule
                for line in scenario_content.split("\n"):
                    lines.append("  " + line if line else "")

        return "\n".join(lines)
