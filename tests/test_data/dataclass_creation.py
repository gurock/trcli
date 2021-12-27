from junitparser import Skipped, Failure, Error


FAILED_RESULT_INPUT = Failure(type_="Fail", message="This test Failed")
FAILED_RESULT_INPUT.text = "Assertion failed"
FAILED_EXPECTED = {
    "status_id": 5,
    "comment": "Type: Fail\nMessage: This test Failed\nText: Assertion failed",
}

SKIPPED_RESULT_INPUT = Skipped(type_="Skipped", message="This test Skipped")
SKIPPED_RESULT_INPUT.text = "Skipped by user"
SKIPPED_EXPECTED = {
    "status_id": 4,
    "comment": "Type: Skipped\nMessage: This test Skipped\nText: Skipped by user",
}

SKIPPED_RESULT_EMPTY_INPUT = Skipped()
SKIPPED_EMPTY_EXPECTED = {"status_id": 4, "comment": ""}

ERROR_RESULT_INPUT = Error(type_="Error", message="This test Error")
ERROR_RESULT_INPUT.text = "Error in line 1"
ERROR_EXPECTED = {
    "status_id": 5,
    "comment": "Type: Error\nMessage: This test Error\nText: Error in line 1",
}

PASSED_EXPECTED = {"status_id": 1, "comment": ""}
