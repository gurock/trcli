import os
import subprocess

import pytest


def _has_testrail_credentials():
    """Check if TestRail credentials are available in environment variables"""
    return bool(os.environ.get("TR_CLI_USERNAME") and os.environ.get("TR_CLI_PASSWORD"))


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


def _run_cmd_allow_failure(multiline_cmd: str):
    """Run command and return output and return code (allows non-zero exit codes)"""
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
    process = subprocess.Popen(single_line_cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    with process.stdout:
        output = ""
        for line in iter(process.stdout.readline, b''):
            output += line.decode()
        print(output)
    process.wait()
    return output, process.returncode


class TestsEndToEnd:

    # TestRail 101 instance has the required configuration for this test run
    TR_INSTANCE = "https://testrail101.testrail.io/"
    # Uncomment and enter your credentials below in order to execute the tests locally
    #os.environ.setdefault("TR_CLI_USERNAME", "")
    #os.environ.setdefault("TR_CLI_PASSWORD", "")

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
        
    def test_cli_add_run_include_all(self):
        output = _run_cmd(f"""
trcli -y \\
  -h {self.TR_INSTANCE} \\
  --project "SA - (DO NOT DELETE) TRCLI-E2E-Tests" \\
  add_run --run-include-all\\
  --title "[CLI-E2E-Tests] ADD RUN TEST: Include All Cases" \\
  -f "run_config.yml"
        """)
        _assert_contains(
            output,
            [
                "Creating test run.",
                f"Test run: {self.TR_INSTANCE}index.php?/runs/view",
                "title: [CLI-E2E-Tests] ADD RUN TEST: Include All Cases",
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
    
    def test_cli_add_run_and_plan_with_due_date(self):
        output = _run_cmd(f"""
trcli -y \\
  -h {self.TR_INSTANCE} \\
  --project "SA - (DO NOT DELETE) TRCLI-E2E-Tests" \\
  add_run --run-include-all \\
  --title "[CLI-E2E-Tests] ADD RUN TEST: Test Run with Due Date" \\
  --run-start-date "03/01/2030" --run-end-date "03/12/2030"
        """)
        _assert_contains(
            output,
            [
                "Creating test run.",
                f"Test run: {self.TR_INSTANCE}index.php?/runs/view",
                "title: [CLI-E2E-Tests] ADD RUN TEST: Test Run with Due Date"
            ]
        )

    def test_cli_add_run_refs_with_references(self):
        """Test creating a run with references"""
        import random
        import string
        
        # Generate random suffix to avoid conflicts
        random_suffix = ''.join(random.choices(string.ascii_lowercase + string.digits, k=6))
        
        output = _run_cmd(f"""
trcli -y \\
  -h {self.TR_INSTANCE} \\
  --project "SA - (DO NOT DELETE) TRCLI-E2E-Tests" \\
  add_run \\
  --title "[CLI-E2E-Tests] ADD RUN TEST: With References {random_suffix}" \\
  --run-refs "JIRA-100,JIRA-200,REQ-{random_suffix}" \\
  -f "run_config_refs.yml"
        """)
        _assert_contains(
            output,
            [
                "Creating test run.",
                f"Test run: {self.TR_INSTANCE}index.php?/runs/view",
                f"title: [CLI-E2E-Tests] ADD RUN TEST: With References {random_suffix}",
                f"Refs: JIRA-100,JIRA-200,REQ-{random_suffix}",
                "Writing test run data to file (run_config_refs.yml). Done."
            ]
        )

    def test_cli_add_run_refs_validation_error(self):
        """Test references validation (too long)"""
        long_refs = "A" * 251  # Exceeds 250 character limit
        
        output, return_code = _run_cmd_allow_failure(f"""
trcli -y \\
  -h {self.TR_INSTANCE} \\
  --project "SA - (DO NOT DELETE) TRCLI-E2E-Tests" \\
  add_run \\
  --title "[CLI-E2E-Tests] ADD RUN TEST: Refs Too Long" \\
  --run-refs "{long_refs}"
        """)
        
        assert return_code != 0
        _assert_contains(
            output,
            ["Error: References field cannot exceed 250 characters."]
        )

    def test_cli_add_run_refs_update_action_validation(self):
        """Test that update/delete actions require run_id"""
        output, return_code = _run_cmd_allow_failure(f"""
trcli -y \\
  -h {self.TR_INSTANCE} \\
  --project "SA - (DO NOT DELETE) TRCLI-E2E-Tests" \\
  add_run \\
  --title "[CLI-E2E-Tests] ADD RUN TEST: Invalid Action" \\
  --run-refs "JIRA-123" \\
  --run-refs-action "update"
        """)
        
        assert return_code != 0
        _assert_contains(
            output,
            ["Error: --run-refs-action 'update' and 'delete' can only be used when updating an existing run (--run-id required)."]
        )

    def test_cli_add_run_refs_update_workflow(self):
        """Test complete workflow: create run, then update references"""
        import random
        import string
        import re
        
        # Generate random suffix to avoid conflicts
        random_suffix = ''.join(random.choices(string.ascii_lowercase + string.digits, k=6))
        
        # Step 1: Create a run with initial references
        create_output = _run_cmd(f"""
trcli -y \\
  -h {self.TR_INSTANCE} \\
  --project "SA - (DO NOT DELETE) TRCLI-E2E-Tests" \\
  add_run \\
  --title "[CLI-E2E-Tests] ADD RUN TEST: Refs Workflow {random_suffix}" \\
  --run-refs "JIRA-100,JIRA-200" \\
  -f "run_config_workflow.yml"
        """)
        
        # Extract run ID from output
        run_id_match = re.search(r'run_id: (\d+)', create_output)
        assert run_id_match, "Could not extract run ID from output"
        run_id = run_id_match.group(1)
        
        _assert_contains(
            create_output,
            [
                "Creating test run.",
                f"run_id: {run_id}",
                "Refs: JIRA-100,JIRA-200"
            ]
        )
        
        # Step 2: Add more references to the existing run
        add_output = _run_cmd(f"""
trcli -y \\
  -h {self.TR_INSTANCE} \\
  --project "SA - (DO NOT DELETE) TRCLI-E2E-Tests" \\
  add_run \\
  --run-id {run_id} \\
  --title "[CLI-E2E-Tests] ADD RUN TEST: Refs Workflow {random_suffix}" \\
  --run-refs "JIRA-300,REQ-{random_suffix}" \\
  --run-refs-action "add"
        """)
        
        _assert_contains(
            add_output,
            [
                "Updating test run.",
                f"run_id: {run_id}",
                "Refs Action: add"
            ]
        )
        
        # Step 3: Update (replace) all references
        update_output = _run_cmd(f"""
trcli -y \\
  -h {self.TR_INSTANCE} \\
  --project "SA - (DO NOT DELETE) TRCLI-E2E-Tests" \\
  add_run \\
  --run-id {run_id} \\
  --title "[CLI-E2E-Tests] ADD RUN TEST: Refs Workflow {random_suffix}" \\
  --run-refs "NEW-100,NEW-200" \\
  --run-refs-action "update"
        """)
        
        _assert_contains(
            update_output,
            [
                "Updating test run.",
                f"run_id: {run_id}",
                "Refs: NEW-100,NEW-200",
                "Refs Action: update"
            ]
        )
        
        # Step 4: Delete specific references
        delete_output = _run_cmd(f"""
trcli -y \\
  -h {self.TR_INSTANCE} \\
  --project "SA - (DO NOT DELETE) TRCLI-E2E-Tests" \\
  add_run \\
  --run-id {run_id} \\
  --title "[CLI-E2E-Tests] ADD RUN TEST: Refs Workflow {random_suffix}" \\
  --run-refs "NEW-100" \\
  --run-refs-action "delete"
        """)
        
        _assert_contains(
            delete_output,
            [
                "Updating test run.",
                f"run_id: {run_id}",
                "Refs Action: delete"
            ]
        )
        
        # Step 5: Delete all references
        delete_all_output = _run_cmd(f"""
trcli -y \\
  -h {self.TR_INSTANCE} \\
  --project "SA - (DO NOT DELETE) TRCLI-E2E-Tests" \\
  add_run \\
  --run-id {run_id} \\
  --title "[CLI-E2E-Tests] ADD RUN TEST: Refs Workflow {random_suffix}" \\
  --run-refs-action "delete"
        """)
        
        _assert_contains(
            delete_all_output,
            [
                "Updating test run.",
                f"run_id: {run_id}",
                "Refs: ",
                "Refs Action: delete"
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
    
    def bug_test_automation_id(self):
        output = _run_cmd(f"""
trcli -y \\
  -h {self.TR_INSTANCE} \\
  --project "SA - (DO NOT DELETE) TRCLI-E2E-Tests" \\
  -c run_config.yml \\
  parse_junit \\
  --title "(DO NOT DELETE) [CLI-E2E-Tests] Test updated Automation ID" \\
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

    def test_labels_full_workflow(self):
        """Test complete labels workflow: add, list, get, update, delete"""
        
        # Step 1: Add a new label
        add_output = _run_cmd(f"""
trcli -y \\
  -h {self.TR_INSTANCE} \\
  --project "SA - (DO NOT DELETE) TRCLI-E2E-Tests" \\
  labels add \\
  --title "E2E-Test-Label"
        """)
        _assert_contains(
            add_output,
            [
                "Adding label 'E2E-Test-Label'...",
                "Successfully added label: ID=",
                "Title='E2E-Test-Label'"
            ]
        )
        
        # Extract label ID from the add output
        import re
        label_id_match = re.search(r"ID=(\d+)", add_output)
        assert label_id_match, f"Could not find label ID in output: {add_output}"
        label_id = label_id_match.group(1)
        print(f"Created label with ID: {label_id}")
        
        # Step 2: List labels to verify it exists
        list_output = _run_cmd(f"""
trcli -y \\
  -h {self.TR_INSTANCE} \\
  --project "SA - (DO NOT DELETE) TRCLI-E2E-Tests" \\
  labels list
        """)
        _assert_contains(
            list_output,
            [
                "Retrieving labels...",
                "Found",
                f"ID: {label_id}, Title: 'E2E-Test-Label'"
            ]
        )
        
        # Step 3: Get the specific label
        get_output = _run_cmd(f"""
trcli -y \\
  -h {self.TR_INSTANCE} \\
  --project "SA - (DO NOT DELETE) TRCLI-E2E-Tests" \\
  labels get \\
  --id {label_id}
        """)
        _assert_contains(
            get_output,
            [
                f"Retrieving label with ID {label_id}...",
                "Label details:",
                f"ID: {label_id}",
                "Title: 'E2E-Test-Label'"
            ]
        )
        
        # Step 4: Update the label
        update_output = _run_cmd(f"""
trcli -y \\
  -h {self.TR_INSTANCE} \\
  --project "SA - (DO NOT DELETE) TRCLI-E2E-Tests" \\
  labels update \\
  --id {label_id} \\
  --title "Updated-E2E-Label"
        """)
        _assert_contains(
            update_output,
            [
                f"Updating label with ID {label_id}...",
                f"Successfully updated label: ID={label_id}",
                "Title='Updated-E2E-Label'"
            ]
        )
        
        # Step 5: Verify the update by getting the label again
        get_updated_output = _run_cmd(f"""
trcli -y \\
  -h {self.TR_INSTANCE} \\
  --project "SA - (DO NOT DELETE) TRCLI-E2E-Tests" \\
  labels get \\
  --id {label_id}
        """)
        _assert_contains(
            get_updated_output,
            [
                f"ID: {label_id}",
                "Title: 'Updated-E2E-Label'"
            ]
        )
        
        # Step 6: Delete the label (with confirmation)
        delete_output = _run_cmd(f"""
echo "y" | trcli -y \\
  -h {self.TR_INSTANCE} \\
  --project "SA - (DO NOT DELETE) TRCLI-E2E-Tests" \\
  labels delete \\
  --ids {label_id}
        """)
        _assert_contains(
            delete_output,
            [
                f"Deleting labels with IDs: {label_id}...",
                "Successfully deleted 1 label(s)"
            ]
        )

    def test_labels_add_multiple_and_delete_multiple(self):
        """Test adding multiple labels and deleting them in batch"""
        
        # Add first label
        add_output1 = _run_cmd(f"""
trcli -y \\
  -h {self.TR_INSTANCE} \\
  --project "SA - (DO NOT DELETE) TRCLI-E2E-Tests" \\
  labels add \\
  --title "Batch-Test-1"
        """)
        
        # Add second label
        add_output2 = _run_cmd(f"""
trcli -y \\
  -h {self.TR_INSTANCE} \\
  --project "SA - (DO NOT DELETE) TRCLI-E2E-Tests" \\
  labels add \\
  --title "Batch-Test-2"
        """)
        
        # Add third label
        add_output3 = _run_cmd(f"""
trcli -y \\
  -h {self.TR_INSTANCE} \\
  --project "SA - (DO NOT DELETE) TRCLI-E2E-Tests" \\
  labels add \\
  --title "Batch-Test-3"
        """)
        
        # Extract all label IDs
        import re
        label_id1 = re.search(r"ID=(\d+)", add_output1).group(1)
        label_id2 = re.search(r"ID=(\d+)", add_output2).group(1)
        label_id3 = re.search(r"ID=(\d+)", add_output3).group(1)
        
        label_ids = f"{label_id1},{label_id2},{label_id3}"
        print(f"Created labels with IDs: {label_ids}")
        
        # Verify all labels exist in list
        list_output = _run_cmd(f"""
trcli -y \\
  -h {self.TR_INSTANCE} \\
  --project "SA - (DO NOT DELETE) TRCLI-E2E-Tests" \\
  labels list
        """)
        _assert_contains(
            list_output,
            [
                f"ID: {label_id1}, Title: 'Batch-Test-1'",
                f"ID: {label_id2}, Title: 'Batch-Test-2'",
                f"ID: {label_id3}, Title: 'Batch-Test-3'"
            ]
        )
        
        # Delete all labels in batch
        delete_output = _run_cmd(f"""
echo "y" | trcli -y \\
  -h {self.TR_INSTANCE} \\
  --project "SA - (DO NOT DELETE) TRCLI-E2E-Tests" \\
  labels delete \\
  --ids {label_ids}
        """)
        _assert_contains(
            delete_output,
            [
                f"Deleting labels with IDs: {label_ids}...",
                "Successfully deleted 3 label(s)"
            ]
        )

    def test_labels_help_commands(self):
        """Test labels help functionality"""
        
        # Test main labels help
        main_help_output = _run_cmd(f"""
trcli labels --help
        """)
        _assert_contains(
            main_help_output,
            [
                "Manage labels in TestRail",
                "add     Add a new label in TestRail",
                "delete  Delete labels from TestRail",
                "get     Get a specific label by ID",
                "list    List all labels in the project",
                "update  Update an existing label in TestRail"
            ]
        )
        
        # Test add command help
        add_help_output = _run_cmd(f"""
trcli labels add --help
        """)
        _assert_contains(
            add_help_output,
            [
                "Add a new label in TestRail",
                "--title",
                "Title of the label to add (max 20 characters)"
            ]
        )
        
        # Test update command help
        update_help_output = _run_cmd(f"""
trcli labels update --help
        """)
        _assert_contains(
            update_help_output,
            [
                "Update an existing label in TestRail",
                "--id",
                "--title",
                "ID of the label to update",
                "New title for the label (max 20 characters)"
            ]
        )
        
        # Test delete command help
        delete_help_output = _run_cmd(f"""
trcli labels delete --help
        """)
        _assert_contains(
            delete_help_output,
            [
                "Delete labels from TestRail",
                "--ids",
                "Comma-separated list of label IDs to delete"
            ]
        )
        
        # Test list command help
        list_help_output = _run_cmd(f"""
trcli labels list --help
        """)
        _assert_contains(
            list_help_output,
            [
                "List all labels in the project",
                "--offset",
                "--limit",
                "Offset for pagination",
                "Limit for pagination"
            ]
        )
        
        # Test get command help
        get_help_output = _run_cmd(f"""
trcli labels get --help
        """)
        _assert_contains(
            get_help_output,
            [
                "Get a specific label by ID",
                "--id",
                "ID of the label to retrieve"
            ]
        )

    def test_labels_pagination(self):
        """Test labels pagination functionality"""
        
        # Test basic list command
        list_output = _run_cmd(f"""
trcli -y \\
  -h {self.TR_INSTANCE} \\
  --project "SA - (DO NOT DELETE) TRCLI-E2E-Tests" \\
  labels list
        """)
        _assert_contains(
            list_output,
            [
                "Retrieving labels...",
                "Found"
            ]
        )
        
        # Test pagination with limit
        paginated_output = _run_cmd(f"""
trcli -y \\
  -h {self.TR_INSTANCE} \\
  --project "SA - (DO NOT DELETE) TRCLI-E2E-Tests" \\
  labels list \\
  --limit 5
        """)
        _assert_contains(
            paginated_output,
            [
                "Retrieving labels...",
                "Found"
            ]
        )
        
        # Test pagination with offset and limit
        offset_output = _run_cmd(f"""
trcli -y \\
  -h {self.TR_INSTANCE} \\
  --project "SA - (DO NOT DELETE) TRCLI-E2E-Tests" \\
  labels list \\
  --offset 0 \\
  --limit 10
        """)
        _assert_contains(
            offset_output,
            [
                "Retrieving labels...",
                "Found"
            ]
        )

    def test_labels_validation_errors(self):
        """Test labels validation and error handling"""
        
        # Test title too long (more than 20 characters)
        long_title_output, returncode = _run_cmd_allow_failure(f"""
trcli -y \\
  -h {self.TR_INSTANCE} \\
  --project "SA - (DO NOT DELETE) TRCLI-E2E-Tests" \\
  labels add \\
  --title "ThisTitleIsWayTooLongForTheValidationLimit"
        """)
        # Should fail with validation error
        assert returncode != 0, f"Expected validation error but command succeeded: {long_title_output}"
        assert "Error: Label title must be 20 characters or less." in long_title_output
        
        # Test invalid label ID for get
        invalid_get_output, returncode = _run_cmd_allow_failure(f"""
trcli -y \\
  -h {self.TR_INSTANCE} \\
  --project "SA - (DO NOT DELETE) TRCLI-E2E-Tests" \\
  labels get \\
  --id 999999
        """)
        # Should fail with API error
        assert returncode != 0, f"Expected API error but command succeeded: {invalid_get_output}"
        assert "Failed to retrieve label:" in invalid_get_output
        
        # Test invalid label ID format for delete
        invalid_delete_output, returncode = _run_cmd_allow_failure(f"""
echo "y" | trcli -y \\
  -h {self.TR_INSTANCE} \\
  --project "SA - (DO NOT DELETE) TRCLI-E2E-Tests" \\
  labels delete \\
  --ids "abc,def"
        """)
        # Should fail with format validation error
        assert returncode != 0, f"Expected validation error but command succeeded: {invalid_delete_output}"
        assert "Error: Invalid label IDs format" in invalid_delete_output

    def test_labels_edge_cases(self):
        """Test labels edge cases and boundary conditions"""
        
        # Test with exactly 20 character title (boundary condition)
        twenty_char_title = "ExactlyTwentyCharss!"  # Exactly 20 characters
        assert len(twenty_char_title) == 20, "Test title should be exactly 20 characters"
        
        add_output = _run_cmd(f"""
trcli -y \\
  -h {self.TR_INSTANCE} \\
  --project "SA - (DO NOT DELETE) TRCLI-E2E-Tests" \\
  labels add \\
  --title "{twenty_char_title}"
        """)
        _assert_contains(
            add_output,
            [
                f"Adding label '{twenty_char_title}'...",
                "Successfully added label:"
            ]
        )
        
        # Extract label ID for cleanup
        import re
        label_id_match = re.search(r"ID=(\d+)", add_output)
        if label_id_match:
            label_id = label_id_match.group(1)
            
            # Cleanup - delete the test label
            delete_output = _run_cmd(f"""
echo "y" | trcli -y \\
  -h {self.TR_INSTANCE} \\
  --project "SA - (DO NOT DELETE) TRCLI-E2E-Tests" \\
  labels delete \\
  --ids {label_id}
            """)
            _assert_contains(
                delete_output,
                [
                    f"Deleting labels with IDs: {label_id}...",
                    "Successfully deleted 1 label(s)"
                ]
            )


    def test_labels_cases_full_workflow(self):
        """Test complete workflow of test case label operations"""
        import random
        import string
        
        # Generate random suffix to avoid label conflicts
        random_suffix = ''.join(random.choices(string.ascii_lowercase + string.digits, k=6))
        case_label_title = f"e2e-case-{random_suffix}"
        
        # First, create a test label
        add_label_output = _run_cmd(f"""
trcli -y \\
  -h {self.TR_INSTANCE} \\
  --project "SA - (DO NOT DELETE) TRCLI-E2E-Tests" \\
  labels add \\
  --title "{case_label_title}"
        """)
        _assert_contains(
            add_label_output,
            [
                f"Adding label '{case_label_title}'...",
                "Successfully added label:"
            ]
        )
        
        # Extract label ID for later use
        import re
        label_id_match = re.search(r"ID=(\d+)", add_label_output)
        assert label_id_match, "Could not extract label ID from output"
        label_id = label_id_match.group(1)
        
        try:
            # Use known test case IDs that should exist in the test project
            test_case_ids = ["24964", "24965"]  # Multiple test cases for batch testing
            
            # Add labels to test cases
            add_cases_output = _run_cmd(f"""
trcli -y \\
  -h {self.TR_INSTANCE} \\
  --project "SA - (DO NOT DELETE) TRCLI-E2E-Tests" \\
  labels cases add \\
  --case-ids "{','.join(test_case_ids)}" \\
  --title "{case_label_title}"
            """)
            _assert_contains(
                add_cases_output,
                [
                    f"Adding label '{case_label_title}' to {len(test_case_ids)} test case(s)...",
                    "Successfully processed"
                ]
            )
            
            # List test cases by label title
            list_by_title_output = _run_cmd(f"""
trcli -y \\
  -h {self.TR_INSTANCE} \\
  --project "SA - (DO NOT DELETE) TRCLI-E2E-Tests" \\
  labels cases list \\
  --title "{case_label_title}"
            """)
            _assert_contains(
                list_by_title_output,
                [
                    f"Retrieving test cases with label title '{case_label_title}'...",
                    "matching test case(s):"
                ]
            )
            
            # List test cases by label ID
            list_by_id_output = _run_cmd(f"""
trcli -y \\
  -h {self.TR_INSTANCE} \\
  --project "SA - (DO NOT DELETE) TRCLI-E2E-Tests" \\
  labels cases list \\
  --ids "{label_id}"
            """)
            _assert_contains(
                list_by_id_output,
                [
                    f"Retrieving test cases with label IDs: {label_id}...",
                    "matching test case(s):"
                ]
            )
            
        finally:
            # Cleanup - delete the test label
            delete_output = _run_cmd(f"""
echo "y" | trcli -y \\
  -h {self.TR_INSTANCE} \\
  --project "SA - (DO NOT DELETE) TRCLI-E2E-Tests" \\
  labels delete \\
  --ids {label_id}
            """)
            _assert_contains(
                delete_output,
                [
                    f"Deleting labels with IDs: {label_id}...",
                    "Successfully deleted 1 label(s)"
                ]
            )

    def test_labels_cases_validation_errors(self):
        """Test validation errors for test case label commands"""
        # Test title too long for add cases
        long_title_output, return_code = _run_cmd_allow_failure(f"""
trcli -y \\
  -h {self.TR_INSTANCE} \\
  --project "SA - (DO NOT DELETE) TRCLI-E2E-Tests" \\
  labels cases add \\
  --case-ids "1" \\
  --title "this-title-is-way-too-long-for-testrail"
        """)
        assert return_code != 0
        _assert_contains(
            long_title_output,
            ["Error: Label title must be 20 characters or less."]
        )
        
        # Test invalid case IDs format
        invalid_ids_output, return_code = _run_cmd_allow_failure(f"""
trcli -y \\
  -h {self.TR_INSTANCE} \\
  --project "SA - (DO NOT DELETE) TRCLI-E2E-Tests" \\
  labels cases add \\
  --case-ids "invalid,ids" \\
  --title "test"
        """)
        assert return_code != 0
        _assert_contains(
            invalid_ids_output,
            ["Error: Invalid case IDs format. Use comma-separated integers (e.g., 1,2,3)."]
        )
        
        # Test missing filter for list cases
        no_filter_output, return_code = _run_cmd_allow_failure(f"""
trcli -y \\
  -h {self.TR_INSTANCE} \\
  --project "SA - (DO NOT DELETE) TRCLI-E2E-Tests" \\
  labels cases list
        """)
        assert return_code != 0
        _assert_contains(
            no_filter_output,
            ["Error: Either --ids or --title must be provided."]
        )
        
        # Test title too long for list cases
        long_title_list_output, return_code = _run_cmd_allow_failure(f"""
trcli -y \\
  -h {self.TR_INSTANCE} \\
  --project "SA - (DO NOT DELETE) TRCLI-E2E-Tests" \\
  labels cases list \\
  --title "this-title-is-way-too-long-for-testrail"
        """)
        assert return_code != 0
        _assert_contains(
            long_title_list_output,
            ["Error: Label title must be 20 characters or less."]
        )

    def test_labels_cases_help_commands(self):
        """Test help output for test case label commands"""
        # Test main cases help
        cases_help_output = _run_cmd("trcli labels cases --help")
        _assert_contains(
            cases_help_output,
            [
                "Usage: trcli labels cases [OPTIONS] COMMAND [ARGS]...",
                "Manage labels for test cases",
                "add   Add a label to test cases",
                "list  List test cases filtered by label ID or title"
            ]
        )
        
        # Test cases add help
        cases_add_help_output = _run_cmd("trcli labels cases add --help")
        _assert_contains(
            cases_add_help_output,
            [
                "Usage: trcli labels cases add [OPTIONS]",
                "Add a label to test cases",
                "--case-ids",
                "--title"
            ]
        )
        
        # Test cases list help
        cases_list_help_output = _run_cmd("trcli labels cases list --help")
        _assert_contains(
            cases_list_help_output,
            [
                "Usage: trcli labels cases list [OPTIONS]",
                "List test cases filtered by label ID or title",
                "--ids",
                "--title"
            ]
        )

    def test_labels_cases_no_matching_cases(self):
        """Test behavior when no test cases match the specified label"""
        # Test with non-existent label title
        no_match_output = _run_cmd(f"""
trcli -y \\
  -h {self.TR_INSTANCE} \\
  --project "SA - (DO NOT DELETE) TRCLI-E2E-Tests" \\
  labels cases list \\
  --title "non-existent-label"
        """)
        _assert_contains(
            no_match_output,
            [
                "Retrieving test cases with label title 'non-existent-label'...",
                "Found 0 matching test case(s):",
                "No test cases found with label title 'non-existent-label'."
            ]
        )
        
        # Test with non-existent label ID
        no_match_id_output = _run_cmd(f"""
trcli -y \\
  -h {self.TR_INSTANCE} \\
  --project "SA - (DO NOT DELETE) TRCLI-E2E-Tests" \\
  labels cases list \\
  --ids "99999"
        """)
        _assert_contains(
            no_match_id_output,
            [
                "Retrieving test cases with label IDs: 99999...",
                "Found 0 matching test case(s):",
                "No test cases found with the specified label IDs."
            ]
        )

    def test_labels_cases_single_case_workflow(self):
        """Test single case label operations using update_case endpoint"""
        import random
        import string
        
        # Generate random suffix to avoid label conflicts
        random_suffix = ''.join(random.choices(string.ascii_lowercase + string.digits, k=6))
        single_case_label_title = f"e2e-single-{random_suffix}"
        
        # First, create a test label
        add_label_output = _run_cmd(f"""
trcli -y \\
  -h {self.TR_INSTANCE} \\
  --project "SA - (DO NOT DELETE) TRCLI-E2E-Tests" \\
  labels add \\
  --title "{single_case_label_title}"
        """)
        _assert_contains(
            add_label_output,
            [
                f"Adding label '{single_case_label_title}'...",
                "Successfully added label:"
            ]
        )

        # Extract label ID for later use
        import re
        label_id_match = re.search(r"ID=(\d+)", add_label_output)
        assert label_id_match, "Could not extract label ID from output"
        label_id = label_id_match.group(1)

        try:
            # Use single test case ID for testing update_case endpoint
            single_case_id = "24964"

            # Add label to single test case
            add_single_case_output = _run_cmd(f"""
trcli -y \\
  -h {self.TR_INSTANCE} \\
  --project "SA - (DO NOT DELETE) TRCLI-E2E-Tests" \\
  labels cases add \\
  --case-ids "{single_case_id}" \\
  --title "{single_case_label_title}"
            """)
            _assert_contains(
                add_single_case_output,
                [
                    f"Adding label '{single_case_label_title}' to 1 test case(s)...",
                    "Successfully processed 1 case(s):",
                    f"Successfully added label '{single_case_label_title}' to case {single_case_id}"
                ]
            )

            # Verify the label was added by listing cases with this label
            list_cases_output = _run_cmd(f"""
trcli -y \\
  -h {self.TR_INSTANCE} \\
  --project "SA - (DO NOT DELETE) TRCLI-E2E-Tests" \\
  labels cases list \\
  --title "{single_case_label_title}"
            """)
            _assert_contains(
                list_cases_output,
                [
                    f"Retrieving test cases with label title '{single_case_label_title}'...",
                    "Found 1 matching test case(s):",
                    f"Case ID: {single_case_id}"
                ]
            )

        finally:
            # Clean up: delete the test label
            _run_cmd(f"""
echo "y" | trcli -y \\
  -h {self.TR_INSTANCE} \\
  --project "SA - (DO NOT DELETE) TRCLI-E2E-Tests" \\
  labels delete \\
  --ids {label_id}
            """)

    def test_labels_tests_full_workflow(self):
        """Test complete workflow of test label operations"""
        import random
        import string
        
        # Generate random suffix to avoid label conflicts
        random_suffix = ''.join(random.choices(string.ascii_lowercase + string.digits, k=6))
        test_label_title = f"e2e-test-{random_suffix}"
        
        # First, create a test label
        add_label_output = _run_cmd(f"""
trcli -y \\
  -h {self.TR_INSTANCE} \\
  --project "SA - (DO NOT DELETE) TRCLI-E2E-Tests" \\
  labels add \\
  --title "{test_label_title}"
        """)
        _assert_contains(
            add_label_output,
            [
                f"Adding label '{test_label_title}'...",
                "Successfully added label:"
            ]
        )

        # Extract label ID for cleanup
        import re
        label_id_match = re.search(r"ID=(\d+)", add_label_output)
        assert label_id_match, "Could not extract label ID from output"
        label_id = label_id_match.group(1)

        try:
            # Use known test IDs that should exist in the test project
            test_ids = ["266149", "266151"]  # Real test IDs for functional testing

            # Test 1: Add labels to tests using --test-ids
            add_tests_output = _run_cmd(f"""
trcli -y \\
  -h {self.TR_INSTANCE} \\
  --project "SA - (DO NOT DELETE) TRCLI-E2E-Tests" \\
  labels tests add \\
  --test-ids "{','.join(test_ids)}" \\
  --title "{test_label_title}"
            """)
            
            _assert_contains(
                add_tests_output,
                [
                    f"Adding label '{test_label_title}' to {len(test_ids)} test(s)..."
                ]
            )

            # Test 2: Add labels to tests using CSV file
            import os
            csv_file_path = os.path.join(os.path.dirname(__file__), "sample_csv", "test_ids.csv")
            
            add_tests_csv_output = _run_cmd(f"""
trcli -y \\
  -h {self.TR_INSTANCE} \\
  --project "SA - (DO NOT DELETE) TRCLI-E2E-Tests" \\
  labels tests add \\
  --test-id-file "{csv_file_path}" \\
  --title "{test_label_title}"
            """)
            
            _assert_contains(
                add_tests_csv_output,
                [
                    "Loaded 2 test ID(s) from file",
                    f"Adding label '{test_label_title}' to 2 test(s)..."
                ]
            )

            # Test 3: List tests by label ID
            list_tests_output = _run_cmd(f"""
trcli -y \\
  -h {self.TR_INSTANCE} \\
  --project "SA - (DO NOT DELETE) TRCLI-E2E-Tests" \\
  labels tests list \\
  --ids "{label_id}"
            """)
            _assert_contains(
                list_tests_output,
                [
                    f"Retrieving tests with label IDs: {label_id}...",
                    "matching test(s):"
                ]
            )

            # Test 4: Get test labels for specific tests
            get_test_labels_output = _run_cmd(f"""
trcli -y \\
  -h {self.TR_INSTANCE} \\
  --project "SA - (DO NOT DELETE) TRCLI-E2E-Tests" \\
  labels tests get \\
  --test-id "{','.join(test_ids)}"
            """)
            _assert_contains(
                get_test_labels_output,
                [
                    f"Retrieving labels for {len(test_ids)} test(s)...",
                    "Test label information:"
                ]
            )

        finally:
            # Cleanup - delete the test label
            delete_output = _run_cmd(f"""
echo "y" | trcli -y \\
  -h {self.TR_INSTANCE} \\
  --project "SA - (DO NOT DELETE) TRCLI-E2E-Tests" \\
  labels delete \\
  --ids {label_id}
            """)

    def test_labels_tests_validation_errors(self):
        """Test validation errors for test label commands"""
        import random
        import string
        
        # Generate random suffix to avoid label conflicts
        random_suffix = ''.join(random.choices(string.ascii_lowercase + string.digits, k=6))
        
        # Test title too long (21 characters exceeds 20 character limit)
        long_title = f"this-is-a-very-long-title-{random_suffix}"  # This will be > 20 chars
        title_error_output, return_code = _run_cmd_allow_failure(f"""
trcli -y \\
  -h {self.TR_INSTANCE} \\
  --project "SA - (DO NOT DELETE) TRCLI-E2E-Tests" \\
  labels tests add \\
  --test-ids "266149" \\
  --title "{long_title}"
        """)
        assert return_code != 0
        _assert_contains(
            title_error_output,
            ["Error: Label title must be 20 characters or less."]
        )

        # Test missing test-ids and file
        valid_title = f"test-{random_suffix}"[:20]  # Ensure valid length
        missing_ids_output, return_code = _run_cmd_allow_failure(f"""
trcli -y \\
  -h {self.TR_INSTANCE} \\
  --project "SA - (DO NOT DELETE) TRCLI-E2E-Tests" \\
  labels tests add \\
  --title "{valid_title}"
        """)
        assert return_code != 0
        _assert_contains(
            missing_ids_output,
            ["Error: Either --test-ids or --test-id-file must be provided."]
        )

        # Test invalid label IDs format in list command
        invalid_ids_output, return_code = _run_cmd_allow_failure(f"""
trcli -y \\
  -h {self.TR_INSTANCE} \\
  --project "SA - (DO NOT DELETE) TRCLI-E2E-Tests" \\
  labels tests list \\
  --ids "invalid,ids"
        """)
        assert return_code != 0
        _assert_contains(
            invalid_ids_output,
            ["Error: Invalid label IDs format. Use comma-separated integers (e.g., 1,2,3)."]
        )

    def test_labels_tests_help_commands(self):
        """Test help output for test label commands"""
        
        # Test main tests help
        tests_help_output = _run_cmd("trcli labels tests --help")
        _assert_contains(
            tests_help_output,
            [
                "Usage: trcli labels tests [OPTIONS] COMMAND [ARGS]...",
                "Manage labels for tests",
                "Commands:",
                "add",
                "list", 
                "get"
            ]
        )

        # Test tests add help
        tests_add_help_output = _run_cmd("trcli labels tests add --help")
        _assert_contains(
            tests_add_help_output,
            [
                "Usage: trcli labels tests add [OPTIONS]",
                "Add a label to tests",
                "--test-ids",
                "--test-id-file",
                "--title"
            ]
        )

        # Test tests list help
        tests_list_help_output = _run_cmd("trcli labels tests list --help")
        _assert_contains(
            tests_list_help_output,
            [
                "Usage: trcli labels tests list [OPTIONS]",
                "List tests filtered by label ID",
                "--ids"
            ]
        )

        # Test tests get help
        tests_get_help_output = _run_cmd("trcli labels tests get --help")
        _assert_contains(
            tests_get_help_output,
            [
                "Usage: trcli labels tests get [OPTIONS]",
                "Get the labels of tests using test IDs",
                "--test-id"
            ]
        )
    