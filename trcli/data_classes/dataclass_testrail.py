from dataclasses import dataclass, field
from typing import List


@dataclass
class TestCaseDataclass:
    """Class for creating Test Rail test case"""

    name: str
    case_id: int
    time: str
    results: List
    section_id: str = None
    status_id: int = None

    def __index__(self):
        try:
            return int(self.case_id)
        except TypeError:
            return 0

    def __post_init__(self):
        results_parsed = []
        for i in self.results:
            results_parsed.append(
                {"tag": i._tag, "message": i.message, "type": i.type, "text": i.text}
            )
        self.results = results_parsed
        self.calculate_status_id()

    def update_section_id(self, section_id):
        self.section_id = section_id

    def calculate_status_id(self):
        """
         Calculate id for first result
        1 - Passed
        3 - Untested
        4 - Retest
        5 - Failed
        """
        if len(self.results) > 0:
            test_result_tag = self.results[0]["tag"].lower()
            if test_result_tag == "skipped":
                self.status_id = 4
            elif test_result_tag == "error" or "failure":
                self.status_id = 5
            else:
                self.status_id = 3
        else:
            self.status_id = 1


@dataclass
class PropertiesDataclass:
    """Class for creating Test Rail properties"""

    name: str
    value: str
    description: str = field(init=False)

    def __repr__(self) -> str:
        return self.description

    def __post_init__(self):
        self.description = f"{self.name}: {self.value}"


@dataclass
class TestSuiteDataclass:
    """Class for creating Test Rail test suite"""

    name: str
    suite_id: str
    time: str
    testcases: List[TestCaseDataclass] = field(default_factory=list)
    properties: List[PropertiesDataclass] = field(default_factory=list)

    def __post_init__(self):
        [i.update_section_id(self.suite_id) for i in self.testcases]


@dataclass
class SuitesDataclass:
    """Class for creating XML fields"""

    name: str
    id: str
    time: str
    testsuites: List[TestSuiteDataclass] = field(default_factory=list)
