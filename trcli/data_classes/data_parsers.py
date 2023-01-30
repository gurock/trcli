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


class ResultFieldsParser:

    @staticmethod
    def parse_result_fields(result_fields: Union[list[str], dict]) -> (dict, str):
        error = None
        fields_dictionary = {}
        try:
            if isinstance(result_fields, list) or isinstance(result_fields, tuple):
                for result_field in result_fields:
                    field, value = result_field.split(":", maxsplit=1)
                    fields_dictionary[field] = value
            elif isinstance(result_fields, dict):
                fields_dictionary = result_fields
            else:
                error = f"Invalid result fields type ({type(result_fields)}), supported types are tuple/list/dictionary"
            return fields_dictionary, error
        except Exception as ex:
            return fields_dictionary, f"Error parsing result fields: {ex}"
