"""
Dynamic Filters Utilities - Helper functions for loading, validating, and formatting dynamic filters

Dynamic filters enable auto-updating test runs that continuously synchronize with test case repository.
This module provides utilities for working with dynamic filter JSON files.
"""

from beartype.typing import Dict, Tuple, Any
import json
import builtins

# Field type constants (from TestRail API)
FIELD_TYPES = {
    1: "String",
    2: "Integer",
    4: "URL",
    5: "Checkbox",
    6: "Dropdown",
    7: "User",
    8: "Date",
    9: "Milestone",
    12: "Multi-select",
}

# Operator constants (from TestRail API)
OPERATORS = {
    1: "Is",
    2: "Is Not",
    3: "Is Before",
    4: "Is After",
    5: "Contains",
    6: "Does not contain",
    7: "Is Less",
    8: "Is More",
}


def load_dynamic_filters_from_file(file_path: str) -> Tuple[Dict[str, Any], str]:
    """
    Load and validate dynamic filters from JSON file.

    Supports two formats:
    1. Full format with top-level mode:
       {"mode": "1", "filters": {"cases:priority_id": {...}}}

    2. Simplified format (auto-wrapped):
       {"cases:priority_id": {...}}
       (automatically wrapped with mode "1")

    :param file_path: Path to JSON file containing filter criteria
    :returns: Tuple with (filters_dict, error_message)
              filters_dict has structure: {"mode": "1/2", "filters": {...}}
    """
    try:
        with open(file_path, "r") as f:
            filters = json.load(f)

        # Normalize: if no top-level "filters" key, wrap it
        if "filters" not in filters:
            # Simplified format - wrap it with default mode
            filters = {"mode": "1", "filters": filters}

        # Validate structure
        is_valid, error = validate_dynamic_filters_structure(filters)
        if not is_valid:
            return {}, error

        return filters, ""
    except json.JSONDecodeError as e:
        return {}, f"Invalid JSON: {str(e)}"
    except FileNotFoundError:
        return {}, f"File not found: {file_path}"
    except Exception as e:
        return {}, f"Error loading filter file: {str(e)}"


def validate_dynamic_filters_structure(filters: dict) -> Tuple[bool, str]:
    """
    Validate filter structure matches TestRail API requirements.

    Note: Client sends format WITHOUT type_id.
    TestRail validates and enriches with type_id on server side.

    :param filters: The filters dictionary to validate
    :returns: Tuple with (is_valid, error_message)
    """
    if not isinstance(filters, dict):
        return False, "Filters must be a JSON object"

    # Check top-level mode if present
    if "mode" in filters:
        if filters["mode"] not in ["1", "2"]:
            return False, "Top-level mode must be '1' (AND) or '2' (OR)"
    else:
        # Default to AND mode if not specified
        filters["mode"] = "1"

    # Check filters dict
    if "filters" not in filters:
        return False, "Missing 'filters' key in top-level object"

    filters_dict = filters["filters"]
    if not isinstance(filters_dict, dict):
        return False, "'filters' must be a JSON object"

    if len(filters_dict) == 0:
        return False, "'filters' object cannot be empty - at least one filter field required"

    # Validate each field filter
    for field_name, field_filter in filters_dict.items():
        if not field_name.startswith("cases:"):
            return False, f"Field name must start with 'cases:' prefix: {field_name}"

        is_valid, error = validate_field_filter(field_name, field_filter)
        if not is_valid:
            return False, f"Invalid filter for {field_name}: {error}"

    return True, ""


def validate_field_filter(field_name: str, field_filter: dict) -> Tuple[bool, str]:
    """
    Validate individual field filter structure.

    Supports multiple formats based on field type:
    1. Single value: {"value": true/false/1/"string"}
       - Checkbox: {"value": true/false}
       - Dropdown single select: {"value": 1}
    2. Multiple values: {"values": ["all", 1, 2]}
       - Dropdown/User/Milestone: {"values": ["all", 1, 2]}
    3. String/Integer/Date with operators: {"mode": "1/2", "filters": [{"op": 1, "value": "..."}]}
    4. Multi-select: {"mode": "1/2", "values": [1, 2, 3]}

    :param field_name: Name of the field (e.g., "cases:priority_id")
    :param field_filter: The filter configuration for this field
    :returns: Tuple with (is_valid, error_message)
    """
    if not isinstance(field_filter, dict):
        return False, "Field filter must be a JSON object"

    # Check for valid structures based on which keys are present
    has_value = "value" in field_filter
    has_values = "values" in field_filter
    has_filters = "filters" in field_filter
    has_mode = "mode" in field_filter

    if has_value:
        # Format 1: Single value selection
        # - Checkbox: {"value": true/false} - boolean
        # - Dropdown/Single select: {"value": 1} - number or string
        value = field_filter["value"]
        if not isinstance(value, (bool, int, str)):
            return False, "Value must be boolean (for checkboxes), number, or string"

    elif has_values and not has_filters:
        # Format 2: Dropdown/Multi-select {"values": [...]}
        # or Format 4: Multi-select with mode {"mode": "1/2", "values": [...]}
        if not isinstance(field_filter["values"], builtins.list):
            return False, "'values' must be an array"

        if has_mode and field_filter["mode"] not in ["1", "2"]:
            return False, "Mode must be '1' (AND) or '2' (OR)"

    elif has_filters:
        # Format 3: Operator-based {"mode": "1/2", "filters": [...]}
        if not has_mode:
            return False, "Filters with operators require 'mode'"

        if field_filter["mode"] not in ["1", "2"]:
            return False, "Filter mode must be '1' (match all) or '2' (match any)"

        if not isinstance(field_filter["filters"], builtins.list):
            return False, "'filters' must be an array"

        if len(field_filter["filters"]) == 0:
            return False, "'filters' array cannot be empty"

        # Validate each operator filter
        for op_filter in field_filter["filters"]:
            if not isinstance(op_filter, dict):
                return False, "Operator filter must be a JSON object"

            if "op" not in op_filter or "value" not in op_filter:
                return False, "Operator filter must have 'op' and 'value' keys"

            if not isinstance(op_filter["op"], int):
                return False, "Operator 'op' must be an integer (1-8)"

            # Validate operator value range
            if op_filter["op"] not in OPERATORS:
                return False, f"Invalid operator: {op_filter['op']}. Must be 1-8"
    else:
        return False, "Field filter must have 'value', 'values', or 'filters'"

    return True, ""


def format_filter_for_display(filters: dict, field_labels: dict = None) -> str:
    """
    Format filters for human-readable CLI display.

    :param filters: The dynamic_filters object with structure {"mode": "1/2", "filters": {...}}
    :param field_labels: Optional dict mapping system_name to label for better readability
    :returns: Formatted multi-line string for CLI output
    """
    if not filters or "filters" not in filters:
        return "No filters"

    mode = filters.get("mode", "1")
    mode_text = "Match ALL conditions (AND)" if mode == "1" else "Match ANY condition (OR)"

    lines = [f"Mode: {mode_text}", "Filters:"]

    for field_name, field_filter in filters["filters"].items():
        # Remove "cases:" prefix for display
        display_name = field_name.replace("cases:", "")

        # Use label if provided
        if field_labels and field_name in field_labels:
            display_name = field_labels[field_name]

        # Format based on filter type
        if "value" in field_filter:
            # Checkbox
            value_text = "true" if field_filter["value"] else "false"
            lines.append(f"  - {display_name}: {value_text}")

        elif "values" in field_filter:
            # Dropdown/Multi-select
            values = field_filter["values"]
            if "all" in values:
                values_text = "all"
            else:
                values_text = ", ".join(str(v) for v in values)
            lines.append(f"  - {display_name}: {values_text}")

        elif "filters" in field_filter:
            # Operator-based
            filter_mode = "Match ALL" if field_filter.get("mode") == "1" else "Match ANY"
            lines.append(f"  - {display_name} ({filter_mode}):")

            for op_filter in field_filter["filters"]:
                op_name = OPERATORS.get(op_filter["op"], f"Operator {op_filter['op']}")
                value = op_filter["value"]
                lines.append(f"      {op_name}: {value}")

    return "\n".join(lines)
