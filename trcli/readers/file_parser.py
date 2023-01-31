from pathlib import Path
from abc import abstractmethod
from typing import Union

from trcli.cli import Environment
from trcli.data_classes.dataclass_testrail import TestRailSuite


class FileParser:
    """
    Each new parser should inherit from this class, to make file reading modular.
    """

    def __init__(self, environment: Environment):
        filepath = environment.file
        self.filepath = filepath
        self.check_file(filepath)
        self.filename = Path(filepath).name
        self.case_matcher = environment.case_matcher
        self.env = environment
        self.special = environment.special_parser

    @staticmethod
    def check_file(filepath: Union[str, Path]):
        if not Path(filepath).is_file():
            raise FileNotFoundError("File not found.")

    @abstractmethod
    def parse_file(self) -> list[TestRailSuite]:
        raise NotImplementedError
