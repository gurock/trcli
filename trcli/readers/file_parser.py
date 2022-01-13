from pathlib import Path
from abc import abstractmethod
from typing import Union


class FileParser:
    """
    Each new parser should inherit from this class, to make file reading modular.
    """

    def __init__(self, filepath: Union[str, Path]):
        self.filepath = filepath
        self.check_file(filepath)
        self.filename = Path(filepath).name

    @staticmethod
    def check_file(filepath: Union[str, Path]):
        if not Path(filepath).is_file():
            raise FileNotFoundError("File not found.")

    @abstractmethod
    def parse_file(self):
        raise NotImplementedError
