import re, ast
from beartype.typing import Union, List, Dict, Tuple


class MatchersParser:

    AUTO = "auto"
    NAME = "name"
    PROPERTY = "property"

    @staticmethod
    def parse_name_with_id(case_name: str) -> Tuple[Union[int, List[int], None], str]:
        """Parses case names expecting an ID following one of the following patterns:

        Single ID patterns:
        - "C123 my test case"
        - "my test case C123"
        - "C123_my_test_case"
        - "my_test_case_C123"
        - "module_1_C123_my_test_case"
        - "[C123] my test case"
        - "my test case [C123]"
        - "module 1 [C123] my test case"
        - "my_test_case_C123()" (JUnit 5 support)

        Multiple ID patterns:
        - "[C123, C456, C789] my test case"
        - "my test case [C123, C456, C789]"
        - "C123_C456_C789_my_test_case" (underscore-separated)

        :param case_name: Name of the test case
        :return: Tuple with test case ID(s) (int for single, List[int] for multiple) and test case name without the ID(s)
        """
        # First, try to parse brackets for single or multiple IDs
        results = re.findall(r"\[(.*?)\]", case_name)
        for result in results:
            # Check if it contains comma-separated IDs
            if "," in result:
                # Multiple IDs in brackets: [C123, C456, C789]
                case_ids = MatchersParser._parse_multiple_case_ids_from_string(result)
                if case_ids:
                    id_tag = f"[{result}]"
                    tag_idx = case_name.find(id_tag)
                    cleaned_name = f"{case_name[0:tag_idx].strip()} {case_name[tag_idx + len(id_tag):].strip()}".strip()
                    # Return list for multiple IDs, int for single ID (backwards compatibility)
                    return case_ids if len(case_ids) > 1 else case_ids[0], cleaned_name
            elif result.lower().startswith("c"):
                # Single ID in brackets: [C123]
                case_id = result[1:]
                if case_id.isnumeric():
                    id_tag = f"[{result}]"
                    tag_idx = case_name.find(id_tag)
                    cleaned_name = f"{case_name[0:tag_idx].strip()} {case_name[tag_idx + len(id_tag):].strip()}".strip()
                    return int(case_id), cleaned_name

        # Try underscore-separated multiple IDs: C123_C456_C789_test_name
        underscore_case_ids = MatchersParser._parse_multiple_underscore_ids(case_name)
        if underscore_case_ids:
            return underscore_case_ids

        # Fall back to original space/underscore single ID parsing
        for char in [" ", "_"]:
            parts = case_name.split(char)
            parts_copy = parts.copy()
            for idx, part in enumerate(parts):
                if part.lower().startswith("c") and len(part) > 1:
                    id_part = part[1:]
                    id_part_clean = re.sub(r"\(.*\)$", "", id_part)
                    if id_part_clean.isnumeric():
                        parts_copy.pop(idx)
                        return int(id_part_clean), char.join(parts_copy)

        return None, case_name

    @staticmethod
    def _parse_multiple_case_ids_from_string(ids_string: str) -> List[int]:
        """
        Parse comma-separated case IDs from a string.

        Examples:
          - "C123, C456, C789" -> [123, 456, 789]
          - "123, 456, 789" -> [123, 456, 789]
          - " C123 , C456 " -> [123, 456]

        :param ids_string: String containing comma-separated case IDs
        :return: List of integer case IDs
        """
        case_ids = []
        parts = [part.strip() for part in ids_string.split(",")]

        for part in parts:
            if not part:
                continue

            # Remove 'C' or 'c' prefix if present
            cleaned = part.lower().replace("c", "", 1).strip()

            # Check if it's a valid numeric ID
            if cleaned.isdigit():
                case_id = int(cleaned)
                # Deduplicate
                if case_id not in case_ids:
                    case_ids.append(case_id)

        return case_ids

    @staticmethod
    def _parse_multiple_underscore_ids(case_name: str) -> Union[Tuple[List[int], str], Tuple[int, str], None]:
        """
        Parse multiple underscore-separated case IDs from test name.

        Examples:
          - "C123_C456_C789_test_name" -> ([123, 456, 789], "test_name")
          - "C100_C200_my_test" -> ([100, 200], "my_test")

        :param case_name: Test case name
        :return: Tuple with case IDs and cleaned name, or None if no multiple IDs found
        """
        parts = case_name.split("_")
        case_ids = []
        non_id_parts = []

        for part in parts:
            if part.lower().startswith("c") and len(part) > 1:
                id_part = part[1:]
                # Remove parentheses (JUnit 5 support)
                id_part_clean = re.sub(r"\(.*\)$", "", id_part)
                if id_part_clean.isdigit():
                    case_id = int(id_part_clean)
                    if case_id not in case_ids:
                        case_ids.append(case_id)
                    continue
            non_id_parts.append(part)

        # Only return if we found at least 2 case IDs
        if len(case_ids) >= 2:
            cleaned_name = "_".join(non_id_parts)
            return case_ids, cleaned_name

        return None


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
        delimiters = [" ", "\t", ";", ":", ">", "/", "."]

        # Replace multiple consecutive delimiters with a single space
        regex_pattern = "|".join(map(re.escape, delimiters))
        cleaned_string = re.sub(f"[{regex_pattern}]+", " ", input_string.strip())

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
        result = " ".join(reversed(extracted_words))

        # as fallback, return the last characters if the result is empty
        if result.strip() == "":
            result = input_string[-max_characters:]

        return result
