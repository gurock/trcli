import pytest
from dataclasses import asdict
from junitparser import TestCase, TestSuite, JUnitXml, Attr, JUnitXmlError
from trcli.readers.junit_xml import JunitParser
from tests.test_data.parser_test_data import *

TestCase.id = Attr("id")
TestSuite.id = Attr("id")
JUnitXml.id = Attr("id")


class TestDataClasses:
    @pytest.mark.parametrize(
        "input_xml, expected",
        [
            (XML_NO_ROOT, EXPECTED_NO_ROOT),
            (XML_ROOT, EXPECTED_ROOT),
            (XML_EMPTY, EXPECTED_EMPTY),
        ],
        ids=[
            "XML without testsuites root",
            "XML with testsuites root",
            "XML with no data",
        ],
    )
    def test_junit_xml_parser(self, tmp_path, input_xml, expected):
        d = tmp_path / "xml_tmp"
        d.mkdir()
        p = d / "xml_test.xml"
        p.write_text(input_xml)
        file_reader = JunitParser(p)
        read_junit = file_reader.parse_file()
        result = asdict(read_junit)

        assert result == expected

    def test_junit_xml_parser_invalid_file(self, tmp_path):
        d = tmp_path / "xml_tmp"
        d.mkdir()
        p = d / "xml_test.xml"
        p.write_text(XML_INVALID)
        file_reader = JunitParser(p)
        with pytest.raises(JUnitXmlError):
            file_reader.parse_file()

    def test_junit_xml_parser_file_not_found(self, tmp_path):
        d = tmp_path / "not_found.xml"
        with pytest.raises(FileNotFoundError):
            JunitParser(d)
