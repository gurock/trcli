def check_parsed_data(expected_result: dict, result_to_compare: dict):
    assert (
        expected_result == result_to_compare
    ), f"Wrong data received after config parsing. Expected: {expected_result} but received: {result_to_compare}."


def check_verbose_message(expected_message: str, result_to_compare: str):
    assert (
        result_to_compare in expected_message
    ), f"Wrong verbose message. Expected: {expected_message} but got {result_to_compare} instead."
