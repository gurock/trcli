import html
import re

from serde.json import to_dict
from beartype.typing import List, Union, Any, Callable
from humanfriendly import parse_timespan

_MISSING = object()

# TestRail (v9.8.1+) can wrap/transform plain-text custom field values when a
# write request is sent with `is_legacy: True` (TRCLI sends this to request
# Markdown->HTML conversion for rich-text fields). This can wrap even plain
# Text fields in a single <p>...</p> block, convert runs of whitespace into
# &nbsp; entities, and append a trailing newline - none of which represent an
# actual content change. Strip that formatting before comparing so --verify
# doesn't false-positive on it.
_WRAPPING_P_TAG_RE = re.compile(r"^\s*<p>(.*)</p>\s*$", re.DOTALL)


def _strip_legacy_html_wrapping(value: str) -> str:
    """Undo TestRail's is_legacy-driven HTML wrapping of plain-text field values.

    Only unwraps a single outer <p>...</p> pair and decodes HTML entities
    (e.g. &nbsp;). Does not strip arbitrary/nested HTML, so genuinely
    HTML-formatted content still compares meaningfully instead of silently
    matching unrelated values.
    """
    match = _WRAPPING_P_TAG_RE.match(value)
    if match:
        value = match.group(1)
    value = html.unescape(value)
    # &nbsp; decodes to U+00A0 (non-breaking space), not a regular space - normalize
    # it back to a regular space since it represents the same whitespace semantically
    # (TestRail substitutes it for whitespace runs during Markdown->HTML conversion).
    value = value.replace("\xa0", " ")
    return value.strip()


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
            returned_value = returned_data_json.get(key, _MISSING)
            if returned_value is _MISSING:
                # Field is missing from the response entirely (e.g. a custom field that was
                # renamed/relocated server-side, such as the automation_id field variants).
                # Treat this as a verification failure rather than raising a KeyError.
                return False
            if not self.field_compare(key)(returned_value, value):
                return False

        return True

    def verify_returned_data_for_list(self, added_data: List[dict], returned_data: List[dict]):
        if not self.verify:
            return True  # skip verification
        if len(added_data) != len(returned_data):
            return False
        else:
            comparison_result = [
                self.verify_returned_data(item, returned_data[index]) for index, item in enumerate(added_data)
            ]
            return all(comparison_result)

    def field_compare(self, added_data_key: str) -> Callable:
        function_list = {
            "estimate": self.__compare_estimate,
            "description": self.__compare_strings,
            "comment": self.__compare_strings,
        }
        return function_list[added_data_key] if added_data_key in function_list else self.__simple_comparison

    @staticmethod
    def __simple_comparison(returned_value: Any, added_value: Any) -> bool:
        if returned_value == added_value:
            return True
        # Fall back to a legacy-HTML-tolerant comparison only for string values -
        # covers e.g. custom_automation_id coming back wrapped as "<p>...&nbsp;...</p>\n"
        # when TRCLI's `is_legacy` flag triggered TestRail's Markdown->HTML conversion
        # on a plain-text field. Non-string types (int, bool, None, etc.) always use
        # strict equality above - this fallback never changes their result.
        if isinstance(returned_value, str) and isinstance(added_value, str):
            return _strip_legacy_html_wrapping(returned_value) == _strip_legacy_html_wrapping(added_value)
        return False

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
