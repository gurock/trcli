from dataclasses import dataclass, field
from typing import List
from serde import serialize, deserialize

set_default_and_skip = field(
    default=None, metadata={"serde_skip_if": lambda v: v is None}
)


@serialize
@deserialize
@dataclass
class TestRailResult:
    """Class for creating Test Rail result for cases"""

    case_id: int
    status_id: int = None
    comment: str = None
    version: str = None
    elapsed: str = None
    defects: str = None
    assignedto_id: int = None
    junit_result_unparsed: list = field(default=None, metadata={"serde_skip": True})

    def __post_init__(self):
        if self.junit_result_unparsed is not None:
            self.status_id = self.calculate_status_id_from_junit_element(
                self.junit_result_unparsed
            )
            self.comment = self.get_comment_from_junit_element(
                self.junit_result_unparsed
            )

    @staticmethod
    def calculate_status_id_from_junit_element(junit_result: list) -> int:
        """
         Calculate id for first result. In junit no result mean pass
        1 - Passed
        3 - Untested
        4 - Retest
        5 - Failed
        """
        if len(junit_result) == 0:
            return 1
        test_result_tag = junit_result[0]._tag.lower()
        if test_result_tag == "skipped":
            return 4
        elif test_result_tag == "error" or "failure":
            return 5

    @staticmethod
    def get_comment_from_junit_element(junit_result: list) -> str:
        if len(junit_result) == 0:
            return ""
        elif not any(
            [junit_result[0].type, junit_result[0].message, junit_result[0].text]
        ):
            return ""
        else:
            return f"Type: {junit_result[0].type or ''}\nMessage: {junit_result[0].message or ''}\nText: {junit_result[0].text or ''}"


@serialize
@deserialize
@dataclass
class TestRailCase:
    """Class for creating Test Rail test case"""

    section_id: int
    title: str
    case_id: str = None
    estimate: str = None
    template_id: int = None
    type_id: int = None
    milestone_id: int = None
    refs: str = None
    result: TestRailResult = None

    def __int__(self):
        return int(self.case_id) if self.case_id is not None else -1

    def __getitem__(self, item):
        return getattr(self, item)


@serialize
@deserialize
@dataclass
class TestRailProperty:
    """Class for creating Test Rail property - run description"""

    name: str = None
    value: str = None
    description: str = None

    def __repr__(self) -> str:
        return self.description

    def __post_init__(self):
        self.description = f"{self.name}: {self.value}"


@serialize
@deserialize
@dataclass
class TestRailSection:
    """Class for creating Test Rail test section"""

    name: str
    suite_id: int
    time: str = None
    parent_id: int = None
    description: str = None
    section_id: int = None
    testcases: List[TestRailCase] = field(default_factory=list)
    properties: List[TestRailProperty] = field(default_factory=list)

    def __getitem__(self, item):
        return getattr(self, item)


@serialize
@deserialize
@dataclass
class TestRailSuite:
    """Class for creating Test Rail Suite fields"""

    name: str
    suite_id: int = None
    time: str = None
    description: str = None
    testsections: List[TestRailSection] = field(default_factory=list)
