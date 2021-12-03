from pathlib import Path
import os
from abc import abstractmethod


class FileParser:
    """
    Each new parser should inherit from this class, to make file reading modular.
    """

    def __init__(self, filepath: Path):
        self.filepath = filepath
        self.check_file(filepath)

    @staticmethod
    def check_file(filepath: Path):
        if not os.path.isfile(filepath):
            raise FileNotFoundError("File not found.")

    @abstractmethod
    def parse_file(self):
        raise NotImplementedError
