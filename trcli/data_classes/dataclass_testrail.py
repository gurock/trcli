from dataclasses import dataclass, field
from typing import List


@dataclass
class TestCaseDataclass:
    """Class for creating Test Rail test case"""

    name: str
    case_id: str
    time: str
    results: List

    def __post_init__(self):
        results_parsed = []
        for i in self.results:
            results_parsed.append(
                {"tag": i._tag, "message": i.message, "type": i.type, "text": i.text}
            )
        self.results = results_parsed


@dataclass
class PropertiesDataclass:
    """Class for creating Test Rail properties"""

    name: str
    value: str
    description: str = field(init=False)

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


@dataclass
class SuitesDataclass:
    """Class for creating XML fields"""

    name: str
    id: str
    time: str
    testsuites: List[TestSuiteDataclass] = field(default_factory=list)
