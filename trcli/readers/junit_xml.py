from pathlib import Path
from typing import Union
from xml.etree import ElementTree as etree

from junitparser import TestCase, TestSuite, JUnitXml, IntAttr, JUnitXmlError, Element, Attr

from trcli.data_classes.data_parsers import MatchersParser, FieldsParser
from trcli.data_classes.dataclass_testrail import (
    TestRailCase,
    TestRailSuite,
    TestRailSection,
    TestRailProperty,
    TestRailResult,
)
from trcli.readers.file_parser import FileParser

TestCase.id = IntAttr("id")
TestSuite.id = IntAttr("id")
JUnitXml.id = IntAttr("id")


class Properties(Element):
    _tag = "properties"


class Property(Element):
    _tag = "property"
    name = Attr()
    value = Attr()


class JunitParser(FileParser):
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
        self.env.log(f"Parsing JUnit report.")
        suite = JUnitXml.fromfile(
            self.filepath, parse_func=self._add_root_element_to_tree
        )

        if self.special == "saucectl":
            suites = self.split_sauce_report(suite)
        else:
            suites = [suite]

        testrail_suites = []

        for suite in suites:
            self.env.log(f"Processing suite - {suite.name}")
            cases_count = 0
            test_sections = []
            processed_section_properties = []
            for section in suite:
                if not len(section):
                    continue
                test_cases = []
                properties = []
                for prop in section.properties():
                    if prop.name not in processed_section_properties:
                        properties.append(TestRailProperty(prop.name, prop.value))
                        processed_section_properties.append(prop.name)
                for case in section:
                    cases_count += 1
                    case_id = None
                    case_name = case.name
                    attachments = []
                    result_fields = []
                    case_fields = []
                    comments = []
                    sauce_session = None
                    automation_id = f"{case.classname}.{case_name}"
                    if self.case_matcher == MatchersParser.NAME:
                        case_id, case_name = MatchersParser.parse_name_with_id(case_name)
                    for case_props in case.iterchildren(Properties):
                        for prop in case_props.iterchildren(Property):
                            if prop.name and self.case_matcher == MatchersParser.PROPERTY and prop.name == "test_id":
                                case_id = int(prop.value.lower().replace("c", ""))
                            if prop.name and prop.name.startswith("testrail_attachment"):
                                attachments.append(prop.value)
                            if prop.name and prop.name.startswith("testrail_result_field"):
                                result_fields.append(prop.value)
                            if prop.name and prop.name.startswith("testrail_result_comment"):
                                comments.append(prop.value)
                            if prop.name and prop.name.startswith("testrail_case_field"):
                                case_fields.append(prop.value)
                            if prop.name and prop.name.startswith("testrail_sauce_session"):
                                sauce_session = prop.value
                    result_fields_dict, error = FieldsParser.resolve_fields(result_fields)
                    if error:
                        self.env.elog(error)
                        raise Exception(error)
                    case_fields_dict, error = FieldsParser.resolve_fields(case_fields)
                    if error:
                        self.env.elog(error)
                        raise Exception(error)
                    result = TestRailResult(
                        case_id,
                        elapsed=case.time,
                        junit_result_unparsed=case.result,
                        attachments=attachments,
                        result_fields=result_fields_dict
                    )
                    for comment in reversed(comments):
                        result.prepend_comment(comment)
                    if sauce_session:
                        result.prepend_comment(f"SauceLabs session: {sauce_session}")
                    test_cases.append(
                        TestRailCase(
                            section.id,
                            case_name,
                            case_id,
                            result=result,
                            custom_automation_id=automation_id,
                            case_fields=case_fields_dict
                        )
                    )
                test_sections.append(
                    TestRailSection(
                        section.name,
                        suite.id,
                        time=section.time,
                        section_id=section.id,
                        testcases=test_cases,
                        properties=properties,
                    )
                )
            self.env.log(f"Processed {cases_count} test cases in {len(test_sections)} sections.")
            testrail_suites.append(
                TestRailSuite(
                    suite.name,
                    suite_id=suite.id,
                    time=suite.time,
                    testsections=test_sections,
                    source=self.filename,
                )
            )

        return testrail_suites

    def split_sauce_report(self, suite) -> list[JUnitXml]:
        self.env.log(f"Processing SauceLabs report.")
        subsuites = {}
        for section in suite:
            if not len(section):
                continue
            divider_index = section.name.find('-')
            subsuite_name = section.name[:divider_index].strip()
            section.name = section.name[divider_index + 1:].strip()
            new_xml = JUnitXml(subsuite_name)
            if subsuite_name not in subsuites.keys():
                subsuites[subsuite_name] = new_xml
            subsuites[subsuite_name].add_testsuite(section)

        for suite_name, suite in subsuites.items():
            for section in suite:
                if not len(section):
                    continue
                session_url = None
                session_prop = None
                for section_prop in section.properties():
                    if section_prop.name == "url":
                        session_prop = section_prop
                        session_url = section_prop.value
                if session_prop:
                    section.remove_property(session_prop)
                for case in section:
                    case_props = case.child(Properties)
                    if not case_props:
                        case_props = Properties()
                        case.append(case_props)
                    case_prop = Property()
                    case_prop.name = "testrail_sauce_session"
                    case_prop.value = session_url
                    case_props.append(case_prop)

        self.env.log(f"Found {len(subsuites)} SauceLabs suites.")

        return [v for k, v in subsuites.items()]
