![Tests](https://github.com/gurock/trcli/actions/workflows/python-app.yml/badge.svg)

trcli - The TestRail CLI
================================
The TestRail CLI (trcli) is a command line tool for interacting with TestRail and uploading test automation results.

- Install the CLI tool on your system and run it as part of your build pipeline
- Automatically generate new test runs and upload results from automated tests
- Optionally create new test cases in TestRail for test cases scripted in your test automation suite

To see more documentation about the TestRail CLI, please refer to the 
[TestRail CLI documentation pages](https://support.gurock.com/hc/en-us/articles/7146548750868-TestRail-CLI)
on the TestRail help center.

Installation
------------

If you already have [Python](https://www.python.org/) and [pip](https://pip.pypa.io) installed,
you can simply run the command below in your terminal. We recommend using **Python 3.10** or newer.
```
$ pip install trcli
```

To verify the installation was successful, you can run the `trcli` command.
```
$ trcli
TestRail CLI v1.4.0 
Copyright 2021 Gurock Software GmbH - www.gurock.com
Supported and loaded modules: 
- junit: JUnit XML Files (& Similar) 
```

CLI general reference
--------
```
$ trcli --help
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
  -k, --key          API key.
  -v, --verbose      Output all API calls and their results.
  --verify           Verify the data was added correctly.
  --insecure         Allow insecure requests.
  -b, --batch-size   Configurable batch size.  [default: (50); x>=2]
  -t, --timeout      Batch timeout duration.  [default: (30); x>=0]
  -y, --yes          answer 'yes' to all prompts around auto-creation
  -n, --no           answer 'no' to all prompts around auto-creation
  -s, --silent       Silence stdout
  --help             Show this message and exit.

Commands:
  parse_junit  Parse report files and upload results to TestRail
```

Parse JUnit Reference (Upload Results)
--------
```
$ trcli parse_junit --help
Usage: trcli parse_junit [OPTIONS]

  Parse report files and upload results to TestRail

Options:
  -f, --file          Filename and path.
  --close-run         Close the newly created run
  --title             Title of Test Run to be created in TestRail.
  --case-matcher      Mechanism to match cases between the JUnit report and
                      TestRail.
  --suite-id          Suite ID for the results they are reporting.  [x>=1]
  --run-id            Run ID for the results they are reporting (otherwise the
                      tool will attempt to create a new run).  [x>=1]
  --milestone-id      Milestone ID to which the Test Run should be associated
                      to.  [x>=1]
  --run-description   Summary text to be added to the test run.
  --case-fields       List of case fields and values for new test cases
                      creation. Usage: --case-fields type_id:1 --case-fields
                      priority_id:3
  --result-fields     List of result fields and values for test results
                      creation. Usage: --result-fields custom_field_a:value1
                      --result-fields custom_field_b:3
  --special-parser    Optional special parser option for specialized JUnit
                      reports.
  --allow-ms          Allows using milliseconds for elapsed times.
  --help              Show this message and exit.
```

JUnit XML report example
--------
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

Uploading test results
--------

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

### 1. Using Automation ID
To use this mechanism, you must first add a new [custom field](https://www.gurock.com/testrail/docs/user-guide/howto/fields/) 
of type `String` with system name `automation_id`.

The TestRail CLI will use the unique combination of your automation test case’s `classname` and `name` 
(expressed as `classname.name`) to compare against values of the `automation_id` field in your TestRail test case repository.
If a match is found, this test case will be included in the auto-generated test run for this upload. 

Example:

| Test Result from Automation Results File                                               | Automation ID in TestRail      |
|----------------------------------------------------------------------------------------|--------------------------------|
| ```<testcase classname="tests.LoginTests" name="test_case_1" time="159"></testcase>``` | `tests.LoginTests.test_case_1` |


> **Important usage notes:**
> 1. If you would like to upload automation results for test cases that already exist in TestRail, be sure to update the `automation_id` for those test cases before uploading your automation results
> 2. If you change the test name in your automation suite later, that will create a new test case in TestRail, unless you also update the `automation_id` field for the test case in TestRail
> 3. If you are using the CLI tool in a CI context, we recommend using the `-y` option to automatically accept test case creation prompts

For more detail, please refer to the [Automation workflows - Code-first](https://support.gurock.com/hc/en-us/articles/12609674354068)
documentation.

### 2. Using Case ID

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

Exploring other features
------------------------

### General features
Please refer to the [Usage examples](https://support.gurock.com/hc/en-us/articles/12908548726804) documentation page to see how you
can leverage all the functionalities provided by the TestRail CLI.

### SauceLabs saucectl reports
If you are using `saucectl` from SauceLabs to execute your automation projects, the TestRail CLI has an enhanced parser 
that fetches session information and adds it to your test runs. You can enable this functionality by using 
the `--special-parser saucectl` command line option.

Please refer to the [SauceLabs and saucectl reports](https://support.gurock.com/hc/en-us/articles/12719558686484)
documentation for further information.

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


Contributing
------------
Interested in contributing and helping improve the TestRail CLI client? Please start by looking into [CONTRIBUTING.md](https://github.com/gurock/trcli/blob/main/CONTRIBUTING.md) and creating an issue.


License
-------
The TestRail CLI client is licensed under the [Mozilla Public License 2.0](https://github.com/gurock/trcli/blob/main/LICENSE.md).
