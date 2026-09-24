import pytest

from trcli.api.api_utils import extract_jira_references


class TestExtractJiraReferences:
    """Whitebox unit tests for ``extract_jira_references``, covering the three
    supported tag conventions (bare ``PROJ-123``-shaped tags, explicit
    ``jira:<value>`` prefix, explicit ``refs:<value>`` prefix), their interactions
    (mixed conventions, duplicates, noise tags), and edge cases (empty/missing input)."""

    def test_no_tags_returns_empty_list(self):
        assert extract_jira_references([]) == []

    def test_none_tags_returns_empty_list(self):
        assert extract_jira_references(None) == []

    def test_only_noise_tags_returns_empty_list(self):
        assert extract_jira_references(["smoke", "priority-high", "regression"]) == []

    def test_bare_jira_key_shaped_tag(self):
        assert extract_jira_references(["JIRA-1234"]) == ["JIRA-1234"]

    def test_bare_jira_key_shaped_tag_short_prefix(self):
        assert extract_jira_references(["TR-1"]) == ["TR-1"]

    def test_bare_key_with_alphanumeric_project_prefix(self):
        assert extract_jira_references(["AB12-99"]) == ["AB12-99"]

    def test_lowercase_bare_key_is_not_matched(self):
        # Bare-key matching requires an all-caps project prefix; lowercase tags
        # like "priority-high" must not be misidentified as references.
        assert extract_jira_references(["priority-high"]) == []

    def test_mixed_case_bare_key_is_not_matched(self):
        assert extract_jira_references(["Jira-1234"]) == []

    def test_explicit_jira_prefix(self):
        assert extract_jira_references(["jira:PROJ-123"]) == ["PROJ-123"]

    def test_explicit_jira_prefix_case_insensitive(self):
        assert extract_jira_references(["JIRA:PROJ-123"]) == ["PROJ-123"]
        assert extract_jira_references(["Jira:PROJ-123"]) == ["PROJ-123"]

    def test_explicit_refs_prefix(self):
        assert extract_jira_references(["refs:TSTRAIL-5"]) == ["TSTRAIL-5"]

    def test_explicit_refs_prefix_case_insensitive(self):
        assert extract_jira_references(["REFS:TSTRAIL-5"]) == ["TSTRAIL-5"]

    def test_prefix_with_surrounding_whitespace(self):
        assert extract_jira_references(["jira: PROJ-123"]) == ["PROJ-123"]
        assert extract_jira_references([" refs:TSTRAIL-5 "]) == ["TSTRAIL-5"]

    def test_prefixed_value_need_not_be_jira_key_shaped(self):
        # The value after "jira:"/"refs:" is taken verbatim, with no shape
        # validation - unlike the bare-key convention.
        assert extract_jira_references(["refs:anything-goes-here"]) == ["anything-goes-here"]

    def test_prefix_with_empty_value_is_ignored(self):
        assert extract_jira_references(["jira:", "refs:  "]) == []

    def test_multiple_distinct_references_preserve_first_seen_order(self):
        assert extract_jira_references(["JIRA-1234", "jira:PROJ-1", "refs:TSTRAIL-5"]) == [
            "JIRA-1234",
            "PROJ-1",
            "TSTRAIL-5",
        ]

    def test_mixed_reference_and_noise_tags(self):
        assert extract_jira_references(["smoke", "JIRA-1234", "priority-high"]) == ["JIRA-1234"]

    def test_duplicates_across_conventions_are_deduplicated(self):
        assert extract_jira_references(["JIRA-1", "jira:JIRA-1", "refs:JIRA-1"]) == ["JIRA-1"]

    def test_duplicate_bare_keys_are_deduplicated(self):
        assert extract_jira_references(["JIRA-1234", "JIRA-1234"]) == ["JIRA-1234"]

    def test_empty_and_whitespace_only_tags_are_ignored(self):
        assert extract_jira_references(["", "   ", "JIRA-1234"]) == ["JIRA-1234"]

    def test_large_number_of_tags(self):
        tags = [f"JIRA-{i}" for i in range(1, 101)] + ["smoke"] * 50
        result = extract_jira_references(tags)
        assert result == [f"JIRA-{i}" for i in range(1, 101)]
