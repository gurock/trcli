from dataclasses import dataclass
from typing import List
from serde import field, serialize, deserialize
from time import gmtime, strftime
from trcli.data_classes.validation_exception import ValidationException


@serialize
@deserialize
@dataclass
class TestRailResult:
    """Class for creating Test Rail result for cases"""

    case_id: int
    status_id: int = field(default=None, skip_if_default=True)
    comment: str = field(default=None, skip_if_default=True)
    version: str = field(default=None, skip_if_default=True)
    elapsed: str = field(default=None, skip_if_default=True)
    defects: str = field(default=None, skip_if_default=True)
    assignedto_id: int = field(default=None, skip_if_default=True)
    junit_result_unparsed: list = field(default=None, metadata={"serde_skip": True})

    def __post_init__(self):
        if self.junit_result_unparsed is not None:
            self.status_id = self.calculate_status_id_from_junit_element(
                self.junit_result_unparsed
            )
            self.comment = self.get_comment_from_junit_element(
                self.junit_result_unparsed
            )
        if self.elapsed is not None:
            self.elapsed = self.proper_format_for_elapsed(self.elapsed)

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

    @staticmethod
    def proper_format_for_elapsed(elapsed):
        try:
            rounded_secs = round(float(elapsed))
            return f"{rounded_secs}s" if rounded_secs > 0 else None
        except ValueError:
            # unable to parse time format
            return None


@serialize
@deserialize
@dataclass
class TestRailCase:
    """Class for creating Test Rail test case"""

    section_id: int
    title: str
    case_id: int = field(default=None, skip_if_default=True)
    estimate: str = field(default=None, skip_if_default=True)
    template_id: int = field(default=None, skip_if_default=True)
    type_id: int = field(default=None, skip_if_default=True)
    milestone_id: int = field(default=None, skip_if_default=True)
    refs: str = field(default=None, skip_if_default=True)
    result: TestRailResult = field(default=None, metadata={"serde_skip": True})
    custom_automation_id: str = field(default=None, skip_if_default=True)

    def __int__(self):
        return int(self.case_id) if self.case_id is not None else -1

    def __getitem__(self, item):
        return getattr(self, item)

    def __post_init__(self):
        if not self.title:
            raise ValidationException(
                field_name="title",
                class_name=self.__class__.__name__,
                reason="Title is empty.",
            )


@serialize
@deserialize
@dataclass
class TestRailProperty:
    """Class for creating Test Rail property - run description"""

    name: str = field(default=None, skip_if_default=True)
    value: str = field(default=None, skip_if_default=True)
    description: str = field(default=None, skip_if_default=True)

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
    time: str = field(default=None, metadata={"serde_skip": True})
    parent_id: int = field(default=None, skip_if_default=True)
    description: str = field(default=None, skip_if_default=True)
    section_id: int = field(default=None, metadata={"serde_skip": True})
    testcases: List[TestRailCase] = field(
        default_factory=list, metadata={"serde_skip": True}
    )
    properties: List[TestRailProperty] = field(
        default_factory=list, metadata={"serde_skip": True}
    )

    def __getitem__(self, item):
        return getattr(self, item)

    def __post_init__(self):
        if not self.name:
            raise ValidationException(
                field_name="name",
                class_name=self.__class__.__name__,
                reason="Name is empty.",
            )


@serialize
@deserialize
@dataclass
class TestRailSuite:
    """Class for creating Test Rail Suite fields"""

    name: str
    suite_id: int = field(default=None, skip_if_default=True)
    time: str = field(default=None, metadata={"serde_skip": True})
    description: str = field(default=None, skip_if_default=True)
    testsections: List[TestRailSection] = field(
        default_factory=list, metadata={"serde_skip": True}
    )
    source: str = field(default=None, metadata={"serde_skip": True})

    def __post_init__(self):
        current_time = strftime("%d-%m-%y %H:%M:%S", gmtime())
        self.name = f"{self.source} {current_time}" if self.name is None else self.name
