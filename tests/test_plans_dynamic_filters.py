"""
Unit tests for dynamic filters in plans add command
"""

import pytest
from unittest.mock import Mock, MagicMock

from trcli.api.plan_handler import PlanHandler
from trcli.api.api_client import APIClient
from trcli.cli import Environment


class TestPlansDynamicFilters:
    """Tests for dynamic filters in plans add command"""

    @pytest.fixture
    def plan_handler(self):
        """Create a PlanHandler instance with mocked dependencies"""
        mock_client = Mock(spec=APIClient)
        mock_env = Mock(spec=Environment)
        mock_env.log = MagicMock()
        mock_env.elog = MagicMock()
        return PlanHandler(client=mock_client, environment=mock_env)

    def test_validate_basic_plan_with_filters(self, plan_handler):
        """Test validation of basic plan with dynamic filters"""
        entries = [
            {
                "suite_id": 1,
                "name": "Smoke Tests",
                "runs": [{"dynamic_filters": {"mode": "1", "filters": {"cases:priority_id": {"values": [1, 2]}}}}],
            }
        ]

        validated, error = plan_handler.validate_and_process_plan_entries(entries)

        assert error == ""
        assert len(validated) == 1
        assert "dynamic_filters" in validated[0]["runs"][0]
        # include_all should be set to false when using dynamic_filters
        assert validated[0]["runs"][0]["include_all"] is False

    def test_validate_simplified_format_auto_wrapping(self, plan_handler):
        """Test that simplified filter format is auto-wrapped"""
        entries = [
            {"suite_id": 1, "name": "Entry 1", "runs": [{"dynamic_filters": {"cases:priority_id": {"values": [1, 2]}}}]}
        ]

        validated, error = plan_handler.validate_and_process_plan_entries(entries)

        assert error == ""
        # Check that filters were wrapped
        assert "filters" in validated[0]["runs"][0]["dynamic_filters"]
        assert validated[0]["runs"][0]["dynamic_filters"]["mode"] == "1"
        assert "cases:priority_id" in validated[0]["runs"][0]["dynamic_filters"]["filters"]

    def test_reject_filters_with_case_ids(self, plan_handler):
        """Test rejection of entries with both filters and case_ids"""
        entries = [
            {
                "suite_id": 1,
                "name": "Invalid Entry",
                "runs": [{"case_ids": [1, 2, 3], "dynamic_filters": {"cases:priority_id": {"values": [1]}}}],
            }
        ]

        validated, error = plan_handler.validate_and_process_plan_entries(entries)

        assert error != ""
        assert "Entry 'Invalid Entry', Run 1" in error
        assert "dynamic_filters and case_ids cannot be used together" in error

    def test_reject_filters_with_include_all_true(self, plan_handler):
        """Test rejection of entries with filters and include_all=true"""
        entries = [
            {
                "suite_id": 1,
                "name": "Test Entry",
                "runs": [{"include_all": True, "dynamic_filters": {"cases:priority_id": {"values": [1]}}}],
            }
        ]

        validated, error = plan_handler.validate_and_process_plan_entries(entries)

        assert error != ""
        assert "Entry 'Test Entry', Run 1" in error
        assert "dynamic_filters and include_all=true cannot be used together" in error

    def test_allow_filters_with_include_all_false(self, plan_handler):
        """Test that filters with include_all=false are allowed"""
        entries = [
            {
                "suite_id": 1,
                "name": "Valid Entry",
                "runs": [{"include_all": False, "dynamic_filters": {"cases:priority_id": {"values": [1]}}}],
            }
        ]

        validated, error = plan_handler.validate_and_process_plan_entries(entries)

        assert error == ""
        # include_all should be set to false when using dynamic_filters
        assert validated[0]["runs"][0]["include_all"] is False

    def test_multiple_entries_with_different_filters(self, plan_handler):
        """Test validation of multiple entries with different filters"""
        entries = [
            {"suite_id": 1, "name": "Smoke Tests", "runs": [{"dynamic_filters": {"cases:label_id": {"values": [4]}}}]},
            {
                "suite_id": 1,
                "name": "Regression Tests",
                "runs": [{"dynamic_filters": {"cases:priority_id": {"values": [1, 2]}}}],
            },
        ]

        validated, error = plan_handler.validate_and_process_plan_entries(entries)

        assert error == ""
        assert len(validated) == 2
        assert "label_id" in str(validated[0]["runs"][0]["dynamic_filters"])
        assert "priority_id" in str(validated[1]["runs"][0]["dynamic_filters"])

    def test_multiple_runs_per_entry_with_different_filters(self, plan_handler):
        """Test multiple runs per entry with different filter configurations"""
        entries = [
            {
                "suite_id": 1,
                "name": "Multi-Run Entry",
                "runs": [
                    {"dynamic_filters": {"cases:priority_id": {"values": [1]}}},
                    {"case_ids": [10, 20, 30]},
                    {"include_all": True},
                ],
            }
        ]

        validated, error = plan_handler.validate_and_process_plan_entries(entries)

        assert error == ""
        assert len(validated[0]["runs"]) == 3
        # First run has dynamic filters
        assert "dynamic_filters" in validated[0]["runs"][0]
        # Second run has case_ids
        assert validated[0]["runs"][1]["case_ids"] == [10, 20, 30]
        # Third run has include_all
        assert validated[0]["runs"][2]["include_all"] is True

    def test_reject_empty_filters_object(self, plan_handler):
        """Test rejection of empty filters object"""
        entries = [
            {"suite_id": 1, "name": "Invalid Entry", "runs": [{"dynamic_filters": {"mode": "1", "filters": {}}}]}
        ]

        validated, error = plan_handler.validate_and_process_plan_entries(entries)

        assert error != ""
        assert "Entry 'Invalid Entry', Run 1" in error
        assert "'filters' object cannot be empty" in error

    def test_reject_invalid_filter_structure(self, plan_handler):
        """Test rejection of invalid filter structure"""
        entries = [
            {
                "suite_id": 1,
                "name": "Bad Entry",
                "runs": [
                    {
                        "dynamic_filters": {
                            "mode": "1",
                            "filters": {"priority_id": {"values": [1, 2]}},  # Missing "cases:" prefix
                        }
                    }
                ],
            }
        ]

        validated, error = plan_handler.validate_and_process_plan_entries(entries)

        assert error != ""
        assert "Entry 'Bad Entry', Run 1" in error
        assert "must start with 'cases:' prefix" in error

    def test_error_context_includes_entry_and_run_info(self, plan_handler):
        """Test that error messages include entry name and run index"""
        entries = [
            {
                "suite_id": 1,
                "name": "Test Suite A",
                "runs": [
                    {"include_all": True},  # Run 1 - valid
                    {"case_ids": [1, 2], "dynamic_filters": {"cases:priority_id": {"values": [1]}}},  # Run 2 - invalid
                ],
            }
        ]

        validated, error = plan_handler.validate_and_process_plan_entries(entries)

        assert error != ""
        assert "Entry 'Test Suite A', Run 2" in error

    def test_entry_without_name_uses_index(self, plan_handler):
        """Test that entries without names use index in error messages"""
        entries = [
            {
                "suite_id": 1,
                # No "name" field
                "runs": [{"case_ids": [1, 2], "dynamic_filters": {"cases:priority_id": {"values": [1]}}}],
            }
        ]

        validated, error = plan_handler.validate_and_process_plan_entries(entries)

        assert error != ""
        assert "Entry 'Entry 1', Run 1" in error  # Note: quotes around generated name

    def test_config_ids_with_filters_allowed(self, plan_handler):
        """Test that config_ids can be used with dynamic filters"""
        entries = [
            {
                "suite_id": 1,
                "name": "Multi-Config Entry",
                "runs": [{"config_ids": [1, 2], "dynamic_filters": {"cases:priority_id": {"values": [1, 2]}}}],
            }
        ]

        validated, error = plan_handler.validate_and_process_plan_entries(entries)

        assert error == ""
        assert validated[0]["runs"][0]["config_ids"] == [1, 2]
        assert "dynamic_filters" in validated[0]["runs"][0]

    def test_empty_entries_list_returns_empty(self, plan_handler):
        """Test that empty entries list is handled gracefully"""
        entries = []

        validated, error = plan_handler.validate_and_process_plan_entries(entries)

        assert error == ""
        assert validated == []

    def test_none_entries_returns_none(self, plan_handler):
        """Test that None entries is handled gracefully"""
        validated, error = plan_handler.validate_and_process_plan_entries(None)

        assert error == ""
        assert validated is None

    def test_entry_with_no_runs_passes_through(self, plan_handler):
        """Test that entries without runs are passed through unchanged"""
        entries = [
            {
                "suite_id": 1,
                "name": "Empty Entry",
                # No "runs" field
            }
        ]

        validated, error = plan_handler.validate_and_process_plan_entries(entries)

        assert error == ""
        assert len(validated) == 1
        assert validated[0]["name"] == "Empty Entry"

    def test_complex_nested_mode_filters(self, plan_handler):
        """Test complex filters with nested modes"""
        entries = [
            {
                "suite_id": 1,
                "name": "Complex Entry",
                "runs": [
                    {
                        "dynamic_filters": {
                            "mode": "1",
                            "filters": {
                                "cases:priority_id": {"values": [1, 2]},
                                "cases:title": {
                                    "mode": "2",
                                    "filters": [{"op": 5, "value": "login"}, {"op": 5, "value": "auth"}],
                                },
                            },
                        }
                    }
                ],
            }
        ]

        validated, error = plan_handler.validate_and_process_plan_entries(entries)

        assert error == ""
        filters = validated[0]["runs"][0]["dynamic_filters"]
        assert filters["mode"] == "1"
        assert "cases:title" in filters["filters"]
        assert filters["filters"]["cases:title"]["mode"] == "2"

    def test_mode_from_json_flag_removed(self, plan_handler):
        """Test that _mode_from_json internal flag is removed"""
        entries = [
            {
                "suite_id": 1,
                "name": "Test Entry",
                "runs": [
                    {
                        "dynamic_filters": {
                            "mode": "1",
                            "filters": {"cases:priority_id": {"values": [1]}},
                            "_mode_from_json": True,  # Internal flag should be removed
                        }
                    }
                ],
            }
        ]

        validated, error = plan_handler.validate_and_process_plan_entries(entries)

        assert error == ""
        assert "_mode_from_json" not in validated[0]["runs"][0]["dynamic_filters"]

    def test_cli_mode_override_simplified_format(self, plan_handler):
        """Test that CLI mode overrides default mode when using simplified format"""
        # Without CLI mode - should default to "1"
        entries1 = [
            {
                "suite_id": 1,
                "name": "Test Entry",
                "runs": [
                    {
                        "dynamic_filters": {
                            # Simplified format - no explicit mode
                            "cases:priority_id": {"values": [1, 2]}
                        }
                    }
                ],
            }
        ]
        validated, error = plan_handler.validate_and_process_plan_entries(entries1)
        assert error == ""
        assert validated[0]["runs"][0]["dynamic_filters"]["mode"] == "1"

        # With CLI mode "2" - should use CLI mode (use fresh entries)
        entries2 = [
            {
                "suite_id": 1,
                "name": "Test Entry",
                "runs": [
                    {
                        "dynamic_filters": {
                            # Simplified format - no explicit mode
                            "cases:priority_id": {"values": [1, 2]}
                        }
                    }
                ],
            }
        ]
        validated, error = plan_handler.validate_and_process_plan_entries(entries2, cli_mode="2")
        assert error == ""
        assert validated[0]["runs"][0]["dynamic_filters"]["mode"] == "2"

    def test_cli_mode_does_not_override_explicit_json_mode(self, plan_handler):
        """Test that CLI mode does NOT override explicit mode in JSON"""
        entries = [
            {
                "suite_id": 1,
                "name": "Test Entry",
                "runs": [
                    {
                        "dynamic_filters": {
                            "mode": "2",  # Explicit mode in JSON
                            "filters": {"cases:priority_id": {"values": [1, 2]}},
                        }
                    }
                ],
            }
        ]

        # CLI mode "1" should NOT override JSON mode "2"
        validated, error = plan_handler.validate_and_process_plan_entries(entries, cli_mode="1")
        assert error == ""
        assert validated[0]["runs"][0]["dynamic_filters"]["mode"] == "2"  # JSON mode preserved

    def test_cli_mode_applies_to_all_runs(self, plan_handler):
        """Test that CLI mode applies to all runs in the plan"""
        entries = [
            {"suite_id": 1, "name": "Entry 1", "runs": [{"dynamic_filters": {"cases:priority_id": {"values": [1]}}}]},
            {"suite_id": 2, "name": "Entry 2", "runs": [{"dynamic_filters": {"cases:label_id": {"values": [5]}}}]},
        ]

        # CLI mode "2" should apply to all runs
        validated, error = plan_handler.validate_and_process_plan_entries(entries, cli_mode="2")
        assert error == ""
        assert validated[0]["runs"][0]["dynamic_filters"]["mode"] == "2"
        assert validated[1]["runs"][0]["dynamic_filters"]["mode"] == "2"

    def test_cli_mode_respects_mixed_explicit_and_simplified(self, plan_handler):
        """Test CLI mode with mix of explicit and simplified formats"""
        entries = [
            {
                "suite_id": 1,
                "name": "Entry 1",
                "runs": [
                    {
                        "dynamic_filters": {
                            "mode": "1",  # Explicit mode
                            "filters": {"cases:priority_id": {"values": [1]}},
                        }
                    }
                ],
            },
            {
                "suite_id": 2,
                "name": "Entry 2",
                "runs": [
                    {
                        "dynamic_filters": {
                            # Simplified format - no explicit mode
                            "cases:label_id": {"values": [5]}
                        }
                    }
                ],
            },
        ]

        # CLI mode "2" should only apply to Entry 2 (simplified format)
        validated, error = plan_handler.validate_and_process_plan_entries(entries, cli_mode="2")
        assert error == ""
        assert validated[0]["runs"][0]["dynamic_filters"]["mode"] == "1"  # Explicit mode preserved
        assert validated[1]["runs"][0]["dynamic_filters"]["mode"] == "2"  # CLI mode applied

    def test_cli_mode_with_multiple_runs_per_entry(self, plan_handler):
        """Test CLI mode with multiple runs per entry"""
        entries = [
            {
                "suite_id": 1,
                "name": "Test Entry",
                "runs": [
                    {"dynamic_filters": {"cases:priority_id": {"values": [1]}}},
                    {"dynamic_filters": {"cases:priority_id": {"values": [2]}}},
                ],
            }
        ]

        # CLI mode should apply to all runs
        validated, error = plan_handler.validate_and_process_plan_entries(entries, cli_mode="2")
        assert error == ""
        assert validated[0]["runs"][0]["dynamic_filters"]["mode"] == "2"
        assert validated[0]["runs"][1]["dynamic_filters"]["mode"] == "2"
