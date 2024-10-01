import json
from pathlib import Path

import requests
from beartype.typing import Union, Callable, Dict, List
from time import sleep
from base64 import b64encode

import urllib3
from urllib.parse import urlparse
from requests.auth import HTTPBasicAuth
from json import JSONDecodeError
from requests.exceptions import RequestException, Timeout, ConnectionError, ProxyError, SSLError, InvalidProxyURL
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
    response_text: Union[Dict, str, List]
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
        proxy: str = None, #added proxy params
        proxy_user: str = None,
        noproxy: str = None, 
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
        self.proxy = proxy
        self.proxy_user = proxy_user
        self.noproxy = noproxy.split(',') if noproxy else [] 
        
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

    def send_post(self, uri: str, payload: dict = None, files: Dict[str, Path] = None) -> APIClientResult:
        """
        Sends POST request to host specified by host_name.
        Handles retries taking into consideration retries parameter. Retry will occur when one of the following happens:
            * got status code 429 in a response from host
            * timeout occurred
            * connection error occurred
        """
        return self.__send_request("POST", uri, payload, files)

    def __send_request(self, method: str, uri: str, payload: dict, files: Dict[str, Path] = None) -> APIClientResult:
        status_code = -1
        response_text = ""
        error_message = ""
        url = self.__url + uri
        password = self.__get_password()
        auth = HTTPBasicAuth(username=self.username, password=password)
        headers = {"User-Agent": self.USER_AGENT}
        headers.update(self.__get_proxy_headers())
        if files is None:
            headers["Content-Type"] = "application/json"
        verbose_log_message = ""
        proxies = self._get_proxies_for_request(url)
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
                        proxies=proxies
                    )
                else:
                    response = requests.get(
                        url=url, 
                        auth=auth, 
                        json=payload, 
                        timeout=self.timeout, 
                        verify=self.verify, 
                        headers=headers,
                        proxies=proxies
                    )
            except InvalidProxyURL:
                error_message = FAULT_MAPPING["proxy_invalid_configuration"]
                self.verbose_logging_function(verbose_log_message)
                break
            except ProxyError:
                error_message = FAULT_MAPPING["proxy_connection_error"]
                self.verbose_logging_function(verbose_log_message)
                break
            except SSLError:
                error_message = FAULT_MAPPING["ssl_error_on_proxy"]
                self.verbose_logging_function(verbose_log_message)
                break
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
                    # workaround for buggy legacy TR server version response
                    if response.content.startswith(b"USER AUTHENTICATION SUCCESSFUL!\n"):
                        response_text = response.content.replace(b"USER AUTHENTICATION SUCCESSFUL!\n", b"", 1)
                        response_text = json.loads(response_text)
                    else:
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

    def __get_proxy_headers(self) -> Dict[str, str]:
        """
        Returns headers for proxy authentication using Basic Authentication if proxy_user is provided.
        """
        headers = {}
        if self.proxy_user:
            user_pass_encoded = b64encode(self.proxy_user.encode('utf-8')).decode('utf-8')

            # Add Proxy-Authorization header
            headers["Proxy-Authorization"] = f"Basic {user_pass_encoded}"
            print(f"Proxy authentication header added: {headers['Proxy-Authorization']}")

        return headers

    def _get_proxies_for_request(self, url: str) -> Dict[str, str]:
        """
        Returns the appropriate proxy dictionary for a given request URL.
        Will return None if the URL matches a proxy bypass host.
        """
        parsed_url = urlparse(url)
        scheme = parsed_url.scheme  # The scheme of the target URL (http or https)
        host = parsed_url.hostname

        # If proxy or noproxy is None, return None, and requests will not use nor bypass a proxy server
        if self.proxy is None:
            return None

        # Bypass the proxy if the host is in the noproxy list
        if self.noproxy:
        # Ensure noproxy is a list or tuple
            if isinstance(self.noproxy, str):
                self.noproxy = self.noproxy.split(',')
            if host in self.noproxy:
                print(f"Bypassing proxy for host: {host}")
                return None

        # Ensure proxy has a scheme (either http or https)
        if self.proxy and not self.proxy.startswith("http://") and not self.proxy.startswith("https://"):
            self.proxy = "http://" + self.proxy  # Default to http if scheme is missing

        #print(f"Parsed URL: {url}, Proxy: {self.proxy} , NoProxy: {self.noproxy}")

        # Define the proxy dictionary
        proxy_dict = {}
        if self.proxy:
            # Use HTTP proxy for both HTTP and HTTPS traffic
            if self.proxy.startswith("http://"):
                proxy_dict = {
                    "http": self.proxy,  # Use HTTP proxy for HTTP traffic
                    "https": self.proxy  # Also use HTTP proxy for HTTPS traffic
                }
            else:
                # If the proxy is HTTPS, route accordingly
                proxy_dict = {
                    scheme: self.proxy  # Match the proxy scheme with the target URL scheme
                }

            #print(f"Using proxy: {proxy_dict}")
            return proxy_dict

        return None

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
