import re
from typing import Union


class MatchersParser:

    AUTO = "auto"
    NAME = "name"
    PROPERTY = "property"

    @staticmethod
    def parse_name_with_id(case_name: str) -> (int, str):
        m = re.findall(r"\[(.*?)\]", case_name)
        for res in m:
            if res.lower().startswith("c"):
                case_id = res[1:]
                if case_id.isnumeric():
                    id_tag = f"[{res}]"
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
