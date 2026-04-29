from pathlib import Path
from abc import abstractmethod
from beartype.typing import Union, List

from trcli.cli import Environment
from trcli.data_classes.dataclass_testrail import TestRailSuite


class FileParser:
    """
    Each new parser should inherit from this class, to make file reading modular.
    """

    def __init__(self, environment: Environment):
        self.filepath = self.check_file(environment.file)
        self.filename = self.filepath.name
        self.env = environment
        self._case_result_statuses = {}

    def _update_with_custom_statuses(self):
        custom_statuses = self.env.params_from_config.get("case_result_statuses", None)
        if custom_statuses:
            self._case_result_statuses.update(custom_statuses)

    @staticmethod
    def check_file(filepath: Union[str, Path]) -> Path:
        filepath = Path(filepath)
        if not filepath.is_file():
            raise FileNotFoundError("File not found.")
        return filepath

    @abstractmethod
    def parse_file(self) -> List[TestRailSuite]:
        raise NotImplementedError
