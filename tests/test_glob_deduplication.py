"""
Unit tests for glob pattern deduplication logic.

Tests verify that when glob patterns merge multiple files containing the same test
(same automation_id), the deduplication logic works correctly:
1. Only one test case is created (not duplicates)
2. All results are uploaded for that test case
"""

import pytest
from pathlib import Path
from trcli.data_classes.dataclass_testrail import (
    TestRailSuite,
    TestRailSection,
    TestRailCase,
    TestRailResult,
)
from trcli.data_providers.api_data_provider import ApiDataProvider


class TestGlobDeduplication:
    """Tests for deduplication logic when glob patterns merge files with duplicate tests"""

    @pytest.mark.data_provider
    def test_add_cases_deduplicates_by_automation_id(self):
        """Test that add_cases() deduplicates test cases by automation_id.

        Scenario 1: Multiple XML files contain the same test (same automation_id).
        Expected: Only ONE test case should be added, duplicates should be linked.
        """
        # Create test data with duplicate automation_ids
        section = TestRailSection(
            name="Test Section",
            section_id=1,
            testcases=[
                TestRailCase(
                    title="Test Login",
                    case_id=None,  # Not yet created
                    custom_automation_id="com.example.LoginTest.testLogin",
                    result=TestRailResult(case_id=None, status_id=1),  # Passed
                ),
                TestRailCase(
                    title="Test Login",
                    case_id=None,  # Not yet created (duplicate)
                    custom_automation_id="com.example.LoginTest.testLogin",  # Same automation_id!
                    result=TestRailResult(case_id=None, status_id=5),  # Failed
                ),
                TestRailCase(
                    title="Test Logout",
                    case_id=None,
                    custom_automation_id="com.example.LoginTest.testLogout",  # Different test
                    result=TestRailResult(case_id=None, status_id=1),
                ),
            ],
        )

        suite = TestRailSuite(name="Test Suite", suite_id=1, testsections=[section])
        data_provider = ApiDataProvider(suite)

        # Call add_cases() which should deduplicate
        cases_to_add = data_provider.add_cases()

        # Verify: Only 2 cases should be in the list (not 3)
        # One for testLogin (not the duplicate) and one for testLogout
        assert len(cases_to_add) == 2, f"Expected 2 cases, got {len(cases_to_add)}"

        # Verify the automation_ids are unique
        automation_ids = [case.custom_automation_id for case in cases_to_add]
        assert len(automation_ids) == len(set(automation_ids)), "Automation IDs should be unique"
        assert "com.example.LoginTest.testLogin" in automation_ids
        assert "com.example.LoginTest.testLogout" in automation_ids

        # Verify the first testLogin case has _duplicates attribute
        test_login_case = next(
            case for case in cases_to_add if case.custom_automation_id == "com.example.LoginTest.testLogin"
        )
        assert hasattr(test_login_case, "_duplicates"), "Master case should have _duplicates attribute"
        assert len(test_login_case._duplicates) == 1, "Should have 1 duplicate linked"

    @pytest.mark.data_provider
    def test_add_cases_preserves_all_results_via_deduplication(self):
        """Test that duplicate results are preserved through linking.

        Scenario 2: After deduplication, verify that ALL test cases still exist
        in the original suite (they're just not in add_cases() list).
        This ensures add_results_for_cases() can still find them.
        """
        # Create test data with duplicate automation_ids but different results
        section = TestRailSection(
            name="Test Section",
            section_id=1,
            testcases=[
                TestRailCase(
                    title="Test Payment",
                    case_id=None,
                    custom_automation_id="com.example.PaymentTest.testPayment",
                    result=TestRailResult(case_id=None, status_id=1, comment="Passed in file1.xml"),
                ),
                TestRailCase(
                    title="Test Payment",
                    case_id=None,
                    custom_automation_id="com.example.PaymentTest.testPayment",
                    result=TestRailResult(case_id=None, status_id=5, comment="Failed in file2.xml"),
                ),
                TestRailCase(
                    title="Test Payment",
                    case_id=None,
                    custom_automation_id="com.example.PaymentTest.testPayment",
                    result=TestRailResult(case_id=None, status_id=4, comment="Skipped in file3.xml"),
                ),
            ],
        )

        suite = TestRailSuite(name="Test Suite", suite_id=1, testsections=[section])
        data_provider = ApiDataProvider(suite)

        # Verify suite still contains all 3 test cases (not modified by add_cases)
        assert len(suite.testsections[0].testcases) == 3, "Original suite should still have all 3 testcases"

        # Call add_cases() - should return only 1 case
        cases_to_add = data_provider.add_cases()
        assert len(cases_to_add) == 1, "Should only add 1 case (master)"

        # Verify the master case has 2 duplicates linked
        master_case = cases_to_add[0]
        assert hasattr(master_case, "_duplicates"), "Master should have _duplicates"
        assert len(master_case._duplicates) == 2, "Should have 2 duplicates linked"

        # Verify the duplicates are the other 2 cases with different results
        duplicate_comments = [dup.result.comment for dup in master_case._duplicates]
        assert "Failed in file2.xml" in duplicate_comments
        assert "Skipped in file3.xml" in duplicate_comments

    @pytest.mark.data_provider
    def test_add_cases_no_deduplication_without_automation_id(self):
        """Test that cases without automation_id are not deduplicated."""
        section = TestRailSection(
            name="Test Section",
            section_id=1,
            testcases=[
                TestRailCase(
                    title="Test A",
                    case_id=None,
                    custom_automation_id=None,  # No automation_id
                    result=TestRailResult(case_id=None, status_id=1),
                ),
                TestRailCase(
                    title="Test A",
                    case_id=None,
                    custom_automation_id=None,  # No automation_id (duplicate title)
                    result=TestRailResult(case_id=None, status_id=5),
                ),
            ],
        )

        suite = TestRailSuite(name="Test Suite", suite_id=1, testsections=[section])
        data_provider = ApiDataProvider(suite)

        cases_to_add = data_provider.add_cases()

        # Without automation_id, both cases should be added (no deduplication)
        assert len(cases_to_add) == 2, "Cases without automation_id should not be deduplicated"

    @pytest.mark.data_provider
    def test_add_results_includes_all_cases_with_case_id(self):
        """Test that add_results_for_cases() includes all cases with case_id set.

        This verifies Scenario 2 fix: After case_id propagation to duplicates,
        all results should be uploaded (not just the master).
        """
        # Simulate after case creation: master and duplicates all have case_id set
        section = TestRailSection(
            name="Test Section",
            section_id=1,
            testcases=[
                TestRailCase(
                    title="Test Login",
                    case_id=101,  # Case created
                    custom_automation_id="com.example.LoginTest.testLogin",
                    result=TestRailResult(case_id=101, status_id=1, comment="Run 1: Passed"),
                ),
                TestRailCase(
                    title="Test Login",
                    case_id=101,  # Duplicate has same case_id (propagated)
                    custom_automation_id="com.example.LoginTest.testLogin",
                    result=TestRailResult(case_id=101, status_id=5, comment="Run 2: Failed"),
                ),
                TestRailCase(
                    title="Test Login",
                    case_id=101,  # Another duplicate
                    custom_automation_id="com.example.LoginTest.testLogin",
                    result=TestRailResult(case_id=101, status_id=1, comment="Run 3: Passed"),
                ),
            ],
        )

        suite = TestRailSuite(name="Test Suite", suite_id=1, testsections=[section])
        data_provider = ApiDataProvider(suite)

        # Call add_results_for_cases() - should return ALL 3 results (not deduplicated)
        result_chunks = data_provider.add_results_for_cases(bulk_size=10)
        all_results = []
        for chunk in result_chunks:
            all_results.extend(chunk["results"])

        # Verify: All 3 results should be included
        assert len(all_results) == 3, f"Expected 3 results, got {len(all_results)}"

        # Verify all have the same case_id
        case_ids = [result["case_id"] for result in all_results]
        assert all(cid == 101 for cid in case_ids), "All results should have case_id=101"

        # Verify all 3 comments are present
        comments = [result["comment"] for result in all_results]
        assert "Run 1: Passed" in comments
        assert "Run 2: Failed" in comments
        assert "Run 3: Passed" in comments

    @pytest.mark.data_provider
    def test_add_cases_multiple_duplicates_same_automation_id(self):
        """Test deduplication with many duplicates of the same test."""
        # Create 5 test cases with the same automation_id
        testcases = [
            TestRailCase(
                title=f"Test API Call #{i}",
                case_id=None,
                custom_automation_id="com.example.APITest.testGetUser",  # Same for all
                result=TestRailResult(case_id=None, status_id=1),
            )
            for i in range(5)
        ]

        section = TestRailSection(name="Test Section", section_id=1, testcases=testcases)
        suite = TestRailSuite(name="Test Suite", suite_id=1, testsections=[section])
        data_provider = ApiDataProvider(suite)

        cases_to_add = data_provider.add_cases()

        # Should only add 1 case
        assert len(cases_to_add) == 1, f"Expected 1 case, got {len(cases_to_add)}"

        # Should have 4 duplicates linked
        master_case = cases_to_add[0]
        assert hasattr(master_case, "_duplicates")
        assert len(master_case._duplicates) == 4, "Should have 4 duplicates"

    @pytest.mark.data_provider
    def test_add_cases_mixed_duplicates_and_unique(self):
        """Test deduplication with mix of duplicate and unique tests."""
        section = TestRailSection(
            name="Test Section",
            section_id=1,
            testcases=[
                # Duplicate group 1: testLogin appears 2 times
                TestRailCase(
                    title="Test Login",
                    case_id=None,
                    custom_automation_id="LoginTest.testLogin",
                    result=TestRailResult(case_id=None, status_id=1),
                ),
                TestRailCase(
                    title="Test Login",
                    case_id=None,
                    custom_automation_id="LoginTest.testLogin",
                    result=TestRailResult(case_id=None, status_id=5),
                ),
                # Unique test
                TestRailCase(
                    title="Test Register",
                    case_id=None,
                    custom_automation_id="LoginTest.testRegister",
                    result=TestRailResult(case_id=None, status_id=1),
                ),
                # Duplicate group 2: testLogout appears 3 times
                TestRailCase(
                    title="Test Logout",
                    case_id=None,
                    custom_automation_id="LoginTest.testLogout",
                    result=TestRailResult(case_id=None, status_id=1),
                ),
                TestRailCase(
                    title="Test Logout",
                    case_id=None,
                    custom_automation_id="LoginTest.testLogout",
                    result=TestRailResult(case_id=None, status_id=4),
                ),
                TestRailCase(
                    title="Test Logout",
                    case_id=None,
                    custom_automation_id="LoginTest.testLogout",
                    result=TestRailResult(case_id=None, status_id=1),
                ),
            ],
        )

        suite = TestRailSuite(name="Test Suite", suite_id=1, testsections=[section])
        data_provider = ApiDataProvider(suite)

        cases_to_add = data_provider.add_cases()

        # Should add 3 unique cases: testLogin, testRegister, testLogout
        assert len(cases_to_add) == 3, f"Expected 3 cases, got {len(cases_to_add)}"

        automation_ids = [case.custom_automation_id for case in cases_to_add]
        assert "LoginTest.testLogin" in automation_ids
        assert "LoginTest.testRegister" in automation_ids
        assert "LoginTest.testLogout" in automation_ids

        # Verify duplicate counts
        login_case = next(c for c in cases_to_add if c.custom_automation_id == "LoginTest.testLogin")
        logout_case = next(c for c in cases_to_add if c.custom_automation_id == "LoginTest.testLogout")
        register_case = next(c for c in cases_to_add if c.custom_automation_id == "LoginTest.testRegister")

        assert len(login_case._duplicates) == 1, "testLogin should have 1 duplicate"
        assert len(logout_case._duplicates) == 2, "testLogout should have 2 duplicates"
        assert not hasattr(register_case, "_duplicates"), "testRegister should have no duplicates"
