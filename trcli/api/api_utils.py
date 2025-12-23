"""
API Utilities - Shared utilities for API handlers

This module provides common utilities to reduce code duplication across handlers:
- Reference parsing and validation
- Response validation
- Type definitions for better type safety
"""

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
