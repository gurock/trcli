import pytest

from trcli.data_classes.data_parsers import PriorityTagMappingParser


class TestPriorityTagMappingParser:
    """Test cases for PriorityTagMappingParser.resolve_mapping method"""

    def test_default_mapping_is_returned_for_falsy_input(self):
        """No CLI option at all (empty list/tuple, empty dict, or None) should resolve to
        exactly the built-in defaults, so the feature works out of the box."""
        for empty_value in ([], (), {}, None):
            mapping, error = PriorityTagMappingParser.resolve_mapping(empty_value)
            assert error is None
            assert mapping == PriorityTagMappingParser.DEFAULT_MAPPING
            # Returned dict must be a copy, not the class-level default itself,
            # so callers can't accidentally mutate the shared default mapping.
            assert mapping is not PriorityTagMappingParser.DEFAULT_MAPPING

    @pytest.mark.parametrize(
        "cli_values, expected_mapping",
        [
            # Single override - only the specified level changes, others keep defaults.
            (["critical:5"], {"critical": 5, "high": 3, "medium": 2, "low": 1}),
            (["low:10"], {"critical": 4, "high": 3, "medium": 2, "low": 10}),
            # Multiple overrides at once.
            (
                ["critical:5", "low:1", "high:2"],
                {"critical": 5, "high": 2, "medium": 2, "low": 1},
            ),
            # All four levels overridden.
            (
                ["critical:10", "high:9", "medium:8", "low:7"],
                {"critical": 10, "high": 9, "medium": 8, "low": 7},
            ),
            # New/unrecognized level names are added rather than rejected -
            # lets users extend the mapping to custom tag values too.
            (["blocker:6"], {"critical": 4, "high": 3, "medium": 2, "low": 1, "blocker": 6}),
        ],
    )
    def test_partial_override_merges_over_defaults(self, cli_values, expected_mapping):
        mapping, error = PriorityTagMappingParser.resolve_mapping(cli_values)
        assert error is None
        assert mapping == expected_mapping

    def test_dict_input_is_merged_over_defaults(self):
        """resolve_mapping also accepts an already-parsed dict (e.g. from a config file),
        not just the raw list of 'level:id' CLI strings."""
        mapping, error = PriorityTagMappingParser.resolve_mapping({"high": 9})
        assert error is None
        assert mapping == {"critical": 4, "high": 9, "medium": 2, "low": 1}

    def test_tuple_input_is_accepted(self):
        """Click passes `multiple=True` option values as a tuple, not a list."""
        mapping, error = PriorityTagMappingParser.resolve_mapping(("critical:5",))
        assert error is None
        assert mapping == {"critical": 5, "high": 3, "medium": 2, "low": 1}

    @pytest.mark.parametrize(
        "level_input, expected_key",
        [
            ("CRITICAL:5", "critical"),
            ("Critical:5", "critical"),
            ("  critical  :5", "critical"),
        ],
    )
    def test_level_names_are_normalized_to_lowercase(self, level_input, expected_key):
        mapping, error = PriorityTagMappingParser.resolve_mapping([level_input])
        assert error is None
        assert mapping[expected_key] == 5

    def test_priority_id_value_is_cast_to_int(self):
        mapping, error = PriorityTagMappingParser.resolve_mapping(["critical: 5 "])
        assert error is None
        assert mapping["critical"] == 5
        assert isinstance(mapping["critical"], int)

    def test_entry_without_colon_is_rejected(self):
        mapping, error = PriorityTagMappingParser.resolve_mapping(["critical5"])
        assert error is not None
        assert "expected format" in error
        # On error, the returned mapping still falls back to the defaults.
        assert mapping == PriorityTagMappingParser.DEFAULT_MAPPING

    def test_non_integer_priority_id_is_rejected(self):
        mapping, error = PriorityTagMappingParser.resolve_mapping(["critical:not_a_number"])
        assert error is not None
        assert "priority ID must be an integer" in error
        assert mapping == PriorityTagMappingParser.DEFAULT_MAPPING

    def test_empty_level_name_is_rejected(self):
        mapping, error = PriorityTagMappingParser.resolve_mapping([":5"])
        assert error is not None
        assert "level name cannot be empty" in error

    def test_non_string_entry_in_list_is_rejected(self):
        mapping, error = PriorityTagMappingParser.resolve_mapping([123])
        assert error is not None
        assert "expected format" in error

    def test_invalid_type_is_rejected(self):
        mapping, error = PriorityTagMappingParser.resolve_mapping("critical:5")  # a bare str, not list/tuple/dict
        assert error is not None
        assert "supported types are list/tuple/dict" in error
        assert mapping == PriorityTagMappingParser.DEFAULT_MAPPING

    def test_first_invalid_entry_stops_processing(self):
        """Validation should surface the first error rather than silently applying
        some overrides and rejecting others."""
        mapping, error = PriorityTagMappingParser.resolve_mapping(["critical:5", "bad_entry"])
        assert error is not None
        assert "bad_entry" in error

    def test_valid_entry_followed_by_invalid_entry_returns_clean_defaults(self):
        """Regression test: an earlier valid pair (e.g. 'critical:5') must not leak into
        the returned mapping when a later pair fails validation (e.g. non-integer priority
        ID). The caller should get back pristine defaults on error, never a partially
        applied/mutated mapping."""
        mapping, error = PriorityTagMappingParser.resolve_mapping(["critical:5", "high:not_a_number"])
        assert error is not None
        assert "priority ID must be an integer" in error
        assert mapping == PriorityTagMappingParser.DEFAULT_MAPPING
        assert mapping is not PriorityTagMappingParser.DEFAULT_MAPPING

    def test_valid_entry_followed_by_empty_level_returns_clean_defaults(self):
        """Same regression as above, but for the 'empty level name' error path."""
        mapping, error = PriorityTagMappingParser.resolve_mapping(["critical:5", ":9"])
        assert error is not None
        assert "level name cannot be empty" in error
        assert mapping == PriorityTagMappingParser.DEFAULT_MAPPING
        assert mapping is not PriorityTagMappingParser.DEFAULT_MAPPING
