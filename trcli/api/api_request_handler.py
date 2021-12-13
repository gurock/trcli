from trcli.api_client import APIClient, APIClientResult
from trcli.cli import Environment
from trcli.data_classes.dataclass_testrail import SuitesDataclass
from trcli.data_providers.api_data_provider import ApiPostProvider


class ApiRequestHandler:
    def __init__(
        self,
        env: Environment,
        api_client: APIClient,
        suites_data: SuitesDataclass,
    ):
        self.env = env
        self.client = api_client
        self.suites_data = suites_data
        self.suites_data_provider = ApiPostProvider(env, suites_data)

    def get_project_id(self, project_name):

        response = self.client.send_get("get_projects")
        available_projects = [
            project["id"]
            for project in response.response_text["projects"]
            if project["name"] == project_name
        ]
        if len(available_projects) == 1:
            return available_projects[0]
        else:
            return -1

    def check_suite_id(self, project_id):
        suite_id = self.suites_data.id
        response = self.client.send_get(f"get_suites/{project_id}")
        available_suites = [suite["id"] for suite in response.response_text]
        return True if suite_id in available_suites else False

    def add_suite(self, project_id):
        add_suite_data = self.suites_data_provider.suite
        responses = []
        for body in add_suite_data["bodies"]:
            responses.append(self.client.send_post(f"add_suite/{project_id}", body))
        return [
            {
                "suite_id": response.response_text["id"],
                "name": response.response_text["name"],
            }
            for response in responses
        ]

    def check_missing_section_id(self, project_id):
        suite_id = self.suites_data.id
        sections = [section.suite_id for section in self.suites_data.testsuites]
        response = self.client.send_get(
            f"get_sections/{project_id}&suite_id={suite_id}"
        )

        return list(
            set(sections) - set([section["id"] for section in response.response_text])
        )

    def add_section(self, project_id):
        add_sections_data = self.suites_data_provider.sections
        responses = []
        for body in add_sections_data["bodies"]:
            responses.append(self.client.send_post(f"add_section/{project_id}", body))

        return [
            {
                "section_id": response.response_text["id"],
                "suite_id": response.response_text["suite_id"],
                "name": response.response_text["name"],
            }
            for response in responses
        ]

    def add_case(self):
        add_case_data = self.suites_data_provider.cases
        responses = []
        for body in add_case_data["bodies"]:
            responses.append(
                self.client.send_post(f"add_case/{body.pop('section_id')}", body)
            )

        return [
            {
                "case_id": response.response_text["id"],
                "section_id": response.response_text["section_id"],
                "title": response.response_text["title"],
            }
            for response in responses
        ]
