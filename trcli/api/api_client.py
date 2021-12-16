import requests
from typing import Union
from time import sleep
from requests.auth import HTTPBasicAuth
from json import JSONDecodeError
from requests.exceptions import RequestException, Timeout, ConnectionError
from trcli.constants import FAULT_MAPPING
from dataclasses import dataclass


@dataclass
class APIClientResult:
    """
    status_code - status code returned by GET/POST request or -1 if error occurred during request handling
    response_text - json object or bare text string is response could not be parsed
    error_message - custom error message when -1 was returned in status_code"""

    status_code: int
    response_text: Union[dict, str]
    error_message: str


class APIClient:
    """
    Class to be used for basic communication over API.
    """

    SUFFIX_API_VERSION = "index.php?/api/v2/"
    RETRY_ON = [429, 500]

    def __init__(self, host_name: str, retries: int = 3, timeout: int = 30):
        self.username = ""
        self.password = ""
        self.api_key = ""
        self.retries = retries
        self.timeout = timeout
        if not host_name.endswith("/"):
            host_name = host_name + "/"
        self.__url = host_name + self.SUFFIX_API_VERSION

    def send_get(self, uri: str) -> APIClientResult:
        """
        Sends GET request to host specified by host_name.
        Handles retries taking into consideration retries parameter. Retry will occur when one of the following happens:
            * got status code 429 in a response from host
            * timeout occurred
            * connection error occurred
        """
        return self.__send_request("GET", uri, None)

    def send_post(self, uri: str, payload: dict) -> APIClientResult:
        """
        Sends POST request to host specified by host_name.
        Handles retries taking into consideration retries parameter. Retry will occur when one of the following happens:
            * got status code 429 in a response from host
            * timeout occurred
            * connection error occurred
        """
        return self.__send_request("POST", uri, payload)

    def __send_request(self, method: str, uri: str, payload: dict) -> APIClientResult:
        status_code = -1
        response_text = ""
        error_message = ""
        url = self.__url + uri
        password = self.__get_password()
        auth = HTTPBasicAuth(username=self.username, password=password)
        headers = {"Content-Type": "application/json"}

        for i in range(self.retries + 1):
            error_message = ""
            try:
                if method == "POST":
                    response = requests.post(
                        url=url, auth=auth, json=payload, timeout=self.timeout, headers=headers
                    )
                else:
                    response = requests.get(
                        url=url, auth=auth, json=payload, timeout=self.timeout
                    )
            except Timeout:
                error_message = FAULT_MAPPING["no_response_from_host"]
                continue
            except ConnectionError:
                error_message = FAULT_MAPPING["connection_error"]
                continue
            except RequestException:
                error_message = FAULT_MAPPING["host_issues"]
                break
            else:
                status_code = response.status_code
                if status_code == 429:
                    retry_time = float(response.headers["Retry-After"])
                    sleep(retry_time)
                try:
                    response_text = response.json()
                    error_message = response_text.get("error", "")
                except (JSONDecodeError, ValueError):
                    response_text = str(response.content)
                except AttributeError:
                    error_message = ""

            if status_code not in self.RETRY_ON:
                break

        return APIClientResult(status_code, response_text, error_message)

    def __get_password(self) -> str:
        """Based on what is set, choose to use api_key or password as authentication method"""
        if self.api_key:
            password = self.api_key
        else:
            password = self.password
        return password
