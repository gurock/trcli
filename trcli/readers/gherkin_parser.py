from pathlib import Path
from beartype.typing import List, Dict, Any, Optional
from gherkin.parser import Parser
from gherkin.token_scanner import TokenScanner

from trcli.cli import Environment
from trcli.data_classes.data_parsers import MatchersParser, TestRailCaseFieldsOptimizer
from trcli.data_classes.dataclass_testrail import (
    TestRailCase,
    TestRailSuite,
    TestRailSection,
    TestRailProperty,
    TestRailResult,
    TestRailSeparatedStep,
)
from trcli.readers.file_parser import FileParser


class GherkinParser(FileParser):
    """Parser for Gherkin .feature files"""

    def __init__(self, environment: Environment):
        super().__init__(environment)
        self.case_matcher = environment.case_matcher

    def parse_file(self) -> List[TestRailSuite]:
        """Parse a Gherkin .feature file and convert to TestRailSuite structure"""
        self.env.log(f"Parsing Gherkin feature file: {self.filename}")

        # Read and parse the feature file
        with open(self.filepath, "r", encoding="utf-8") as f:
            feature_text = f.read()

        parser = Parser()
        scanner = TokenScanner(feature_text)
        gherkin_document = parser.parse(scanner)

        # Extract feature
        feature = gherkin_document.get("feature")
        if not feature:
            raise ValueError("No feature found in the Gherkin file")

        # Parse feature into TestRail structure
        suite_name = self.env.suite_name if self.env.suite_name else feature.get("name", self.filepath.stem)
        sections = self._parse_feature_children(feature)

        cases_count = sum(len(section.testcases) for section in sections)
        self.env.log(f"Processed {cases_count} test cases in {len(sections)} sections.")

        testrail_suite = TestRailSuite(
            name=suite_name,
            testsections=sections,
            source=self.filename,
        )

        return [testrail_suite]

    def _parse_feature_children(self, feature: Dict[str, Any]) -> List[TestRailSection]:
        """Parse feature children (Background, Scenarios, Scenario Outlines) into sections"""
        sections = []
        background_steps = None

        # First pass: extract background if present
        for child in feature.get("children", []):
            if "background" in child:
                background_steps = self._extract_steps(child["background"])
                break

        # Group scenarios into a single section (using feature name)
        feature_name = feature.get("name", "Feature")
        section = TestRailSection(name=feature_name, testcases=[])

        # Store background as section property if exists
        if background_steps:
            background_text = "\n".join([f"{step['keyword']}{step['text']}" for step in background_steps])
            section.properties = [TestRailProperty(name="background", value=background_text)]

        # Second pass: process scenarios
        for child in feature.get("children", []):
            if "scenario" in child:
                scenario = child["scenario"]
                # Check if it's a Scenario Outline
                if scenario.get("keyword") == "Scenario Outline":
                    # Expand scenario outline into multiple test cases
                    test_cases = self._parse_scenario_outline(scenario, feature_name)
                    section.testcases.extend(test_cases)
                else:
                    # Regular scenario
                    test_case = self._parse_scenario(scenario, feature_name)
                    if test_case:
                        section.testcases.append(test_case)

        if section.testcases:
            sections.append(section)

        return sections

    def _parse_scenario(self, scenario: Dict[str, Any], feature_name: str) -> Optional[TestRailCase]:
        """Parse a single Gherkin scenario into a TestRailCase"""
        scenario_name = scenario.get("name", "Untitled Scenario")
        tags = self._extract_tags(scenario)
        steps = self._extract_steps(scenario)

        # Extract case ID if using name or property matcher
        case_id = None
        if self.case_matcher == MatchersParser.NAME:
            case_id, scenario_name = MatchersParser.parse_name_with_id(scenario_name)
        elif self.case_matcher == MatchersParser.PROPERTY:
            # Look for @C<id> tag pattern
            for tag in tags:
                if tag.startswith("@C") or tag.startswith("@c"):
                    try:
                        case_id = int(tag[2:])
                        break
                    except ValueError:
                        pass

        # Create automation ID from feature, tags, and scenario name
        # Format: "feature_name.@tag1.@tag2.scenario_name"
        tag_part = ".".join(tags) if tags else ""
        automation_id = f"{feature_name}.{tag_part}.{scenario_name}" if tag_part else f"{feature_name}.{scenario_name}"

        # Convert Gherkin steps to TestRail separated steps
        step_results = []
        for step in steps:
            step_content = f"{step['keyword']}{step['text']}"
            tr_step = TestRailSeparatedStep(content=step_content)
            tr_step.status_id = 3  # Untested by default
            step_results.append(tr_step)

        # Create result object
        result = TestRailResult(
            case_id=case_id,
            status_id=3,  # Untested (no execution results yet)
            comment=f"Gherkin scenario with {len(steps)} steps",
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
            case_fields={"tags": ", ".join(tags)} if tags else {},
        )

        return test_case

    def _parse_scenario_outline(self, scenario_outline: Dict[str, Any], feature_name: str) -> List[TestRailCase]:
        """Parse a Scenario Outline into multiple TestRailCases (one per example row)"""
        test_cases = []
        outline_name = scenario_outline.get("name", "Untitled Outline")
        tags = self._extract_tags(scenario_outline)
        steps = self._extract_steps(scenario_outline)
        examples = scenario_outline.get("examples", [])

        if not examples:
            # No examples, treat as regular scenario
            test_case = self._parse_scenario(scenario_outline, feature_name)
            if test_case:
                return [test_case]

        # Process each example table
        for example_table in examples:
            table_header = example_table.get("tableHeader", {})
            table_body = example_table.get("tableBody", [])

            # Get column names from header
            header_cells = table_header.get("cells", [])
            column_names = [cell.get("value", "") for cell in header_cells]

            # Create a test case for each row
            for row_idx, row in enumerate(table_body, start=1):
                row_cells = row.get("cells", [])
                row_values = [cell.get("value", "") for cell in row_cells]

                # Create parameter mapping
                params = dict(zip(column_names, row_values))

                # Replace placeholders in scenario name
                scenario_name = self._replace_placeholders(outline_name, params)
                scenario_name = f"{outline_name} [Example {row_idx}]"

                # Replace placeholders in steps
                instantiated_steps = []
                for step in steps:
                    step_text = self._replace_placeholders(step["text"], params)
                    instantiated_steps.append(
                        {"keyword": step["keyword"], "text": step_text, "keywordType": step.get("keywordType")}
                    )

                # Create automation ID
                tag_part = ".".join(tags) if tags else ""
                automation_id = (
                    f"{feature_name}.{tag_part}.{outline_name}.example_{row_idx}"
                    if tag_part
                    else f"{feature_name}.{outline_name}.example_{row_idx}"
                )

                # Convert steps to TestRail format
                step_results = []
                for step in instantiated_steps:
                    step_content = f"{step['keyword']}{step['text']}"
                    tr_step = TestRailSeparatedStep(content=step_content)
                    tr_step.status_id = 3  # Untested
                    step_results.append(tr_step)

                # Create result
                result = TestRailResult(
                    case_id=None,
                    status_id=3,
                    comment=f"Scenario Outline example {row_idx}: {params}",
                    custom_step_results=step_results,
                )

                # Create test case
                test_case = TestRailCase(
                    title=TestRailCaseFieldsOptimizer.extract_last_words(
                        scenario_name, TestRailCaseFieldsOptimizer.MAX_TESTCASE_TITLE_LENGTH
                    ),
                    case_id=None,
                    result=result,
                    custom_automation_id=automation_id,
                    case_fields=(
                        {"tags": ", ".join(tags), "example_params": str(params)}
                        if tags
                        else {"example_params": str(params)}
                    ),
                )

                test_cases.append(test_case)

        return test_cases

    @staticmethod
    def _extract_tags(scenario: Dict[str, Any]) -> List[str]:
        """Extract tags from a scenario"""
        tags = []
        for tag in scenario.get("tags", []):
            tag_name = tag.get("name", "")
            if tag_name:
                tags.append(tag_name)
        return tags

    @staticmethod
    def _extract_steps(scenario_or_background: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Extract steps from a scenario or background"""
        steps = []
        for step in scenario_or_background.get("steps", []):
            steps.append(
                {
                    "keyword": step.get("keyword", ""),
                    "text": step.get("text", ""),
                    "keywordType": step.get("keywordType", ""),
                }
            )
        return steps

    @staticmethod
    def _replace_placeholders(text: str, params: Dict[str, str]) -> str:
        """Replace <placeholder> with actual values from params"""
        result = text
        for key, value in params.items():
            result = result.replace(f"<{key}>", value)
        return result
