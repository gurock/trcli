from beartype.typing import List, Dict, Optional

from serde.json import to_dict
from datetime import datetime, timezone

from trcli.constants import OLD_SYSTEM_NAME_AUTOMATION_ID, UPDATED_SYSTEM_NAME_AUTOMATION_ID
from trcli.data_classes.dataclass_testrail import TestRailSuite, TestRailSection
from trcli.data_classes.validation_exception import ValidationException


class ApiDataProvider:
    """
    ApiDataProvider is a place where you can convert TestRailSuite dataclass to bodies for API requests
    """

    def __init__(
        self,
        suites_input: TestRailSuite,
        case_fields: dict = None,
        run_description: str = None,
        result_fields: dict = None,
        parent_section_id: int = None,
    ):
        self.suites_input = suites_input
        self.case_fields = case_fields
        self.run_description = run_description
        self.result_fields = result_fields
        self.update_data([{"suite_id": self.suites_input.suite_id}])
        self.__update_parent_section(parent_section_id)

    def add_suites_data(self) -> list:
        """Return list of bodies for adding suites"""
        return [to_dict(self.suites_input)]

    def add_sections_data(self, return_all_items=False) -> list:
        """Return list of bodies for adding sections, in parent-before-child (topological)
        order. The ID of the test suite (ignored if the project is operating in single suite
        mode, required otherwise).

        For sections linked via `parent_section` (nested hierarchies, e.g. from the Robot
        Framework parser), `parent_id` is resolved from the parent's live `section_id` at
        the moment each body is built - so this only produces a fully-correct `parent_id`
        for children whose parent already has a resolved `section_id` (either pre-existing/
        matched, or already created earlier in the same, already-topologically-sorted list).
        Sections with no `parent_section` link (flat/legacy usage) are entirely unaffected.
        """
        ordered_sections = self._topologically_sorted_sections(self.suites_input.testsections)
        return [
            self.build_section_body(section)
            for section in ordered_sections
            if section.section_id is None or return_all_items
        ]

    def sections_in_creation_order(self, only_pending: bool = True) -> List[TestRailSection]:
        """Return this suite's sections in parent-before-child (topological) order.

        :param only_pending: if True (default), only sections still missing a `section_id`
            (i.e. not yet created/matched) are returned.
        """
        ordered_sections = self._topologically_sorted_sections(self.suites_input.testsections)
        if only_pending:
            return [section for section in ordered_sections if section.section_id is None]
        return ordered_sections

    def build_section_body(self, section: TestRailSection) -> dict:
        """Build the add_section request body for a single section.

        If the section is linked to a parent via `parent_section` (nested hierarchy), its
        `parent_id` is resolved from the parent's current `section_id` right before
        serializing. Sections without a `parent_section` link keep whatever flat `parent_id`
        was already set (e.g. via --section-id), unchanged.
        """
        if section.parent_section is not None:
            section.parent_id = section.parent_section.section_id
        return to_dict(section)

    def apply_created_section(self, section: TestRailSection, section_id: int, suite_id: int = None) -> None:
        """Write a newly-created (or matched) section's real TestRail ID directly onto the
        given section object (and cascade to its test cases), so that any pending children
        already linked to it via `parent_section` can immediately resolve their own
        `parent_id` on their next `build_section_body()` call.
        """
        section.section_id = section_id
        if suite_id is not None:
            section.suite_id = suite_id
        for case in section.testcases:
            case.section_id = section_id

    @staticmethod
    def _topologically_sorted_sections(sections: List[TestRailSection]) -> List[TestRailSection]:
        """Order `sections` so that every section's `parent_section` (when it points to
        another section within this same list) always comes before it.

        Uses Kahn's algorithm (BFS-based topological sort). Sections whose `parent_section`
        is None, or points to a section outside this list (e.g. already resolved/external),
        are treated as roots with no in-list dependency. Raises ValidationException if a
        circular parent_section chain is detected (defensive: the tree built by the Robot
        Framework parser's own recursion cannot cycle, but any other producer of
        TestRailSection data - manual construction, future readers, etc. - is not guaranteed
        to be acyclic).

        Sibling order (original relative order within `sections`) is preserved.
        """
        section_ids_in_list = {id(section) for section in sections}
        in_degree: Dict[int, int] = {id(section): 0 for section in sections}
        children_by_parent: Dict[int, List[TestRailSection]] = {id(section): [] for section in sections}

        for section in sections:
            parent = section.parent_section
            if parent is not None and id(parent) in section_ids_in_list:
                in_degree[id(section)] += 1
                children_by_parent[id(parent)].append(section)

        queue = [section for section in sections if in_degree[id(section)] == 0]
        ordered: List[TestRailSection] = []
        while queue:
            current = queue.pop(0)
            ordered.append(current)
            for child in children_by_parent[id(current)]:
                in_degree[id(child)] -= 1
                if in_degree[id(child)] == 0:
                    queue.append(child)

        if len(ordered) != len(sections):
            unresolved = [section.name for section in sections if section not in ordered]
            raise ValidationException(
                field_name="parent_section",
                class_name="TestRailSection",
                reason=(
                    "Circular parent_section dependency detected among sections: "
                    f"{unresolved}. A section cannot be its own ancestor."
                ),
            )
        return ordered

    def add_cases(self, return_all_items=False) -> list:
        """Return list of bodies for adding test cases.

        Deduplicates by automation_id to prevent creating duplicate cases when
        merged files contain the same test multiple times (glob pattern support).
        Duplicates are linked so they receive the same case_id after creation.
        """
        testcases = [sections.testcases for sections in self.suites_input.testsections]
        bodies = []
        seen_automation_ids = {}

        for sublist in testcases:
            for case in sublist:
                if case.case_id is None or return_all_items:
                    case.add_global_case_fields(self.case_fields)

                    # Deduplicate by automation_id to avoid creating duplicate cases
                    if case.custom_automation_id:
                        if case.custom_automation_id in seen_automation_ids:
                            master_case = seen_automation_ids[case.custom_automation_id]
                            if not hasattr(master_case, "_duplicates"):
                                master_case._duplicates = []
                            master_case._duplicates.append(case)
                            continue
                        else:
                            seen_automation_ids[case.custom_automation_id] = case

                    bodies.append(case)
        return bodies

    def existing_cases(self):
        """Return list of bodies for existing test cases."""
        testcases = [sections.testcases for sections in self.suites_input.testsections]
        bodies = []
        for sublist in testcases:
            for case in sublist:
                if case.case_id is not None:
                    case.add_global_case_fields(self.case_fields)
                    bodies.append(case)
        return bodies

    def add_run(
        self,
        run_name: Optional[str],
        case_ids=None,
        start_date=None,
        end_date=None,
        milestone_id=None,
        assigned_to_id=None,
        include_all=None,
        refs=None,
    ):
        """Return body for adding or updating a run."""
        if case_ids is None:
            case_ids = [
                int(case) for section in self.suites_input.testsections for case in section.testcases if int(case) > 0
            ]
        properties = [
            str(prop)
            for section in self.suites_input.testsections
            for prop in section.properties
            if prop.description is not None
        ]
        if self.run_description:
            properties.insert(0, f"{self.run_description}\n")
        body = {"suite_id": self.suites_input.suite_id, "description": "\n".join(properties), "case_ids": case_ids}
        if isinstance(start_date, list) and start_date is not None:
            try:
                dt = datetime(start_date[2], start_date[0], start_date[1], tzinfo=timezone.utc)
                body["start_on"] = int(dt.timestamp())
            except ValueError:
                body["start_on"] = None
        if isinstance(end_date, list) and end_date is not None:
            try:
                dt = datetime(end_date[2], end_date[0], end_date[1], tzinfo=timezone.utc)
                body["due_on"] = int(dt.timestamp())
            except ValueError:
                body["due_on"] = None
        if include_all is not None:
            body["include_all"] = include_all
        if assigned_to_id is not None:
            body["assignedto_id"] = assigned_to_id
        if refs is not None:
            body["refs"] = refs
        if run_name is not None:
            body["name"] = run_name
        if milestone_id is not None:
            body["milestone_id"] = milestone_id
        return body

    def add_results_for_cases(self, bulk_size, user_ids=None):
        """Return bodies for adding results for cases. Returns bodies for results that already have case ID.

        Splits results into separate batches:
        1. Results WITHOUT quality_rating (for Text template cases)
        2. Results WITH quality_rating (for AI Evaluation template cases)

        This is necessary because TestRail validates each batch and rejects mixed batches.
        """
        testcases = [sections.testcases for sections in self.suites_input.testsections]

        bodies_without_quality_rating = []
        bodies_with_quality_rating = []
        user_index = 0
        assigned_count = 0
        total_failed_count = 0

        for sublist in testcases:
            for case in sublist:
                if case.case_id is not None:
                    case.result.add_global_result_fields(self.result_fields)

                    # Count failed tests
                    if case.result.status_id == 5:  # status_id 5 = Failed
                        total_failed_count += 1

                        # Assign failed tests to users in round-robin fashion if user_ids provided
                        if user_ids:
                            case.result.assignedto_id = user_ids[user_index % len(user_ids)]
                            user_index += 1
                            assigned_count += 1

                    result_dict = case.result.to_dict()

                    # Split results based on presence of quality_rating
                    # This prevents TestRail validation errors when mixing template types
                    if "quality_rating" in result_dict and result_dict["quality_rating"] is not None:
                        bodies_with_quality_rating.append(result_dict)
                    else:
                        bodies_without_quality_rating.append(result_dict)

        # Store counts for logging (we'll access this from the api_request_handler)
        self._assigned_count = assigned_count if user_ids else 0
        self._total_failed_count = total_failed_count

        # Create separate batches for results with and without quality_rating
        result_batches = []

        # Add batches for results WITHOUT quality_rating (Text template cases)
        if bodies_without_quality_rating:
            result_bulks_without = ApiDataProvider.divide_list_into_bulks(
                bodies_without_quality_rating,
                bulk_size=bulk_size,
            )
            result_batches.extend([{"results": result_bulk} for result_bulk in result_bulks_without])

        # Add batches for results WITH quality_rating (AI Evaluation template cases)
        if bodies_with_quality_rating:
            result_bulks_with = ApiDataProvider.divide_list_into_bulks(
                bodies_with_quality_rating,
                bulk_size=bulk_size,
            )
            result_batches.extend([{"results": result_bulk} for result_bulk in result_bulks_with])

        return result_batches

    def update_data(
        self,
        suite_data: List[Dict] = None,
        section_data: List[Dict] = None,
        case_data: List[Dict] = None,
    ):
        """Here you can provide responses from service after creating resources.
        This way TestRailSuite data will be updated by ID's of new created resources.
        """
        if suite_data is not None:
            self.__update_suite_data(suite_data)
        if section_data is not None:
            self.__update_section_data(section_data)
        if case_data is not None:
            self.__update_case_data(case_data)

    def __update_suite_data(self, suite_data: List[Dict]):
        """suite_data comes from add_suite API response
        example:
            {
                "suite_id": 123,
            }

        """
        self.suites_input.suite_id = suite_data[0]["suite_id"]
        for section in self.suites_input.testsections:
            section.suite_id = self.suites_input.suite_id

    def check_section_names_duplicates(self):
        """
        Check if section names are duplicated among siblings (sections sharing the same
        `parent_section`).

        This is intentionally scoped per-parent rather than global: with nested section
        hierarchies (e.g. built by the Robot Framework parser), it is common and valid for
        sections at different levels/branches of the tree to share the same bare name (e.g.
        two different suites each contributing a "Setup" sub-section). Only a name collision
        between two sections with the *same* parent (including two top-level/root sections,
        which share the implicit `None` parent) is an actual ambiguous duplicate.
        """
        names_by_parent: Dict[int, List[str]] = {}
        for section in self.suites_input.testsections:
            parent_key = id(section.parent_section) if section.parent_section is not None else None
            names_by_parent.setdefault(parent_key, []).append(section.name)

        for sibling_names in names_by_parent.values():
            if len(sibling_names) != len(set(sibling_names)):
                return True
        return False

    def __update_section_data(self, section_data: List[Dict]):
        """section_data comes from add_section API response
        example:
            {
            "name": "Passed test",
             "section_id": 12345
            }

        """
        for section_updater in section_data:
            matched_section = next(
                (section for section in self.suites_input.testsections if section["name"] == section_updater["name"]),
                None,
            )
            if matched_section is not None:
                matched_section.section_id = section_updater["section_id"]
                for case in matched_section.testcases:
                    case.section_id = section_updater["section_id"]

    def __update_parent_section(self, parent_section_id: int):
        for section in self.suites_input.testsections:
            section.parent_id = parent_section_id

    def __update_case_data(self, case_data: List[Dict]):
        """case_data comes from add_case API response
        example:
            {
                "case_id": 1,
                "section_id": 1
                "title": "testCase1",
                "custom_automation_id": "className.testCase1",
                "custom_case_automation_id": "className.testCase1"
            }

        """
        testcases = [sections.testcases for sections in self.suites_input.testsections]
        for case_updater in case_data:
            # Update ALL cases with matching automation_id (not just first match)
            # This is critical for glob pattern support where multiple files contain the same test
            automation_id = case_updater.get(OLD_SYSTEM_NAME_AUTOMATION_ID)
            updated_automation_id = case_updater.get(UPDATED_SYSTEM_NAME_AUTOMATION_ID)

            for sublist in testcases:
                for case in sublist:
                    # Check both old and new automation_id field names
                    matches = False
                    if automation_id and case.custom_automation_id == automation_id:
                        matches = True
                    elif updated_automation_id and hasattr(case, UPDATED_SYSTEM_NAME_AUTOMATION_ID):
                        if case.custom_case_automation_id == updated_automation_id:
                            matches = True

                    if matches:
                        # Update this case (may be one of many duplicates)
                        case.case_id = case_updater["case_id"]
                        case.result.case_id = case_updater["case_id"]
                        case.section_id = case_updater["section_id"]

    @staticmethod
    def divide_list_into_bulks(input_list: List, bulk_size: int) -> List:
        return [input_list[i : i + bulk_size] for i in range(0, len(input_list), bulk_size)]
