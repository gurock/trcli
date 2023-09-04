from datetime import datetime
from xml.etree import ElementTree

from trcli.cli import Environment
from trcli.data_classes.data_parsers import MatchersParser, FieldsParser
from trcli.data_classes.dataclass_testrail import (
    TestRailCase,
    TestRailSuite,
    TestRailSection,
    TestRailResult, TestRailSeparatedStep,
)
from trcli.readers.file_parser import FileParser


class RobotParser(FileParser):

    def __init__(self, environment: Environment):
        super().__init__(environment)
        self.case_matcher = environment.case_matcher

    def parse_file(self) -> list[TestRailSuite]:
        self.env.log(f"Parsing Robot Framework report.")
        tree = ElementTree.parse(self.filepath)
        root = tree.getroot()
        sections_list = []
        suite_elements = root.findall("suite")
        for suite_element in suite_elements:
            self._find_suites(suite_element, sections_list)
        cases_count = sum(len(section.testcases) for section in sections_list)
        self.env.log(f"Processed {cases_count} test cases in {len(sections_list)} sections.")
        testrail_suites = [
            TestRailSuite(
                self.env.suite_name if self.env.suite_name else self.filepath.stem,
                testsections=sections_list,
                source=self.filename,
            )
        ]

        return testrail_suites

    def _find_suites(self, suite_element, sections_list: list, namespace=""):
        name = suite_element.get("name")
        namespace += f".{name}" if namespace else name
        tests = suite_element.findall("test")
        if tests:
            section = TestRailSection(namespace)
            sections_list.append(section)
            for test in tests:
                case_id = None
                case_name = test.get("name")
                attachments = []
                result_fields = []
                case_fields = []
                comments = []
                documentation = test.find("doc")
                if self.case_matcher == MatchersParser.NAME:
                    case_id, case_name = MatchersParser.parse_name_with_id(case_name)
                if documentation is not None:
                    lines = [line.strip() for line in documentation.text.splitlines()]
                    for line in lines:
                        if line.lower().startswith("- testrail_case_id:") \
                                and self.case_matcher == MatchersParser.PROPERTY:
                            case_id = int(self._remove_tr_prefix(line, "- testrail_case_id:").lower().replace("c", ""))
                        if line.lower().startswith("- testrail_attachment:"):
                            attachments.append(self._remove_tr_prefix(line, "- testrail_attachment:"))
                        if line.lower().startswith("- testrail_result_field"):
                            result_fields.append(self._remove_tr_prefix(line, "- testrail_result_field:"))
                        if line.lower().startswith("- testrail_result_comment"):
                            comments.append(self._remove_tr_prefix(line, "- testrail_result_comment:"))
                        if line.lower().startswith("- testrail_case_field"):
                            case_fields.append(self._remove_tr_prefix(line, "- testrail_case_field:"))
                status = test.find("status")
                status_dict = {
                    "pass": 1,
                    "not run": 3,
                    "skip": 4,
                    "fail": 5
                }
                status_id = status_dict[status.get("status").lower()]
                elapsed_time = self._parse_rf_time(status.get("endtime")) - self._parse_rf_time(status.get("starttime"))
                error_msg = status.text
                keywords = test.findall("kw")
                step_keywords = []
                for kw in keywords:
                    kw_result = kw.find("status").get("status")
                    step = TestRailSeparatedStep(kw.get("name"))
                    step.status_id = status_dict[kw_result.lower()]
                    step_keywords.append(step)

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
                    elapsed=f"{elapsed_time}",
                    status_id=status_id,
                    comment=error_msg,
                    attachments=attachments,
                    result_fields=result_fields_dict,
                    custom_step_results=step_keywords
                )
                for comment in reversed(comments):
                    result.prepend_comment(comment)
                tr_test = TestRailCase(
                    title=case_name,
                    case_id=case_id,
                    result=result,
                    custom_automation_id=f"{namespace}.{case_name}",
                    case_fields=case_fields_dict
                )
                section.testcases.append(tr_test)

        for sub_suite_element in suite_element.findall("suite"):
            self._find_suites(sub_suite_element, sections_list, namespace=namespace)

    @staticmethod
    def _parse_rf_time(time_str: str) -> datetime:
        return datetime.strptime(time_str, '%Y%m%d %H:%M:%S.%f')

    @staticmethod
    def _remove_tr_prefix(text: str, tr_prefix: str) -> str:
        return text.strip().removeprefix(tr_prefix).strip()
