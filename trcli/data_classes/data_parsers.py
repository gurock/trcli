import re, ast
from beartype.typing import Union, List, Dict, Tuple


class MatchersParser:

    AUTO = "auto"
    NAME = "name"
    PROPERTY = "property"

    @staticmethod
    def parse_name_with_id(case_name: str) -> Tuple[int, str]:
        """Parses case names expecting an ID following one of the following patterns:
        - "C123 my test case"
        - "my test case C123"
        - "C123_my_test_case"
        - "my_test_case_C123"
        - "module_1_C123_my_test_case"
        - "[C123] my test case"
        - "my test case [C123]"
        - "module 1 [C123] my test case"
        - "my_test_case_C123()" (JUnit 5 support)

        :param case_name: Name of the test case
        :return: Tuple with test case ID and test case name without the ID
        """
        for char in [" ", "_"]:
            parts = case_name.split(char)
            parts_copy = parts.copy()
            for idx, part in enumerate(parts):
                if part.lower().startswith("c") and len(part) > 1:
                    id_part = part[1:]
                    id_part_clean = re.sub(r'\(.*\)$', '', id_part)
                    if id_part_clean.isnumeric():
                        parts_copy.pop(idx)
                        return int(id_part_clean), char.join(parts_copy)

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
    def resolve_fields(fields: Union[List[str], Dict]) -> Tuple[Dict, str]:
        error = None
        fields_dictionary = {}
        try:
            if isinstance(fields, list) or isinstance(fields, tuple):
                for field in fields:
                    field, value = field.split(":", maxsplit=1)
                    if value.startswith("["):
                        try:
                            value = ast.literal_eval(value)
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

class TestRailCaseFieldsOptimizer:

    MAX_TESTCASE_TITLE_LENGTH = 250

    @staticmethod
    def extract_last_words(input_string, max_characters=MAX_TESTCASE_TITLE_LENGTH):
        if input_string is None:
            return None

        # Define delimiters for splitting words
        delimiters = [' ', '\t', ';', ':', '>', '/', '.']

        # Replace multiple consecutive delimiters with a single space
        regex_pattern = '|'.join(map(re.escape, delimiters))
        cleaned_string = re.sub(f'[{regex_pattern}]+', ' ', input_string.strip())

        # Split the cleaned string into words
        words = cleaned_string.split()

        # Extract the last words up to the maximum character limit
        extracted_words = []
        current_length = 0
        for word in reversed(words):
            if current_length + len(word) <= max_characters:
                extracted_words.append(word)
                current_length += len(word) + 1  # Add 1 for the space between words
            else:
                break

        # Reverse the extracted words to maintain the original order
        result = ' '.join(reversed(extracted_words))

        # as fallback, return the last characters if the result is empty
        if result.strip() == "":
            result = input_string[-max_characters:]

        return result