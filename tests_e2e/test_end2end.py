import os
import subprocess

import pytest


def _run_cmd(multiline_cmd: str):
    lines_list = []
    for line in multiline_cmd.splitlines():
        line = line.strip()
        if not line:
            continue
        if line.endswith("\\"):
            lines_list.append(line.rstrip("\\").strip())
        else:
            lines_list.append(f"{line} &&")
    lines_list.append("echo DONE")
    single_line_cmd = " ".join(lines_list)
    print("")
    print(f"Executing: {single_line_cmd}")
    process = subprocess.Popen(single_line_cmd, shell=True, stdout=subprocess.PIPE)
    with process.stdout:
        output = ""
        for line in iter(process.stdout.readline, b''):
            output += line.decode()
        print(output)
    process.wait()
    assert process.returncode == 0, f"Error executing shell command. \n{output}"
    return output


def _assert_contains(text: str, expected_text_list: list):
    for expected in expected_text_list:
        assert expected in text, f"Expected to find {expected} in: \n{text}"


class TestsEndToEnd:

    # TestRail 101 instance has the required configuration for this test run
    TR_INSTANCE = "https://testrail101.testrail.io/"
    # Uncomment and enter your credentials below in order to execute the tests locally
    # os.environ.setdefault("TR_CLI_USERNAME", "")
    # os.environ.setdefault("TR_CLI_PASSWORD", "")

    @pytest.fixture(autouse=True, scope="module")
    def install_trcli(self):
        _run_cmd("cd .. && pip install .")

    def test_cli_robot_report_RF50(self):
        output = _run_cmd(f"""
trcli -y \\
  -h {self.TR_INSTANCE} \\
  --project "SA - (DO NOT DELETE) TRCLI-E2E-Tests" \\
  parse_robot \\
  --title "[CLI-E2E-Tests] ROBOT FRAMEWORK PARSER" \\
  -f "reports_robot/simple_report_RF50.xml"
        """)
        _assert_contains(
            output,
            [
                "Processed 3 test cases in 2 sections.",
                f"Creating test run. Test run: {self.TR_INSTANCE}index.php?/runs/view",
                "Uploading 1 attachments for 1 test results.",
                "Submitted 3 test results in"
            ]
        )

    def test_cli_robot_report_RF70(self):
        output = _run_cmd(f"""
trcli -y \\
  -h {self.TR_INSTANCE} \\
  --project "SA - (DO NOT DELETE) TRCLI-E2E-Tests" \\
  parse_robot \\
  --title "[CLI-E2E-Tests] ROBOT FRAMEWORK PARSER" \\
  -f "reports_robot/simple_report_RF50.xml"
        """)
        _assert_contains(
            output,
            [
                "Processed 3 test cases in 2 sections.",
                f"Creating test run. Test run: {self.TR_INSTANCE}index.php?/runs/view",
                "Uploading 1 attachments for 1 test results.",
                "Submitted 3 test results in"
            ]
        )

    def test_cli_plan_id(self):
        output = _run_cmd(f"""
trcli -y \\
  -h {self.TR_INSTANCE} \\
  --project "SA - (DO NOT DELETE) TRCLI-E2E-Tests" \\
  parse_junit \\
  --plan-id 1578 \\
  --title "[CLI-E2E-Tests] With Plan ID" \\
  -f "reports_junit/generic_ids_auto.xml"
        """)
        _assert_contains(
            output,
            [
                "Processed 3 test cases in section [GENERIC-IDS-AUTO]",
                f"Creating test run. Test run: {self.TR_INSTANCE}index.php?/runs/view",
                "Uploading 1 attachments for 1 test results.",
                "Submitted 6 test results in"
            ]
        )

    def test_cli_plan_id_and_config_id(self):
        output = _run_cmd(f"""
trcli -y \\
  -h {self.TR_INSTANCE} \\
  --project "SA - (DO NOT DELETE) TRCLI-E2E-Tests" \\
  parse_junit \\
  --plan-id 1578 \\
  --config-ids 142,143 \\
  --title "[CLI-E2E-Tests] With Plan ID and Config ID" \\
  -f "reports_junit/generic_ids_auto.xml"
        """)
        _assert_contains(
            output,
            [
                "Processed 3 test cases in section [GENERIC-IDS-AUTO]",
                f"Creating test run. Test run: {self.TR_INSTANCE}index.php?/runs/view",
                "Uploading 1 attachments for 1 test results.",
                "Submitted 6 test results in"
            ]
        )

    def test_cli_update_run_in_plan(self):
        output = _run_cmd(f"""
trcli -y \\
  -h {self.TR_INSTANCE} \\
  --project "SA - (DO NOT DELETE) TRCLI-E2E-Tests" \\
  parse_junit \\
  --run-id 1550 \\
  --title "[CLI-E2E-Tests] Update Run in Plan" \\
  -f "reports_junit/generic_ids_auto.xml"
        """)
        _assert_contains(
            output,
            [
                "Processed 3 test cases in section [GENERIC-IDS-AUTO]",
                f"Updating test run. Test run: {self.TR_INSTANCE}index.php?/runs/view",
                "Uploading 1 attachments for 1 test results.",
                "Submitted 6 test results in"
            ]
        )
    
    def test_cli_update_run_in_plan_with_configs(self):
        output = _run_cmd(f"""
trcli -y \\
  -h {self.TR_INSTANCE} \\
  --project "SA - (DO NOT DELETE) TRCLI-E2E-Tests" \\
  parse_junit \\
  --run-id 1551 \\
  --title "[CLI-E2E-Tests] Update Run in Plan with Configs" \\
  -f "reports_junit/generic_ids_auto.xml"
        """)
        _assert_contains(
            output,
            [
                "Processed 3 test cases in section [GENERIC-IDS-AUTO]",
                f"Updating test run. Test run: {self.TR_INSTANCE}index.php?/runs/view",
                "Uploading 1 attachments for 1 test results.",
                "Submitted 6 test results in"
            ]
        )

    def test_cli_matchers_auto(self):
        output = _run_cmd(f"""
trcli -y \\
  -h {self.TR_INSTANCE} \\
  --project "SA - (DO NOT DELETE) TRCLI-E2E-Tests" \\
  parse_junit \\
  --title "[CLI-E2E-Tests] Matcher: AUTO" \\
  -f "reports_junit/generic_ids_auto.xml"
        """)
        _assert_contains(
            output,
            [
                "Processed 3 test cases in section [GENERIC-IDS-AUTO]",
                f"Creating test run. Test run: {self.TR_INSTANCE}index.php?/runs/view",
                "Uploading 1 attachments for 1 test results.",
                "Submitted 6 test results in"
            ]
        )

    def test_cli_matchers_auto_update_run(self):
        output = _run_cmd(f"""
trcli -y \\
  -h {self.TR_INSTANCE} \\
  --project "SA - (DO NOT DELETE) TRCLI-E2E-Tests" \\
  parse_junit \\
  --title "(DO NOT DELETE) [CLI-E2E-Tests] Update Run" \\
  --run-id "1568" \\
  --milestone-id "107" \\
  -f "reports_junit/generic_ids_auto_plus_one.xml"
        """)
        _assert_contains(
            output,
            [
                "Processed 3 test cases in section [GENERIC-IDS-AUTO]",
                f"Updating test run. Test run: {self.TR_INSTANCE}index.php?/runs/view",
                "Uploading 1 attachments for 1 test results.",
                "Submitted 6 test results in"
            ]
        )

    def test_cli_matchers_auto_multiple_files(self):
        output = _run_cmd(f"""
trcli -y \\
  -h {self.TR_INSTANCE} \\
  --project "SA - (DO NOT DELETE) TRCLI-E2E-Tests" \\
  parse_junit \\
  --title "[CLI-E2E-Tests] Matcher: AUTO with multiple files" \\
  -f "reports_junit/junit_multiple_parts_*"
        """)
        _assert_contains(
            output,
            [
                "Processed 3 test cases in section [MULTIPART-REPORT-2]",
                f"Creating test run. Test run: {self.TR_INSTANCE}index.php?/runs/view",
                "No attachments found to upload.",
                "Submitted 4 test results in"
            ]
        )
    
    def test_cli_matchers_name(self):
        output = _run_cmd(f"""
trcli -n \\
  -h {self.TR_INSTANCE} \\
  --project "SA - (DO NOT DELETE) TRCLI-E2E-Tests" \\
  parse_junit \\
  --title "[CLI-E2E-Tests] Matcher: NAME" \\
  --case-matcher "NAME" \\
  -f "reports_junit/generic_ids_name.xml"
        """)
        _assert_contains(
            output,
            [
                "Processed 3 test cases in section [GENERIC-IDS-NAME]",
                "Found 3 test cases without case ID in the report file.",
                f"Creating test run. Test run: {self.TR_INSTANCE}index.php?/runs/view",
                "Uploading 1 attachments for 1 test results.",
                "Submitted 3 test results in"
            ]
        )
    
    def test_cli_matchers_property(self):
        output = _run_cmd(f"""
trcli -n \\
  -h {self.TR_INSTANCE} \\
  --project "SA - (DO NOT DELETE) TRCLI-E2E-Tests" \\
  parse_junit \\
  --title "[CLI-E2E-Tests] Matcher: PROPERTY" \\
  --case-matcher "PROPERTY" \\
  -f "reports_junit/generic_ids_property.xml"
        """)
        _assert_contains(
            output,
            [
                "Processed 3 test cases in section [GENERIC-IDS-PROP]",
                "Found 3 test cases without case ID in the report file.",
                f"Creating test run. Test run: {self.TR_INSTANCE}index.php?/runs/view",
                "Uploading 1 attachments for 1 test results.",
                "Submitted 3 test results in"
            ]
        )
    
    def test_cli_attachments(self):
        output = _run_cmd(f"""
trcli -y \\
  -h {self.TR_INSTANCE} \\
  --project "SA - (DO NOT DELETE) TRCLI-E2E-Tests" \\
  parse_junit \\
  --title "[CLI-E2E-Tests] Attachments test" \\
  -f "reports_junit/attachments.xml"
        """)
        _assert_contains(
            output,
            [
                "Processed 3 test cases in section [ATTACHMENTS]",
                f"Creating test run. Test run: {self.TR_INSTANCE}index.php?/runs/view",
                "Uploading 4 attachments for 2 test results.",
                "Submitted 3 test results in"
            ]
        )
    def test_cli_multisuite_with_suite_id(self):
        output = _run_cmd(f"""
trcli -y \\
  -h {self.TR_INSTANCE} \\
  --project "SA - (DO NOT DELETE) TRCLI-E2E-Tests Multisuite" \\
  parse_junit \\
  --title "[CLI-E2E-Tests] Multisuite with suite id" \\
  --suite-id 128 \\
  -f "reports_junit/duplicate-names.xml"
        """)
        _assert_contains(
            output,
            [
                "Processed 1 test cases in section [DUPLICATES] NewTest",
                "Processed 3 test cases in section [DUPLICATES] Professional",
                "Processed 3 test cases in section [DUPLICATES] Enterprise",
                "Processed 3 test cases in section [DUPLICATES] Basic",
                f"Creating test run. Test run: {self.TR_INSTANCE}index.php?/runs/view",
                "No attachments found to upload.",
                "Submitted 10 test results in"
            ]
        )

    def test_cli_multisuite_with_suite_name(self):
        output = _run_cmd(f"""
trcli -y \\
  -h {self.TR_INSTANCE} \\
  --project "SA - (DO NOT DELETE) TRCLI-E2E-Tests Multisuite" \\
  parse_junit \\
  --suite-name "My suite" \\
  --title "[CLI-E2E-Tests] Multisuite without suite id" \\
  -f "reports_junit/duplicate-names.xml"
        """)
        _assert_contains(
            output,
            [
                "Processed 1 test cases in section [DUPLICATES] NewTest",
                "Processed 3 test cases in section [DUPLICATES] Professional",
                "Processed 3 test cases in section [DUPLICATES] Enterprise",
                "Processed 3 test cases in section [DUPLICATES] Basic",
                f"Creating test run. Test run: {self.TR_INSTANCE}index.php?/runs/view",
                "No attachments found to upload.",
                "Submitted 10 test results in"
            ]
        )

    def test_cli_multisuite_without_suite_id(self):
        output = _run_cmd(f"""
trcli -y \\
  -h {self.TR_INSTANCE} \\
  --project "SA - (DO NOT DELETE) TRCLI-E2E-Tests Multisuite" \\
  parse_junit \\
  --title "[CLI-E2E-Tests] Multisuite without suite id" \\
  -f "reports_junit/duplicate-names.xml"
        """)
        _assert_contains(
            output,
            [
                "Processed 1 test cases in section [DUPLICATES] NewTest",
                "Processed 3 test cases in section [DUPLICATES] Professional",
                "Processed 3 test cases in section [DUPLICATES] Enterprise",
                "Processed 3 test cases in section [DUPLICATES] Basic",
                f"Creating test run. Test run: {self.TR_INSTANCE}index.php?/runs/view",
                "No attachments found to upload.",
                "Submitted 10 test results in"
            ]
        )
    
    def test_cli_saucelabs(self):
        output = _run_cmd(f"""
trcli -y \\
  -h {self.TR_INSTANCE} \\
  --project "SA - (DO NOT DELETE) TRCLI-E2E-Tests" \\
  parse_junit \\
  --title "[CLI-E2E-Tests] saucectl parser" \\
  --special-parser "saucectl" \\
  -f "reports_junit/saucelabs.xml"
        """)
        _assert_contains(
            output,
            [
                "Found 2 SauceLabs suites.",
                "Processing JUnit suite - Firefox",
                "Processing JUnit suite - Chrome",
                "Processed 1 test cases in section [SAUCELABS]",
                f"Creating test run. Test run: {self.TR_INSTANCE}index.php?/runs/view"
            ]
        )
    
    def test_cli_openapi(self):
        output = _run_cmd(f"""
trcli -y \\
  -h {self.TR_INSTANCE} \\
  --project "SA - (DO NOT DELETE) TRCLI-E2E-Tests" \\
  parse_openapi \\
  -f "openapi_specs/openapi.yml"
        """)
        _assert_contains(
            output,
            [
                "Processed 22 test cases based on possible responses.",
                "Submitted 22 test cases"
            ]
        )

    def test_cli_add_run(self):
        output = _run_cmd(f"""
trcli -y \\
  -h {self.TR_INSTANCE} \\
  --project "SA - (DO NOT DELETE) TRCLI-E2E-Tests" \\
  add_run \\
  --title "[CLI-E2E-Tests] ADD RUN TEST: Create run_config.yml" \\
  -f "run_config.yml"
        """)
        _assert_contains(
            output,
            [
                "Creating test run.",
                f"Test run: {self.TR_INSTANCE}index.php?/runs/view",
                "title: [CLI-E2E-Tests] ADD RUN TEST: Create run_config.yml",
                "Writing test run data to file (run_config.yml). Done."
            ]
        )

    def test_cli_add_run_upload_results(self):
        output = _run_cmd(f"""
trcli -y \\
  -h {self.TR_INSTANCE} \\
  --project "SA - (DO NOT DELETE) TRCLI-E2E-Tests" \\
  -c run_config.yml \\
  parse_junit \\
  -f "reports_junit/generic_ids_auto.xml"
        """)
        _assert_contains(
            output,
            [
                f"Updating test run. Test run: {self.TR_INSTANCE}index.php?/runs/view",
                "Uploading 1 attachments for 1 test results.",
                "Submitted 6 test results"
            ]
        )

    def bug_test_cli_robot_description_bug(self):
        output = _run_cmd(f"""
trcli -y \\
  -h {self.TR_INSTANCE} \\
  --project "SA - (DO NOT DELETE) TRCLI-E2E-Tests" \\
  parse_robot \\
  --title "[CLI-E2E-Tests] RUN DESCRIPTION BUG" \\
  -f "reports_robot/simple_report_RF50.xml" \\
  --run-id 2332
        """)
        _assert_contains(
            output,
            [
                "Processed 3 test cases in 2 sections.",
                "Uploading 1 attachments for 1 test results.",
                "Submitted 3 test results in"
            ]
        )
    