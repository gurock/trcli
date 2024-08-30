import glob
from pathlib import Path
from beartype.typing import Union, List
from unittest import TestCase, TestSuite
from xml.etree import ElementTree as etree

from junitparser import JUnitXml, JUnitXmlError, Element, Attr

from trcli.cli import Environment
from trcli.data_classes.data_parsers import MatchersParser, FieldsParser, TestRailCaseFieldsOptimizer
from trcli.data_classes.dataclass_testrail import (
    TestRailCase,
    TestRailSuite,
    TestRailSection,
    TestRailProperty,
    TestRailResult, TestRailSeparatedStep,
)
from trcli.readers.file_parser import FileParser

TestCase.id = Attr("id")
TestSuite.id = Attr("id")
JUnitXml.id = Attr("id")


class Properties(Element):
    _tag = "properties"


class Property(Element):
    _tag = "property"
    name = Attr()
    value = Attr()


class JunitParser(FileParser):

    def __init__(self, environment: Environment):
        super().__init__(environment)
        self.case_matcher = environment.case_matcher
        self.special = environment.special_parser

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

    @staticmethod
    def check_file(filepath: Union[str, Path]) -> Path:
        filepath = Path(filepath)
        files = glob.glob(str(filepath))
        if not files:
            raise FileNotFoundError("File not found.")
        elif len(files) == 1:
            return Path().cwd().joinpath(files[0])
        sub_suites = []
        for file in files:
            suite = JUnitXml.fromfile(file)
            sub_suites.append(suite)
        suite = sub_suites.pop(0)
        for sub_suite in sub_suites:
            suite += sub_suite
        merged_report_path = Path().cwd().joinpath("Merged-JUnit-report.xml")
        suite.write(merged_report_path)
        return merged_report_path

    def parse_file(self) -> List[TestRailSuite]:
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
            if suite.name:
                self.env.log(f"Processing JUnit suite - {suite.name}")
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
                    result_steps = []
                    sauce_session = None
                    automation_id = f"{case.classname}.{case_name}"
                    if self.case_matcher == MatchersParser.NAME:
                        case_id, case_name = MatchersParser.parse_name_with_id(case_name)
                    for case_props in case.iterchildren(Properties):
                        for prop in case_props.iterchildren(Property):
                            if prop.name and self.case_matcher == MatchersParser.PROPERTY and prop.name == "test_id":
                                case_id = int(prop.value.lower().replace("c", ""))
                            if prop.name and prop.name.startswith("testrail_result_step"):
                                status, step = prop.value.split(':', maxsplit=1)
                                step = TestRailSeparatedStep(step.strip())
                                status_dict = {
                                    "passed": 1,
                                    "untested": 3,
                                    "skipped": 4,
                                    "failed": 5
                                }
                                step.status_id = status_dict[status.lower().strip()]
                                result_steps.append(step)
                            if prop.name and prop.name.startswith("testrail_attachment"):
                                attachments.append(prop.value)
                            if prop.name and prop.name.startswith("testrail_result_field"):
                                result_fields.append(prop.value)
                            if prop.name and prop.name.startswith("testrail_result_comment"):
                                comments.append(prop.value)
                            if prop.name and prop.name.startswith("testrail_case_field"):
                                if prop._elem.text is not None and prop._elem.text.strip() != "":
                                    case_fields.append(prop._elem.text.strip())
                                else:
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
                        result_fields=result_fields_dict,
                        custom_step_results=result_steps
                    )
                    for comment in reversed(comments):
                        result.prepend_comment(comment)
                    if sauce_session:
                        result.prepend_comment(f"SauceLabs session: {sauce_session}")
                    test_cases.append(
                        TestRailCase(
                            title=TestRailCaseFieldsOptimizer.extract_last_words(case_name, TestRailCaseFieldsOptimizer.MAX_TESTCASE_TITLE_LENGTH),
                            case_id=case_id,
                            result=result,
                            custom_automation_id=automation_id,
                            case_fields=case_fields_dict
                        )
                    )
                self.env.log("Processed {0} test cases in section {1}.".format(len(test_cases), section.name))
                test_sections.append(
                    TestRailSection(
                        section.name,
                        testcases=test_cases,
                        properties=properties,
                    )
                )
            testrail_suites.append(
                TestRailSuite(
                    self.env.suite_name if self.env.suite_name else suite.name,
                    testsections=test_sections,
                    source=self.filename,
                )
            )

        return testrail_suites

    def split_sauce_report(self, suite) -> List[JUnitXml]:
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
