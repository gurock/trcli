import io
import pytest

from tests.helpers.load_data_from_config_helper import (
    check_parsed_data,
    check_verbose_message,
)
from trcli.cli import Environment
from tests.test_data.load_data_from_config_test_data import (
    correct_yaml_expected_result,
    correct_config_file_path,
    incorrect_config_file_path,
)
from trcli.constants import FAULT_MAPPING


@pytest.fixture(scope="function")
def load_config_resources(mocker):
    environment = Environment()
    environment.verbose = True
    stdout_mock = mocker.patch("sys.stdout", new_callable=io.StringIO)
    yield environment, stdout_mock


class TestLoadDataFromConfig:
    @pytest.mark.load_config
    def test_check_loading_data_correct_file(self, load_config_resources):
        """The purpose of this test is to check that yaml file will be parsed correctly
        when it contains correct data and proper path is provided"""
        environment, stdout_mock = load_config_resources
        params_from_config = environment.get_params_from_config_file(
            correct_config_file_path
        )
        expected_verbose_message = ""

        check_parsed_data(correct_yaml_expected_result, params_from_config)
        check_verbose_message(expected_verbose_message, stdout_mock.getvalue())

    @pytest.mark.load_config
    def test_check_loading_data_from_corrupted_file(self, load_config_resources):
        """The purpose of this test is to check that empty dictionary will be returned and
        proper verbose message would be printed when trying to parse corrupted yaml file"""
        environment, stdout_mock = load_config_resources
        params_from_config = environment.get_params_from_config_file(
            incorrect_config_file_path
        )
        expected_verbose_message = FAULT_MAPPING["yaml_file_parse_issue"].format(
            file_path=incorrect_config_file_path
        )

        check_parsed_data({}, params_from_config)
        check_verbose_message(expected_verbose_message, stdout_mock.getvalue())

    @pytest.mark.load_config
    def test_check_loading_data_from_not_existing_file(self, load_config_resources):
        """The purpose of this test is to check that empty dictionary will be returned and
        proper verbose message would be printed when trying to open non existing file"""
        environment, stdout_mock = load_config_resources
        params_from_config = environment.get_params_from_config_file(
            "not_existing_file.yaml"
        )
        expected_verbose_message = FAULT_MAPPING["file_open_issue"].format(
            file_path="not_existing_file.yaml"
        )

        check_parsed_data({}, params_from_config)
        check_verbose_message(expected_verbose_message, stdout_mock.getvalue())
