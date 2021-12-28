import itertools
from typing import List, Tuple


class CLIParametersHelper:
    def __init__(self):
        self.optional_arguments = {}

        self.required_arguments = {
            "host": ["--host", "fake host name"],
            "project": ["--project", "fake project name"],
            "title": ["--title", "fake run title"],
            "username": ["--username", "fake user name"],
            "password": ["--password", "fake password"],
            "key": ["--key", "fake API key"],
            "parse_junit": ["parse_junit"],
            "file": ["--file", "fake_result_file.xml"],
        }

    def get_all_required_parameters(self) -> List[str]:
        return list(
            itertools.chain(*[value for key, value in self.required_arguments.items()])
        )

    def get_all_required_parameters_without_specified(
        self, args_to_remove: List[str]
    ) -> List[str]:
        return list(
            itertools.chain(
                *[
                    value
                    for key, value in self.required_arguments.items()
                    if key not in args_to_remove
                ]
            )
        )

    def get_all_required_parameters_plus_optional(
        self, args_to_add: List[str]
    ) -> List[str]:
        required_args = self.get_all_required_parameters()
        return args_to_add + required_args

    def get_required_parameters_without_command_no_dashes(
        self,
    ) -> List[Tuple[str, str]]:
        return [
            (key, value[-1])
            for key, value in self.required_arguments.items()
            if key != "parse_junit"
        ]
