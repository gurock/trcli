"""
API Utilities - Shared utilities for API handlers

This module provides common utilities to reduce code duplication across handlers:
- Reference parsing and validation
- Response validation
- Type definitions for better type safety
"""

import re

from beartype.typing import List, Tuple, Optional, Literal
from typing_extensions import TypedDict


# ============================================================================
# Type Definitions for Better Type Safety
# ============================================================================


class TestRailResponse(TypedDict, total=False):
    """Type definition for TestRail API responses"""

    id: int
    name: str
    title: str
    suite_id: int
    section_id: int
    case_id: int
    refs: str
    error: str


# Literal types for strategy parameters
ReferenceStrategy = Literal["add", "update", "delete", "append", "replace"]


# ============================================================================
# Reference Utilities
# ============================================================================


def parse_references(refs_string: str) -> List[str]:
    """
    Parse a comma-separated reference string into a list of cleaned references.

    Args:
        refs_string: Comma-separated string of references (e.g., "REF-1, REF-2, REF-3")

    Returns:
        List of cleaned, non-empty reference strings

    Example:
        >>> parse_references("REF-1, , REF-2  ,REF-3")
        ['REF-1', 'REF-2', 'REF-3']
    """
    if not refs_string:
        return []
    return [ref.strip() for ref in refs_string.split(",") if ref.strip()]


def deduplicate_references(references: List[str]) -> List[str]:
    """
    Deduplicate a list of references while preserving order.

    Args:
        references: List of reference strings

    Returns:
        List of unique references in original order

    Example:
        >>> deduplicate_references(['REF-1', 'REF-2', 'REF-1', 'REF-3'])
        ['REF-1', 'REF-2', 'REF-3']
    """
    seen = set()
    result = []
    for ref in references:
        ref_clean = ref.strip()
        if ref_clean and ref_clean not in seen:
            result.append(ref_clean)
            seen.add(ref_clean)
    return result


# Recognizes a "bare" Jira-issue-key-shaped tag, e.g. "JIRA-1234", "PROJ-42", "TR-1".
# Requires an all-caps (letters+digits) project-key prefix followed by a hyphen and
# digits, so generic noise tags such as "priority-high" or "smoke" are never matched.
_BARE_JIRA_KEY_RE = re.compile(r"^[A-Z][A-Z0-9]*-\d+$")

# Recognizes an explicit "jira:<value>" or "refs:<value>" tag prefix (case-insensitive
# on the prefix only). The value after the colon is used verbatim (whitespace-trimmed)
# with no further shape validation, mirroring the pre-existing
# "- testrail_case_field: refs:VALUE" documentation-property convention already used
# by both the Robot Framework and JUnit readers, just applied to tags instead of
# documentation lines.
_PREFIXED_REF_TAG_RE = re.compile(r"^(?:jira|refs)\s*:\s*(.+)$", re.IGNORECASE)


def extract_jira_references(tags: List[str]) -> List[str]:
    """
    Extract TestRail/Jira references from a list of Robot Framework style tags.

    Recognizes three tag conventions (checked independently per-tag; any mix may be
    present on the same test):
        - Explicit "jira:<value>" prefix (case-insensitive), e.g. "jira:PROJ-123"
        - Explicit "refs:<value>" prefix (case-insensitive), e.g. "refs:TSTRAIL-5"
        - A "bare" Jira-issue-key-shaped tag, e.g. "JIRA-1234" (an all-caps
          letters/digits project-key prefix, a hyphen, then digits)

    Any tag that doesn't match one of these three conventions (e.g. "priority-high",
    "smoke") is silently ignored - it isn't a reference and isn't treated as an error.

    Args:
        tags: Raw list of tag strings from a Robot Framework test (e.g. ``test.tags``)

    Returns:
        List of extracted, deduplicated reference strings, in first-seen order.

    Example:
        >>> extract_jira_references(["jira:PROJ-123", "smoke"])
        ['PROJ-123']
        >>> extract_jira_references(["JIRA-1234", "priority-high"])
        ['JIRA-1234']
        >>> extract_jira_references(["refs:TSTRAIL-5"])
        ['TSTRAIL-5']
        >>> extract_jira_references(["JIRA-1", "jira:JIRA-1", "refs:JIRA-1"])
        ['JIRA-1']
    """
    found = []
    for tag in tags or []:
        tag = (tag or "").strip()
        if not tag:
            continue
        prefixed_match = _PREFIXED_REF_TAG_RE.match(tag)
        if prefixed_match:
            value = prefixed_match.group(1).strip()
            if value:
                found.append(value)
            continue
        if _BARE_JIRA_KEY_RE.match(tag):
            found.append(tag)
    return deduplicate_references(found)


def join_references(references: List[str]) -> str:
    """
    Join a list of references into a comma-separated string.

    Args:
        references: List of reference strings

    Returns:
        Comma-separated string of references

    Example:
        >>> join_references(['REF-1', 'REF-2', 'REF-3'])
        'REF-1,REF-2,REF-3'
    """
    return ",".join(references)


def validate_references_length(refs_string: str, max_length: int) -> Tuple[bool, Optional[str]]:
    """
    Validate that a reference string doesn't exceed the maximum length.

    Args:
        refs_string: Comma-separated string of references
        max_length: Maximum allowed length

    Returns:
        Tuple of (is_valid, error_message)
        - is_valid: True if length is valid, False otherwise
        - error_message: None if valid, error description if invalid

    Example:
        >>> validate_references_length("REF-1,REF-2", 2000)
        (True, None)
        >>> validate_references_length("X" * 2001, 2000)
        (False, "Combined references length (2001 characters) exceeds 2000 character limit")
    """
    length = len(refs_string)
    if length > max_length:
        return False, f"Combined references length ({length} characters) exceeds {max_length} character limit"
    return True, None


def merge_references(existing_refs: str, new_refs: str, strategy: ReferenceStrategy = "add") -> str:
    """
    Merge existing and new references based on the specified strategy.

    Args:
        existing_refs: Current comma-separated references
        new_refs: New comma-separated references to merge
        strategy: How to merge references:
            - 'add'/'append': Add new refs to existing, avoiding duplicates
            - 'update'/'replace': Replace all existing refs with new refs
            - 'delete': Remove specified refs from existing

    Returns:
        Merged comma-separated reference string

    Examples:
        >>> merge_references("REF-1,REF-2", "REF-3,REF-4", "add")
        'REF-1,REF-2,REF-3,REF-4'
        >>> merge_references("REF-1,REF-2", "REF-3", "update")
        'REF-3'
        >>> merge_references("REF-1,REF-2,REF-3", "REF-2", "delete")
        'REF-1,REF-3'
    """
    if strategy in ("update", "replace"):
        # Replace all references with new ones
        return new_refs

    elif strategy == "delete":
        if not new_refs:
            # Delete all references
            return ""
        # Delete specific references
        existing_list = parse_references(existing_refs)
        refs_to_delete = set(parse_references(new_refs))
        remaining = [ref for ref in existing_list if ref not in refs_to_delete]
        return join_references(remaining)

    else:  # strategy in ('add', 'append')
        # Add new references to existing ones, avoiding duplicates
        if not existing_refs:
            return new_refs

        existing_list = parse_references(existing_refs)
        new_list = parse_references(new_refs)

        # Combine, avoiding duplicates while preserving order
        combined = existing_list + [ref for ref in new_list if ref not in existing_list]
        return join_references(combined)


def calculate_reference_changes(existing_refs: str, new_refs: str) -> Tuple[List[str], List[str]]:
    """
    Calculate which references will be added and which are duplicates.

    Args:
        existing_refs: Current comma-separated references
        new_refs: New comma-separated references to process

    Returns:
        Tuple of (added_refs, skipped_refs)
        - added_refs: References that will be newly added
        - skipped_refs: References that already exist (duplicates)

    Example:
        >>> calculate_reference_changes("REF-1,REF-2", "REF-2,REF-3")
        (['REF-3'], ['REF-2'])
    """
    existing_list = parse_references(existing_refs)
    new_list = deduplicate_references(parse_references(new_refs))

    added_refs = [ref for ref in new_list if ref not in existing_list]
    skipped_refs = [ref for ref in new_list if ref in existing_list]

    return added_refs, skipped_refs


# ============================================================================
# Response Validation Utilities
# ============================================================================


def check_response_error(response, default_error_msg: str = "API request failed") -> Optional[str]:
    """
    Check if a response contains an error and return the error message.

    Args:
        response: API response object with error_message attribute
        default_error_msg: Default message if error_message is empty

    Returns:
        Error message string if error exists, None otherwise

    Example:
        >>> response = MockResponse(error_message="Field not found")
        >>> check_response_error(response)
        'Field not found'
    """
    if hasattr(response, "error_message") and response.error_message:
        return response.error_message
    return None


def validate_response_field(
    response_data: dict, field_name: str, error_prefix: str = "Response"
) -> Tuple[bool, Optional[str]]:
    """
    Validate that a required field exists in the response data.

    Args:
        response_data: Dictionary containing response data
        field_name: Name of the required field
        error_prefix: Prefix for error message

    Returns:
        Tuple of (is_valid, error_message)
        - is_valid: True if field exists, False otherwise
        - error_message: None if valid, error description if invalid

    Example:
        >>> validate_response_field({"id": 123, "name": "Test"}, "id")
        (True, None)
        >>> validate_response_field({"name": "Test"}, "id")
        (False, "Response missing 'id' field")
    """
    if field_name in response_data:
        return True, None
    return False, f"{error_prefix} missing '{field_name}' field"


# ============================================================================
# Common Patterns
# ============================================================================


def safe_get_nested(data: dict, *keys, default=None):
    """
    Safely get a nested value from a dictionary.

    Args:
        data: Dictionary to search
        *keys: Sequence of keys to traverse
        default: Default value if key path not found

    Returns:
        Value at the key path, or default if not found

    Example:
        >>> data = {"user": {"profile": {"name": "John"}}}
        >>> safe_get_nested(data, "user", "profile", "name")
        'John'
        >>> safe_get_nested(data, "user", "invalid", "key", default="N/A")
        'N/A'
    """
    current = data
    for key in keys:
        if isinstance(current, dict) and key in current:
            current = current[key]
        else:
            return default
    return current
