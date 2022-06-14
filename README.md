trcli - The TestRail CLI client
================================
TR CLI (trcli) is a command line tool for interacting with TestRail and uploading test automation results.

- Install the CLI tool on your system and run it as part of your build pipeline
- Automatically generate new test runs and upload results from automated tests
- Optionally create new test cases in TestRail for test cases scripted in your test automation suite

![Tests](https://github.com/gurock/trcli/actions/workflows/python-app.yml/badge.svg)

Installation
------------

If you already have [Python](https://www.python.org/) with [pip](https://pip.pypa.io) installed,
you can simply run:
```
pip install trcli
```
We recommend using Python 3.10 or newer.

Commands
--------
```
$ trcli
TestRail Connect v1.1.0
Copyright 2021 Gurock Software GmbH - www.gurock.com
Supported and loaded modules:
    - junit: JUnit XML Files (& Similar)
```

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

Parsers
-------

### parse_junit
For JUnit XML files compatible with Jenkins and pytest reporting schemas
```
$ trcli parse_junit --help
Usage: trcli parse_junit [OPTIONS]

  Parse report files and upload results to TestRail

Options:
  -f, --file           Filename and path.
  --close-run BOOLEAN  Whether to close the newly created run
  --title              Title of Test Run to be created in TestRail.
  --suite-id           Suite ID for the results they are reporting.  [x>=1]
  --run-id             Run ID for the results they are reporting (otherwise
                       the tool will attempt to create a new run).  [x>=1]
  --run-description    Summary text to be added to the test run.
  --case-fields        List of case fields and values for new test cases
                       creation. Usage: --case-fields type_id:1 --case-fields
                       priority_id:3
  --help               Show this message and exit.
```

#### JUnit XML report example
```xml
<testsuites name="test suites root">
  <testsuite failures="0" errors="0" skipped="1" tests="1" time="0.05" name="tests.LoginTests">
    <properties><property name="setting1" value="True"/></properties>
    <testcase classname="tests.LoginTests" name="test_case_1" time="159">
      <skipped type="pytest.skip" message="Please skip">skipped by user</skipped>
    </testcase>
    <testcase classname="tests.LoginTests" name="test_case_2" time="650">
    </testcase>
    <testcase classname="tests.LoginTests" name="test_case_3" time="159">
      <failure type="pytest.failure" message="Fail due to...">failed due to...</failure>
    </testcase>
  </testsuite>
</testsuites>
```

#### Mapping XML elements to TestRail entities

| XML junit file tag                                       | Test Rail mapped to                               |
|----------------------------------------------------------|---------------------------------------------------|
| \<testsuites>                                            | suite                                             |
| \<testsuite>                                             | section                                           |
| \<testcase>                                              | case                                              |
| \<testcase ***time=1***>                                 | run - elapsed time of test case execution         |
| \<testcase>***\<skipped or error>***\</testcase>         | run - result of case                              |
| \<error>***"message"***\</error>                         | run - comment result of case                      |
| \<properties>***\<property>\</property>***\</properties> | All properties joined and sent as run description |
| name or title attributes on every level                  | name                                              |


#### Uploading test results

When you upload a new JUnit XML file containing test automation results, the TestRail CLI will automatically generate a new test run with the test cases from your report file and upload the results.

To specify which test cases to add to the test run, the TestRail CLI will attempt to match the test cases in your automation suite to test cases in TestRail.

To allow for this, you must first add a new [custom field](https://www.gurock.com/testrail/docs/user-guide/howto/fields/) 
of type `String` with system name `automation_id`.

The TestRail CLI will use the unique combination of your automation test case’s classname and name (expressed as `classname.name`) to compare against values of the `automation_id` field in your TestRail test case repository.
If a match is found, this test case will be included in the auto-generated test run for this upload. 

Example:

| Test Result from Automation Results File                                               | Automation ID in TestRail   |
|----------------------------------------------------------------------------------------|-----------------------------|
| ```<testcase classname="tests.LoginTests" name="test_case_1" time="159"></testcase>``` | test.LoginTests.test_case_1 |

```
Important usage notes: 

1. If you would like to upload automation results for test cases that already exist in TestRail, be sure to update the automation_id for those test cases before uploading your automation results
2. If you change the test name in your automation suite later, that will create a new test case in TestRail, unless you also update the automation_id field for the test case in TestRail
```

When you upload your test automation results, the TestRail CLI will prompt you to choose how it should handle test cases that it cannot match in TestRail:
- If you enter `yes`, the TestRail CLI will automatically add new test cases in TestRail based on your automation test case, and add the `classname.name` value to the Automation ID field of the new test case.
- If you enter `no`, the TestRail CLI will not automatically provision a test case in TestRail and will ignore your test automation result

If you are using the CLI tool in a CI context, you can use the `-y` option to automatically accept all prompts.

You can also provide the ID of the test suite you want the cases to be created in using the `--suite-id` command line option, otherwise the CLI tool will attempt to find the suite on TestRail by name.<br>


Setting parameters from different places
----------------------------------------
User can choose to set parameters from different places like default config file,
environment variables, custom config file, cli parameters or in some cases use
default values.
The priority (1-highest, 5-lowest) of setting parameters from different places is as follows:

| priority | source                |
|----------|-----------------------|
| 1        | cli parameters        |
| 2        | custom config file    |
| 3        | environment variables |
| 4        | default config file   |
| 5        | default value         |


### Configuration files
Configuration files can be used to pass parameters, options, settings
and preferences to the trcli tool. The configuration files should be written in YAML format.

We expect only `key: value`, `---` and `...`.

Possible fields:<br>

| Field name             | description                                                                                                                               |
|------------------------|-------------------------------------------------------------------------------------------------------------------------------------------|
| host                   | specifies the URL of the TestRail instance in which to send the results                                                                   |
| project                | specifies the name of the Project the Test Run should be created under                                                                    |
| project_id             | Project id. Will be only used in case project name will be duplicated in TestRail                                                         |
| username               | username                                                                                                                                  |
| password               | password                                                                                                                                  |
| key                    | API key                                                                                                                                   |
| file                   | specifies the filename and/or path of the result file to be used                                                                          |
| title                  | Specifies the title of the Test Run to be created in TestRail                                                                             |
| verbose                | enables verbose mode when true (false by default)                                                                                         |
| verify                 | verify the data was added correctly                                                                                                       |
| insecure               | allow insecure requests                                                                                                                   |
| silent                 | enables silence mode (only stdout) when true (false by default)                                                                           |
| config                 | specifies the filename and/or path of the configuration file to be used                                                                   |
| batch_size             | specifies the batch size of results to pass to TestRail                                                                                   |
| timeout                | specifies how many seconds to wait for more results before termination                                                                    |
| auto_creation_response | Sets the response for auto creation prompts. If not set user will be prompted whether to create resources (suite, test case etc.) or not. |
| suite_id               | specifies the Suite ID for the Test Run to be created under                                                                               |
| run_id                 | specifies the Run ID for the Test Run to be created under                                                                                 |
| close_run              | specifies whether to close the run after adding all the results (false by default)                                                        |
| case_fields            | dictionary with case fields to be filled on case creation as a key value pair                                                             |
| run_description        | text to be added to the run description (for example, if you want to add the link to your CI job)                                         |

Below is an example of a sample configuration file for the TestRail CLI.
```yaml
host: https://fakename.testrail.io/
project: Mockup Automation Project
username: myuser@name.com
password: StrongP@ssword
file: \<PATH\>/result_file.xml
title: Daily Selenium smoke test
config: \<PATH\>/alternate_config.yml
batch_size: 20
timeout: 5.5
auto_creation_response: true
case_fields: 
  type_id: 1,
  priority_id: 3
```

#### Default configuration file
Default configuration file should be named `config.yaml` or `config.yml` and be stored in the same directory as the trcli executable file. The default path for pip installation of executable depends on your system and python settings (venv).

Please check where trcli was installed by using `which trcli` or `where trcli` command
(depending on the operating system).

#### Custom configuration file
Apart from default configuration file a custom one can be passed after -c/--config
as a parameter. For more details check the [Commands](#Commands) section.


### Environment variables
It is possible to pass parameters and options to the trcli tool by setting environment variables.
The variables should be named as follows: `TR_CLI_PARAMETER_NAME_CAPITALIZED`

For example, for `-c`/`--config`: `TR_CLI_CONFIG`

```
Note: One exception to this rule is for --yes/--no parameters.
One should use: TR_CLI_AUTO_CREATION_RESPONSE (false/true).
true - agree for auto creation<br>
false - do not agree for auto creation
```

```
Note: In case there is a `-` in the parameter name it should be changed to `_`.
Example: for --project-id environment variable name will be TR_CLI_PROJECT_ID
```

```
Note: there are different ways of setting variables depending on system used.
Please make sure that value was set correctly.

example for setting environment variable (for single session) to string value:
set TR_CLI_PROJECT=project name for Windows
export TR_CLI_PROJECT="project name" for Linux-like systems
```


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
