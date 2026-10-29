from unittest.mock import MagicMock

import pytest

from trcli.api.api_client import APIClientResult
from trcli.api.section_handler import SectionHandler
from trcli.cli import Environment
from trcli.data_classes.dataclass_testrail import TestRailCase, TestRailSection, TestRailSuite
from trcli.data_providers.api_data_provider import ApiDataProvider


def _make_suite(sections):
    return TestRailSuite(name="Section Hierarchy Suite", testsections=sections)


def _make_handler(sections, get_all_sections_return=None):
    """Build a SectionHandler wired to a real ApiDataProvider (so the hierarchy-resolution
    logic under test runs for real) and a MagicMock client/environment/callback."""
    provider = ApiDataProvider(_make_suite(sections))
    client = MagicMock()
    environment = Environment()
    environment.section_id = None
    get_all_sections_callback = MagicMock(
        return_value=get_all_sections_return if get_all_sections_return is not None else ([], "")
    )
    handler = SectionHandler(client, environment, provider, get_all_sections_callback)
    return handler, client, provider


class TestSectionHandlerHierarchy:
    """Tests for hierarchy-aware section matching/creation in SectionHandler:
    `check_missing_section_ids` (matching against sections already on TestRail) and
    `add_sections` (one-at-a-time, parent-before-child creation)."""

    @pytest.mark.section_handler
    def test_add_sections_creates_parent_before_child_and_resolves_parent_id(self):
        """A 3-level nested hierarchy (Root -> Child -> Grandchild) must be created in
        parent-before-child order, with each child's request body carrying the real,
        freshly-created `parent_id` of its parent."""
        root = TestRailSection("Root")
        child = TestRailSection("Child")
        child.parent_section = root
        grandchild = TestRailSection("Grandchild")
        grandchild.parent_section = child

        # Deliberately scrambled input order.
        handler, client, provider = _make_handler([grandchild, child, root])

        created_ids = iter([101, 102, 103])
        sent_bodies = []

        def fake_send_post(url, body):
            sent_bodies.append(dict(body))
            new_id = next(created_ids)
            return APIClientResult(
                200,
                {"id": new_id, "suite_id": 1, "name": body["name"], "parent_id": body.get("parent_id")},
                "",
            )

        client.send_post.side_effect = fake_send_post
        verify_callback = MagicMock(return_value=True)

        resources, error_message = handler.add_sections(project_id=1, verify_callback=verify_callback)

        assert error_message == ""
        assert [body["name"] for body in sent_bodies] == ["Root", "Child", "Grandchild"]
        assert sent_bodies[0].get("parent_id") is None
        assert sent_bodies[1]["parent_id"] == 101
        assert sent_bodies[2]["parent_id"] == 102
        assert [resource["section_id"] for resource in resources] == [101, 102, 103]
        assert root.section_id == 101
        assert child.section_id == 102
        assert grandchild.section_id == 103

    @pytest.mark.section_handler
    def test_add_sections_distinguishes_same_name_under_different_parents(self):
        """Two sections both named "Setup" but nested under two DIFFERENT parent suites must
        be created as two distinct sections with distinct ids/parents - the old flat
        name-based matching logic would have confused these."""
        root_a = TestRailSection("SuiteA")
        root_b = TestRailSection("SuiteB")
        setup_a = TestRailSection("Setup")
        setup_a.parent_section = root_a
        setup_b = TestRailSection("Setup")
        setup_b.parent_section = root_b

        handler, client, provider = _make_handler([root_a, setup_a, root_b, setup_b])

        created_ids = iter([201, 202, 203, 204])

        def fake_send_post(url, body):
            new_id = next(created_ids)
            return APIClientResult(
                200,
                {"id": new_id, "suite_id": 1, "name": body["name"], "parent_id": body.get("parent_id")},
                "",
            )

        client.send_post.side_effect = fake_send_post
        verify_callback = MagicMock(return_value=True)

        resources, error_message = handler.add_sections(project_id=1, verify_callback=verify_callback)

        assert error_message == ""
        assert setup_a.section_id != setup_b.section_id
        assert setup_a.parent_id == root_a.section_id
        assert setup_b.parent_id == root_b.section_id

    @pytest.mark.section_handler
    def test_add_sections_stops_and_reports_error_on_send_post_failure(self):
        """If a POST fails partway through, no more sections should be created afterward and
        the error message should be surfaced; sections created before the failure keep their
        resolved ids."""
        root = TestRailSection("Root")
        child = TestRailSection("Child")
        child.parent_section = root

        handler, client, provider = _make_handler([root, child])

        def fake_send_post(url, body):
            if body["name"] == "Root":
                return APIClientResult(200, {"id": 301, "suite_id": 1, "name": "Root"}, "")
            return APIClientResult(-1, "", "connection error")

        client.send_post.side_effect = fake_send_post
        verify_callback = MagicMock(return_value=True)

        resources, error_message = handler.add_sections(project_id=1, verify_callback=verify_callback)

        assert error_message == "connection error"
        assert len(resources) == 1
        assert root.section_id == 301
        assert child.section_id is None

    @pytest.mark.section_handler
    def test_add_sections_stops_on_verify_failure_without_double_appending(self):
        """If `verify_callback` rejects a response, `add_sections` must stop immediately and
        report the data-verification error - and, critically, must not append that response
        twice (a pre-existing bug in the old implementation)."""
        from trcli.constants import FAULT_MAPPING

        root = TestRailSection("Root")
        handler, client, provider = _make_handler([root])

        client.send_post.return_value = APIClientResult(200, {"id": 401, "suite_id": 1, "name": "Root"}, "")
        verify_callback = MagicMock(return_value=False)

        resources, error_message = handler.add_sections(project_id=1, verify_callback=verify_callback)

        assert error_message == FAULT_MAPPING["data_verification_error"]
        assert resources == []

    @pytest.mark.section_handler
    def test_check_missing_section_ids_matches_by_parent_and_name(self):
        """Local sections should be matched against sections already on TestRail using both
        `parent_id` and `name`, applying the match immediately so pending children can resolve
        their own parent."""
        root = TestRailSection("Root")
        child = TestRailSection("Child")
        child.parent_section = root

        remote_sections = [
            {"id": 501, "suite_id": 1, "name": "Root", "parent_id": None},
            {"id": 502, "suite_id": 1, "name": "Child", "parent_id": 501},
        ]
        handler, client, provider = _make_handler([root, child], get_all_sections_return=(remote_sections, ""))

        missing, error_message = handler.check_missing_section_ids(
            project_id=1, suite_id=1, suites_data=provider.suites_input
        )

        assert error_message == ""
        assert missing is False
        assert root.section_id == 501
        assert child.section_id == 502
        assert child.suite_id == 1

    @pytest.mark.section_handler
    def test_check_missing_section_ids_distinguishes_same_name_under_different_parents(self):
        """Two remote sections both named "Setup" but under different remote `parent_id`s must
        resolve to their correct, distinct local counterparts - not both match the first one
        found (the old bare-name-only matching bug)."""
        root_a = TestRailSection("SuiteA")
        root_b = TestRailSection("SuiteB")
        setup_a = TestRailSection("Setup")
        setup_a.parent_section = root_a
        setup_b = TestRailSection("Setup")
        setup_b.parent_section = root_b

        remote_sections = [
            {"id": 601, "suite_id": 1, "name": "SuiteA", "parent_id": None},
            {"id": 602, "suite_id": 1, "name": "SuiteB", "parent_id": None},
            {"id": 603, "suite_id": 1, "name": "Setup", "parent_id": 601},
            {"id": 604, "suite_id": 1, "name": "Setup", "parent_id": 602},
        ]
        handler, client, provider = _make_handler(
            [root_a, setup_a, root_b, setup_b], get_all_sections_return=(remote_sections, "")
        )

        missing, error_message = handler.check_missing_section_ids(
            project_id=1, suite_id=1, suites_data=provider.suites_input
        )

        assert error_message == ""
        assert missing is False
        assert setup_a.section_id == 603
        assert setup_b.section_id == 604

    @pytest.mark.section_handler
    def test_check_missing_section_ids_reports_missing_when_child_not_found_remotely(self):
        """If the parent exists remotely but the child doesn't, `missing_test_sections` must be
        True even though the parent matched fine."""
        root = TestRailSection("Root")
        child = TestRailSection("Child")
        child.parent_section = root

        remote_sections = [
            {"id": 701, "suite_id": 1, "name": "Root", "parent_id": None},
        ]
        handler, client, provider = _make_handler([root, child], get_all_sections_return=(remote_sections, ""))

        missing, error_message = handler.check_missing_section_ids(
            project_id=1, suite_id=1, suites_data=provider.suites_input
        )

        assert error_message == ""
        assert missing is True
        assert root.section_id == 701
        assert child.section_id is None

    @pytest.mark.section_handler
    def test_check_missing_section_ids_propagates_get_all_sections_error(self):
        root = TestRailSection("Root")
        handler, client, provider = _make_handler([root], get_all_sections_return=([], "boom"))

        missing, error_message = handler.check_missing_section_ids(
            project_id=1, suite_id=1, suites_data=provider.suites_input
        )

        assert missing is False
        assert error_message == "boom"

    @pytest.mark.section_handler
    def test_delete_sections_posts_delete_for_each_section(self):
        root = TestRailSection("Root")
        handler, client, provider = _make_handler([root])
        client.send_post.return_value = APIClientResult(200, {"id": 801}, "")

        responses, error_message = handler.delete_sections([{"section_id": 801, "suite_id": 1, "name": "Root"}])

        assert error_message == ""
        assert responses == [{"id": 801}]
        client.send_post.assert_called_once_with("delete_section/801", payload={})
