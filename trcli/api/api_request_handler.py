import os
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from beartype.typing import List, Union, Tuple, Dict, Optional

from trcli.api.api_client import APIClient, APIClientResult
from trcli.api.api_response_verify import ApiResponseVerify
from trcli.api.api_cache import RequestCache
from trcli.api.label_manager import LabelManager
from trcli.api.reference_manager import ReferenceManager
from trcli.api.case_matcher import CaseMatcherFactory
from trcli.api.suite_handler import SuiteHandler
from trcli.api.section_handler import SectionHandler
from trcli.api.result_handler import ResultHandler
from trcli.api.run_handler import RunHandler
from trcli.api.bdd_handler import BddHandler
from trcli.api.case_handler import CaseHandler
from trcli.cli import Environment
from trcli.constants import (
    ProjectErrors,
    FAULT_MAPPING,
    OLD_SYSTEM_NAME_AUTOMATION_ID,
    UPDATED_SYSTEM_NAME_AUTOMATION_ID,
)
from trcli.data_classes.data_parsers import MatchersParser
from trcli.data_classes.dataclass_testrail import TestRailSuite, TestRailCase, ProjectData
from trcli.data_providers.api_data_provider import ApiDataProvider
from trcli.settings import (
    MAX_WORKERS_ADD_RESULTS,
    MAX_WORKERS_ADD_CASE,
    ENABLE_PARALLEL_PAGINATION,
    MAX_WORKERS_PARALLEL_PAGINATION,
)


class ApiRequestHandler:
    """Sends requests based on DataProvider bodies"""

    def __init__(
        self,
        environment: Environment,
        api_client: APIClient,
        suites_data: TestRailSuite,
        verify: bool = False,
    ):
        self.environment = environment
        self.client = api_client
        self.suffix = api_client.VERSION
        self.data_provider = ApiDataProvider(
            suites_data,
            environment.case_fields,
            environment.run_description,
            environment.result_fields,
            environment.section_id,
        )
        self.suites_data_from_provider = self.data_provider.suites_input
        self.response_verifier = ApiResponseVerify(verify)
        # Initialize session-scoped cache for API responses
        self._cache = RequestCache(max_size=512)
        # Initialize specialized managers
        self.label_manager = LabelManager(api_client, environment)
        self.reference_manager = ReferenceManager(api_client, environment)
        self.suite_handler = SuiteHandler(
            api_client, environment, self.data_provider, get_all_suites_callback=self.__get_all_suites
        )
        self.section_handler = SectionHandler(
            api_client, environment, self.data_provider, get_all_sections_callback=self.__get_all_sections
        )
        self.result_handler = ResultHandler(
            api_client,
            environment,
            self.data_provider,
            get_all_tests_in_run_callback=self.__get_all_tests_in_run,
            handle_futures_callback=self.handle_futures,
        )
        self.run_handler = RunHandler(
            api_client, environment, self.data_provider, get_all_tests_in_run_callback=self.__get_all_tests_in_run
        )
        self.bdd_handler = BddHandler(api_client, environment)
        self.case_handler = CaseHandler(
            api_client,
            environment,
            self.data_provider,
            handle_futures_callback=self.handle_futures,
            retrieve_results_callback=ApiRequestHandler.retrieve_results_after_cancelling,
        )

        # BDD case cache for feature name matching (shared by CucumberParser and JunitParser)
        # Structure: {"{project_id}_{suite_id}": {normalized_name: [case_dict, case_dict, ...]}}
        self._bdd_case_cache = {}

        # Cache for resolved BDD field names (resolved from TestRail API)
        self._bdd_case_field_name = None  # BDD Scenarios field (type_id=13)
        self._bdd_result_field_name = None  # BDD Scenario Results field (type_id=14)

    def check_automation_id_field(self, project_id: int) -> Union[str, None]:
        """
        Checks if the automation_id field (custom_automation_id or custom_case_automation_id) is available for the project
        :param project_id: the id of the project
        :return: error message
        """
        response = self.client.send_get("get_case_fields")
        if not response.error_message:
            fields: List = response.response_text
            automation_id_field = next(
                filter(
                    lambda x: x["system_name"] in [OLD_SYSTEM_NAME_AUTOMATION_ID, UPDATED_SYSTEM_NAME_AUTOMATION_ID],
                    fields,
                ),
                None,
            )
            if automation_id_field:
                if automation_id_field["is_active"] is False:
                    return FAULT_MAPPING["automation_id_unavailable"]
                if not automation_id_field["configs"]:
                    self._active_automation_id_field = automation_id_field["system_name"]
                    self.case_handler._active_automation_id_field = automation_id_field["system_name"]
                    return None
                for config in automation_id_field["configs"]:
                    context = config["context"]
                    if context["is_global"] or project_id in context["project_ids"]:
                        self._active_automation_id_field = automation_id_field["system_name"]
                        self.case_handler._active_automation_id_field = automation_id_field["system_name"]
                        return None
                return FAULT_MAPPING["automation_id_unavailable"]
            else:
                return FAULT_MAPPING["automation_id_unavailable"]
        else:
            return response.error_message

    def get_project_data(self, project_name: str, project_id: int = None) -> ProjectData:
        """
        Send get_projects with project name
        :project_name: Project name
        :returns: ProjectData
        """
        projects_data, error = self.__get_all_projects()
        if not error:
            available_projects = [project for project in projects_data if project["name"] == project_name]

            if len(available_projects) == 1:
                return ProjectData(
                    project_id=int(available_projects[0]["id"]),
                    suite_mode=int(available_projects[0]["suite_mode"]),
                    error_message=error,
                )
            elif len(available_projects) > 1:
                if project_id in [project["id"] for project in available_projects]:
                    project_index = [
                        index for index, project in enumerate(available_projects) if project["id"] == project_id
                    ][0]
                    return ProjectData(
                        project_id=int(available_projects[project_index]["id"]),
                        suite_mode=int(available_projects[project_index]["suite_mode"]),
                        error_message=error,
                    )
                else:
                    return ProjectData(
                        project_id=ProjectErrors.multiple_project_same_name,
                        suite_mode=-1,
                        error_message=FAULT_MAPPING["more_than_one_project"],
                    )
            else:
                return ProjectData(
                    project_id=ProjectErrors.not_existing_project,
                    suite_mode=-1,
                    error_message=FAULT_MAPPING["project_doesnt_exists"],
                )
        else:
            return ProjectData(
                project_id=ProjectErrors.other_error,
                suite_mode=-1,
                error_message=error,
            )

    def check_suite_id(self, project_id: int) -> Tuple[bool, str]:
        suite_id = self.suites_data_from_provider.suite_id
        return self.suite_handler.check_suite_id(project_id, suite_id)

    def resolve_suite_id_using_name(self, project_id: int) -> Tuple[int, str]:
        suite_name = self.suites_data_from_provider.name
        return self.suite_handler.resolve_suite_id_using_name(project_id, suite_name)

    def get_suite_ids(self, project_id: int) -> Tuple[List[int], str]:
        return self.suite_handler.get_suite_ids(project_id)

    def add_suites(self, project_id: int) -> Tuple[List[Dict], str]:
        return self.suite_handler.add_suites(project_id, verify_callback=self.response_verifier.verify_returned_data)

    def check_missing_section_ids(self, project_id: int) -> Tuple[bool, str]:
        suite_id = self.suites_data_from_provider.suite_id
        return self.section_handler.check_missing_section_ids(project_id, suite_id, self.suites_data_from_provider)

    def add_sections(self, project_id: int) -> Tuple[List[Dict], str]:
        return self.section_handler.add_sections(
            project_id, verify_callback=self.response_verifier.verify_returned_data
        )

    def check_missing_test_cases_ids(self, project_id: int) -> Tuple[bool, str]:
        """
        Check what test cases id's are missing in DataProvider using the configured matcher strategy.
        :project_id: project_id
        :returns: Tuple with list test case ID missing and error string.
        """
        suite_id = self.suites_data_from_provider.suite_id

        # Create appropriate matcher based on configuration (Strategy pattern)
        matcher = CaseMatcherFactory.create_matcher(self.environment.case_matcher, self.environment, self.data_provider)

        # Delegate to the matcher
        return matcher.check_missing_cases(
            project_id,
            suite_id,
            self.suites_data_from_provider,
            get_all_cases_callback=self.__get_all_cases,
            validate_case_ids_callback=self.__validate_case_ids_exist,
        )

    def add_cases(self) -> Tuple[List[dict], str]:
        return self.case_handler.add_cases()

    def add_run(
        self,
        project_id: int,
        run_name: str,
        milestone_id: int = None,
        start_date: str = None,
        end_date: str = None,
        plan_id: int = None,
        config_ids: List[int] = None,
        assigned_to_id: int = None,
        include_all: bool = False,
        refs: str = None,
        case_ids: List[int] = None,
    ) -> Tuple[int, str]:
        return self.run_handler.add_run(
            project_id,
            run_name,
            milestone_id,
            start_date,
            end_date,
            plan_id,
            config_ids,
            assigned_to_id,
            include_all,
            refs,
            case_ids,
        )

    def update_run(
        self,
        run_id: int,
        run_name: str,
        start_date: str = None,
        end_date: str = None,
        milestone_id: int = None,
        refs: str = None,
        refs_action: str = "add",
    ) -> Tuple[dict, str]:
        return self.run_handler.update_run(run_id, run_name, start_date, end_date, milestone_id, refs, refs_action)

    def _manage_references(self, existing_refs: str, new_refs: str, action: str) -> str:
        return self.run_handler._manage_references(existing_refs, new_refs, action)

    def append_run_references(self, run_id: int, references: List[str]) -> Tuple[Dict, List[str], List[str], str]:
        return self.run_handler.append_run_references(run_id, references)

    def update_existing_case_references(
        self, case_id: int, junit_refs: str, strategy: str = "append"
    ) -> Tuple[bool, str, List[str], List[str]]:
        return self.case_handler.update_existing_case_references(case_id, junit_refs, strategy)

    def upload_attachments(self, report_results: List[Dict], results: List[Dict], run_id: int):
        return self.result_handler.upload_attachments(report_results, results, run_id)

    def add_results(self, run_id: int) -> Tuple[List, str, int]:
        return self.result_handler.add_results(run_id)

    def handle_futures(self, futures, action_string, progress_bar) -> Tuple[list, str]:
        responses = []
        error_message = ""
        try:
            for future in as_completed(futures):
                arguments = futures[future]
                response = future.result()
                if not response.error_message:
                    responses.append(response)
                    if action_string == "add_results":
                        progress_bar.update(len(arguments["results"]))
                    else:
                        if action_string == "add_case":
                            arguments = arguments.to_dict()
                            arguments.pop("case_id")
                        if not self.response_verifier.verify_returned_data(arguments, response.response_text):
                            responses.append(response)
                            error_message = FAULT_MAPPING["data_verification_error"]
                            self.__cancel_running_futures(futures, action_string)
                            break
                        progress_bar.update(1)
                else:
                    error_message = response.error_message
                    self.environment.log(f"\nError during {action_string}. Trying to cancel scheduled tasks.")
                    self.__cancel_running_futures(futures, action_string)
                    break
            else:
                progress_bar.set_postfix_str(s="Done.")
        except KeyboardInterrupt:
            self.__cancel_running_futures(futures, action_string)
            raise KeyboardInterrupt
        return responses, error_message

    def close_run(self, run_id: int) -> Tuple[dict, str]:
        return self.run_handler.close_run(run_id)

    def delete_suite(self, suite_id: int) -> Tuple[dict, str]:
        return self.suite_handler.delete_suite(suite_id)

    def delete_sections(self, added_sections: List[Dict]) -> Tuple[List, str]:
        return self.section_handler.delete_sections(added_sections)

    def delete_cases(self, suite_id: int, added_cases: List[Dict]) -> Tuple[Dict, str]:
        return self.case_handler.delete_cases(suite_id, added_cases)

    def delete_run(self, run_id) -> Tuple[dict, str]:
        return self.run_handler.delete_run(run_id)

    @staticmethod
    def retrieve_results_after_cancelling(futures) -> list:
        """
        Retrieve results from futures after cancellation has been triggered.
        Delegated to ResultHandler for backward compatibility.
        """
        return ResultHandler.retrieve_results_after_cancelling(futures)

    def get_user_by_email(self, email: str) -> Tuple[Union[int, None], str]:
        """
        Validates a user email and returns the user ID if valid.

        :param email: User email to validate
        :returns: Tuple with user ID (or None if not found) and error message
        """
        if not email or not email.strip():
            return None, "Email cannot be empty"

        email = email.strip()
        # Use proper URL encoding for the query parameter
        import urllib.parse

        encoded_email = urllib.parse.quote_plus(email)
        response = self.client.send_get(f"get_user_by_email&email={encoded_email}")

        if response.error_message:
            # Map TestRail's email validation error to our expected format
            if "Field :email is not a valid email address" in response.error_message:
                return None, f"User not found: {email}"
            return None, response.error_message

        if response.status_code == 200:
            try:
                user_data = response.response_text
                if isinstance(user_data, dict) and "id" in user_data:
                    return user_data["id"], ""
                else:
                    return None, f"Invalid response format for user: {email}"
            except (KeyError, TypeError):
                return None, f"Invalid response format for user: {email}"
        elif response.status_code == 400:
            # Check if the response contains the email validation error
            if (
                hasattr(response, "response_text")
                and response.response_text
                and isinstance(response.response_text, dict)
                and "Field :email is not a valid email address" in str(response.response_text.get("error", ""))
            ):
                return None, f"User not found: {email}"
            return None, f"User not found: {email}"
        else:
            # For other status codes, check if it's the email validation error
            if (
                hasattr(response, "response_text")
                and response.response_text
                and "Field :email is not a valid email address" in str(response.response_text)
            ):
                return None, f"User not found: {email}"
            return None, f"API error (status {response.status_code}) when validating user: {email}"

    def _add_case_and_update_data(self, case: TestRailCase) -> APIClientResult:
        return self.case_handler._add_case_and_update_data(case)

    def __cancel_running_futures(self, futures, action_string):
        self.environment.log(f"\nAborting: {action_string}. Trying to cancel scheduled tasks.")
        for future in futures:
            future.cancel()

    def __get_all_cases(self, project_id=None, suite_id=None) -> Tuple[List[dict], str]:
        """
        Get all cases from all pages (with caching)
        """
        cache_key = f"get_cases/{project_id}"
        params = (project_id, suite_id)

        def fetch():
            if suite_id is None:
                return self.__get_all_entities("cases", f"get_cases/{project_id}", entities=[])
            else:
                return self.__get_all_entities("cases", f"get_cases/{project_id}&suite_id={suite_id}", entities=[])

        return self._cache.get_or_fetch(cache_key, fetch, params)

    def __get_all_sections(self, project_id=None, suite_id=None) -> Tuple[List[dict], str]:
        """
        Get all sections from all pages (with caching)
        """
        cache_key = f"get_sections/{project_id}"
        params = (project_id, suite_id)

        def fetch():
            return self.__get_all_entities("sections", f"get_sections/{project_id}&suite_id={suite_id}", entities=[])

        return self._cache.get_or_fetch(cache_key, fetch, params)

    def __get_all_tests_in_run(self, run_id=None) -> Tuple[List[dict], str]:
        """
        Get all tests from all pages (with caching)
        """
        cache_key = f"get_tests/{run_id}"
        params = (run_id,)

        def fetch():
            return self.__get_all_entities("tests", f"get_tests/{run_id}", entities=[])

        return self._cache.get_or_fetch(cache_key, fetch, params)

    def __get_all_projects(self) -> Tuple[List[dict], str]:
        """
        Get all projects from all pages (with caching)
        """
        cache_key = "get_projects"
        params = None

        def fetch():
            return self.__get_all_entities("projects", f"get_projects", entities=[])

        return self._cache.get_or_fetch(cache_key, fetch, params)

    def __get_all_suites(self, project_id) -> Tuple[List[dict], str]:
        """
        Get all suites from all pages (with caching)
        """
        cache_key = f"get_suites/{project_id}"
        params = (project_id,)

        def fetch():
            return self.__get_all_entities("suites", f"get_suites/{project_id}", entities=[])

        return self._cache.get_or_fetch(cache_key, fetch, params)

    def __get_all_entities(self, entity: str, link=None, entities=[]) -> Tuple[List[Dict], str]:
        """
        Get all entities from all pages if number of entities is too big to return in single response.
        Function using next page field in API response.
        Entity examples: cases, sections

        If ENABLE_PARALLEL_PAGINATION is True or --parallel-pagination flag is set,
        will use parallel fetching for better performance.
        """
        # Check if parallel pagination is enabled (CLI flag takes precedence)
        parallel_enabled = getattr(self.environment, "parallel_pagination", False) or ENABLE_PARALLEL_PAGINATION

        # Use parallel pagination if enabled and this is the first call (entities is empty)
        if parallel_enabled and not entities:
            return self.__get_all_entities_parallel(entity, link)

        # Otherwise use sequential pagination (original implementation)
        if link.startswith(self.suffix):
            link = link.replace(self.suffix, "")
        response = self.client.send_get(link)
        if not response.error_message:
            # Endpoints without pagination (legacy)
            if isinstance(response.response_text, list):
                return response.response_text, response.error_message
            # Check if response is a string (JSON parse failed)
            if isinstance(response.response_text, str):
                error_msg = FAULT_MAPPING["invalid_api_response"].format(error_details=response.response_text[:200])
                return [], error_msg
            # Endpoints with pagination
            entities = entities + response.response_text[entity]
            if response.response_text["_links"]["next"] is not None:
                next_link = response.response_text["_links"]["next"].replace("limit=0", "limit=250")
                return self.__get_all_entities(entity, link=next_link, entities=entities)
            else:
                return entities, response.error_message
        else:
            return [], response.error_message

    def __get_all_entities_parallel(self, entity: str, link: str) -> Tuple[List[Dict], str]:
        """
        Parallel version of __get_all_entities for faster pagination.
        Fetches multiple pages concurrently using ThreadPoolExecutor.

        :param entity: Entity type (cases, sections, etc.)
        :param link: Initial API link
        :returns: Tuple of (all entities list, error message)
        """
        fetch_start_time = time.time()

        if link.startswith(self.suffix):
            link = link.replace(self.suffix, "")

        # Step 1: Fetch first page to get metadata
        self.environment.log(f"Fetching first page to determine total pages...")
        response = self.client.send_get(link)

        if response.error_message:
            return [], response.error_message

        # Handle non-paginated responses (legacy endpoints)
        if isinstance(response.response_text, list):
            return response.response_text, response.error_message

        if isinstance(response.response_text, str):
            error_msg = FAULT_MAPPING["invalid_api_response"].format(error_details=response.response_text[:200])
            return [], error_msg

        # Collect first page results
        all_entities = response.response_text[entity]
        first_page_count = len(all_entities)

        # Check if there are more pages
        if response.response_text["_links"]["next"] is None:
            # Only one page, return immediately
            fetch_time = time.time() - fetch_start_time
            self.environment.log(f"Single page fetch completed in {fetch_time:.1f}s")
            return all_entities, response.error_message

        # Step 2: Calculate total pages needed
        # TestRail pagination uses limit parameter (default 250)
        # We need to parse the next link to understand pagination structure
        next_link = response.response_text["_links"]["next"]

        # Extract offset/limit from the link to calculate total pages
        from urllib.parse import urlparse, parse_qs

        # Parse the next link to get offset and limit
        parsed = urlparse(next_link)
        query_params = parse_qs(parsed.query)

        # Get limit (page size) - default to 250 if not found
        limit = int(query_params.get("limit", [250])[0])
        if limit == 0:
            limit = 250

        # Get offset from next link
        next_offset = int(query_params.get("offset", [limit])[0])

        # Step 3: Fetch pages in parallel with dynamic offset generation
        # Build base link without offset parameter
        # TestRail API uses '&' as separator (e.g., get_cases/123&suite_id=2&offset=250)
        base_link = link.split("&offset=")[0].split("?offset=")[0]

        self.environment.log(
            f"Starting parallel fetch: first page has {first_page_count} {entity}, "
            f"fetching remaining pages with {MAX_WORKERS_PARALLEL_PAGINATION} workers..."
        )

        def fetch_page(offset):
            """Fetch a single page by offset"""
            # TestRail always uses '&' as separator, not '?'
            page_link = f"{base_link}&offset={offset}&limit={limit}"
            page_response = self.client.send_get(page_link)

            if page_response.error_message:
                return None, page_response.error_message

            if isinstance(page_response.response_text, dict) and entity in page_response.response_text:
                page_data = page_response.response_text[entity]
                # Return empty list if this page has no data (we've reached the end)
                if not page_data:
                    return [], None
                return page_data, None
            else:
                return None, "Invalid response format"

        # Fetch pages in parallel with intelligent batching to avoid overwhelming server
        error_message = ""
        pages_fetched = 1  # We already have the first page

        # Use batching: submit batches of pages, check results, submit next batch
        # This prevents overwhelming the server with 10k requests at once
        batch_size = 100  # Submit 100 pages at a time
        current_page_index = 0
        max_pages = 10000  # Safety cap
        consecutive_empty_pages = 0
        max_consecutive_empty = 10  # Stop after 10 consecutive empty pages

        with ThreadPoolExecutor(max_workers=MAX_WORKERS_PARALLEL_PAGINATION) as executor:
            should_continue = True

            while should_continue and current_page_index < max_pages:
                # Submit next batch of pages
                futures = {}
                batch_offsets = []

                for i in range(batch_size):
                    if current_page_index + i >= max_pages:
                        break
                    offset = next_offset + ((current_page_index + i) * limit)
                    batch_offsets.append(offset)
                    future = executor.submit(fetch_page, offset)
                    futures[future] = offset

                if not futures:
                    break

                # Process this batch
                batch_had_data = False
                for future in as_completed(futures):
                    offset = futures[future]
                    try:
                        page_data, page_error = future.result()

                        if page_error:
                            error_message = page_error
                            self.environment.elog(f"Error fetching page at offset {offset}: {page_error}")
                            should_continue = False
                            # Cancel remaining futures in this batch
                            for f in futures:
                                if not f.done():
                                    f.cancel()
                            break

                        if page_data is None:
                            # Error occurred
                            error_message = "Invalid response format"
                            should_continue = False
                            # Cancel remaining
                            for f in futures:
                                if not f.done():
                                    f.cancel()
                            break

                        if len(page_data) == 0:
                            # Empty page
                            consecutive_empty_pages += 1
                            if consecutive_empty_pages >= max_consecutive_empty:
                                # We've hit enough empty pages, stop fetching
                                self.environment.log(f"Reached end of data after {consecutive_empty_pages} empty pages")
                                should_continue = False
                                # Cancel remaining futures in this batch
                                for f in futures:
                                    if not f.done():
                                        f.cancel()
                                break
                        else:
                            # Got data - reset consecutive empty counter
                            consecutive_empty_pages = 0
                            batch_had_data = True

                            # Add results to our collection
                            all_entities.extend(page_data)
                            pages_fetched += 1

                            # Log progress every 50 pages
                            if pages_fetched % 50 == 0:
                                self.environment.log(
                                    f"Fetched {pages_fetched} pages, {len(all_entities)} {entity} so far..."
                                )

                    except Exception as ex:
                        error_message = f"Exception during parallel fetch: {str(ex)}"
                        self.environment.elog(error_message)
                        should_continue = False
                        # Cancel remaining
                        for f in futures:
                            if not f.done():
                                f.cancel()
                        break

                # Move to next batch
                current_page_index += batch_size

                # If this batch had no data at all, we've likely reached the end
                if not batch_had_data and consecutive_empty_pages > 0:
                    should_continue = False

        fetch_time = time.time() - fetch_start_time

        if error_message:
            self.environment.elog(f"Parallel fetch failed after {fetch_time:.1f}s, falling back to sequential...")
            # Fall back to sequential fetch
            return self.__get_all_entities_sequential(entity, link, [])

        self.environment.log(
            f"Parallel fetch completed: {len(all_entities)} {entity} in {fetch_time:.1f}s "
            f"(~{len(all_entities) / fetch_time:.0f} items/sec)"
        )

        return all_entities, ""

    def __get_all_entities_sequential(self, entity: str, link: str, entities: List[Dict]) -> Tuple[List[Dict], str]:
        """
        Sequential fallback for __get_all_entities (original implementation).
        This is kept separate for fallback purposes.
        """
        if link.startswith(self.suffix):
            link = link.replace(self.suffix, "")
        response = self.client.send_get(link)
        if not response.error_message:
            if isinstance(response.response_text, list):
                return response.response_text, response.error_message
            if isinstance(response.response_text, str):
                error_msg = FAULT_MAPPING["invalid_api_response"].format(error_details=response.response_text[:200])
                return [], error_msg
            entities = entities + response.response_text[entity]
            if response.response_text["_links"]["next"] is not None:
                next_link = response.response_text["_links"]["next"].replace("limit=0", "limit=250")
                return self.__get_all_entities_sequential(entity, link=next_link, entities=entities)
            else:
                return entities, response.error_message
        else:
            return [], response.error_message

    def __validate_case_ids_exist(self, suite_id: int, case_ids: List[int]) -> set:
        """
        Validate that case IDs exist in TestRail without fetching all cases.
        Returns set of valid case IDs.

        :param suite_id: Suite ID
        :param case_ids: List of case IDs to validate
        :returns: Set of case IDs that exist in TestRail
        """
        if not case_ids:
            return set()

        valid_ids = set()

        # For large numbers of case IDs, use concurrent validation
        if len(case_ids) > 50:
            from concurrent.futures import ThreadPoolExecutor, as_completed

            def check_case_exists(case_id):
                """Check if a single case exists"""
                response = self.client.send_get(f"get_case/{case_id}")
                if response.status_code == 200 and not response.error_message:
                    # Verify case belongs to correct project/suite
                    case_data = response.response_text
                    if case_data.get("suite_id") == suite_id:
                        return case_id
                return None

            # Use 10 concurrent workers to validate IDs
            with ThreadPoolExecutor(max_workers=10) as executor:
                futures = {executor.submit(check_case_exists, cid): cid for cid in case_ids}

                for future in as_completed(futures):
                    result = future.result()
                    if result is not None:
                        valid_ids.add(result)
        else:
            # For small sets, validate sequentially
            for case_id in case_ids:
                response = self.client.send_get(f"get_case/{case_id}")
                if response.status_code == 200 and not response.error_message:
                    case_data = response.response_text
                    if case_data.get("suite_id") == suite_id:
                        valid_ids.add(case_id)

        return valid_ids

    # Label management methods (delegated to LabelManager for backward compatibility)
    def add_label(self, project_id: int, title: str) -> Tuple[dict, str]:
        return self.label_manager.add_label(project_id, title)

    def update_label(self, label_id: int, project_id: int, title: str) -> Tuple[dict, str]:
        return self.label_manager.update_label(label_id, project_id, title)

    def get_label(self, label_id: int) -> Tuple[dict, str]:
        return self.label_manager.get_label(label_id)

    def get_labels(self, project_id: int, offset: int = 0, limit: int = 250) -> Tuple[dict, str]:
        return self.label_manager.get_labels(project_id, offset, limit)

    def delete_label(self, label_id: int) -> Tuple[bool, str]:
        return self.label_manager.delete_label(label_id)

    def delete_labels(self, label_ids: List[int]) -> Tuple[bool, str]:
        return self.label_manager.delete_labels(label_ids)

    def add_labels_to_cases(
        self, case_ids: List[int], title: str, project_id: int, suite_id: int = None
    ) -> Tuple[dict, str]:
        return self.label_manager.add_labels_to_cases(
            case_ids, title, project_id, suite_id, get_all_cases_callback=self.__get_all_cases
        )

    def get_cases_by_label(
        self, project_id: int, suite_id: int = None, label_ids: List[int] = None, label_title: str = None
    ) -> Tuple[List[dict], str]:
        return self.label_manager.get_cases_by_label(
            project_id, suite_id, label_ids, label_title, get_all_cases_callback=self.__get_all_cases
        )

    def add_labels_to_tests(
        self, test_ids: List[int], titles: Union[str, List[str]], project_id: int
    ) -> Tuple[dict, str]:
        return self.label_manager.add_labels_to_tests(test_ids, titles, project_id)

    def get_tests_by_label(
        self, project_id: int, label_ids: List[int] = None, label_title: str = None, run_ids: List[int] = None
    ) -> Tuple[List[dict], str]:
        return self.label_manager.get_tests_by_label(project_id, label_ids, label_title, run_ids)

    def get_test_labels(self, test_ids: List[int]) -> Tuple[List[dict], str]:
        return self.label_manager.get_test_labels(test_ids)

    # Test case reference management methods (delegated to ReferenceManager for backward compatibility)
    def add_case_references(self, case_id: int, references: List[str]) -> Tuple[bool, str]:
        return self.reference_manager.add_case_references(case_id, references)

    def update_case_references(self, case_id: int, references: List[str]) -> Tuple[bool, str]:
        return self.reference_manager.update_case_references(case_id, references)

    def delete_case_references(self, case_id: int, specific_references: List[str] = None) -> Tuple[bool, str]:
        return self.reference_manager.delete_case_references(case_id, specific_references)

    def update_case_automation_id(self, case_id: int, automation_id: str) -> Tuple[bool, str]:
        return self.case_handler.update_case_automation_id(case_id, automation_id)

    def add_bdd(self, section_id: int, feature_content: str) -> Tuple[List[int], str]:
        return self.bdd_handler.add_bdd(section_id, feature_content)

    def update_bdd(self, case_id: int, feature_content: str) -> Tuple[List[int], str]:
        """
        Update existing BDD test case with .feature file content

        Updates TestRail BDD test case from Gherkin .feature content.
        The Gherkin content is sent in the request body as plain text.

        Args:
            case_id: TestRail test case ID to update
            feature_content: Raw .feature file content (Gherkin syntax)

        Returns:
            Tuple of (case_ids, error_message)
            - case_ids: List containing the updated test case ID
            - error_message: Empty string on success, error details on failure

        API Endpoint: POST /api/v2/update_bdd/{case_id}
        Request Body: Raw Gherkin text (multipart/form-data)
        Response: Standard TestRail test case JSON with BDD custom fields
        """
        # Send Gherkin content as file upload (multipart/form-data)
        # TestRail expects the .feature file as an attachment
        self.environment.vlog(f"Updating .feature file via update_bdd/{case_id}")
        files = {"attachment": ("feature.feature", feature_content, "text/plain")}
        response = self.client.send_post(f"update_bdd/{case_id}", payload=None, files=files)

        if response.status_code == 200:
            # Response is a test case object with 'id' field
            if isinstance(response.response_text, dict):
                case_id = response.response_text.get("id")
                if case_id:
                    return [case_id], ""
                else:
                    return [], "Response missing 'id' field"
            else:
                return [], "Unexpected response format"
        else:
            error_msg = response.error_message or f"Failed to update feature file (HTTP {response.status_code})"
            return [], error_msg

    def get_bdd(self, case_id: int) -> Tuple[str, str]:
        return self.bdd_handler.get_bdd(case_id)

    def get_bdd_template_id(self, project_id: int) -> Tuple[int, str]:
        return self.bdd_handler.get_bdd_template_id(project_id)

    def find_bdd_case_by_name(
        self, feature_name: str, project_id: int, suite_id: int
    ) -> Tuple[Optional[int], Optional[str], List[int]]:
        """
        Find a BDD test case by feature name (normalized matching).

        This method is shared by CucumberParser and JunitParser for feature name matching.

        Args:
            feature_name: The feature name to search for
            project_id: TestRail project ID
            suite_id: TestRail suite ID

        Returns:
            Tuple of (case_id, error_message, duplicate_case_ids):
            - case_id: The matched case ID, or -1 if not found, or None if error/duplicates
            - error_message: Error message if operation failed, None otherwise
            - duplicate_case_ids: List of case IDs if duplicates found, empty list otherwise
        """
        # Build cache if not already cached for this project/suite
        cache_key = f"{project_id}_{suite_id}"
        if cache_key not in self._bdd_case_cache:
            error = self._build_bdd_case_cache(project_id, suite_id)
            if error:
                return None, error, []

        # Normalize the feature name for matching
        normalized_name = self._normalize_feature_name(feature_name)

        # Look up in cache
        cache = self._bdd_case_cache.get(cache_key, {})
        matching_cases = cache.get(normalized_name, [])

        if len(matching_cases) == 0:
            # Not found
            self.environment.vlog(f"Feature '{feature_name}' not found in TestRail")
            return -1, None, []
        elif len(matching_cases) == 1:
            # Single match - success
            case_id = matching_cases[0].get("id")
            self.environment.vlog(f"Feature '{feature_name}' matched to case ID: C{case_id}")
            return case_id, None, []
        else:
            # Multiple matches - duplicate error
            duplicate_ids = [case.get("id") for case in matching_cases]
            self.environment.vlog(f"Feature '{feature_name}' has {len(matching_cases)} duplicates: {duplicate_ids}")
            return None, None, duplicate_ids

    def _build_bdd_case_cache(self, project_id: int, suite_id: int) -> Optional[str]:
        """
        Build cache of BDD test cases for a project/suite.

        Args:
            project_id: TestRail project ID
            suite_id: TestRail suite ID

        Returns:
            Error message if failed, None if successful
        """
        cache_key = f"{project_id}_{suite_id}"

        self.environment.vlog(f"Building BDD case cache for project {project_id}, suite {suite_id}...")

        # Fetch all cases for this suite
        all_cases, error = self.__get_all_cases(project_id, suite_id)

        if error:
            return f"Error fetching cases for cache: {error}"

        # Resolve BDD case field name dynamically
        bdd_field_name = self.get_bdd_case_field_name()

        # Filter to BDD cases only (have BDD scenarios field with content)
        bdd_cases = [case for case in all_cases if case.get(bdd_field_name)]

        self.environment.vlog(
            f"Found {len(bdd_cases)} BDD cases out of {len(all_cases)} total cases (using field: {bdd_field_name})"
        )

        # Build normalized name -> [case, case, ...] mapping
        cache = {}
        for case in bdd_cases:
            title = case.get("title", "")
            normalized = self._normalize_feature_name(title)

            if normalized not in cache:
                cache[normalized] = []
            cache[normalized].append(case)

        self._bdd_case_cache[cache_key] = cache
        self.environment.vlog(f"Cached {len(cache)} unique feature name(s)")

        return None

    @staticmethod
    def _normalize_feature_name(name: str) -> str:
        """
        Normalize a feature name for case-insensitive, whitespace-insensitive matching.

        Converts to lowercase, strips whitespace, and removes special characters.
        Hyphens, underscores, and special chars are converted to spaces for word boundaries.

        Args:
            name: The feature name to normalize

        Returns:
            Normalized name (lowercase, special chars removed, collapsed whitespace, stripped)
        """
        import re

        # Convert to lowercase and strip
        normalized = name.lower().strip()
        # Replace hyphens, underscores, and special chars with spaces
        normalized = re.sub(r"[^a-z0-9\s]", " ", normalized)
        # Collapse multiple spaces to single space
        normalized = re.sub(r"\s+", " ", normalized)
        # Final strip
        return normalized.strip()

    def get_bdd_case_field_name(self) -> str:
        """Resolve BDD Scenarios case field name from TestRail API

        Dynamically resolves the actual field name for BDD Scenarios (type_id=13).
        This supports custom field names when users rename the default field in TestRail.

        Returns:
            Resolved system_name of BDD Scenarios field, or default name if resolution fails
        """
        # Return cached value if already resolved
        if self._bdd_case_field_name is not None:
            return self._bdd_case_field_name

        try:
            response = self.client.send_get("get_case_fields")
            if not response.error_message and response.response_text:
                for field in response.response_text:
                    if field.get("type_id") == 13:  # BDD Scenarios type
                        self._bdd_case_field_name = field.get("system_name")
                        self.environment.vlog(f"Resolved BDD case field name: {self._bdd_case_field_name}")
                        return self._bdd_case_field_name
        except Exception as e:
            self.environment.vlog(f"Error resolving BDD case field name: {e}")

        # Fallback to default name
        self._bdd_case_field_name = "custom_testrail_bdd_scenario"
        self.environment.vlog(f"Using default BDD case field name: {self._bdd_case_field_name}")
        return self._bdd_case_field_name

    def get_bdd_result_field_name(self) -> str:
        """Resolve BDD Scenario Results result field name from TestRail API

        Dynamically resolves the actual field name for BDD Scenario Results (type_id=14).
        This supports custom field names when users rename the default field in TestRail.

        Returns:
            Resolved system_name of BDD Scenario Results field, or default name if resolution fails
        """
        # Return cached value if already resolved
        if self._bdd_result_field_name is not None:
            return self._bdd_result_field_name

        try:
            response = self.client.send_get("get_result_fields")
            if not response.error_message and response.response_text:
                for field in response.response_text:
                    if field.get("type_id") == 14:  # BDD Scenario Results type
                        self._bdd_result_field_name = field.get("system_name")
                        self.environment.vlog(f"Resolved BDD result field name: {self._bdd_result_field_name}")
                        return self._bdd_result_field_name
        except Exception as e:
            self.environment.vlog(f"Error resolving BDD result field name: {e}")

        # Fallback to default name
        self._bdd_result_field_name = "custom_testrail_bdd_scenario_results"
        self.environment.vlog(f"Using default BDD result field name: {self._bdd_result_field_name}")
        return self._bdd_result_field_name

    def add_case_bdd(
        self, section_id: int, title: str, bdd_content: str, template_id: int, tags: List[str] = None
    ) -> Tuple[int, str]:
        return self.bdd_handler.add_case_bdd(section_id, title, bdd_content, template_id, tags)
