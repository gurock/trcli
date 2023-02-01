from typing import Union


class MatchersParser:

    AUTO = "auto"
    NAME = "name"
    PROPERTY = "property"

    @staticmethod
    def parse_name_with_id(case_name: str) -> (str, str):
        if case_name.lower().startswith("[c"):
            close_idx = case_name.find("]")
            case_id = int(case_name[2:close_idx])
            case_name = case_name[close_idx + 1:].lstrip()
            return case_id, case_name
        else:
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
                    fields_dictionary[field] = value
            elif isinstance(fields, dict):
                fields_dictionary = fields
            else:
                error = f"Invalid field type ({type(fields)}), supported types are tuple/list/dictionary"
            return fields_dictionary, error
        except Exception as ex:
            return fields_dictionary, f"Error parsing fields: {ex}"
