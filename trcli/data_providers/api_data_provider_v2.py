from typing import List, Dict, Optional

from trcli.cli import Environment
from trcli.data_classes.dataclass_testrail import TestRailSuite, TestRun, TestRailCase, TestRailSection


class DataProviderException(Exception):
    """Custom exception type for data-provider-level errors like None field/not initiated data failures."""
    def __init__(self, message=""):
        self.message = message
        super().__init__(self.message)


class ApiDataProvider:
    """
    ApiDataProvider is responsible for preparing and storing data
    """
    def __init__(self, suites_input: TestRailSuite, environment: Environment):
        self.suites_input = suites_input
        self._environment = environment

        self.case_fields = self._environment.case_fields
        self.run_description = self._environment.run_description
        self.result_fields = self._environment.result_fields
        self._update_parent_section()
        self._add_global_case_fields()

        self._project_id: Optional[int] = None
        self._test_run: Optional[TestRun] = None
        self.test_run_id: Optional[int] = None
        self.test_plan_id: Optional[int] = None
        self.config_ids: Optional[List[int]] = None
        self._automation_id_system_name: Optional[str] = None

        self.existing_cases: List[TestRailCase] = []
        self.missing_cases: List[TestRailCase] = []

        self.created_suite_id: Optional[int] = None
        self.created_sections_ids: Optional[List[int]] = None
        self.updated_cases_ids: List[int] = []
        self.created_cases_ids: List[int] = []
        self.created_test_run_id: Optional[int] = None


    @property
    def project_id(self) -> int:
        """Return project ID."""
        if self._project_id is None:
            raise DataProviderException("Project ID is not initialized. Resolve project and update project id first.")
        return self._project_id

    @project_id.setter
    def project_id(self, project_id: int) -> None:
        """Set project ID."""
        self._project_id = project_id

    @property
    def suite_id(self) -> int:
        """Return suite ID."""
        if self.suites_input.suite_id is None:
            raise DataProviderException("Suite ID is not initialized. Resolve suite and update suite id first.")
        return self.suites_input.suite_id

    @property
    def test_run(self) -> TestRun:
        """Return test run object."""
        if self._test_run is None:
            raise DataProviderException("Test run is not initialized. Call add_run() first.")
        return self._test_run

    @property
    def automation_id_system_name(self) -> Optional[str]:
        """Return automation ID system name."""
        if self._automation_id_system_name is None:
            raise DataProviderException("Automation ID system name is not initialized")
        return self._automation_id_system_name

    def collect_all_testcases(self) -> List[TestRailCase]:
        return [c for s in self.suites_input.testsections for c in self._recurse_cases(s)]

    def collect_all_testcases_by_automation_id(self) -> Dict[str,TestRailCase]:
        """Collect all test cases by their automation IDs."""
        all_cases = self.collect_all_testcases()
        cases_by_automation_id = {}
        for case in all_cases:
            if aut_id:= case.case_fields.get(self.automation_id_system_name):
                cases_by_automation_id[aut_id] = case
        return cases_by_automation_id

    def update_suite_id(self, suite_id: int, is_created: bool=False) -> None:
        """Update suite_id in the input suite."""
        self.suites_input.suite_id = suite_id
        for section in self._collect_all_sections():
            section.suite_id = suite_id

        if self._test_run is not None:
            self._test_run.suite_id = suite_id
        if is_created:
            self.created_suite_id = suite_id

    def update_cases_section_ids(self):
        """Update case section IDs with actual section IDs."""
        case_ids_to_update = self._collect_cases_id_from_existing_cases()
        for section in self._collect_all_sections():

            if section.section_id is None:
                raise DataProviderException(f"Section ID is not initialized for section: {section.name}.")

            for case in section.testcases:
                #no need to update section_id for existing cases if update is not allowed
                if not self._environment.update_cases:
                    if case.case_id in case_ids_to_update:
                        continue
                case.section_id = section.section_id


    def _collect_cases_id_from_existing_cases(self) -> set[int]:
        return {case.case_id for case in self.existing_cases if case.case_id is not None}

    def update_test_run_description(self, description: str) -> None:
        """Update test run description."""
        if self._test_run is None:
            raise DataProviderException("Test run is not initialized. Call add_run() first.")
        self.test_run.description = description

    def update_test_run_id_if_created(self, run_id: int) -> None:
        self.created_test_run_id = run_id
        self.test_run_id = run_id

    def update_custom_automation_id_system_name(self, automation_id_system_name: str) -> None:
        """
        Update custom_automation_id field name with actual system name in all test cases.
        Needs to be explained:
        I don't like that we have custom_automation_id field in TestRailCase dataclass,
        because it is not standard field in TestRail and might have another name as we see.
        #TODO But I decided leave it as is, otherwise the field must be removed from data class
        #TODO and needs to change couple lines of code in parser.
        Here I just update custom_case fields with actual system name of that field and value.
        So later when case data object serialized to dict it will have correct field name.
        I added {"serde_skip": True} in data class to ignore for serialization if the name is different,
        but it seems not necessary, since if the field doesn't exist in TestRail,
        fortunately it will be just dropped during the POST.
        Kind reminder: currently  parser sets custom_automation_id whatever MatchersParser.AUTO  or not.
        For future filtering by custom_automation_id you should use the value stored in case_fields
        and self.automation_id_system_name as key.
        """
        self._automation_id_system_name = automation_id_system_name
        for case in self.collect_all_testcases():
            automation_id = case.custom_automation_id
            case.case_fields[self.automation_id_system_name] = automation_id

    def add_run(self) -> None:
        run_name = self._environment.title
        if self._environment.special_parser == "saucectl":
            run_name += f" ({self.suites_input.name})"

        run = TestRun(name=run_name,
                       description=self._environment.run_description,
                       milestone_id=self._environment.milestone_id,
                       assignedto_id=self._environment.run_assigned_to_id,
                       include_all=bool(self._environment.run_include_all),
                       refs=self._environment.run_refs,
                       start_on=self._environment.run_start_date,
                       due_on=self._environment.run_end_date)

        if run.suite_id is None:
            run.suite_id = self.suite_id

        if not run.case_ids:
            run.case_ids = [case.case_id for case in self.collect_all_testcases() if case.case_id is not None]

        properties = [
            str(prop)
            for section in self.suites_input.testsections
            for prop in section.properties
            if prop.description is not None
        ]

        if run.description:
            properties.insert(0, f"{run.description}")
        run.description = "\n".join(properties)

        if self._environment.run_id:
            self.test_run_id = self._environment.run_id

        if self._environment.plan_id:
            self.test_plan_id = self._environment.plan_id

        if self._environment.config_ids:
            self.config_ids = self._environment.config_ids

        self._test_run = run

    def merge_run_case_ids(self, run_case_ids: List[int]) -> None:
        """Merge existing run case IDs with the ones from the suite."""
        if self.test_run is None:
            self.add_run()
        if self.test_run.case_ids is None:
            self.test_run.case_ids = []
        self.test_run.case_ids = list(set(self.test_run.case_ids + run_case_ids))

    def get_results_for_cases(self):
        """Return bodies for adding results for cases. Returns bodies for results that already have case ID."""
        bodies = []
        testcases = self.collect_all_testcases()
        for case in testcases:
            if case.case_id is not None:
                case.result.add_global_result_fields(self.result_fields)
                case.result.case_id = case.case_id
                bodies.append(case.result.to_dict())

        result_bulks = self._divide_list_into_bulks(
            bodies,
            bulk_size=self._environment.batch_size,
        )
        return [{"results": result_bulk} for result_bulk in result_bulks]

    def check_section_names_duplicates(self):
        """
        Check if section names in result xml file are duplicated.
        #TODO I don't see a reason to use this method, since TestRail allows to have sections with the same name.
        In our case the first found with specified name will be selected.
        If we want to prevent name duplication we must validate it at parser level.
        #TODO Now I just leave it here, latter will be removed.
        """
        sections_names = [sections.name for sections in self.suites_input.testsections]

        if len(sections_names) == len(set(sections_names)):
            return False
        else:
            return True

    @staticmethod
    def _divide_list_into_bulks(input_list: List, bulk_size: int) -> List:
        return [
            input_list[i : i + bulk_size] for i in range(0, len(input_list), bulk_size)
        ]

    def _collect_all_sections(self) -> List[TestRailSection]:
        return [s for s in self.suites_input.testsections] + \
               [ss for s in self.suites_input.testsections for ss in self._recurse_sections(s)]

    def _recurse_cases(self, section: TestRailSection) -> List[TestRailCase]:
        return list(section.testcases) + [tc for ss in section.sub_sections for tc in self._recurse_cases(ss)]

    def _recurse_sections(self, section: TestRailSection) -> List[TestRailSection]:
        return list(section.sub_sections) + [ss for s in section.sub_sections for ss in self._recurse_sections(s)]

    def _add_global_case_fields(self):
        """Update case fields with global case fields."""
        # not sure should we check if case_fields have custom_automation_id
        # which must be unique for each case and shouldn't be global
        # may be cli should prevent that

        for case in self.collect_all_testcases():
            case.add_global_case_fields(self.case_fields)

    def _update_parent_section(self):
        if parent_section_id:= self._environment.section_id:
            for section in self.suites_input.testsections:
                section.parent_id = parent_section_id