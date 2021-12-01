import pytest
from dataclasses import asdict
from junitparser import TestCase, TestSuite, JUnitXml, Attr
from trcli.readers import junit_xml
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
        read_junit = junit_xml.parse_junit(p)
        result = asdict(read_junit)

        assert result == expected
