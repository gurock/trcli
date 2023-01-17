import ast
from pathlib import Path
from typing import Union
from junitparser import TestCase, TestSuite, JUnitXml, IntAttr, JUnitXmlError, Element, Attr
from xml.etree import ElementTree as etree

from trcli.data_classes.matchers import Matchers
from trcli.readers.file_parser import FileParser
from trcli.data_classes.dataclass_testrail import (
    TestRailCase,
    TestRailSuite,
    TestRailSection,
    TestRailProperty,
    TestRailResult,
)

TestCase.id = IntAttr("id")
TestSuite.id = IntAttr("id")
JUnitXml.id = IntAttr("id")


class Properties(Element):
    _tag = "properties"


class Property(Element):
    _tag = "property"
    name = Attr()
    value = Attr()


class JunitSaucectlParser(FileParser):
    @classmethod
    def _add_root_element_to_tree(cls, filepath: Union[str, Path]) -> etree:
        """
        Because some of junits have XML root as testsuites and some not.
        This way make sure that we always have testsuites root.
        """
        tree = etree.parse(filepath)
        root_elem = tree.getroot()
        if root_elem.tag == "testsuites":
            return tree
        elif root_elem.tag == "testsuite":
            new_root = etree.Element("testsuites")
            new_root.insert(0, root_elem)
            return etree.ElementTree(new_root)
        else:
            raise JUnitXmlError("Invalid format.")

    def parse_file(self) -> list[TestRailSuite]:
        suite = JUnitXml.fromfile(
            self.filepath, parse_func=self._add_root_element_to_tree
        )
        self.env.log(f"Parsing JUnit report (special parser: saucectl).")
        cases_count = 0

        subsuites = {}
        subsuites_parsed_properties = {}
        for section in suite:
            if not len(section):
                continue

            divider_index = section.name.find('-')
            subsuite_name = section.name[:divider_index].strip()
            section_name = section.name[divider_index + 1:].strip()

            if subsuite_name not in subsuites.keys():
                subsuites[subsuite_name] = []
                subsuites_parsed_properties[subsuite_name] = []

            test_cases = []
            properties = []
            section_url = None
            for prop in section.properties():
                if prop.name == "url":
                    section_url = prop.value
                elif prop.name not in subsuites_parsed_properties[subsuite_name]:
                    properties.append(TestRailProperty(prop.name, prop.value))
                    subsuites_parsed_properties[subsuite_name].append(prop.name)

            for case in section:
                cases_count += 1
                case_id = None
                automation_id = None
                case_name = case.name
                attachments = []
                if self.case_matcher == Matchers.AUTO:
                    automation_id = f"{case.classname}.{case_name}"
                elif self.case_matcher == Matchers.NAME:
                    case_id, case_name = Matchers.parse_name_with_id(case_name)
                for case_props in case.iterchildren(Properties):
                    for prop in case_props.iterchildren(Property):
                        if prop.name and self.case_matcher == Matchers.PROPERTY and prop.name == "test_id":
                            case_id = int(prop.value.lower().replace("c", ""))
                        if prop.name and prop.name.startswith("testrail_attachment"):
                            attachments.append(prop.value)
                result = TestRailResult(
                    case_id,
                    elapsed=case.time,
                    junit_result_unparsed=case.result,
                    attachments=attachments
                )
                result.comment = f"SauceLabs session: {section_url}\n\n{result.comment}"
                test_cases.append(
                    TestRailCase(
                        section.id,
                        case_name,
                        case_id,
                        result=result,
                        custom_automation_id=automation_id
                    )
                )
            subsuites[subsuite_name].append(
                TestRailSection(
                    section_name,
                    suite.id,
                    time=section.time,
                    section_id=section.id,
                    testcases=test_cases,
                    properties=properties,
                )
            )
        suites = []
        for subsuite_name, test_sections in subsuites.items():
            suites.append(
                TestRailSuite(
                    subsuite_name,
                    suite_id=suite.id,
                    time=suite.time,
                    testsections=test_sections,
                    source=self.filename,
                )
            )
        self.env.log(f"Processed {cases_count} test cases in {len(subsuites)} subsuites.")
        return suites
