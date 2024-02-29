import json
from pathlib import Path
from beartype.typing import List

import yaml
from trcli.data_classes.data_parsers import TestRailCaseFieldsOptimizer

from trcli.data_classes.dataclass_testrail import (
    TestRailCase,
    TestRailSuite,
    TestRailSection,
    TestRailResult,
)
from trcli.readers.file_parser import FileParser
from openapi_spec_validator import validate_spec, openapi_v30_spec_validator
from openapi_spec_validator.readers import read_from_filename
from prance import ResolvingParser


class OpenApiTestCase:

    def __init__(
            self,
            path: str,
            verb: str,
            response_code: str,
            response_description: str,
            operation_id: str = None,
            request_details: dict = None,
            response_details: dict = None
    ):
        self.path = path
        self.verb = verb
        self.operation_id = operation_id
        self.response_code = response_code
        self.response_description = response_description
        self.request_details = request_details
        self.response_details = response_details

    @property
    def name(self) -> str:
        name = f"{self.verb.upper()} {self.path} -> {self.response_code}"
        if self.response_description:
            name += f" ({self.response_description})"
        return name

    @property
    def unique_id(self) -> str:
        name = f"{self.path}.{self.verb.upper()}.{self.response_code}"
        return name

    @property
    def preconditions(self) -> str:
        details = self.request_details.copy()
        preconditions = ""

        key = "deprecated"
        if key in details and details[key]:
            preconditions += """
||| :WARNING
|| ENDPOINT IS DEPRECATED
"""

        key = "summary"
        if key in details and details[key]:
            preconditions += self._format_text("Summary", details[key])
            details.pop(key)

        key = "description"
        if key in details and details[key]:
            preconditions += self._format_text("Description", details[key])
            details.pop(key)

        key = "externalDocs"
        if key in details and details[key]:
            preconditions += self._format_text("External Docs", details[key])
            details.pop(key)

        return preconditions

    @property
    def steps(self) -> str:
        details = self.request_details.copy()
        steps = f"""
Request
=======
    {self.verb.upper()} {self.path}
"""

        key = "parameters"
        if key in details and details[key]:
            steps += self._format_text("Parameters", details[key])
            details.pop(key)

        key = "requestBody"
        if key in details and details[key]:
            steps += self._format_text("Request body schema", details[key])
            details.pop(key)

        key = "security"
        if key in details and details[key]:
            steps += self._format_text("Security", details[key])
            details.pop(key)

        return steps

    @property
    def expected(self) -> str:
        details = self.response_details.copy()
        expected = f"""
Response code
=======
{self.response_code} ({self.response_description})
"""
        key = "content"
        if key in details and details[key]:
            expected += self._format_text("Response content", details[key])
            details.pop(key)
        return expected

    @staticmethod
    def _format_text(title, details):
        text = f"""
{title}
=======
"""
        if type(details) is str:
            text += details
        else:
            details = yaml.dump(details, Dumper=yaml.Dumper)
            for line in details.splitlines(keepends=True):
                text += f"    {line}"
        return text


class OpenApiParser(FileParser):

    def parse_file(self) -> List[TestRailSuite]:
        self.env.log(f"Parsing OpenAPI specification.")
        spec = self.resolve_openapi_spec()
        sections = {
            "untagged": TestRailSection("untagged")
        }
        cases_count = 0
        for path, path_data in spec["paths"].items():
            for verb, verb_details in path_data.items():
                tag = None
                if verb.lower() not in ["get", "put", "patch", "post", "delete", "options", "trace", "connect"]:
                    continue
                if "responses" not in verb_details.keys():
                    continue
                if "tags" in verb_details.keys() and len(verb_details["tags"]):
                    tag = verb_details["tags"][0]
                    if tag not in sections:
                        sections[tag] = TestRailSection(tag)
                for response, response_data in verb_details["responses"].items():
                    request_details = verb_details.copy()
                    request_details.pop("responses")
                    openapi_test = OpenApiTestCase(
                        path=path,
                        verb=verb,
                        response_code=response,
                        response_description=response_data["description"] if "description" in response_data else None,
                        operation_id=verb_details["operationId"] if "operationId" in verb_details else None,
                        request_details=request_details,
                        response_details=response_data
                    )
                    section: TestRailSection = sections[tag]
                    section.testcases.append(
                        TestRailCase(
                            TestRailCaseFieldsOptimizer.extract_last_words(openapi_test.name, TestRailCaseFieldsOptimizer.MAX_TESTCASE_TITLE_LENGTH),
                            custom_automation_id=f"{openapi_test.unique_id}",
                            result=TestRailResult(),
                            case_fields={
                                "template_id": 1,
                                "custom_preconds": openapi_test.preconditions,
                                "custom_steps": openapi_test.steps,
                                "custom_expected": openapi_test.expected
                            }
                        )
                    )
                    cases_count += 1

        test_suite = TestRailSuite(
            spec["info"]["title"],
            testsections=[section for _name, section in sections.items() if section.testcases],
            source=self.filename
        )

        self.env.log(f"Processed {cases_count} test cases based on possible responses.")

        return [test_suite]

    def resolve_openapi_spec(self) -> dict:
        spec_path = self.filepath
        unresolved_spec_dict, spec_url = read_from_filename(str(spec_path.absolute()))
        parser = ResolvingParser(spec_string=json.dumps(unresolved_spec_dict), backend='openapi-spec-validator')
        spec_dictionary = parser.specification
        validate_spec(spec_dictionary, validator=openapi_v30_spec_validator)
        return spec_dictionary
