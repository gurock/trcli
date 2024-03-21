from dataclasses import dataclass
from time import gmtime, strftime
from beartype.typing import List, Optional

from serde import field, serialize, deserialize, to_dict

from trcli import settings
from trcli.data_classes.validation_exception import ValidationException


@serialize
@deserialize
@dataclass
class TestRailSeparatedStep:
    """Class to store steps using the separated steps template"""

    content: str
    status_id: int = field(default=None, skip_if_default=True)

    def __init__(self, content: str):
        self.content = content


@serialize
@deserialize
@dataclass
class TestRailResult:
    """Class for creating Test Rail result for cases"""

    case_id: int = field(default=None, skip_if_default=True)
    status_id: int = field(default=None, skip_if_default=True)
    comment: str = field(default=None, skip_if_default=True)
    version: str = field(default=None, skip_if_default=True)
    elapsed: str = field(default=None, skip_if_default=True)
    defects: str = field(default=None, skip_if_default=True)
    assignedto_id: int = field(default=None, skip_if_default=True)
    attachments: Optional[List[str]] = field(default_factory=list, skip_if_default=True)
    result_fields: Optional[dict] = field(default_factory=dict, skip=True)
    junit_result_unparsed: List = field(default=None, metadata={"serde_skip": True})
    custom_step_results: List[TestRailSeparatedStep] = field(default_factory=list, skip_if_default=True)

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
    def calculate_status_id_from_junit_element(junit_result: List) -> int:
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
    def get_comment_from_junit_element(junit_result: List) -> str:
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
            if settings.ALLOW_ELAPSED_MS:
                return f"{round(float(elapsed), 3)}s" if float(elapsed) >= 0.001 else None
            else:
                elapsed = float(elapsed)
                if elapsed > 1:
                    return f"{round(elapsed)}s"
                elif elapsed > 0:
                    return "1s"
                else:
                    return None
        except ValueError:
            # unable to parse time format
            elapsed = None

        return elapsed

    def prepend_comment(self, comment: str):
        self.comment = f"{comment}\n\n{self.comment}"

    def add_global_result_fields(self, results_fields: dict) -> None:
        """Add global result fields without overriding the existing test-specific result fields

        :param results_fields: Global results fields to be added to the result
        :return: None
        """
        if not results_fields:
            return
        new_results_fields = results_fields.copy()
        new_results_fields.update(self.result_fields)
        self.result_fields = new_results_fields

    def to_dict(self) -> dict:
        result_dict = to_dict(self)
        result_dict.update(self.result_fields)
        return result_dict


@serialize
@deserialize
@dataclass
class TestRailCase:
    """Class for creating Test Rail test case"""

    title: str
    section_id: int = field(default=None, skip_if_default=True)
    case_id: int = field(default=None, skip_if_default=True)
    estimate: str = field(default=None, skip_if_default=True)
    template_id: int = field(default=None, skip_if_default=True)
    type_id: int = field(default=None, skip_if_default=True)
    milestone_id: int = field(default=None, skip_if_default=True)
    refs: str = field(default=None, skip_if_default=True)
    case_fields: Optional[dict] = field(default_factory=dict, skip=True)
    result: TestRailResult = field(default=None, metadata={"serde_skip": True})
    custom_automation_id: str = field(default=None, skip_if_default=True)
    # Uncomment if we want to support separated steps in cases in the future
    # custom_steps_separated: List[TestRailSeparatedStep] = field(default_factory=list, skip_if_default=True)

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
        if self.custom_automation_id:
            self.custom_automation_id = self.custom_automation_id.strip()

    def add_global_case_fields(self, case_fields: dict) -> None:
        """Add global case fields without overriding the existing case-specific fields

        :param case_fields: Global case fields to be added to the result
        :return: None
        """
        if not case_fields:
            return
        new_case_fields = case_fields.copy()
        new_case_fields.update(self.case_fields)
        self.case_fields = new_case_fields

    def to_dict(self) -> dict:
        case_dict = to_dict(self)
        case_dict.update(self.case_fields)
        return case_dict


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
    suite_id: int = field(default=None, skip_if_default=True)
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
    description: str = field(default=None, skip_if_default=True)
    testsections: List[TestRailSection] = field(
        default_factory=list, metadata={"serde_skip": True}
    )
    source: str = field(default=None, metadata={"serde_skip": True})

    def __post_init__(self):
        current_time = strftime("%d-%m-%y %H:%M:%S", gmtime())
        self.name = f"{self.source} {current_time}" if self.name is None else self.name


@dataclass
class ProjectData:
    project_id: int
    suite_mode: int
    error_message: str
