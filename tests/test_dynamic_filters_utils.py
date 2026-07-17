"""
Unit tests for dynamic_filters_utils module
"""

import json
import os
import tempfile
import pytest

from trcli.api.dynamic_filters_utils import (
    load_dynamic_filters_from_file,
    validate_dynamic_filters_structure,
    validate_field_filter,
    format_filter_for_display,
    FIELD_TYPES,
    OPERATORS,
)


class TestLoadDynamicFiltersFromFile:
    """Tests for load_dynamic_filters_from_file function"""

    def test_load_full_format_valid(self):
        """Test loading filters in full format with top-level mode"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(
                {"mode": "1", "filters": {"cases:priority_id": {"values": [1, 2]}}},
                f,
            )
            f.flush()
            filters, error = load_dynamic_filters_from_file(f.name)
            os.unlink(f.name)

        assert error == ""
        assert filters["mode"] == "1"
        assert filters["filters"] == {"cases:priority_id": {"values": [1, 2]}}
        assert filters["_mode_from_json"] is True

    def test_load_simplified_format_auto_wrapped(self):
        """Test loading filters in simplified format (auto-wrapped with mode=1)"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump({"cases:priority_id": {"values": [1, 2]}}, f)
            f.flush()
            filters, error = load_dynamic_filters_from_file(f.name)
            os.unlink(f.name)

        assert error == ""
        assert filters["mode"] == "1"
        assert filters["filters"] == {"cases:priority_id": {"values": [1, 2]}}
        assert filters["_mode_from_json"] is False

    def test_load_invalid_json(self):
        """Test loading file with invalid JSON"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            f.write("{invalid json}")
            f.flush()
            filters, error = load_dynamic_filters_from_file(f.name)
            os.unlink(f.name)

        assert "Invalid JSON" in error
        assert filters == {}

    def test_load_file_not_found(self):
        """Test loading non-existent file"""
        filters, error = load_dynamic_filters_from_file("/nonexistent/file.json")
        assert "File not found" in error
        assert filters == {}

    def test_load_empty_filters(self):
        """Test loading file with empty filters object"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump({"mode": "1", "filters": {}}, f)
            f.flush()
            filters, error = load_dynamic_filters_from_file(f.name)
            os.unlink(f.name)

        assert "'filters' object cannot be empty" in error
        assert filters == {}


class TestValidateDynamicFiltersStructure:
    """Tests for validate_dynamic_filters_structure function"""

    def test_validate_valid_structure(self):
        """Test validation of valid filter structure"""
        filters = {"mode": "1", "filters": {"cases:priority_id": {"values": [1, 2]}}}
        is_valid, error = validate_dynamic_filters_structure(filters)
        assert is_valid is True
        assert error == ""

    def test_validate_missing_mode_defaults_to_1(self):
        """Test that missing mode defaults to '1'"""
        filters = {"filters": {"cases:priority_id": {"values": [1, 2]}}}
        is_valid, error = validate_dynamic_filters_structure(filters)
        assert is_valid is True
        assert filters["mode"] == "1"

    def test_validate_invalid_mode(self):
        """Test validation rejects invalid mode"""
        filters = {"mode": "3", "filters": {"cases:priority_id": {"values": [1, 2]}}}
        is_valid, error = validate_dynamic_filters_structure(filters)
        assert is_valid is False
        assert "mode must be '1' (AND) or '2' (OR)" in error

    def test_validate_missing_filters_key(self):
        """Test validation rejects missing filters key"""
        filters = {"mode": "1"}
        is_valid, error = validate_dynamic_filters_structure(filters)
        assert is_valid is False
        assert "Missing 'filters' key" in error

    def test_validate_filters_not_dict(self):
        """Test validation rejects non-dict filters"""
        filters = {"mode": "1", "filters": []}
        is_valid, error = validate_dynamic_filters_structure(filters)
        assert is_valid is False
        assert "'filters' must be a JSON object" in error

    def test_validate_empty_filters(self):
        """Test validation rejects empty filters object"""
        filters = {"mode": "1", "filters": {}}
        is_valid, error = validate_dynamic_filters_structure(filters)
        assert is_valid is False
        assert "'filters' object cannot be empty" in error

    def test_validate_field_without_cases_prefix(self):
        """Test validation rejects field names without 'cases:' prefix"""
        filters = {"mode": "1", "filters": {"priority_id": {"values": [1, 2]}}}
        is_valid, error = validate_dynamic_filters_structure(filters)
        assert is_valid is False
        assert "must start with 'cases:' prefix" in error


class TestValidateFieldFilter:
    """Tests for validate_field_filter function"""

    def test_validate_checkbox_format(self):
        """Test validation of checkbox field filter"""
        is_valid, error = validate_field_filter("cases:is_automated", {"value": True})
        assert is_valid is True
        assert error == ""

    def test_validate_single_value_invalid_type(self):
        """Test validation rejects invalid value types (arrays, objects)"""
        is_valid, error = validate_field_filter("cases:priority_id", {"value": [1, 2]})
        assert is_valid is False
        assert "Value must be boolean" in error or "number" in error or "string" in error

    def test_validate_dropdown_single_value(self):
        """Test validation of dropdown with single value (not array)"""
        is_valid, error = validate_field_filter("cases:priority_id", {"value": 1})
        assert is_valid is True
        assert error == ""

        # Also test with string value
        is_valid, error = validate_field_filter("cases:custom_field", {"value": "option1"})
        assert is_valid is True
        assert error == ""

    def test_validate_dropdown_format(self):
        """Test validation of dropdown field filter"""
        is_valid, error = validate_field_filter("cases:priority_id", {"values": [1, 2, 3]})
        assert is_valid is True
        assert error == ""

    def test_validate_dropdown_with_all(self):
        """Test validation of dropdown with 'all' value"""
        is_valid, error = validate_field_filter("cases:priority_id", {"values": ["all"]})
        assert is_valid is True
        assert error == ""

    def test_validate_multi_select_with_mode(self):
        """Test validation of multi-select with mode"""
        is_valid, error = validate_field_filter("cases:custom_field", {"mode": "1", "values": [1, 2, 3]})
        assert is_valid is True
        assert error == ""

    def test_validate_multi_select_invalid_mode(self):
        """Test validation rejects invalid mode in multi-select"""
        is_valid, error = validate_field_filter("cases:custom_field", {"mode": "3", "values": [1, 2, 3]})
        assert is_valid is False
        assert "Mode must be '1' (AND) or '2' (OR)" in error

    def test_validate_operator_based_format(self):
        """Test validation of operator-based field filter"""
        field_filter = {"mode": "1", "filters": [{"op": 5, "value": "test"}]}
        is_valid, error = validate_field_filter("cases:title", field_filter)
        assert is_valid is True
        assert error == ""

    def test_validate_operator_based_missing_mode(self):
        """Test validation rejects operator-based filter without mode"""
        field_filter = {"filters": [{"op": 5, "value": "test"}]}
        is_valid, error = validate_field_filter("cases:title", field_filter)
        assert is_valid is False
        assert "Filters with operators require 'mode'" in error

    def test_validate_operator_based_invalid_mode(self):
        """Test validation rejects invalid mode in operator-based filter"""
        field_filter = {"mode": "3", "filters": [{"op": 5, "value": "test"}]}
        is_valid, error = validate_field_filter("cases:title", field_filter)
        assert is_valid is False
        assert "Filter mode must be '1' (match all) or '2' (match any)" in error

    def test_validate_operator_based_empty_filters(self):
        """Test validation rejects empty filters array"""
        field_filter = {"mode": "1", "filters": []}
        is_valid, error = validate_field_filter("cases:title", field_filter)
        assert is_valid is False
        assert "'filters' array cannot be empty" in error

    def test_validate_operator_based_invalid_operator(self):
        """Test validation rejects invalid operator ID"""
        field_filter = {"mode": "1", "filters": [{"op": 99, "value": "test"}]}
        is_valid, error = validate_field_filter("cases:title", field_filter)
        assert is_valid is False
        assert "Invalid operator" in error

    def test_validate_operator_based_missing_op(self):
        """Test validation rejects operator filter without 'op' key"""
        field_filter = {"mode": "1", "filters": [{"value": "test"}]}
        is_valid, error = validate_field_filter("cases:title", field_filter)
        assert is_valid is False
        assert "must have 'op' and 'value' keys" in error

    def test_validate_operator_based_missing_value(self):
        """Test validation rejects operator filter without 'value' key"""
        field_filter = {"mode": "1", "filters": [{"op": 5}]}
        is_valid, error = validate_field_filter("cases:title", field_filter)
        assert is_valid is False
        assert "must have 'op' and 'value' keys" in error

    def test_validate_invalid_field_filter_format(self):
        """Test validation rejects field filter without required keys"""
        is_valid, error = validate_field_filter("cases:priority_id", {})
        assert is_valid is False
        assert "must have 'value', 'values', or 'filters'" in error


class TestFormatFilterForDisplay:
    """Tests for format_filter_for_display function"""

    def test_format_no_filters(self):
        """Test formatting empty filters"""
        result = format_filter_for_display({})
        assert result == "No filters"

        result = format_filter_for_display(None)
        assert result == "No filters"

    def test_format_and_mode(self):
        """Test formatting filters with AND mode"""
        filters = {"mode": "1", "filters": {"cases:priority_id": {"values": [1, 2]}}}
        result = format_filter_for_display(filters)
        assert "Match ALL conditions (AND)" in result
        assert "priority_id" in result

    def test_format_or_mode(self):
        """Test formatting filters with OR mode"""
        filters = {"mode": "2", "filters": {"cases:priority_id": {"values": [1, 2]}}}
        result = format_filter_for_display(filters)
        assert "Match ANY condition (OR)" in result

    def test_format_checkbox_filter(self):
        """Test formatting checkbox filter"""
        filters = {"mode": "1", "filters": {"cases:is_automated": {"value": True}}}
        result = format_filter_for_display(filters)
        assert "is_automated: true" in result

    def test_format_dropdown_filter(self):
        """Test formatting dropdown filter"""
        filters = {"mode": "1", "filters": {"cases:priority_id": {"values": [1, 2, 3]}}}
        result = format_filter_for_display(filters)
        assert "priority_id: 1, 2, 3" in result

    def test_format_dropdown_filter_with_all(self):
        """Test formatting dropdown filter with 'all' value"""
        filters = {"mode": "1", "filters": {"cases:priority_id": {"values": ["all", 1, 2]}}}
        result = format_filter_for_display(filters)
        assert "priority_id: all" in result

    def test_format_operator_based_filter(self):
        """Test formatting operator-based filter"""
        filters = {
            "mode": "1",
            "filters": {"cases:title": {"mode": "2", "filters": [{"op": 5, "value": "test"}]}},
        }
        result = format_filter_for_display(filters)
        assert "title (Match ANY):" in result
        assert "Contains: test" in result

    def test_format_with_field_labels(self):
        """Test formatting with custom field labels"""
        filters = {"mode": "1", "filters": {"cases:priority_id": {"values": [1, 2]}}}
        field_labels = {"cases:priority_id": "Priority"}
        result = format_filter_for_display(filters, field_labels)
        assert "Priority:" in result


class TestConstants:
    """Tests for module constants"""

    def test_field_types_constant(self):
        """Test FIELD_TYPES constant has expected values"""
        assert FIELD_TYPES[1] == "String"
        assert FIELD_TYPES[6] == "Dropdown"
        assert FIELD_TYPES[12] == "Multi-select"

    def test_operators_constant(self):
        """Test OPERATORS constant has expected values"""
        assert OPERATORS[1] == "Is"
        assert OPERATORS[5] == "Contains"
        assert OPERATORS[8] == "Is More"


class TestModePrecedence:
    """Tests for mode precedence behavior between JSON file and CLI flag"""

    def test_mode_explicitly_provided_in_full_format(self):
        """Test that _mode_from_json flag is True when mode is in JSON (full format)"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(
                {"mode": "2", "filters": {"cases:priority_id": {"values": [1, 2]}}},
                f,
            )
            f.flush()
            filters, error = load_dynamic_filters_from_file(f.name)
            os.unlink(f.name)

        assert error == ""
        assert filters["mode"] == "2"
        assert filters["_mode_from_json"] is True

    def test_mode_not_provided_in_simplified_format(self):
        """Test that _mode_from_json flag is False when using simplified format (no mode in JSON)"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump({"cases:priority_id": {"values": [1, 2]}}, f)
            f.flush()
            filters, error = load_dynamic_filters_from_file(f.name)
            os.unlink(f.name)

        assert error == ""
        assert filters["mode"] == "1"  # Default mode added by validation
        assert filters["_mode_from_json"] is False  # Mode was NOT in original JSON

    def test_mode_not_provided_in_full_format_without_mode_key(self):
        """Test that _mode_from_json flag is False when full format used but no mode key"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(
                {"filters": {"cases:priority_id": {"values": [1, 2]}}},
                f,
            )
            f.flush()
            filters, error = load_dynamic_filters_from_file(f.name)
            os.unlink(f.name)

        assert error == ""
        assert filters["mode"] == "1"  # Default mode added by validation
        assert filters["_mode_from_json"] is False  # Mode was NOT in original JSON

    def test_mode_precedence_json_mode_1_provided(self):
        """Test that mode '1' from JSON is preserved"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(
                {"mode": "1", "filters": {"cases:priority_id": {"values": [1, 2]}}},
                f,
            )
            f.flush()
            filters, error = load_dynamic_filters_from_file(f.name)
            os.unlink(f.name)

        assert error == ""
        assert filters["mode"] == "1"
        assert filters["_mode_from_json"] is True

    def test_mode_precedence_json_mode_2_provided(self):
        """Test that mode '2' from JSON is preserved"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(
                {"mode": "2", "filters": {"cases:priority_id": {"values": [1, 2]}}},
                f,
            )
            f.flush()
            filters, error = load_dynamic_filters_from_file(f.name)
            os.unlink(f.name)

        assert error == ""
        assert filters["mode"] == "2"
        assert filters["_mode_from_json"] is True

    def test_mode_flag_allows_cli_override_for_simplified_format(self):
        """Test that simplified format (no mode) allows CLI override via _mode_from_json=False"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump({"cases:priority_id": {"values": [1, 2]}}, f)
            f.flush()
            filters, error = load_dynamic_filters_from_file(f.name)
            os.unlink(f.name)

        assert error == ""
        # Initially has default mode "1"
        assert filters["mode"] == "1"
        # But flag indicates it can be overridden
        assert filters["_mode_from_json"] is False

        # Simulate CLI override (this would happen in project_based_client.py)
        mode_from_json = filters.pop("_mode_from_json", True)
        cli_mode = "2"
        if cli_mode and not mode_from_json:
            filters["mode"] = cli_mode

        assert filters["mode"] == "2"  # Successfully overridden by CLI

    def test_mode_flag_prevents_cli_override_when_json_has_mode(self):
        """Test that JSON mode takes precedence over CLI via _mode_from_json=True"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(
                {"mode": "1", "filters": {"cases:priority_id": {"values": [1, 2]}}},
                f,
            )
            f.flush()
            filters, error = load_dynamic_filters_from_file(f.name)
            os.unlink(f.name)

        assert error == ""
        assert filters["mode"] == "1"
        assert filters["_mode_from_json"] is True

        # Simulate CLI override attempt (this would happen in project_based_client.py)
        mode_from_json = filters.pop("_mode_from_json", True)
        cli_mode = "2"
        if cli_mode and not mode_from_json:
            filters["mode"] = cli_mode

        assert filters["mode"] == "1"  # JSON mode preserved, CLI ignored

    def test_complex_filter_with_explicit_mode(self):
        """Test complex filter with explicit mode in JSON"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(
                {
                    "mode": "2",
                    "filters": {
                        "cases:priority_id": {"values": [1, 2]},
                        "cases:is_automated": {"value": True},
                        "cases:title": {"mode": "1", "filters": [{"op": 5, "value": "test"}]},
                    },
                },
                f,
            )
            f.flush()
            filters, error = load_dynamic_filters_from_file(f.name)
            os.unlink(f.name)

        assert error == ""
        assert filters["mode"] == "2"
        assert filters["_mode_from_json"] is True
        # Field-level mode is independent
        assert filters["filters"]["cases:title"]["mode"] == "1"

    def test_complex_filter_without_top_level_mode(self):
        """Test complex filter without top-level mode (should allow CLI override)"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(
                {
                    "filters": {
                        "cases:priority_id": {"values": [1, 2]},
                        "cases:is_automated": {"value": True},
                        "cases:title": {"mode": "2", "filters": [{"op": 5, "value": "test"}]},
                    }
                },
                f,
            )
            f.flush()
            filters, error = load_dynamic_filters_from_file(f.name)
            os.unlink(f.name)

        assert error == ""
        assert filters["mode"] == "1"  # Default
        assert filters["_mode_from_json"] is False  # Can be overridden
        # Field-level mode is independent
        assert filters["filters"]["cases:title"]["mode"] == "2"
