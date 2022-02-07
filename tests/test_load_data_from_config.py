import io

import pytest
from click.testing import CliRunner
from shutil import copyfile
from pathlib import Path

import trcli
from tests.helpers.load_data_from_config_helper import (
    check_parsed_data,
    check_verbose_message,
)
from trcli.cli import Environment
from tests.test_data.load_data_from_config_test_data import (
    correct_yaml_expected_result,
    correct_config_file_path,
    incorrect_config_file_path,
    correct_config_file_multiple_documents_path,
    incorrect_config_file_multiple_documents_path,
    correct_config_file_multiple_documents_path_with_custom_config_path,
    correct_config_file_path_with_custom_config_path,
    correct_config_file_loop_check_path,
    correct_config_file_with_custom_config_empty_path,
    incorrect_config_file_with_string_path,
    incorrect_config_file_with_list_path,
    incorrect_config_file_with_start_indicator_at_the_end_path,
    incorrect_config_file_with_with_empty_document,
)
from trcli.constants import FAULT_MAPPING


@pytest.fixture(scope="function")
def load_config_resources(mocker):
    environment = Environment()
    environment.verbose = True
    stdout_mock = mocker.patch("sys.stdout", new_callable=io.StringIO)
    mocker.patch("sys.argv", ["trcli"])
    yield environment, stdout_mock


class TestLoadDataFromConfig:
    @pytest.mark.load_config
    @pytest.mark.parametrize(
        "config_file",
        [correct_config_file_path, correct_config_file_multiple_documents_path],
        ids=["single_document", "multiple_documents"],
    )
    def test_check_loading_data_correct_custom_file_from_parameter(
        self, config_file, load_config_resources, mocker
    ):
        """The purpose of this test is to check that yaml file will be parsed correctly
        when it contains correct data and proper path is provided"""
        context = mocker.Mock()
        context.params = mocker.patch.dict({"config": config_file})
        environment, stdout_mock = load_config_resources
        environment.parse_config_file(context)
        expected_verbose_message = ""

        check_parsed_data(correct_yaml_expected_result, environment.params_from_config)
        check_verbose_message(expected_verbose_message, stdout_mock.getvalue())

    @pytest.mark.load_config
    @pytest.mark.parametrize(
        "config_file",
        [
            correct_config_file_path_with_custom_config_path,
            correct_config_file_multiple_documents_path_with_custom_config_path,
        ],
        ids=["single_document", "multiple_documents"],
    )
    def test_check_loading_data_correct_custom_file_from_default_config(
        self, config_file, load_config_resources, mocker
    ):
        """The purpose of this test is to check that yaml file will be parsed correctly
        when it contains correct data and proper path is provided in default config file"""
        runner = CliRunner()
        context = mocker.Mock()
        context.params = mocker.patch.dict({"config": None})
        environment, stdout_mock = load_config_resources
        environment.parse_config_file(context)
        expected_verbose_message = ""

        with runner.isolated_filesystem():
            copyfile(config_file, "config.yaml")
            copyfile(correct_config_file_path, "custom_config.yaml")
            environment.parse_config_file(context)
        check_parsed_data(correct_yaml_expected_result, environment.params_from_config)
        check_verbose_message(expected_verbose_message, stdout_mock.getvalue())

    @pytest.mark.load_config
    @pytest.mark.parametrize(
        "source_config_file, config_name",
        [
            (correct_config_file_path, "config.yaml"),
            (correct_config_file_multiple_documents_path, "config.yml"),
        ],
        ids=["single document, yaml extension", "multiple document, yml extension"],
    )
    def test_check_loading_data_correct_default_file(
        self, source_config_file, config_name, load_config_resources, mocker
    ):
        """The purpose of this test is to check that yaml file will be parsed correctly
        when it contains correct data"""
        context = mocker.Mock()
        context.params = mocker.patch.dict({"config": None})
        environment, stdout_mock = load_config_resources
        runner = CliRunner()
        with runner.isolated_filesystem():
            copyfile(correct_config_file_path, config_name)
            environment.parse_config_file(context)
            expected_verbose_message = ""
        check_parsed_data(correct_yaml_expected_result, environment.params_from_config)
        check_verbose_message(expected_verbose_message, stdout_mock.getvalue())

    @pytest.mark.load_config
    @pytest.mark.parametrize(
        "config_file",
        [
            incorrect_config_file_path,
            incorrect_config_file_multiple_documents_path,
            incorrect_config_file_with_string_path,
            incorrect_config_file_with_list_path,
            incorrect_config_file_with_start_indicator_at_the_end_path,
            incorrect_config_file_with_with_empty_document,
        ],
        ids=[
            "single_document",
            "multiple_documents",
            "single_document_just_string",
            "single_document_just_list",
            "multiple_document_with_start_indicator_at_the_end",
            "multiple_document_with_one_empty",
        ],
    )
    def test_check_loading_data_from_corrupted_custom_file(
        self, config_file, load_config_resources, mocker
    ):
        """The purpose of this test is to check that empty dictionary will be returned and
        proper verbose message would be printed when trying to parse corrupted yaml file"""
        exit_code = 1
        context = mocker.Mock()
        context.params = mocker.patch.dict({"config": config_file})
        environment, stdout_mock = load_config_resources

        expected_verbose_message = FAULT_MAPPING["yaml_file_parse_issue"].format(
            file_path=config_file
        )

        with pytest.raises(SystemExit) as exception:
            environment.parse_config_file(context)

        check_verbose_message(expected_verbose_message, stdout_mock.getvalue())
        assert (
            exception.type == SystemExit
        ), f"Expected SystemExit exception, but got {exception.type} instead."
        assert (
            exception.value.code == exit_code
        ), f"Expected exit code {exit_code}, but got {exception.value.code} instead."

    @pytest.mark.load_config
    def test_check_loading_data_from_not_existing_file(
        self, load_config_resources, mocker
    ):
        """The purpose of this test is to check that empty dictionary will be returned and
        proper verbose message would be printed when trying to open non existing file"""
        context = mocker.Mock()
        exit_code = 1
        context.params = mocker.patch.dict({"config": "not_existing_file.yaml"})
        environment, stdout_mock = load_config_resources

        expected_verbose_message = FAULT_MAPPING["file_open_issue"].format(
            file_path="not_existing_file.yaml"
        )

        with pytest.raises(SystemExit) as exception:
            environment.parse_config_file(context)

        check_verbose_message(expected_verbose_message, stdout_mock.getvalue())
        assert (
            exception.type == SystemExit
        ), f"Expected SystemExit exception, but got {exception.type} instead."
        assert (
            exception.value.code == exit_code
        ), f"Expected exit code {exit_code}, but got {exception.value.code} instead."

    @pytest.mark.load_config
    def test_config_files_with_cilcular_dependencies(
        self, load_config_resources, mocker
    ):
        """The purpose of this test is to check that trcli will not fall into infinite
        loop then custom and default files contains links to each other"""
        runner = CliRunner()
        context = mocker.Mock()
        context.params = mocker.patch.dict({"config": None})
        environment, stdout_mock = load_config_resources
        environment.parse_config_file(context)
        yaml_expected_results = correct_yaml_expected_result
        yaml_expected_results["config"] = "config.yaml"
        expected_verbose_message = ""

        with runner.isolated_filesystem():
            copyfile(correct_config_file_path_with_custom_config_path, "config.yaml")
            copyfile(correct_config_file_loop_check_path, "custom_config.yaml")
            environment.parse_config_file(context)
        check_parsed_data(yaml_expected_results, environment.params_from_config)
        check_verbose_message(expected_verbose_message, stdout_mock.getvalue())

    @pytest.mark.load_config
    def test_loading_from_default_config_with_empty_custom_config(
        self, load_config_resources, mocker
    ):
        """The purpose of this test is to check that parameters will be correctly parsed when default
        config file contains empty custom config entry (config: )"""
        runner = CliRunner()
        context = mocker.Mock()
        context.params = mocker.patch.dict({"config": None})
        environment, stdout_mock = load_config_resources
        environment.parse_config_file(context)
        yaml_expected_results = correct_yaml_expected_result
        yaml_expected_results["config"] = None
        expected_verbose_message = ""

        with runner.isolated_filesystem():
            copyfile(correct_config_file_with_custom_config_empty_path, "config.yaml")
            environment.parse_config_file(context)
        check_parsed_data(yaml_expected_results, environment.params_from_config)
        check_verbose_message(expected_verbose_message, stdout_mock.getvalue())
