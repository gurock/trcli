import glob
from pathlib import Path
from beartype.typing import Union, List
from unittest import TestCase, TestSuite
from xml.etree import ElementTree as etree

from junitparser import (
    JUnitXml, JUnitXmlError, Element, Attr, TestSuite as JUnitTestSuite, TestCase as JUnitTestCase)

from trcli.cli import Environment
from trcli.constants import OLD_SYSTEM_NAME_AUTOMATION_ID
from trcli.data_classes.data_parsers import MatchersParser, FieldsParser, TestRailCaseFieldsOptimizer
from trcli.data_classes.dataclass_testrail import (
    TestRailCase,
    TestRailSuite,
    TestRailSection,
    TestRailProperty,
    TestRailResult, TestRailSeparatedStep,
)
from trcli.readers.file_parser import FileParser

STEP_STATUSES = {
    "passed": 1,
    "untested": 3,
    "skipped": 4,
    "failed": 5
}

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
        self._case_matcher = environment.case_matcher
        self._special = environment.special_parser
        self._case_result_statuses = {"passed": 1, "skipped": 4,"error": 5, "failure": 5}
        self._update_with_custom_statuses()

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

    @staticmethod
    def _extract_section_properties(section, processed_props) -> List[TestRailProperty]:
        properties = []
        for prop in section.properties():
            if prop.name not in processed_props:
                properties.append(TestRailProperty(prop.name, prop.value))
                processed_props.append(prop.name)

        return properties

    def _update_with_custom_statuses(self):
        custom_statuses = self.env.params_from_config.get("case_result_statuses", None)
        if custom_statuses:
            self._case_result_statuses.update(custom_statuses)

    def _extract_case_id_and_name(self, case) -> tuple:
        case_name = case.name
        case_id = None

        if self._case_matcher == MatchersParser.NAME:
            return MatchersParser.parse_name_with_id(case_name)

        if self._case_matcher == MatchersParser.PROPERTY:
            for case_props in case.iterchildren(Properties):
                for prop in case_props.iterchildren(Property):
                    if prop.name == "test_id":
                        case_id = int(prop.value.lower().replace("c", ""))
                        return case_id, case_name

        return case_id, case_name

    def _get_status_id_for_case_result(self, case: JUnitTestCase) -> Union[int, None]:
        if case.is_passed:
            status = "passed"
        elif case.is_skipped:
            status = "skipped"
        else:
            status = case.result[0]._tag.lower()
        return self._case_result_statuses.get(status)

    @staticmethod
    def _get_comment_for_case_result(case: JUnitTestCase) -> str:
        if case.is_passed:
            return ""
        result = case.result[0]
        parts = [
            f"Type: {result.type}" if result.type else "",
            f"Message: {result.message}" if result.message else "",
            f"Text: {result.text}" if result.text else ""
        ]
        return "\n".join(part for part in parts if part).strip()

    @staticmethod
    def _parse_case_properties(case):
        result_steps = []
        attachments = []
        result_fields = []
        comments = []
        case_fields = []
        sauce_session = None

        for case_props in case.iterchildren(Properties):
            for prop in case_props.iterchildren(Property):
                name, value = prop.name, prop.value
                if not name:
                    continue

                elif name.startswith("testrail_result_step"):
                    status, step = value.split(':', maxsplit=1)
                    step_obj = TestRailSeparatedStep(step.strip())
                    step_obj.status_id = STEP_STATUSES[status.lower().strip()]
                    result_steps.append(step_obj)
                elif name.startswith("testrail_attachment"):
                    attachments.append(value)
                elif name.startswith("testrail_result_field"):
                    result_fields.append(value)
                elif name.startswith("testrail_result_comment"):
                    comments.append(value)
                elif name.startswith("testrail_case_field"):
                    text = prop._elem.text.strip() if prop._elem.text else None
                    case_fields.append(text or value)
                elif name.startswith("testrail_sauce_session"):
                    sauce_session = value

        return result_steps, attachments, result_fields, comments, case_fields, sauce_session

    def _resolve_case_fields(self, result_fields, case_fields):
        result_fields_dict, error = FieldsParser.resolve_fields(result_fields)
        if error:
            self.env.elog(error)
            raise Exception(error)

        case_fields_dict, error = FieldsParser.resolve_fields(case_fields)
        if error:
            self.env.elog(error)
            raise Exception(error)

        return result_fields_dict, case_fields_dict

    def _parse_test_cases(self, section) -> List[TestRailCase]:
        test_cases = []

        for case in section:
            """
            TODO: use section.iterchildren(JUnitTestCase) to get only testcases belonging to the section
            required for nested suites
            """
            automation_id = f"{case.classname}.{case.name}"
            case_id, case_name = self._extract_case_id_and_name(case)
            result_steps, attachments, result_fields, comments, case_fields, sauce_session = self._parse_case_properties(
                case)
            result_fields_dict, case_fields_dict = self._resolve_case_fields(result_fields, case_fields)
            status_id = self._get_status_id_for_case_result(case)
            comment = self._get_comment_for_case_result(case)
            result = TestRailResult(
                case_id=case_id,
                elapsed=case.time,
                attachments=attachments,
                result_fields=result_fields_dict,
                custom_step_results=result_steps,
                status_id=status_id,
                comment=comment,
            )

            for comment in reversed(comments):
                result.prepend_comment(comment)
            if sauce_session:
                result.prepend_comment(f"SauceLabs session: {sauce_session}")

            automation_id = (
                    case_fields_dict.pop(OLD_SYSTEM_NAME_AUTOMATION_ID, None)
                    or case._elem.get(OLD_SYSTEM_NAME_AUTOMATION_ID, automation_id))

            test_cases.append(TestRailCase(
                title=TestRailCaseFieldsOptimizer.extract_last_words(case_name,
                                                                     TestRailCaseFieldsOptimizer.MAX_TESTCASE_TITLE_LENGTH),
                case_id=case_id,
                result=result,
                custom_automation_id=automation_id,
                case_fields=case_fields_dict
            ))

        return test_cases

    def _get_suite_name(self, suite):
        if self.env.suite_name:
            return self.env.suite_name
        elif suite.name:
            return suite.name
        raise ValueError("Suite name is not defined in environment or JUnit report.")


    def _parse_sections(self, suite) -> List[TestRailSection]:
        sections = []
        processed_props = []

        for section in suite:
            if isinstance(section, JUnitTestSuite):
                if not len(section):
                    continue
                """
                TODO: Handle nested suites if needed (add sub_sections to data class TestRailSection)
                inner_suites = section.testsuites()
                sub_sections = self._parse_sections(inner_suites)
                then sub_sections=sub_sections
                """
                properties = self._extract_section_properties(section, processed_props)
                test_cases = self._parse_test_cases(section)
                self.env.log(f"Processed {len(test_cases)} test cases in section {section.name}.")
                sections.append(TestRailSection(
                    section.name,
                    testcases=test_cases,
                    properties=properties,
                ))

        return sections

    def parse_file(self) -> List[TestRailSuite]:
        self.env.log("Parsing JUnit report.")
        suite = JUnitXml.fromfile(self.filepath, parse_func=self._add_root_element_to_tree)

        suites = self._split_sauce_report(suite) if self._special == "saucectl" else [suite]
        testrail_suites = []

        for suite in suites:
            if suite.name:
                self.env.log(f"Processing JUnit suite - {suite.name}")

            testrail_sections = self._parse_sections(suite)
            suite_name = self.env.suite_name if self.env.suite_name else suite.name

            testrail_suites.append(TestRailSuite(
                suite_name,
                testsections=testrail_sections,
                source=self.filename,
            ))

        return testrail_suites

    def _split_sauce_report(self, suite) -> List[JUnitXml]:
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

if __name__ == '__main__':
    pass
