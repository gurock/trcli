import re
from typing import Union


class MatchersParser:

    AUTO = "auto"
    NAME = "name"
    PROPERTY = "property"

    @staticmethod
    def parse_name_with_id(case_name: str) -> (int, str):
        """Parses case names expecting an ID following one of the following patterns:
        - "C123 my test case"
        - "my test case C123"
        - "C123_my_test_case"
        - "my_test_case_C123"
        - "module_1_C123_my_test_case"
        - "[C123] my test case"
        - "my test case [C123]"
        - "module 1 [C123] my test case"

        :param case_name: Name of the test case
        :return: Tuple with test case ID and test case name without the ID
        """
        for char in [" ", "_"]:
            parts = case_name.split(char)
            parts_copy = parts.copy()
            for idx, part in enumerate(parts):
                if part.lower().startswith("c") and len(part) > 1:
                    id_part = part[1:]
                    if id_part.isnumeric():
                        parts_copy.pop(idx)
                        return int(id_part), char.join(parts_copy)

        results = re.findall(r"\[(.*?)\]", case_name)
        for result in results:
            if result.lower().startswith("c"):
                case_id = result[1:]
                if case_id.isnumeric():
                    id_tag = f"[{result}]"
                    tag_idx = case_name.find(id_tag)
                    case_name = f"{case_name[0:tag_idx].strip()} {case_name[tag_idx + len(id_tag):].strip()}".strip()
                    return int(case_id), case_name

        return None, case_name


class FieldsParser:

    @staticmethod
    def resolve_fields(fields: Union[list[str], dict]) -> (dict, str):
        error = None
        fields_dictionary = {}
        try:
            if isinstance(fields, list) or isinstance(fields, tuple):
                for field in fields:
                    field, value = field.split(":", maxsplit=1)
                    if value.startswith("["):
                        try:
                            value = eval(value)
                        except Exception:
                            pass
                    fields_dictionary[field] = value
            elif isinstance(fields, dict):
                fields_dictionary = fields
            else:
                error = f"Invalid field type ({type(fields)}), supported types are tuple/list/dictionary"
            return fields_dictionary, error
        except Exception as ex:
            return fields_dictionary, f"Error parsing fields: {ex}"
