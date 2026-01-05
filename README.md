![Tests](https://github.com/gurock/trcli/actions/workflows/python-app.yml/badge.svg)

trcli - The TestRail CLI
================================
The TestRail CLI (trcli) is a command line tool for interacting with TestRail. 
It integrates directly with the TestRail API and provides abstractions to easily 
create test cases and upload automated test results.

The TestRail CLI currently supports:
- **Uploading automated test results from JUnit reports**
- **Uploading automated test results from Robot Framework reports**
- **Auto-generating test cases from OpenAPI specifications**
- **Creating new test runs for results to be uploaded to**
- **Managing project labels for better organization and categorization**

To see further documentation about the TestRail CLI, please refer to the 
[TestRail CLI documentation pages](https://support.gurock.com/hc/en-us/articles/7146548750868-TestRail-CLI)
on the TestRail help center.

Installation
------------

If you already have [Python](https://www.python.org/) and [pip](https://pip.pypa.io) installed,
you can simply run the command below in your terminal. We recommend using **Python 3.10** or newer.
```
pip install trcli
```

To verify the installation was successful, you can run the `trcli` command.

```shell
trcli
```
You should get something like this:
```
TestRail CLI v1.12.6
Copyright 2025 Gurock Software GmbH - www.gurock.com
Supported and loaded modules:
    - parse_junit: JUnit XML Files (& Similar)
    - parse_robot: Robot Framework XML Files
    - parse_openapi: OpenAPI YML Files
    - add_run: Create a new empty test run
    - labels: Manage labels (add, update, delete, list)
```

CLI general reference
--------
```shell
$ trcli --help
TestRail CLI v1.12.6
Copyright 2025 Gurock Software GmbH - www.gurock.com
Usage: trcli [OPTIONS] COMMAND [ARGS]...

  TestRail CLI

Options:
  -c, --config       Optional path definition for testrail-credentials file or
                     CF file.
  -h, --host         Hostname of instance.
  --project          Name of project the Test Run should be created under.
  --project-id       Project id. Will be only used in case project name will
                     be duplicated in TestRail  [x>=1]
  -u, --username     Username.
  -p, --password     Password.
  -k, --key          API key used for authenticating with TestRail.
                     This must be used in conjunction with --username.
                     If provided, --password is not required.
  -v, --verbose      Output all API calls and their results.
  --verify           Verify the data was added correctly.
  --insecure         Allow insecure requests.
  -b, --batch-size   Configurable batch size.  [default: (50); x>=2]
  -t, --timeout      Batch timeout duration.  [default: (30); x>=0]
  -y, --yes          answer 'yes' to all prompts around auto-creation
  -n, --no           answer 'no' to all prompts around auto-creation
  -s, --silent       Silence stdout
  --proxy            Proxy address and port (e.g.,
                     http://proxy.example.com:8080).
  --proxy-user       Proxy username and password in the format
                     'username:password'.
  --noproxy          Comma-separated list of hostnames to bypass the proxy
                     (e.g., localhost,127.0.0.1).
  --parallel-pagination  Enable parallel pagination for faster case fetching
                     (experimental).
  --help             Show this message and exit.

Commands:
  add_run        Add a new test run in TestRail
  labels         Manage labels in TestRail
  parse_junit    Parse JUnit report and upload results to TestRail
  parse_openapi  Parse OpenAPI spec and create cases in TestRail
  parse_robot    Parse Robot Framework report and upload results to TestRail
  references     Manage references in TestRail
```

Uploading automated test results
--------

The `parse_junit` command allows you to upload automated test results, provided that you are using
a framework that supports generating JUnit XML report files, such as Cypress, Playwright, JUnit5, TestNG, and Pytest. 
In case you are using Robot Framework, you can use the `parse_robot` command using the same parameters. 

In the next sections you will find information on how to use the TestRail CLI for **code-first** and
**specification-first** approaches to test automation.

### Reference
```shell
trcli parse_junit --help
```
```shell
Usage: trcli parse_junit [OPTIONS]

  Parse report files and upload results to TestRail

Options:
  -f, --file          Filename and path.
  --close-run         Close the newly created run
  --title             Title of Test Run to be created in TestRail.
  --case-matcher      Mechanism to match cases between the report and
                      TestRail.
  --suite-id          Suite ID to submit results to.  [x>=1]
  --suite-name        Suite name to submit results to.
  --run-id            Run ID for the results they are reporting (otherwise the
                      tool will attempt to create a new run).  [x>=1]
  --plan-id           Plan ID with which the Test Run will be associated.
                      [x>=1]
  --config-ids        Comma-separated configuration IDs to use along with Test
                      Plans (i.e.: 34,52).
  --milestone-id      Milestone ID to which the Test Run should be associated
                      to.  [x>=1]
  --section-id        Section ID to create new sections with test cases under
                      (optional).  [x>=1]
  --run-description   Summary text to be added to the test run.
  --case-fields       List of case fields and values for new test cases
                      creation. Usage: --case-fields type_id:1 --case-fields
                      priority_id:3
  --result-fields     List of result fields and values for test results
                      creation. Usage: --result-fields custom_field_a:value1
                      --result-fields custom_field_b:3
  --allow-ms          Allows using milliseconds for elapsed times.
  --special-parser    Optional special parser option for specialized JUnit
                      reports.
  -a, --assign        Comma-separated list of user emails to assign failed
                      test results to.
  --test-run-ref      Comma-separated list of reference IDs to append to the
                      test run (up to 250 characters total).
  --json-output       Output reference operation results in JSON format.
  --update-existing-cases   Update existing TestRail cases with values from
                            JUnit properties (default: no).
  --update-strategy         Strategy for combining incoming values with
                            existing case field values, whether to append or
                            replace (Note: only applies to references default: append).
  --help              Show this message and exit.
```

### JUnit XML report example
```xml
<testsuites name="test suites root">
  <testsuite failures="0" errors="0" skipped="1" tests="1" time="3049" name="tests.LoginTests">
    <properties>
      <property name="setting1" value="True"/>
      <property name="setting2" value="value2"/>
    </properties>
    <testcase classname="tests.LoginTests" name="test_case_1" time="159">
      <skipped type="pytest.skip" message="Please skip">skipped by user</skipped>
    </testcase>
    <testcase classname="tests.LoginTests" name="test_case_2" time="650">
    </testcase>
    <testcase classname="tests.LoginTests" name="test_case_3" time="121">
      <failure type="pytest.failure" message="Fail due to...">failed due to...</failure>
      <properties>
        <property name="testrail_attachment" value="path_to/screenshot.jpg"/>
      </properties>
    </testcase>
  </testsuite>
</testsuites>
```

**Mapping JUnit elements to TestRail entities:**

| XML junit file tag | TestRail entity |
|--------------------|-----------------|
| `<testsuites>`     | suite           |
| `<testsuite>`      | section         |
| `<testcase>`       | case            |

For further detail, please refer to the 
[JUnit to TestRail mapping](https://support.gurock.com/hc/en-us/articles/12989737200276) documentation.

### Uploading test results
To submit test case results, the TestRail CLI will attempt to match the test cases in your automation suite to test cases in TestRail.
There are 2 mechanisms to match test cases:
1. Using Automation ID
2. Using Case ID (in test case `name` or `property`)

The first mechanism allows to automatically match test cases, meaning you can take a code-first approach,
while the second one is suited for a specification-first approach, where you write your test cases in TestRail and add the case ID to your automated tests.

> **Notes:**
> 1. The TestRail CLI has a prompt mechanism that allows you to choose whether you want test cases to be automatically created: 
>   - If you enter `yes` (or use the `-y` option), the TestRail CLI will automatically create any test case it can't match in TestRail
>   - If you enter `no` (or use the `-n` option), the TestRail CLI will not create any new test cases
> 2. If you are using a **multi-suite project** in TestRail, you should provide the ID of the test suite 
>   you want the cases to be created in using the `--suite-id` command line option, 
>   otherwise the CLI tool will attempt to find the suite on TestRail or create it.

#### 1. Using Automation ID (code-first approach)
To use this mechanism, you must first add a new [custom field](https://www.gurock.com/testrail/docs/user-guide/howto/fields/) 
of type `Text` with system name `automation_id`.

The TestRail CLI will use the unique combination of your automation test case’s `classname` and `name` 
(expressed as `classname.name`) to compare against values of the `automation_id` field in your TestRail test case repository.
If a match is found, this test case will be included in the auto-generated test run for this upload. 

Example:

| Test Result from Automation Results File                                               | Automation ID in TestRail      |
|----------------------------------------------------------------------------------------|--------------------------------|
| ```<testcase classname="tests.LoginTests" name="test_case_1" time="159"></testcase>``` | `tests.LoginTests.test_case_1` |

If automatically assigned `classname` and `name` as `automation_id` is not suitable, you can set it
via properties, according to:
[JUnit to TestRail mapping](https://support.gurock.com/hc/en-us/articles/12989737200276)
```
 <properties>
     <property name="testrail_case_field" value="custom_automation_id:automation_id_example"/> 
```
Only make sure automation_id system name is correct for your project.

> **Important usage notes:**
> 1. If you would like to upload automation results for test cases that already exist in TestRail, be sure to update the `automation_id` for those test cases before uploading your automation results
> 2. If you change the test name in your automation suite later, that will create a new test case in TestRail, unless you also update the `automation_id` field for the test case in TestRail
> 3. If you are using the CLI tool in a CI context, we recommend using the `-y` option to automatically accept test case creation prompts

For more detail, please refer to the [Automation workflows - Code-first](https://support.gurock.com/hc/en-us/articles/12609674354068)
documentation.

#### 2. Using Case ID (specification-first approach)

You can use the Case ID mechanism if you want to manually match your automated test cases to case IDs in TestRail.
From an implementation perspective, you can do this in one of two ways:

1. Map by setting the case ID in the test name, using the case-matcher `name`:
```xml
<testsuites name="test suites root">
  <testsuite failures="0" errors="0" skipped="1" tests="1" time="3049" name="tests.LoginTests">
    <testcase classname="tests.LoginTests" name="[C123] test_case_1" time="650" />
  </testsuite>
</testsuites>
```

2. Map by setting the case ID in a test case property, using case-matcher `property`:
```xml
<testsuites name="test suites root">
  <testsuite failures="0" errors="0" skipped="1" tests="1" time="3049" name="tests.LoginTests">
    <testcase classname="tests.LoginTests" name="test_case_1" time="650">
     <properties>
         <property name="test_id" value="C123"/>
     </properties>
    </testcase>
  </testsuite>
</testsuites>
```
> **Important usage notes:**
> - We recommend using the `-n` option to skip creating new test cases due to the potential risk of duplication 

For more details, please refer to the [Automation workflows - Specification-first](https://support.gurock.com/hc/en-us/articles/12609869124116)
documentation.

#### 3 Case result statuses mapping
Result statuses for case might be overridden using yaml config. You have to add `case_result_statuses` option with
corresponding mappings to desired statuses.
Example:
```yaml
case_result_statuses:
  passed: 1
  skipped: 3
  error: 4
  failure: 5
```
You can find statuses ids for your project using following endpoint:
 ```/api/v2/get_statuses```

### Auto-Assigning Failed Tests

The `--assign` (or `-a`) option allows you to automatically assign failed test results to specific TestRail users. This feature is particularly useful in CI/CD environments where you want to automatically assign failures to responsible team members for investigation.

#### Usage

```shell
# Assign failed tests to a single user
$ trcli parse_junit -f results.xml --assign user@example.com \
  --host https://yourinstance.testrail.io --username <your_username> --password <your_password> \
  --project "Your Project"

# Assign failed tests to multiple users (round-robin distribution)
$ trcli parse_junit -f results.xml --assign "user1@example.com,user2@example.com,user3@example.com" \
  --host https://yourinstance.testrail.io --username <your_username> --password <your_password> \
  --project "Your Project"

# Short form using -a
$ trcli parse_junit -f results.xml -a user@example.com \
  --host https://yourinstance.testrail.io --username <your_username> --password <your_password> \
  --project "Your Project"
```

#### Example Output

```shell
Parser Results Execution Parameters
> Report file: results.xml
> Config file: /path/to/config.yml
> TestRail instance: https://yourinstance.testrail.io (user: your@email.com)
> Project: Your Project
> Run title: Automated Test Run
> Update run: No
> Add to milestone: No
> Auto-assign failures: Yes (user1@example.com,user2@example.com)
> Auto-create entities: True

Creating test run. Done.
Adding results: 100%|████████████| 25/25 [00:02<00:00, 12.5results/s]
Assigning failed results: 3/3, Done.
Submitted 25 test results in 2.1 secs.
```

### Exploring other features

#### General features
Please refer to the [Usage examples](https://support.gurock.com/hc/en-us/articles/12908548726804) documentation page to see how you
can leverage all the functionalities provided by the TestRail CLI.

#### SauceLabs saucectl reports
If you are using `saucectl` from SauceLabs to execute your automation projects, the TestRail CLI has an enhanced parser 
that fetches session information and adds it to your test runs. You can enable this functionality by using 
the `--special-parser saucectl` command line option.

Please refer to the [SauceLabs and saucectl reports](https://support.gurock.com/hc/en-us/articles/12719558686484)
documentation for further information.

#### Creating new test runs

When a test run MUST created before using one of the parse commands, use the `add_run` command. For example, if
tests are run across parallel, independent test nodes, all nodes should report their results into the same test run.
First, use the `add_run` command to create a new run; then, pass the run title and id to each of the test nodes, which
will be used to upload all results into the same test run.

#### Labels Management

The TestRail CLI provides comprehensive label management capabilities using the `labels` command. Labels help categorize and organize your test management assets efficiently, making it easier to filter and manage test cases, runs, and projects.

The TestRail CLI supports three types of label management:
- **Project Labels**: Manage labels at the project level
- **Test Case Labels**: Apply labels to specific test cases for better organization and filtering  
- **Test Labels**: Apply labels to specific tests (instances of test cases within test runs) for execution management

All types of labels support comprehensive operations with validation and error handling. Project labels support full CRUD operations, while test case and test labels focus on assignment and retrieval operations.

##### Reference
```shell
$ trcli labels --help
Usage: trcli labels [OPTIONS] COMMAND [ARGS]...

  Manage labels in TestRail

Options:
  --help  Show this message and exit.

Commands:
  add     Add a new label in TestRail
  cases   Manage labels for test cases
  delete  Delete labels from TestRail
  get     Get a specific label by ID
  list    List all labels in the project
  tests   Manage labels for tests
  update  Update an existing label in TestRail
```

#### Project Labels

Project labels are managed using the main `labels` command and provide project-wide label management capabilities. These labels can be created, updated, deleted, and listed at the project level.

**Project Labels Support:**
- **Add** new labels to projects
- **List** existing labels with pagination support
- **Get** detailed information about specific labels
- **Update** existing label titles
- **Delete** single or multiple labels in batch

###### Adding Labels
Create new labels for your project with a descriptive title (maximum 20 characters).

```shell
# Add a single label
$ trcli -h https://yourinstance.testrail.io --username <your_username> --password <your_password> \
  --project "Your Project" \
  labels add --title "Critical"

# Add a label for release management
$ trcli -h https://yourinstance.testrail.io --username <your_username> --password <your_password> \
  --project "Your Project" \
  labels add --title "Release-2.0"

# Add a label for test categorization
$ trcli -h https://yourinstance.testrail.io --username <your_username> --password <your_password> \
  --project "Your Project" \
  labels add --title "Regression"
```

###### Listing Labels
View all labels in your project with optional pagination support.

```shell
# List all labels (default: up to 250 labels)
$ trcli -h https://yourinstance.testrail.io --username <your_username> --password <your_password> \
  --project "Your Project" \
  labels list

# List labels with pagination
$ trcli -h https://yourinstance.testrail.io --username <your_username> --password <your_password> \
  --project "Your Project" \
  labels list --limit 10 --offset 0

# List next page of labels
$ trcli -h https://yourinstance.testrail.io --username <your_username> --password <your_password> \
  --project "Your Project" \
  labels list --limit 10 --offset 10
```

**Output example:**
```
Retrieving labels...
Found 5 labels:
  ID: 123, Title: 'Critical'
  ID: 124, Title: 'Release-2.0'
  ID: 125, Title: 'Regression'
  ID: 126, Title: 'Bug-Fix'
  ID: 127, Title: 'Performance'
```

###### Getting Label Details
Retrieve detailed information about a specific label by its ID.

```shell
# Get details for a specific label
$ trcli -h https://yourinstance.testrail.io --username <your_username> --password <your_password> \
  --project "Your Project" \
  labels get --id 123
```

**Output example:**
```
Retrieving label with ID 123...
Label details:
  ID: 123
  Title: 'Critical'
  Created by: 2
  Created on: 1234567890
```

###### Updating Labels
Modify the title of existing labels (maximum 20 characters).

```shell
# Update a label's title
$ trcli -h https://yourinstance.testrail.io --username <your_username> --password <your_password> \
  --project "Your Project" \
  labels update --id 123 --title "High-Priority"
```

**Output example:**
```
Updating label with ID 123...
Successfully updated label: ID=123, Title='High-Priority'
```

###### Deleting Labels
Remove single or multiple labels from your project.

```shell
# Delete a single label
$ trcli -h https://yourinstance.testrail.io --username <your_username> --password <your_password> \
  --project "Your Project" \
  labels delete --ids 123

# Delete multiple labels (batch operation)
$ trcli -h https://yourinstance.testrail.io --username <your_username> --password <your_password> \
  --project "Your Project" \
  labels delete --ids "123,124,125"

```

**Output example:**
```
Are you sure you want to delete these labels? [y/N]: y
Deleting labels with IDs: 123,124...
Successfully deleted 2 label(s)
```

###### Common Use Cases

**1. Release Management**
```shell
# Create release-specific labels
$ trcli -h https://yourinstance.testrail.io --username <your_username> --password <your_password> \
  --project "Mobile App" \
  labels add --title "Sprint-42"

$ trcli -h https://yourinstance.testrail.io --username <your_username> --password <your_password> \
  --project "Mobile App" \
  labels add --title "Hotfix-2.1.3"
```

**2. Test Categorization**
```shell
# Create test type labels
$ trcli -h https://yourinstance.testrail.io --username <your_username> --password <your_password> \
  --project "API Tests" \
  labels add --title "Smoke"

$ trcli -h https://yourinstance.testrail.io --username <your_username> --password <your_password> \
  --project "API Tests" \
  labels add --title "Integration"

$ trcli -h https://yourinstance.testrail.io --username <your_username> --password <your_password> \
  --project "API Tests" \
  labels add --title "E2E"
```

**3. Priority and Severity**
```shell
# Create priority labels
$ trcli -h https://yourinstance.testrail.io --username <your_username> --password <your_password> \
  --project "Bug Tracking" \
  labels add --title "P0-Critical"

$ trcli -h https://yourinstance.testrail.io --username <your_username> --password <your_password> \
  --project "Bug Tracking" \
  labels add --title "P1-High"
```

**4. Cleanup Operations**
```shell
# List all labels to identify unused ones
$ trcli -h https://yourinstance.testrail.io --username <your_username> --password <your_password> \
  --project "Old Project" \
  labels list

# Bulk delete obsolete labels
$ trcli -h https://yourinstance.testrail.io --username <your_username> --password <your_password> \
  --project "Old Project" \
  labels delete --ids "100,101,102,103,104"
```

###### Command Options Reference

**Add Command:**
```shell
$ trcli labels add --help
Options:
  --title  Title of the label to add (max 20 characters) [required]
  --help    Show this message and exit.
```

**List Command:**
```shell
$ trcli labels list --help
Options:
  --offset   Offset for pagination (default: 0)
  --limit    Limit for pagination (default: 250, max: 250)
  --help     Show this message and exit.
```

**Get Command:**
```shell
$ trcli labels get --help
Options:
  --id     ID of the label to retrieve [required]
  --help   Show this message and exit.
```

**Update Command:**
```shell
$ trcli labels update --help
Options:
  --id     ID of the label to update [required]
  --title  New title for the label (max 20 characters) [required]
  --help   Show this message and exit.
```

**Delete Command:**
```shell
$ trcli labels delete --help
Options:
  --ids  Comma-separated list of label IDs to delete [required]
  --help Show this message and exit.
```

###### Error Handling and Validation

The labels command includes comprehensive validation:

- **Title Length**: Label titles are limited to 20 characters maximum
- **ID Validation**: Label IDs must be valid integers
- **Batch Operations**: Multiple label IDs must be comma-separated
- **Confirmation Prompts**: Delete operations require user confirmation (can be bypassed with `-y`)

**Example error scenarios:**
```shell
# Title too long (>20 characters)
$ trcli <host,credentials> labels add --title "This title is way too long for validation"
Error: Label title must be 20 characters or less.

# Invalid label ID
$ trcli <host,credentials> labels get --id 999999
Failed to retrieve label: Label not found

# Invalid ID format in batch delete
$ trcli <host,credentials> labels delete --ids "abc,def"
Error: Invalid label IDs format
```

#### Test Case Labels

In addition to project-level labels, the TestRail CLI also supports **test case label management** through the `labels cases` command. This functionality allows you to assign labels to specific test cases and filter test cases by their labels, providing powerful organization and filtering capabilities for your test suite.

###### Test Case Label Features
- **Add labels to test cases**: Apply existing or new labels to one or multiple test cases
- **List test cases by labels**: Find test cases that have specific labels applied
- **Automatic label creation**: Labels are created automatically if they don't exist when adding to cases
- **Maximum label validation**: Enforces TestRail's limit of 10 labels per test case
- **Flexible filtering**: Search by label ID or title

###### Reference
```shell
$ trcli labels cases --help
Usage: trcli labels cases [OPTIONS] COMMAND [ARGS]...

  Manage labels for test cases

Options:
  --help  Show this message and exit.

Commands:
  add   Add a label to test cases
  list  List test cases filtered by label ID or title
```

###### Adding Labels to Test Cases
Apply labels to one or multiple test cases. If the label doesn't exist, it will be created automatically.

```shell
# Add a label to a single test case
$ trcli -h https://yourinstance.testrail.io --username <your_username> --password <your_password> \
  --project "Your Project" \
  labels cases add --case-ids 123 --title "Regression"

# Add a label to multiple test cases
$ trcli -h https://yourinstance.testrail.io --username <your_username> --password <your_password> \
  --project "Your Project" \
  labels cases add --case-ids "123,124,125" --title "Critical"

# Add a release label to test cases
$ trcli -h https://yourinstance.testrail.io --username <your_username> --password <your_password> \
  --project "Your Project" \
  labels cases add --case-ids "100,101,102" --title "Sprint-42"
```

###### Listing Test Cases by Labels
Find test cases that have specific labels applied, either by label ID or title.

```shell
# List test cases by label title
$ trcli -h https://yourinstance.testrail.io --username <your_username> --password <your_password> \
  --project "Your Project" \
  labels cases list --title "Regression"

# List test cases by label ID
$ trcli -h https://yourinstance.testrail.io --username <your_username> --password <your_password> \
  --project "Your Project" \
  labels cases list --ids 123

# List test cases by multiple label IDs
$ trcli -h https://yourinstance.testrail.io --username <your_username> --password <your_password> \
  --project "Your Project" \
  labels cases list --ids "123,124,125"
```

**Output example:**
```
Retrieving test cases with label title 'Regression'...
Found 3 matching test case(s):

  Case ID: 123, Title: 'Login functionality test' [Labels: ID:5,Title:'Regression'; ID:7,Title:'Critical']
  Case ID: 124, Title: 'Password validation test' [Labels: ID:5,Title:'Regression']
  Case ID: 125, Title: 'User registration test' [Labels: ID:5,Title:'Regression'; ID:8,Title:'UI']
```

**No matches example:**
```
Retrieving test cases with label title 'Non-Existent'...
Found 0 matching test case(s):
  No test cases found with label title 'Non-Existent'.
```

###### Command Options Reference

**Add Cases Command:**
```shell
$ trcli labels cases add --help
Options:
  --case-ids  Comma-separated list of test case IDs [required]
  --title     Title of the label to add (max 20 characters) [required]
  --help      Show this message and exit.
```

**List Cases Command:**
```shell
$ trcli labels cases list --help
Options:
  --ids           Comma-separated list of label IDs to filter by
  --title         Label title to filter by (max 20 characters)
  --help          Show this message and exit.
```

###### Validation Rules

**Test Case Label Management includes these validations:**

- **Label Title**: Maximum 20 characters (same as project labels)
- **Case IDs**: Must be valid integers in comma-separated format
- **Maximum Labels**: Each test case can have maximum 10 labels
- **Filter Requirements**: Either `--ids` or `--title` must be provided for list command
- **Label Creation**: Labels are automatically created if they don't exist when adding to cases
- **Duplicate Prevention**: Adding an existing label to a case is handled gracefully

#### Test Labels

The TestRail CLI also supports **test label management** through the `labels tests` command. This functionality allows you to assign labels to specific tests (instances of test cases within test runs), providing powerful organization and filtering capabilities for your test execution.

###### Test Label Features
- **Add labels to tests**: Apply existing or new labels to one or multiple tests
- **CSV file support**: Bulk assign labels using CSV files containing test IDs
- **List tests by labels**: Find tests that have specific labels applied
- **Get test labels**: Retrieve all labels assigned to specific tests
- **Automatic label creation**: Labels are created automatically if they don't exist when adding to tests
- **Maximum label validation**: Enforces TestRail's limit of 10 labels per test
- **Flexible filtering**: Search by label ID for efficient test management

###### Reference
```shell
$ trcli labels tests --help
Usage: trcli labels tests [OPTIONS] COMMAND [ARGS]...

  Manage labels for tests

Options:
  --help  Show this message and exit.

Commands:
  add   Add a label to tests
  list  List tests filtered by label ID
  get   Get the labels of tests using test IDs
```

###### Adding Labels to Tests
Apply labels to one or multiple tests. If the label doesn't exist, it will be created automatically.

```shell
# Add a label to a single test
$ trcli -h https://yourinstance.testrail.io --username <your_username> --password <your_password> \
  --project "Your Project" \
  labels tests add --test-ids 123 --title "Regression"

# Add a label to multiple tests
$ trcli -h https://yourinstance.testrail.io --username <your_username> --password <your_password> \
  --project "Your Project" \
  labels tests add --test-ids "123,124,125" --title "Critical"

# Add a label to tests using CSV file
$ trcli -h https://yourinstance.testrail.io --username <your_username> --password <your_password> \
  --project "Your Project" \
  labels tests add --test-id-file test_ids.csv --title "Sprint-42"
```

**CSV File Format:**
The CSV file should contain test IDs, one per row or comma-separated. Headers are automatically detected and skipped.
```csv
test_id
123
124
125
```

Or simple format:
```csv
123,124,125
```

###### Listing Tests by Labels
Find tests that have specific labels applied by label ID from specific test runs.

```shell
# List tests by label ID from a specific run
$ trcli -h https://yourinstance.testrail.io --username <your_username> --password <your_password> \
  --project "Your Project" \
  labels tests list --run-id 456 --ids 123

# List tests by multiple label IDs from multiple runs
$ trcli -h https://yourinstance.testrail.io --username <your_username> --password <your_password> \
  --project "Your Project" \
  labels tests list --run-id "456,457" --ids "123,124,125"
```

**Output example:**
```
Retrieving tests from run IDs: 456 with label IDs: 123...
Found 2 matching test(s):

  Test ID: 1001, Title: 'Login functionality test', Status: 1 [Labels: ID:123,Title:'Regression'; ID:124,Title:'Critical']
  Test ID: 1002, Title: 'Password validation test', Status: 2 [Labels: ID:123,Title:'Regression']
```

###### Getting Test Labels
Retrieve all labels assigned to specific tests.

```shell
# Get labels for a single test
$ trcli -h https://yourinstance.testrail.io --username <your_username> --password <your_password> \
  --project "Your Project" \
  labels tests get --test-ids 123

# Get labels for multiple tests
$ trcli -h https://yourinstance.testrail.io --username <your_username> --password <your_password> \
  --project "Your Project" \
  labels tests get --test-ids "123,124,125"
```

**Output example:**
```
Retrieving labels for 2 test(s)...
Test label information:

  Test ID: 123
    Title: 'Login functionality test'
    Status: 1
    Labels (2):
      - ID: 5, Title: 'Regression'
      - ID: 7, Title: 'Critical'

  Test ID: 124
    Title: 'Password validation test'
    Status: 2
    Labels: No labels assigned
```

###### Command Options Reference

**Add Tests Command:**
```shell
$ trcli labels tests add --help
Options:
  --test-ids      Comma-separated list of test IDs (e.g., 1,2,3)
  --test-id-file  CSV file containing test IDs
  --title         Title of the label to add (max 20 characters) [required]
  --help          Show this message and exit.
```

**List Tests Command:**
```shell
$ trcli labels tests list --help
Options:
  --run-id  Comma-separated list of run IDs to filter tests from [required]
  --ids     Comma-separated list of label IDs to filter by [required]
  --help    Show this message and exit.
```

**Get Tests Command:**
```shell
$ trcli labels tests get --help
Options:
  --test-id  Comma-separated list of test IDs (e.g., 1,2,3) [required]
  --help     Show this message and exit.
```

###### Validation Rules

**Test Label Management includes these validations:**

- **Label Title**: Maximum 20 characters (same as project and case labels)
- **Test IDs**: Must be valid integers in comma-separated format
- **Maximum Labels**: Each test can have maximum 10 labels
- **Input Requirements**: Either `--test-ids` or `--test-id-file` must be provided for add command
- **Label Creation**: Labels are automatically created if they don't exist when adding to tests
- **Duplicate Prevention**: Adding an existing label to a test is handled gracefully
- **CSV File Validation**: Invalid entries in CSV files are ignored with warnings

###### Common Use Cases

**1. Test Execution Categorization**
```shell
# Label tests by execution type
$ trcli -h https://yourinstance.testrail.io --username <your_username> --password <your_password> \
  --project "API Tests" \
  labels tests add --test-ids "1001,1002,1003" --title "Smoke"

$ trcli -h https://yourinstance.testrail.io --username <your_username> --password <your_password> \
  --project "API Tests" \
  labels tests add --test-ids "1004,1005" --title "Integration"
```

**2. Release Management**
```shell
# Label tests for specific releases
$ trcli -h https://yourinstance.testrail.io --username <your_username> --password <your_password> \
  --project "Mobile App" \
  labels tests add --test-ids "2001,2002,2003" --title "Release-2.0"

$ trcli -h https://yourinstance.testrail.io --username <your_username> --password <your_password> \
  --project "Mobile App" \
  labels tests add --test-id-file hotfix_tests.csv --title "Hotfix-2.1.3"
```

**3. Priority and Risk Assessment**
```shell
# Label tests by priority
$ trcli -h https://yourinstance.testrail.io --username <your_username> --password <your_password> \
  --project "E-Commerce" \
  labels tests add --test-ids "3001,3002" --title "P0-Critical"

$ trcli -h https://yourinstance.testrail.io --username <your_username> --password <your_password> \
  --project "E-Commerce" \
  labels tests add --test-ids "3003,3004,3005" --title "P1-High"
```

**4. Test Analysis and Reporting**
```shell
# Find all regression tests from run 101
$ trcli -h https://yourinstance.testrail.io --username <your_username> --password <your_password> \
  --project "Web App" \
  labels tests list --run-id 101 --ids 5

# Get detailed label information for failed tests
$ trcli -h https://yourinstance.testrail.io --username <your_username> --password <your_password> \
  --project "Web App" \
  labels tests get --test-ids "4001,4002,4003"
```

#### References Management

The TestRail CLI provides comprehensive reference management capabilities using the `references` command. References help link test assets to external requirements, user stories, or other documentation, making it easier to track test coverage and maintain traceability.

The TestRail CLI supports complete reference management for test cases with the following operations:
- **Add**: Add references to existing test cases without removing existing ones
- **Update**: Replace all existing references with new ones
- **Delete**: Remove all or specific references from test cases

All reference operations support validation and error handling, with a 2000-character limit for the total references field per test case.

##### Reference Management Features

**Test Case References Support:**
- **Add** references to test cases while preserving existing ones (2000 characters maximum, single or multiple test cases)
- **Update** references by replacing existing ones entirely
- **Delete** all references or specific references from test cases

###### Adding References to Test Cases
Add references to test cases without removing existing ones. New references are appended to any existing references.

```shell
# Add references to a single test case
$ trcli -h https://yourinstance.testrail.io --username <your_username> --password <your_password> \
  --project "Your Project" \
  references cases add --case-ids 123 --refs "REQ-001,REQ-002"

# Add references to multiple test cases
$ trcli -h https://yourinstance.testrail.io --username <your_username> --password <your_password> \
  --project "Your Project" \
  references cases add --case-ids "123,124,125" --refs "STORY-456,BUG-789"
```

**Output example:**
```
Adding references to 2 test case(s)...
References: REQ-001, REQ-002
  ✓ Test case 123: References added successfully
  ✓ Test case 124: References added successfully
Successfully added references to 2 test case(s)
```

###### Updating References on Test Cases
Replace all existing references with new ones. This completely overwrites any existing references.

```shell
# Update references for a single test case
$ trcli -h https://yourinstance.testrail.io --username <your_username> --password <your_password> \
  --project "Your Project" \
  references cases update --case-ids 123 --refs "REQ-003,REQ-004"

# Update references for multiple test cases
$ trcli -h https://yourinstance.testrail.io --username <your_username> --password <your_password> \
  --project "Your Project" \
  references cases update --case-ids "123,124" --refs "EPIC-100,STORY-200"
```

**Output example:**
```
Updating references for 2 test case(s)...
New references: REQ-003, REQ-004
  ✓ Test case 123: References updated successfully
  ✓ Test case 124: References updated successfully
Successfully updated references for 2 test case(s)
```

###### Deleting References from Test Cases
Remove all references or specific references from test cases.

```shell
# Delete all references from test cases
$ trcli -h https://yourinstance.testrail.io --username <your_username> --password <your_password> \
  --project "Your Project" \
  references cases delete --case-ids "123,124"

# Delete specific references from test cases
$ trcli -h https://yourinstance.testrail.io --username <your_username> --password <your_password> \
  --project "Your Project" \
  references cases delete --case-ids "123,124" --refs "REQ-001,STORY-456"
```

**Output example:**
```
Deleting all references from 2 test case(s)...
  ✓ Test case 123: All references deleted successfully
  ✓ Test case 124: All references deleted successfully
Successfully deleted references from 2 test case(s)
```

##### Reference Management Command Reference

**Main References Command:**
```shell
$ trcli references --help
Usage: trcli references [OPTIONS] COMMAND [ARGS]...

  Manage references in TestRail

Options:
  --help  Show this message and exit.

Commands:
  cases  Manage references for test cases
```

**Test Cases References Commands:**
```shell
$ trcli references cases --help
Usage: trcli references cases [OPTIONS] COMMAND [ARGS]...

  Manage references for test cases

Options:
  --help  Show this message and exit.

Commands:
  add     Add references to test cases
  delete  Delete all or specific references from test cases
  update  Update references on test cases by replacing existing ones
```

**Add References Command:**
```shell
$ trcli references cases add --help
Options:
  --case-ids  Comma-separated list of test case IDs [required]
  --refs      Comma-separated list of references to add [required]
  --help      Show this message and exit.
```

**Update References Command:**
```shell
$ trcli references cases update --help
Options:
  --case-ids  Comma-separated list of test case IDs [required]
  --refs      Comma-separated list of references to replace existing ones [required]
  --help      Show this message and exit.
```

**Delete References Command:**
```shell
$ trcli references cases delete --help
Options:
  --case-ids  Comma-separated list of test case IDs [required]
  --refs      Comma-separated list of specific references to delete (optional)
  --help      Show this message and exit.
```

### Reference
```shell
$ trcli add_run --help
TestRail CLI v1.12.6
Copyright 2025 Gurock Software GmbH - www.gurock.com
Usage: trcli add_run [OPTIONS]

Options:
  --title                Title of Test Run to be created or updated in
                         TestRail.
  --run-id               ID of existing test run to update. If not provided, 
                         a new run will be created.  [x>=1]
  --suite-id             Suite ID to submit results to.  [x>=1]
  --run-description      Summary text to be added to the test run.
  --milestone-id         Milestone ID to which the Test Run should be
                         associated to.  [x>=1]
  --run-start-date       The expected or scheduled start date of this test run in MM/DD/YYYY format
  --run-end-date         The expected or scheduled end date of this test run in MM/DD/YYYY format
  --run-assigned-to-id   The ID of the user the test run should be assigned
                         to.  [x>=1]
  --run-include-all      Use this option to include all test cases in this test run.
  --auto-close-run       Use this option to automatically close the created run.
  --run-case-ids         Comma separated list of test case IDs to include in
                         the test run (i.e.: 1,2,3,4).
  --run-refs             A comma-separated list of references/requirements (up to 250 characters)
  --run-refs-action      Action to perform on references: 'add' (default), 'update' (replace all), 
                         or 'delete' (remove all or specific)
  -f, --file             Write run title and id to file.
  --help                 Show this message and exit.
```

If the file parameter is used, the run title and id are written to the file in yaml format. Example:
```text
title: Run Title
run_id: 1
```

This file can be used as the config file (or appended to an existing config file) in a later run.

### Managing References in Test Runs

The `add_run` command supports comprehensive reference management for test runs. References are stored in TestRail's "References" field and can contain up to 250 characters.

#### Adding References to New Runs

When creating a new test run, you can add references using the `--run-refs` option:

```bash
trcli -y -h https://example.testrail.io/ --project "My Project" \
  add_run --title "My Test Run" --run-refs "JIRA-100,JIRA-200,REQ-001"
```

#### Managing References in Existing Runs

For existing test runs, you can use the `--run-refs-action` option to specify how references should be handled:

**Add References (default behavior):**
```bash
trcli -y -h https://example.testrail.io/ --project "My Project" \
  add_run --run-id 123 --title "My Test Run" \
  --run-refs "JIRA-300,JIRA-400" --run-refs-action "add"
```

**Update (Replace) All References:**
```bash
trcli -y -h https://example.testrail.io/ --project "My Project" \
  add_run --run-id 123 --title "My Test Run" \
  --run-refs "NEW-100,NEW-200" --run-refs-action "update"
```

**Delete Specific References:**
```bash
trcli -y -h https://example.testrail.io/ --project "My Project" \
  add_run --run-id 123 --title "My Test Run" \
  --run-refs "JIRA-100,JIRA-200" --run-refs-action "delete"
```

**Delete All References:**
```bash
trcli -y -h https://example.testrail.io/ --project "My Project" \
  add_run --run-id 123 --title "My Test Run" \
  --run-refs-action "delete"
```

#### Reference Management Rules

- **Character Limit**: References field supports up to 250 characters
- **Format**: Comma-separated list of reference IDs
- **Duplicate Prevention**: When adding references, duplicates are automatically prevented
- **Action Requirements**: `update` and `delete` actions require an existing run (--run-id must be provided)
- **Validation**: Invalid reference formats are rejected with clear error messages

#### Examples

**Complete Workflow Example:**
```bash
# 1. Create run with initial references
trcli -y -h https://example.testrail.io/ <--username and --password or --key> --project "My Project" \
  add_run --title "Sprint 1 Tests" --run-refs "JIRA-100,JIRA-200" -f "run_config.yml"

# 2. Add more references (from the config file)
trcli -y -h https://example.testrail.io/ <--username and --password or --key>  --project "My Project" \
  -c run_config.yml add_run --run-refs "JIRA-300,REQ-001" --run-refs-action "add"

# 3. Replace all references with new ones
trcli -y -h https://example.testrail.io/ <--username and --password or --key>  --project "My Project" \
  -c run_config.yml add_run --run-refs "FINAL-100,FINAL-200" --run-refs-action "update"

# 4. Remove specific references
trcli -y -h https://example.testrail.io/ <--username and --password or --key>  --project "My Project" \
  -c run_config.yml add_run --run-refs "FINAL-100" --run-refs-action "delete"

# 5. Clear all references
trcli -y -h https://example.testrail.io/ <--username and --password or --key>  --project "My Project" \
  -c run_config.yml add_run --run-refs-action "delete"
```

Generating test cases from OpenAPI specs
-----------------

The `parse_openapi` command allows you to automatically generate and upload test cases to TestRail based on an
OpenAPI specification. This feature is intended to be used once to quickly bootstrap your test case design,
providing you with a solid base of test cases, which you can further expand on TestRail.

### Reference
```shell
$ trcli parse_openapi --help
TestRail CLI v1.12.6
Copyright 2025 Gurock Software GmbH - www.gurock.com
Usage: trcli parse_openapi [OPTIONS]

  Parse OpenAPI spec and create cases in TestRail

Options:
  -f, --file      Filename and path.
  --suite-id      Suite ID to create the tests in (if project is multi-suite).
                  [x>=1]
  --case-fields   List of case fields and values for new test cases creation.
                  Usage: --case-fields type_id:1 --case-fields priority_id:3
  --help          Show this message and exit.
```

### OpenAPI specification example
```yaml
openapi: 3.0.0
info:
  description: This is a sample API.
  version: 1.0.0
  title: My API
paths:
  /pet:
    post:
      summary: Add a new pet to the store
      description: Add new pet to the store inventory.
      operationId: addPet
      responses:
        '200':
          description: Pet created
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/Pet'
        '400':
          description: Invalid request
      requestBody:
        $ref: '#/components/schemas/Pet'
  '/pet/{petId}':
    get:
      summary: Find pet by ID
      description: Returns a single pet
      operationId: getPetById
      parameters:
        - name: petId
          in: path
          description: ID of pet to return
          required: true
          schema:
            type: integer
            format: int64
      responses:
        '200':
          description: Successful operation
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/Pet'
        '400':
          description: Invalid request
        '404':
          description: Pet not found
components:
  schemas:
    Pet:
      type: object
      required:
        - name
      properties:
        id:
          type: integer
          format: int64
          readOnly: true
        name:
          description: The name given to a pet
          type: string
          example: Guru
```

### Generating test cases

The test cases are generated based on the OpenAPI specification paths, operation verbs and possible response
status codes, which provides a good basic test coverage for an API, although we recommend you further
expand your test cases to cover specific business logic and workflows.

| Pattern                               | Test case title example                           |
|---------------------------------------|---------------------------------------------------|
| `VERB /path -> status_code (summary)` | `GET /pet/{petId} -> 200 (Successful operation) ` |

Parameter sources
-----------------
You can choose to set parameters from different sources, like a default config file,
environment variables, custom config file, cli parameters or in some cases use
default values.
The priority of setting parameters from different sources is as per the table below, where 1 is the highest priority.

| priority | source                |
|----------|-----------------------|
| 1        | cli parameters        |
| 2        | custom config file    |
| 3        | environment variables |
| 4        | default config file   |
| 5        | default value         |

For more details, please refer to the [Parameter sources](https://support.gurock.com/hc/en-us/articles/12974525736084) documentation. 

Return values and messaging
---------------------------
trcli tool will return `0` to the console in case of success and value greater than `1` (usually `1` or `2`) in other cases.
Messages that are being printed on the console are being redirected to `sys.stdout` or `sys.stderr`.


Multithreading
--------------
trcli allows users to upload test cases and results using multithreading. This is enabled by default and set to `MAX_WORKERS_ADD_CASE = 5` and
 `MAX_WORKERS_ADD_RESULTS = 10` in `trcli/settings.py`. To disable multithreading, set those to `1`.

During performance tests we discovered that using more than 10 workers didn't improve time of upload and could cause errors. Please set it accordingly to your machine specs.
Average time for uploading:
- 2000 test cases was around 460 seconds
- 5000 test cases was around 1000 seconds

### Parallel Pagination (Experimental)

The TestRail CLI includes an experimental `--parallel-pagination` option that significantly improves performance when fetching large numbers of test cases from TestRail. This feature uses parallel fetching to retrieve multiple pages of results concurrently, rather than fetching them sequentially.

#### When to Use Parallel Pagination

Use `--parallel-pagination` when:
- Working with projects that have thousands of test cases
- Fetching test cases takes a long time during operations
- You need faster case matching and validation during result uploads

#### How It Works

When enabled, parallel pagination:
1. Fetches the first page to determine total pages available
2. Uses a thread pool (default: 10 workers set by `MAX_WORKERS_PARALLEL_PAGINATION` in `trcli/settings.py`) to fetch remaining pages concurrently
3. Automatically handles batching to avoid overwhelming the server
4. Combines all results efficiently for processing

#### Usage

Enable parallel pagination by adding the `--parallel-pagination` flag to any command:

```shell
# Enable parallel pagination for faster case fetching during result upload
$ trcli parse_junit -f results.xml --parallel-pagination \
  --host https://yourinstance.testrail.io --username <your_username> --password <your_password> \
  --project "Your Project"

# Example with parse_robot
$ trcli parse_robot -f output.xml --parallel-pagination \
  --host https://yourinstance.testrail.io --username <your_username> --password <your_password> \
  --project "Your Project"
```

You can also enable this feature globally by setting `ENABLE_PARALLEL_PAGINATION = True` in `trcli/settings.py`. The CLI flag takes precedence over the settings file.

#### Performance Considerations

- This feature is most beneficial when dealing with large test case repositories (1000+ cases)
- The default worker count is set to 10, which provides a good balance between speed and server load
- For smaller projects with few test cases, the performance improvement may be negligible
- This is an experimental feature - please report any issues you encounter


Contributing
------------
Interested in contributing and helping improve the TestRail CLI client? Please start by looking into [CONTRIBUTING.md](https://github.com/gurock/trcli/blob/main/CONTRIBUTING.md) and creating an issue.


License
-------
The TestRail CLI client is licensed under the [Mozilla Public License 2.0](https://github.com/gurock/trcli/blob/main/LICENSE.md).
