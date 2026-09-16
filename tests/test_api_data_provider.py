from tests.test_data.api_data_provider_test_data import *
from trcli.data_classes.dataclass_testrail import TestRailCase, TestRailSection, TestRailSuite
from trcli.data_classes.validation_exception import ValidationException
from trcli.data_providers.api_data_provider import ApiDataProvider
import pytest


@pytest.fixture(scope="function")
def post_data_provider():
    yield ApiDataProvider(test_input)


@pytest.fixture(scope="function")
def post_data_provider_single_result_with_id():
    yield ApiDataProvider(test_input_single_result_with_id)


@pytest.fixture(scope="function")
def post_data_provider_single_result_without_id():
    yield ApiDataProvider(test_input_single_result_without_id)


@pytest.fixture(scope="function")
def post_data_provider_duplicated_case_names():
    yield ApiDataProvider(test_input_duplicated_case_names)


class TestApiDataProvider:
    @pytest.mark.data_provider
    def test_post_suite(self, post_data_provider):
        assert post_data_provider.add_suites_data() == post_suite_bodies, "Adding suite data doesn't match expected"

    @pytest.mark.data_provider
    def test_data_provider_returns_items_without_id(self, post_data_provider):
        """Check if data providers returns data only for items with missing IDs. Numbers correspond to data in
        test_data"""
        missing_sections = 2
        missing_cases = 1
        assert (
            len(post_data_provider.add_sections_data()) == missing_sections
        ), f"Adding suite data doesn't match expected {missing_sections}"
        assert (
            len(post_data_provider.add_cases()) == missing_cases
        ), f"Adding cases data doesn't match expected {missing_cases}"

    @pytest.mark.data_provider
    def test_post_section(self, post_data_provider):
        """Check body for adding sections"""
        suite_updater = [
            {
                "suite_id": 123,
            }
        ]

        post_data_provider.update_data(suite_data=suite_updater)
        assert (
            post_data_provider.add_sections_data() == post_section_bodies
        ), "Adding sections data doesn't match expected body"

    @pytest.mark.data_provider
    def test_post_cases(self, post_data_provider):
        """Check body for adding cases"""
        section_updater = [
            {"name": "Passed test", "section_id": 12345},
        ]
        post_data_provider.update_data(section_data=section_updater)
        cases = [case.to_dict() for case in post_data_provider.add_cases()]
        assert cases == post_cases_bodies, "Adding cases data doesn't match expected body"

    @pytest.mark.data_provider
    def test_post_run(self, post_data_provider):
        """Check body for adding run"""
        suite_updater = [
            {
                "suite_id": 123,
            }
        ]
        post_data_provider.update_data(suite_data=suite_updater)
        assert post_data_provider.add_run("test run") == post_run_bodies, "Adding run data doesn't match expected body"

    @pytest.mark.data_provider
    def test_post_run_all_args(self, post_data_provider):
        """Check body for adding run"""
        suite_updater = [
            {
                "suite_id": 123,
            }
        ]
        post_data_provider.update_data(suite_data=suite_updater)
        assert (
            post_data_provider.add_run("test run", assigned_to_id=1, include_all=True, refs="SAN-1, SAN-2")
            == post_run_full_body
        ), "Adding run full data doesn't match expected body"

    @pytest.mark.data_provider
    def test_post_results_for_cases(self, post_data_provider):
        """Check body for adding results"""
        case_updater = [
            {
                "case_id": 1234567,
                "section_id": 12345,
                "title": "testCase2",
                "custom_automation_id": "className.testCase2abc",
            }
        ]
        post_data_provider.update_data(case_data=case_updater)
        assert (
            post_data_provider.add_results_for_cases(bulk_size=10) == post_results_for_cases_body
        ), "Adding results data doesn't match expected body"

    @pytest.mark.data_provider
    def test_return_all_items_flag(self, post_data_provider):
        all_sections = 3
        all_cases = 3
        assert (
            len(post_data_provider.add_sections_data(return_all_items=True)) == all_sections
        ), f"Adding cases with return_all_items flag should match {all_sections}"
        assert (
            len(post_data_provider.add_cases(return_all_items=True)) == all_cases
        ), f"Adding cases with return_all_items flag should match {all_cases}"

    @pytest.mark.data_provider
    @pytest.mark.parametrize(
        "list_to_divide, bulk_size, expected_result",
        [
            ([1, 2, 3, 4, 5, 6], 3, [[1, 2, 3], [4, 5, 6]]),
            ([1, 2, 3, 4, 5, 6], 4, [[1, 2, 3, 4], [5, 6]]),
            ([1, 2, 3, 4, 5, 6], 6, [[1, 2, 3, 4, 5, 6]]),
            ([1, 2, 3, 4, 5, 6], 7, [[1, 2, 3, 4, 5, 6]]),
            ([], 2, []),
        ],
    )
    def test_divide_list_into_bulks(self, list_to_divide, bulk_size, expected_result):
        result = ApiDataProvider.divide_list_into_bulks(list_to_divide, bulk_size)
        assert result == expected_result, f"Expected: {expected_result} but got {result} instead."


class TestApiDataProviderSectionHierarchy:
    """Tests for nested-section-hierarchy support in ApiDataProvider: topological sort,
    cycle detection, per-parent duplicate-name checking, and the section-creation helpers
    used by SectionHandler (`sections_in_creation_order`, `build_section_body`,
    `apply_created_section`)."""

    @staticmethod
    def _make_suite(sections):
        return TestRailSuite(name="Section Hierarchy Suite", testsections=sections)

    @pytest.mark.data_provider
    def test_topologically_sorted_sections_orders_parent_before_child(self):
        """Sections should always come out parent-before-child, regardless of the scrambled
        input order, and sibling relative order should be preserved."""
        root = TestRailSection("Root")
        child = TestRailSection("Child")
        child.parent_section = root
        grandchild = TestRailSection("Grandchild")
        grandchild.parent_section = child
        other_root = TestRailSection("OtherRoot")

        provider = ApiDataProvider(self._make_suite([grandchild, child, other_root, root]))
        ordered = provider.sections_in_creation_order(only_pending=False)

        assert ordered.index(root) < ordered.index(child) < ordered.index(grandchild)
        assert other_root in ordered

    @pytest.mark.data_provider
    def test_topologically_sorted_sections_raises_on_cycle(self):
        """A circular parent_section chain must raise ValidationException rather than
        silently drop sections or infinite-loop."""
        section_a = TestRailSection("A")
        section_b = TestRailSection("B")
        section_a.parent_section = section_b
        section_b.parent_section = section_a

        provider_holder = [None]

        def build():
            provider_holder[0] = ApiDataProvider(self._make_suite([section_a, section_b]))
            provider_holder[0].sections_in_creation_order(only_pending=False)

        with pytest.raises(ValidationException):
            build()

    @pytest.mark.data_provider
    def test_sections_in_creation_order_only_pending_filters_created_sections(self):
        """`only_pending=True` (the default) should exclude sections that already have a
        `section_id` (i.e. already created/matched)."""
        root = TestRailSection("Root")
        root.section_id = 111
        child = TestRailSection("Child")
        child.parent_section = root

        provider = ApiDataProvider(self._make_suite([root, child]))
        pending = provider.sections_in_creation_order()

        assert root not in pending
        assert child in pending

    @pytest.mark.data_provider
    def test_build_section_body_resolves_parent_id_from_parent_section(self):
        """`build_section_body` must resolve `parent_id` from the live parent's `section_id`
        at build time, not from any value set earlier."""
        root = TestRailSection("Root")
        root.section_id = 555
        child = TestRailSection("Child")
        child.parent_section = root

        provider = ApiDataProvider(self._make_suite([root, child]))
        body = provider.build_section_body(child)

        assert body["parent_id"] == 555
        assert body["name"] == "Child"

    @pytest.mark.data_provider
    def test_build_section_body_leaves_flat_parent_id_untouched(self):
        """Sections with no `parent_section` link (flat/legacy usage, e.g. --section-id, which
        `ApiDataProvider.__init__` applies to every section via `parent_section_id`) must keep
        that flat `parent_id`, unaffected by hierarchy logic."""
        section = TestRailSection("Flat Section")

        provider = ApiDataProvider(self._make_suite([section]), parent_section_id=999)
        body = provider.build_section_body(section)

        assert body["parent_id"] == 999

    @pytest.mark.data_provider
    def test_apply_created_section_cascades_id_to_section_and_cases(self):
        """`apply_created_section` must write the real TestRail id onto the section itself,
        onto `suite_id` when provided, and cascade the section_id onto every test case."""
        case_1 = TestRailCase(title="Case 1")
        case_2 = TestRailCase(title="Case 2")
        section = TestRailSection("Root")
        section.testcases = [case_1, case_2]

        provider = ApiDataProvider(self._make_suite([section]))
        provider.apply_created_section(section, section_id=4242, suite_id=77)

        assert section.section_id == 4242
        assert section.suite_id == 77
        assert case_1.section_id == 4242
        assert case_2.section_id == 4242

    @pytest.mark.data_provider
    def test_apply_created_section_lets_pending_child_resolve_parent_id_afterwards(self):
        """After a parent is applied via `apply_created_section`, a pending child linked via
        `parent_section` must resolve the correct, newly-applied `parent_id` on its own
        subsequent `build_section_body` call."""
        root = TestRailSection("Root")
        child = TestRailSection("Child")
        child.parent_section = root

        provider = ApiDataProvider(self._make_suite([root, child]))
        provider.apply_created_section(root, section_id=1001, suite_id=1)
        body = provider.build_section_body(child)

        assert body["parent_id"] == 1001

    @pytest.mark.data_provider
    def test_check_section_names_duplicates_flat_no_duplicates(self):
        provider = ApiDataProvider(self._make_suite([TestRailSection("A"), TestRailSection("B")]))
        assert provider.check_section_names_duplicates() is False

    @pytest.mark.data_provider
    def test_check_section_names_duplicates_flat_with_duplicates(self):
        provider = ApiDataProvider(self._make_suite([TestRailSection("A"), TestRailSection("A")]))
        assert provider.check_section_names_duplicates() is True

    @pytest.mark.data_provider
    def test_check_section_names_duplicates_same_name_different_parents_is_not_duplicate(self):
        """Two sections named the same (e.g. "Setup") nested under two DIFFERENT parents are
        a valid, non-ambiguous hierarchy and must NOT be flagged as duplicates."""
        root_a = TestRailSection("SuiteA")
        root_b = TestRailSection("SuiteB")
        setup_a = TestRailSection("Setup")
        setup_a.parent_section = root_a
        setup_b = TestRailSection("Setup")
        setup_b.parent_section = root_b

        provider = ApiDataProvider(self._make_suite([root_a, root_b, setup_a, setup_b]))
        assert provider.check_section_names_duplicates() is False

    @pytest.mark.data_provider
    def test_check_section_names_duplicates_same_name_same_parent_is_duplicate(self):
        """Two sections sharing both the same bare name AND the same parent are a genuine,
        ambiguous duplicate."""
        root = TestRailSection("Root")
        setup_1 = TestRailSection("Setup")
        setup_1.parent_section = root
        setup_2 = TestRailSection("Setup")
        setup_2.parent_section = root

        provider = ApiDataProvider(self._make_suite([root, setup_1, setup_2]))
        assert provider.check_section_names_duplicates() is True
