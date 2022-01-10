from serde.json import to_dict
from typing import List, Union, Any


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
            if returned_data_json[key] != value:
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
