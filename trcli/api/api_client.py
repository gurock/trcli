from pathlib import Path

import requests
from typing import Union, Callable
from time import sleep

import urllib3
from requests.auth import HTTPBasicAuth
from json import JSONDecodeError
from requests.exceptions import RequestException, Timeout, ConnectionError
from trcli.constants import FAULT_MAPPING
from trcli.settings import DEFAULT_API_CALL_TIMEOUT, DEFAULT_API_CALL_RETRIES
from dataclasses import dataclass


@dataclass
class APIClientResult:
    """
    status_code - status code returned by GET/POST request or -1 if error occurred during request handling
    response_text - json object or bare text string is response could not be parsed
    error_message - custom error message when -1 was returned in status_code"""

    status_code: int
    response_text: Union[dict, str, list]
    error_message: str


class APIClient:
    """
    Class to be used for basic communication over API.
    """

    PREFIX = "index.php?"
    VERSION = "/api/v2/"
    SUFFIX_API_V2_VERSION = f"{PREFIX}{VERSION}"
    RETRY_ON = [429, 500, 502]
    USER_AGENT = "TRCLI"

    def __init__(
        self,
        host_name: str,
        verbose_logging_function: Callable = print,
        logging_function: Callable = print,
        retries: int = DEFAULT_API_CALL_RETRIES,
        timeout: int = DEFAULT_API_CALL_TIMEOUT,
        verify: bool = True,
    ):
        self.username = ""
        self.password = ""
        self.api_key = ""
        self.timeout = None
        self.retries = retries
        self.verify = verify
        self.verbose_logging_function = verbose_logging_function
        self.logging_function = logging_function
        self.__validate_and_set_timeout(timeout)
        if not host_name.endswith("/"):
            host_name = host_name + "/"
        self.__url = host_name + self.SUFFIX_API_V2_VERSION
        if not verify:
            urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

    def send_get(self, uri: str) -> APIClientResult:
        """
        Sends GET request to host specified by host_name.
        Handles retries taking into consideration retries parameter. Retry will occur when one of the following happens:
            * got status code 429 in a response from host
            * timeout occurred
            * connection error occurred
        """
        return self.__send_request("GET", uri, None)

    def send_post(self, uri: str, payload: dict = None, files: {str: Path} = None) -> APIClientResult:
        """
        Sends POST request to host specified by host_name.
        Handles retries taking into consideration retries parameter. Retry will occur when one of the following happens:
            * got status code 429 in a response from host
            * timeout occurred
            * connection error occurred
        """
        return self.__send_request("POST", uri, payload, files)

    def __send_request(self, method: str, uri: str, payload: dict, files: {str: Path} = None) -> APIClientResult:
        status_code = -1
        response_text = ""
        error_message = ""
        url = self.__url + uri
        password = self.__get_password()
        auth = HTTPBasicAuth(username=self.username, password=password)
        headers = {"User-Agent": self.USER_AGENT}
        if files is None:
            headers["Content-Type"] = "application/json"
        verbose_log_message = ""
        for i in range(self.retries + 1):
            error_message = ""
            try:
                verbose_log_message = APIClient.format_request_for_vlog(
                    method=method, url=url, payload=payload
                )
                if method == "POST":
                    response = requests.post(
                        url=url,
                        auth=auth,
                        json=payload,
                        timeout=self.timeout,
                        headers=headers,
                        verify=self.verify,
                        files=files,
                    )
                else:
                    response = requests.get(
                        url=url, auth=auth, json=payload, timeout=self.timeout, verify=self.verify,
                    )
            except Timeout:
                error_message = FAULT_MAPPING["no_response_from_host"]
                self.verbose_logging_function(verbose_log_message)
                continue
            except ConnectionError:
                error_message = FAULT_MAPPING["connection_error"]
                self.verbose_logging_function(verbose_log_message)
                continue
            except RequestException as e:
                error_message = FAULT_MAPPING[
                    "unexpected_error_during_request_send"
                ].format(request=e.request)
                self.verbose_logging_function(verbose_log_message)
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
                    error_message = response.content
                except AttributeError:
                    error_message = ""
                verbose_log_message = (
                    verbose_log_message
                    + APIClient.format_response_for_vlog(
                        response.status_code, response_text
                    )
                )
            if verbose_log_message:
                self.verbose_logging_function(verbose_log_message)

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

    def __validate_and_set_timeout(self, timeout):
        try:
            self.timeout = float(timeout)
        except ValueError:
            self.logging_function(
                f"Warning. Could not convert provided 'timeout' to float. "
                f"Please make sure that timeout format is correct. Setting to default: "
                f"{DEFAULT_API_CALL_TIMEOUT}"
            )
            self.timeout = DEFAULT_API_CALL_TIMEOUT

    @staticmethod
    def format_request_for_vlog(method: str, url: str, payload: dict):
        return (
            f"\n**** API Call\n"
            f"method: {method}\n"
            f"url: {url}\n" + (f"payload: {payload}\n" if payload else "")
        )

    @staticmethod
    def format_response_for_vlog(status_code, body):
        return f"response status code: {status_code}\nresponse body: {body}\n****"
