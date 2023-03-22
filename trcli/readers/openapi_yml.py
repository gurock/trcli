from pathlib import Path

import yaml

from trcli.data_classes.dataclass_testrail import (
    TestRailCase,
    TestRailSuite,
    TestRailSection,
    TestRailResult,
)
from trcli.readers.file_parser import FileParser


class OpenApiTestCase:

    def __init__(self, path: str, verb: str, response_code: str, response_description: str, operation_id: str = None):
        self.path = path
        self.verb = verb
        self.operation_id = operation_id
        self.response_code = response_code
        self.response_description = response_description

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


class OpenApiParser(FileParser):

    def parse_file(self) -> list[TestRailSuite]:
        self.env.log(f"Parsing OpenAPI specification.")

        with Path(self.filepath).open("r") as yml_file:
            spec = yaml.safe_load(yml_file)

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
                    openapi_test = OpenApiTestCase(
                        path=path,
                        verb=verb,
                        response_code=response,
                        response_description=response_data["description"] if "description" in response_data else None,
                        operation_id=verb_details["operationId"] if "operationId" in verb_details else None
                    )
                    section: TestRailSection = sections[tag]
                    section.testcases.append(
                        TestRailCase(
                            openapi_test.name,
                            custom_automation_id=f"{openapi_test.unique_id}",
                            result=TestRailResult()
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
