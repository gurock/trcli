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
        
        # Generate random suffix to avoid conflicts with existing labels
        import random
        import string
        random_suffix = ''.join(random.choices(string.ascii_lowercase + string.digits, k=6))
        label_title = f"e2e-{random_suffix}"
        assert len(label_title) <= 20, f"Label title '{label_title}' exceeds 20 characters"
        
        # Step 1: Add a new label
        add_output = _run_cmd(f"""
trcli -y \\
  -h {self.TR_INSTANCE} \\
  --project "SA - (DO NOT DELETE) TRCLI-E2E-Tests" \\
  labels add \\
  --title "{label_title}"
        """)
        _assert_contains(
            add_output,
            [
                f"Adding label '{label_title}'...",
                "Successfully added label: ID=",
                f"Title='{label_title}'"
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
                f"ID: {label_id}, Title: '{label_title}'"
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
                f"Title: '{label_title}'"
            ]
        )
        
        # Step 4: Update the label
        updated_title = f"upd-{random_suffix}"
        assert len(updated_title) <= 20, f"Updated title '{updated_title}' exceeds 20 characters"
        update_output = _run_cmd(f"""
trcli -y \\
  -h {self.TR_INSTANCE} \\
  --project "SA - (DO NOT DELETE) TRCLI-E2E-Tests" \\
  labels update \\
  --id {label_id} \\
  --title "{updated_title}"
        """)
        _assert_contains(
            update_output,
            [
                f"Updating label with ID {label_id}...",
                f"Successfully updated label: ID={label_id}",
                f"Title='{updated_title}'"
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
                f"Title: '{updated_title}'"
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
        
        # Generate random suffix to avoid conflicts with existing labels
        import random
        import string
        random_suffix = ''.join(random.choices(string.ascii_lowercase + string.digits, k=6))
        
        # Add first label
        label1_title = f"b1-{random_suffix}"
        assert len(label1_title) <= 20, f"Label1 title '{label1_title}' exceeds 20 characters"
        add_output1 = _run_cmd(f"""
trcli -y \\
  -h {self.TR_INSTANCE} \\
  --project "SA - (DO NOT DELETE) TRCLI-E2E-Tests" \\
  labels add \\
  --title "{label1_title}"
        """)
        
        # Add second label
        label2_title = f"b2-{random_suffix}"
        assert len(label2_title) <= 20, f"Label2 title '{label2_title}' exceeds 20 characters"
        add_output2 = _run_cmd(f"""
trcli -y \\
  -h {self.TR_INSTANCE} \\
  --project "SA - (DO NOT DELETE) TRCLI-E2E-Tests" \\
  labels add \\
  --title "{label2_title}"
        """)
        
        # Add third label
        label3_title = f"b3-{random_suffix}"
        assert len(label3_title) <= 20, f"Label3 title '{label3_title}' exceeds 20 characters"
        add_output3 = _run_cmd(f"""
trcli -y \\
  -h {self.TR_INSTANCE} \\
  --project "SA - (DO NOT DELETE) TRCLI-E2E-Tests" \\
  labels add \\
  --title "{label3_title}"
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
                f"ID: {label_id1}, Title: '{label1_title}'",
                f"ID: {label_id2}, Title: '{label2_title}'",
                f"ID: {label_id3}, Title: '{label3_title}'"
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
    