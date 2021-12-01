from pathlib import Path
from junitparser import TestCase, TestSuite, JUnitXml, Attr, JUnitXmlError
from xml.etree import ElementTree as etree
from trcli.data_classes.dataclass_testrail import (
    PropertiesDataclass,
    SuitesDataclass,
    TestSuiteDataclass,
    TestCaseDataclass,
)

TestCase.id = Attr("id")
TestSuite.id = Attr("id")
JUnitXml.id = Attr("id")


def add_root_element_to_tree(filename: Path) -> etree:
    tree = etree.parse(filename)
    root_elem = tree.getroot()
    if root_elem.tag == "testsuites":
        return tree
    elif root_elem.tag == "testsuite":
        new_root = etree.Element("testsuites")
        new_root.insert(0, root_elem)
        return etree.ElementTree(new_root)
    else:
        raise JUnitXmlError("Invalid format.")


def parse_junit(filename: Path) -> SuitesDataclass:
    xml = JUnitXml.fromfile(filename, parse_func=add_root_element_to_tree)
    test_suites = []
    for suite in xml:
        test_cases = []
        properties = []
        for property in suite.properties():
            properties.append(PropertiesDataclass(property.name, property.value))
        for case in suite:
            test_cases.append(
                TestCaseDataclass(case.name, case.id, case.time, case.result)
            )
        test_suites.append(
            TestSuiteDataclass(suite.name, suite.id, suite.time, test_cases, properties)
        )

    xml_dataclass = SuitesDataclass(xml.name, xml.id, xml.time, test_suites)
    return xml_dataclass
