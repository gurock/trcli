from serde.json import to_dict
from beartype.typing import List, Union, Any, Callable
from humanfriendly import parse_timespan


class ApiResponseVerify:
    """Class for verifying if new resources added to Test Rail are created correctly.
    :verify: If false all verification methods are skipped.
                Default False because verification is an optional parameter steered by user in CLI.
    """

    def __init__(self, verify: bool = False):
        self.verify = verify

    def verify_returned_data(self, added_data: Union[dict, Any], returned_data: dict):
        """
        Check if all added_data fields are in returned data.
        For all POST requests in test rail response will be the same as for GET
        e.g. add_case POST (If successful) method returns the new created test case using
         the same response format as get_case.
        :added_data: dict or dataclass
        :returned_data: dict
        """
        if not self.verify:
            return True  # skip verification
        added_data_json = to_dict(added_data)
        returned_data_json = to_dict(returned_data)
        for key, value in added_data_json.items():
            if not self.field_compare(key)(returned_data_json[key], value):
                return False

        return True

    def verify_returned_data_for_list(
        self, added_data: List[dict], returned_data: List[dict]
    ):
        if not self.verify:
            return True  # skip verification
        if len(added_data) != len(returned_data):
            return False
        else:
            comparison_result = [
                self.verify_returned_data(item, returned_data[index])
                for index, item in enumerate(added_data)
            ]
            return all(comparison_result)

    def field_compare(self, added_data_key: str) -> Callable:
        function_list = {
            "estimate": self.__compare_estimate,
            "description": self.__compare_strings,
            "comment": self.__compare_strings,
        }
        return (
            function_list[added_data_key]
            if added_data_key in function_list
            else self.__simple_comparison
        )

    @staticmethod
    def __simple_comparison(returned_value: Any, added_value: Any) -> bool:
        return returned_value == added_value

    @staticmethod
    def __compare_estimate(returned_value: str, added_value: str) -> bool:
        sum_time_returned = sum(map(parse_timespan, returned_value.split(" ")))
        sum_time_added = sum(map(parse_timespan, added_value.split(" ")))
        return sum_time_returned == sum_time_added

    @staticmethod
    def __compare_strings(returned_value: str, added_value: str) -> bool:
        returned_value = "" if returned_value in [None, ""] else returned_value
        added_value = "" if added_value in [None, ""] else added_value
        return returned_value == added_value
