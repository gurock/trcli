from pathlib import Path

import pytest
import yaml

from click.testing import CliRunner

from trcli.cli import cli as root_cli
from trcli.commands.cmd_init import cli


@pytest.fixture
def runner():
    return CliRunner()


class TestInitCommand:
    @pytest.mark.cli
    def test_init_creates_config_file_interactively(self, runner, mocker):
        mocker.patch("trcli.cli.check_for_updates", return_value=None)
        mocker.patch("trcli.commands.cmd_init._resolve_project_context", return_value=(None, None))

        user_input = "\n".join(
            [
                "https://example.testrail.io",
                "Demo Project",
                "",
                "user@example.com",
                "1",
                "secret-key",
                "secret-key",
                "n",
                "n",
            ]
        ) + "\n"

        with runner.isolated_filesystem():
            result = runner.invoke(root_cli, ["init"], input=user_input)

            assert result.exit_code == 0
            assert "TRCLI initialization" in result.output
            assert "Next step: run `trcli status` to verify the saved configuration." in result.output

            config_path = Path("config.yml")
            assert config_path.exists()

            config_data = yaml.safe_load(config_path.read_text(encoding="utf-8"))
            assert config_data == {
                "host": "https://example.testrail.io",
                "project": "Demo Project",
                "username": "user@example.com",
                "key": "secret-key",
            }

    @pytest.mark.cli
    def test_init_can_store_advanced_settings_and_suite_id(self, runner, mocker):
        mocker.patch("trcli.cli.check_for_updates", return_value=None)

        class FakeProjectData:
            project_id = 12
            suite_mode = 1
            error_message = ""

        class FakeApiHandler:
            def get_suite_ids(self, project_id):
                return ([55], "")

        mocker.patch(
            "trcli.commands.cmd_init._resolve_project_context",
            return_value=(FakeProjectData(), FakeApiHandler()),
        )

        with runner.isolated_filesystem():
            result = runner.invoke(
                root_cli,
                ["init"],
                input="\n".join(
                    [
                        "https://example.testrail.io",
                        "Demo Project",
                        "",
                        "user@example.com",
                        "1",
                        "secret-key",
                        "secret-key",
                        "y",
                        "http://proxy.example.com:8080",
                        "proxy-user:proxy-pass",
                        "localhost,127.0.0.1",
                        "y",
                        "90",
                        "75",
                        "y",
                    ]
                )
                + "\n",
            )

            assert result.exit_code == 0
            config_data = yaml.safe_load(Path("config.yml").read_text(encoding="utf-8"))
            assert config_data == {
                "host": "https://example.testrail.io",
                "project": "Demo Project",
                "username": "user@example.com",
                "key": "secret-key",
                "project_id": 12,
                "suite_id": 55,
                "proxy": "http://proxy.example.com:8080",
                "proxy_user": "proxy-user:proxy-pass",
                "noproxy": "localhost,127.0.0.1",
                "insecure": True,
                "timeout": 90.0,
                "batch_size": 75,
            }

    @pytest.mark.cli
    def test_init_validates_suite_id_when_project_context_is_available(self, runner, mocker):
        mocker.patch("trcli.cli.check_for_updates", return_value=None)

        class FakeProjectData:
            project_id = 12
            suite_mode = 3
            error_message = ""

        class FakeApiHandler:
            def __init__(self):
                self.suites_data_from_provider = type("SuiteData", (), {"suite_id": None})()

            def check_suite_id(self, project_id):
                return (self.suites_data_from_provider.suite_id == 101, "Suite with ID '999' does not exist in TestRail.")

        mocker.patch(
            "trcli.commands.cmd_init._resolve_project_context",
            return_value=(FakeProjectData(), FakeApiHandler()),
        )

        with runner.isolated_filesystem():
            result = runner.invoke(
                cli,
                [],
                input="\n".join(
                    [
                        "https://example.testrail.io",
                        "Demo Project",
                        "",
                        "user@example.com",
                        "1",
                        "secret-key",
                        "secret-key",
                        "n",
                        "y",
                        "999",
                        "101",
                    ]
                )
                + "\n",
            )

            assert result.exit_code == 0
            config_data = yaml.safe_load(Path("config.yml").read_text(encoding="utf-8"))
            assert config_data["suite_id"] == 101

    @pytest.mark.cli
    def test_init_prompts_before_overwriting_existing_file(self, runner):
        with runner.isolated_filesystem():
            Path("config.yml").write_text("host: old\n", encoding="utf-8")

            result = runner.invoke(
                cli,
                [],
                input="n\n",
                catch_exceptions=False,
            )

            assert result.exit_code == 1
            assert "Initialization cancelled. Existing config was left unchanged." in result.output
            assert Path("config.yml").read_text(encoding="utf-8") == "host: old\n"

    @pytest.mark.cli
    def test_init_help_uses_styled_command(self, runner):
        result = runner.invoke(cli, ["--help"])

        assert result.exit_code == 0
        assert "Usage:" in result.output
        assert "--output" in result.output
