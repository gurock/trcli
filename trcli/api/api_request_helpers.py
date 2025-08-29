import html
from abc import abstractmethod, ABC
from concurrent.futures import Future, as_completed
from enum import Enum
from typing import Dict, Callable, Any, Tuple, List, Optional

from serde import to_dict
from tqdm import tqdm

from trcli.api.api_client import APIClient
from trcli.api.api_response_verify import ApiResponseVerify
from trcli.cli import Environment
from trcli.constants import ProjectErrors, FAULT_MAPPING, OLD_SYSTEM_NAME_AUTOMATION_ID, \
    UPDATED_SYSTEM_NAME_AUTOMATION_ID
from trcli.data_classes.data_parsers import MatchersParser
from trcli.data_classes.dataclass_testrail import ProjectData, TestRailCase, TestRailSection
from trcli.data_providers.api_data_provider_v2 import ApiDataProvider


class FutureActions(Enum):
    """Enum for feature actions"""
    ADD_CASE = "adding case"
    UPDATE_CASE = "updating case"
    ADD_RESULTS = "adding results"


class EntityException(Exception):
    """Custom exception type for entity-level errors like section/case getting entities failures."""
    def __init__(self, message=""):
        self.message = message
        super().__init__(self.message)


class FuturesHandler:
    """
    Handles futures for different actions like adding/updating cases or adding results.
    Don't waste time here, it's just boring concurrency handling code (mostly copied from previous implementation)
    with variations for different returns from futures.
    """
    def __init__(self, env: Environment):
        self._environment = env

    def handle_futures(self, futures, action: FutureActions, progress_bar: tqdm):
        if action in {FutureActions.ADD_CASE, FutureActions.UPDATE_CASE}:
            return self._handle_add_update_futures(futures, action, progress_bar)
        elif action == FutureActions.ADD_RESULTS:
            return self._handle_futures_for_results(futures, action, progress_bar)
        else:
            raise ValueError(f"Unsupported action: {action}")

    @staticmethod
    def _retrieve_results_after_cancelling(futures) -> list:
        responses = []
        for future in as_completed(futures):
            if not future.cancelled():
                response, error_message = future.result()
                if not error_message:
                    responses.append(response)
        return responses

    def _handle_add_update_futures(self, futures, action: FutureActions, progress_bar: tqdm) -> str:
        extract_result = lambda result, _: (None, result)  # future returns error string only
        get_progress_increment = lambda _: 1
        _, error_message = self._handle_futures_generic(
            futures, action, progress_bar, extract_result, get_progress_increment
        )
        return error_message

    def _handle_futures_for_results(
            self, futures, action: FutureActions, progress_bar: tqdm
    ) -> Tuple[list, str]:
        extract_result = lambda result, _: result  # future returns (response, error)
        get_progress_increment = lambda args: len(args["results"])

        responses, error_message = self._handle_futures_generic(
            futures, action, progress_bar, extract_result, get_progress_increment
        )

        # If there was an error, collect successful responses from finished futures
        if error_message:
            responses = self._retrieve_results_after_cancelling(futures)

        return responses, error_message

    def _handle_futures_generic(
            self,
            futures: Dict[Future, Any],
            action: FutureActions,
            progress_bar: tqdm,
            extract_result: Callable[[Any, Any], Tuple[Any, str]],
            get_progress_increment: Callable[[Any], int],
    ) -> Tuple[List[Any], str]:
        """
        Generic handler for futures. Lets you specify how to extract response/error
        and how much to update progress bar per completed future.
        """
        responses: List[Any] = []
        error_message = ""

        try:
            for future in as_completed(futures):
                arguments = futures[future]

                try:
                    result = future.result()
                except Exception as e:
                    error_message = str(e)
                    self._environment.elog(f"\nUnexpected error during {action.value}: {error_message}")
                    self._cancel_running_futures(futures, action)
                    break

                response, error_message = extract_result(result, arguments)

                if response is not None:
                    responses.append(response)

                progress_bar.update(get_progress_increment(arguments))

                if error_message:
                    self._cancel_running_futures(futures, action)
                    break
            else:
                progress_bar.set_postfix_str(s="Done.")

        except KeyboardInterrupt:
            self._cancel_running_futures(futures, action)
            raise

        return responses, error_message

    def _cancel_running_futures(self, futures, action: FutureActions):
        self._environment.elog(f"\nAborting: {action.value}. Trying to cancel scheduled tasks.")
        for future in futures:
            future.cancel()


class ApiEntities(ABC):
    """Base class for API entities with pagination support"""

    def __init__(self, env: Environment, api_client: APIClient):
        self._environment = env
        self._client = api_client
        self._response_verifier = ApiResponseVerify(self._environment.verify)
        self._suffix = api_client.VERSION
        self._entities: Optional[List] = None

    @property
    def entities(self) -> List[dict]:
        """Get cached entities, initializing cache if not already done."""
        self._ensure_entities_cache_loaded()
        return self._entities

    @abstractmethod
    def _init_entities_cache(self) -> Tuple[List[dict], str]:
        """Initialize the cache of entities.
        Should be implemented in subclasses to fetch entities from the API.
        :returns: Tuple with list of entities and error message
        """
        pass

    def clean_cache(self) -> None:
        """Clear the cached entities"""
        self._entities = None

    def _normalize_link(self, link: str) -> str:
        return link.replace(self._suffix, "") if link.startswith(self._suffix) else link

    def _get_all_entities(
        self, entity_key: str, link: str, collected: Optional[List[Dict]] = None
    ) -> Tuple[List[Dict], str]:
        """Recursively fetch paginated entities from TestRail API"""
        collected = collected or []

        response = self._client.send_get(self._normalize_link(link))

        if error_message:= response.error_or_bad_code():
            return [], error_message

        data = response.response_text

        # Handle legacy (non-paginated) structure
        if isinstance(data, list):
            return data, ""

        collected.extend(data.get(entity_key, []))

        next_link = data.get("_links", {}).get("next")
        if next_link:
            next_link = next_link.replace("limit=0", "limit=250")
            return self._get_all_entities(entity_key, next_link, collected)

        return collected, ""

    def _ensure_entities_cache_loaded(self):
        if self._entities is None:
            self._entities, error = self._init_entities_cache()
            if error:
                raise EntityException(error)


class ProjectHandler(ApiEntities):
    def __init__(self, env: Environment, api_client: APIClient):
        super().__init__(env, api_client)

    def _init_entities_cache(self) -> Tuple[List[dict], str]:
        """
        Get all cases from all pages
        """
        return self._get_all_entities('projects', f"get_projects")

    def get_project_data_by_id(self, project_id: int) -> ProjectData:
        """
        Gets project data by id.
        :project_id: project id
        :returns: Project data with error or not.
        """
        entities = self.entities
        matched = next((project for project in entities if project["id"] == project_id), None)
        if matched:
            return ProjectData(
                project_id=int(matched["id"]),
                suite_mode=int(matched["suite_mode"]),
                error_message="",
                name=matched["name"]
            )
        return ProjectData(
                project_id=ProjectErrors.not_existing_project,
                suite_mode=-1,
                error_message=FAULT_MAPPING["project_doesnt_exists"],
                name=""
            )

    def get_project_data_by_name(self, project_name: str) -> Optional[ProjectData]:
        """
        Gets project data by name.
        :project_name: project name
        :returns: Project data with error or not.
        """
        entities = self.entities
        available_projects = [project for project in entities if project["name"] == project_name]

        if not available_projects:
            return ProjectData(
                project_id=ProjectErrors.not_existing_project,
                suite_mode=-1,
                error_message=FAULT_MAPPING["project_doesnt_exists"],
                name=project_name
            )

        if len(available_projects) == 1:
            project = available_projects[0]
            return ProjectData(
                project_id=int(project["id"]),
                suite_mode=int(project["suite_mode"]),
                error_message="",
                name=project_name
            )

        return ProjectData(
            project_id=ProjectErrors.multiple_project_same_name,
            suite_mode=-1,
            error_message=FAULT_MAPPING["more_than_one_project"],
            name=project_name
        )

    def define_automation_id_field(self, project_id: int) -> Optional[str]:
        """
        Defines the automation_id field for the project.
        :project_id: The ID of the project
        :returns: The system name of the automation_id field if available, otherwise None.
        """
        response = self._client.send_get("get_case_fields")

        if error_message := response.error_or_bad_code():
            self._environment.elog(f"Can not define automation_id field: {error_message}")
            return None

        # Don't know how to handle if both fields are in the system.
        # Assuming it won't happen or must be solved on user's side.
        fields: List[dict] = response.response_text or []
        automation_id_field = next(
            (
                field for field in fields
                if field.get("system_name") in {OLD_SYSTEM_NAME_AUTOMATION_ID, UPDATED_SYSTEM_NAME_AUTOMATION_ID}
            ),
            None,
        )

        if not automation_id_field:
            self._environment.elog(FAULT_MAPPING["automation_id_unavailable"])
            return None

        if not automation_id_field.get("is_active", False):
            self._environment.elog(FAULT_MAPPING["automation_id_unavailable"])
            return None

        # Below code just copied and slightly refactored with no understanding what it checks, only assumptions.

        # If no configs are defined, the field is globally available
        if not automation_id_field.get("configs"):
            return automation_id_field.get("system_name")

        # Safely check configs
        for config in automation_id_field.get("configs", []):
            context = config.get("context", {})
            if context.get("is_global") or project_id in context.get("project_ids", []):
                return automation_id_field.get("system_name")

        self._environment.elog(FAULT_MAPPING["automation_id_unavailable"])
        return None


class SuiteHandler(ApiEntities):
    def __init__(self, env: Environment, api_client: APIClient, provider: ApiDataProvider):
        super().__init__(env, api_client)
        self._provider = provider

    def _init_entities_cache(self) -> Tuple[List[dict], str]:
        project_id = self._provider.project_id
        return self._get_all_entities("suites", f"get_suites/{project_id}")

    def add_suite(self) -> Tuple[Optional[int], str]:
        project_id = self._provider.project_id
        body = to_dict(self._provider.suites_input)
        response = self._client.send_post(f"add_suite/{project_id}", body)

        if error_message:= response.error_or_bad_code():
            return None, error_message

        if not self._response_verifier.verify_returned_data(body, response.response_text):
            return None, FAULT_MAPPING["data_verification_error"]

        suite_id = response.response_text.get("id")
        return suite_id, ""

    def delete_suite(self, suite_id: int) -> str:
        response = self._client.send_post(f"delete_suite/{suite_id}", payload={})
        return response.error_or_bad_code()


class TestHandler(ApiEntities):
    def __init__(self, env: Environment, api_client: APIClient, provider: ApiDataProvider):
        super().__init__(env, api_client)
        self._provider = provider

    def _init_entities_cache(self) -> Tuple[List[dict], str]:
        """
        Get all tests from all pages
        """
        run_id = self._provider.test_run_id
        return self._get_all_entities('tests', f"get_tests/{run_id}")


class RunHandler:
    def __init__(self, api_client: APIClient, provider: ApiDataProvider):
        self._client = api_client
        self._provider = provider

    def get_run_by_id(self, run_id: int) -> Tuple[dict, str]:
        response = self._client.send_get(f"get_run/{run_id}")

        if error_message:= response.error_or_bad_code():
            return {}, error_message

        return response.response_text, ""

    def add_run(self) -> Tuple[Optional[int], str]:
        project_id = self._provider.project_id
        response = self._client.send_post(f"add_run/{project_id}", self._provider.test_run.to_dict())

        if error_message:= response.error_or_bad_code():
            return None, error_message
        return response.response_text.get("id"), ""

    def update_run(self, run_id: int) -> str:
        response = self._client.send_post(f"update_run/{run_id}", self._provider.test_run.to_dict())
        return response.error_or_bad_code()

    def delete_run(self, run_id: int) -> str:
        response = self._client.send_post(f"delete_run/{run_id}", payload={})
        return response.error_or_bad_code()

    def close_run(self, run_id: int) -> str:
        """
        Closes an existing test run and archives its tests & results.
        :run_id: run id
        :returns: Error message if any, otherwise an empty string
        """
        body = {"run_id": run_id}
        response = self._client.send_post(f"close_run/{run_id}", body)
        return response.error_or_bad_code()


class PlanHandler:
    def __init__(self, api_client: APIClient, provider: ApiDataProvider):
        self._client = api_client
        self._provider = provider

    def get_plan_by_id(self, plan_id: int) -> Tuple[dict, str]:
        response = self._client.send_get(f"get_plan/{plan_id}")

        if error_message:= response.error_or_bad_code():
            return {}, error_message

        return response.response_text, ""

    def update_plan_entry(self, plan_id: int, entry_id: int) -> str:
        run = self._provider.test_run.to_dict()
        response = self._client.send_post(f"update_plan_entry/{plan_id}/{entry_id}", run)
        return response.error_or_bad_code()

    def update_run_in_plan_entry(self, run_id) -> str:
        run = self._provider.test_run.to_dict()
        response = self._client.send_post(f"update_run_in_plan_entry/{run_id}", run)
        return response.error_or_bad_code()

    def add_run_to_plan(self, plan_id: int) -> Tuple[Optional[int], str]:
        """
        Adds a test run to a test plan.
        Returns a tuple of (run_id, error_message).
        """
        run = self._provider.test_run
        config_ids = self._provider.config_ids

        # Prepare entry data depending on whether config_ids exist
        entry_data = (
            {
                "name": run.name,
                "suite_id": run.suite_id,
                "config_ids": config_ids,
                "runs": [run.to_dict()],
            }
            if config_ids
            else run
        )

        response = self._client.send_post(f"add_plan_entry/{plan_id}", entry_data)

        if error_message:= response.error_or_bad_code():
            return None, error_message

        run_id = int(response.response_text["runs"][0]["id"])
        return run_id, ""


class SectionHandler(ApiEntities):
    def __init__(self, env: Environment, api_client: APIClient, provider: ApiDataProvider):
        super().__init__(env, api_client)
        self._provider = provider

    def _init_entities_cache(self) -> Tuple[List[dict], str]:
        project_id = self._provider.project_id
        suite_id = self._provider.suite_id
        return self._get_all_entities("sections", f"get_sections/{project_id}&suite_id={suite_id}")

    def has_missing_sections(self) -> bool:
        for section in self._provider.suites_input.testsections:
            if self._is_section_missed(section):
                return True
        return False

    def create_missing_sections(self) -> Tuple[List[int], str]:
        added_ids = []
        for section in self._provider.suites_input.testsections:
            created, error = self._create_section_tree(section, section.parent_id)
            added_ids.extend(created)
            if error:
                return list(reversed(added_ids)), error
        # important to reverse the order if we need to delete sections later in case rollback
        return list(reversed(added_ids)), ""

    def _is_section_missed(self,section: TestRailSection, parent_id: Optional[int] = None) -> bool:
        entities = self.entities
        matched = next((s for s in entities if s["parent_id"] == parent_id and s["name"] == section.name), None)
        if not matched:
            return True
        parent_id = matched["id"]
        return any(self._is_section_missed(sub, parent_id) for sub in section.sub_sections)

    def _create_section_tree(self, section: TestRailSection, parent_id: Optional[int] = None) -> Tuple[List[int], str]:
        """
        Creates a section tree recursively.
        :section: TestRailSection object to create
        :parent_id: ID of the parent section, None for root sections
        :returns: Tuple with list of created section IDs and error message if any
        """
        project_id = self._provider.project_id
        added = []
        # level = "Section" if parent_id is None else "Subsection"

        entities = self.entities
        existing = next(
            (s for s in entities if s["parent_id"] == parent_id and s["name"] == section.name),
            None
        )

        if existing:
            section.section_id = existing["id"]
            # self._environment.log(f"{level} exists: {section.name} (ID: {section.section_id})")
        else:
            section.parent_id = parent_id
            body = to_dict(section)
            response = self._client.send_post(f"add_section/{project_id}", body)

            if error_message:= response.error_or_bad_code():
                # self._environment.elog(f"Failed to create {level}: {error_message}")
                return added, error_message

            if not self._response_verifier.verify_returned_data(body, response.response_text):
                return added, FAULT_MAPPING["data_verification_error"]

            section.section_id = response.response_text["id"]
            added.append(section.section_id)
            # self._environment.log(f"{level} created: {section.name} (ID: {section.section_id})")

        for sub in section.sub_sections:
            sub_added, error_message = self._create_section_tree(sub, section.section_id)
            added.extend(sub_added)
            if error_message:
                return added, error_message

        return added, ""

    def delete_section(self, section_id: int) -> str:
        """
        Deletes a section by its ID.
        :section_id: ID of the section to delete
        :returns: Error message if any, otherwise an empty string
        """
        response = self._client.send_post(f"delete_section/{section_id}", payload={})
        return response.error_or_bad_code()


class CaseHandler(ApiEntities):
    """
    Class might have two implementations of case matching - by automation_id or by case_id.
    For now as is...
    """
    def __init__(self, env: Environment, api_client: APIClient, provider: ApiDataProvider):
        super().__init__(env, api_client)
        self._provider = provider

    def _init_entities_cache(self):
        project_id = self._provider.project_id
        suite_id = self._provider.suite_id
        return self._get_all_entities("cases", f"get_cases/{project_id}&suite_id={suite_id}")

    def sort_missing_and_existing_cases(self) -> None:
        if self._environment.case_matcher == MatchersParser.AUTO:
            self._sort_missing_and_existing_cases_by_aut_id()
        else:
            self._sort_missing_and_existing_cases_by_id()

    def update_case(self, case: TestRailCase) -> str:
        case_id = case.case_id
        body = case.to_dict()
        response = self._client.send_post(f"update_case/{case_id}", payload=body)
        if error_message:= response.error_or_bad_code():
            return error_message
        self._provider.updated_cases_ids.append(case_id)
        return ""

    def add_case(self, case: TestRailCase) -> str:
        section_id = case.section_id
        body = case.to_dict()
        response = self._client.send_post(f"add_case/{section_id}", payload=body)

        if error_message:= response.error_or_bad_code():
            return error_message

        case.case_id = response.response_text.get("id")

        if case.case_id is None:
            return "Case id is not returned by server"

        self._provider.created_cases_ids.append(case.case_id)
        case.result.case_id = case.case_id

        if not self._response_verifier.verify_returned_data(added_data=body, returned_data=response.response_text):
            return FAULT_MAPPING["data_verification_error"]
        return  ""

    def delete_cases(self, added_cases: List[int]) -> str:
        """
        Delete cases given add_cases response
        :added_cases: List of case IDs to delete
        :returns: Error message if any, otherwise an empty string
        """
        suite_id = self._provider.suite_id
        body = {"case_ids": added_cases}
        response = self._client.send_post(f"delete_cases/{suite_id}", payload=body)
        return response.error_or_bad_code()

    def _sort_missing_and_existing_cases_by_aut_id(self) -> None:
        existing_case_map = self._map_cases_by_automation_id()
        map_by_aut_id = self._provider.collect_all_testcases_by_automation_id()
        for aut_id, case in map_by_aut_id.items():
            if aut_id not in existing_case_map:
                self._provider.missing_cases.append(case)
            else:
                case.case_id = existing_case_map[aut_id]["id"]
                case.section_id = existing_case_map[aut_id]["section_id"]
                case.result.case_id = case.case_id
                self._provider.existing_cases.append(case)

    def _sort_missing_and_existing_cases_by_id(self) -> None:
        case_map = self._map_cases_by_id()
        for case in self._provider.collect_all_testcases():
            if not case.case_id or case.case_id not in case_map:
                self._provider.missing_cases.append(case)
            else:
                case.section_id = case_map[case.case_id]["section_id"]
                case.result.case_id = case.case_id
                self._provider.existing_cases.append(case)

    def _map_cases_by_automation_id(self) -> Dict[str, dict]:
        case_map = {}
        entities = self.entities
        for case in entities:
            # field name may vary based on TestRail version and setup
            aut_id = case.get(self._provider.automation_id_system_name)
            if aut_id:
                case_map[html.unescape(aut_id)] = case
        return case_map

    def _map_cases_by_id(self) -> Dict[int, dict]:
        case_map = {}
        entities = self.entities
        for case in entities:
            case_id = case.get("id")
            if case_id:
                case_map[case_id] = case
        return case_map


class ResultHandler:
    def __init__(self, api_client: APIClient, provider: ApiDataProvider):
        self._client = api_client
        self._provider = provider

    def add_result_for_cases(self, body: dict) -> Tuple[Dict, str]:
        """
        Adds results for cases in the specified in data provider run.
        :body: Dictionary containing results to be added
        :returns: Tuple with response data and error message if any
        """
        run_id = self._provider.test_run_id
        response = self._client.send_post(f"add_results_for_cases/{run_id}", body)
        if error_message:= response.error_or_bad_code():
            return {}, error_message
        return response.response_text, ""


class AttachmentHandler:
    def __init__(self, api_client: APIClient):
        self._client = api_client

    def add_attachment_to_result(self, result_id: int, file_path: str) -> str:
        """
        Adds an attachment to a test result.
        :result_id: ID of the test result
        :file_path: Path to the file to be attached
        :returns: Error message if any, otherwise an empty string
        """
        response = self._client.send_post(f"add_attachment_to_result/{result_id}", files={"attachment": file_path})
        return response.error_or_bad_code()
