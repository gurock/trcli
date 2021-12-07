TEST_RAIL_URL = "https://FakeTestRail.io"
SUFFIX_API_VERSION = "/index.php?/api/v2/"


def create_url(resource: str):
    return TEST_RAIL_URL + SUFFIX_API_VERSION + resource
