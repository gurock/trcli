trcli - The TestRail CLI client
================================
TR CLI (trcli) is a command line tool for interacting with TestRail.

Configuration files
===================
Configuration files can be used to pass parameters, options, settings
and preferences to trcli tool. The configuration files should be written in YAML format.

We expect only `key: value`, `---` and `...`.

Possible fields:<br>

Field name|description 
---|---
host | specifies the URL of the TestRail instance in which to send the results<br>host: https://fakename.testrail.io/
project | specifies the name of the Project the Test Run should be created under<br>project: Mockup Automation Project
project_id | Project id. Will be only used in case project name will be duplicated in TestRail<br>project_id: 10
username | username<br>username: myuser@name.com
password | password<br>password: StrongP@ssword
key | API key<br>key: AGT9PBifAxgWEWNGQgh/-Dc7Dr/fWDvEkLJwPFLRn
file | specifies the filename and/or path of the result file to be used<br>file: \<PATH\>/result_file.xml
title |  Specifies the title of the Test Run to be created in TestRail<br>title: Daily Selenium smoke test
verbose | enables verbose mode when true (false by default)<br>verbose: false/true
verify | verify the data was added correctly<br>verify: false/true
silent | enables silence mode (only stdout) when true (false by default)<br>silent: false/true
config | specifies the filename and/or path of the configuration file to be used<br>config: \<PATH\>/alternate_config.yml
batch_size | specifies the batch size of results to pass to TestRail<br>batch_size: 20
timeout | specifies how many seconds to wait for more results before termination<br>timeout: 5.5
auto_creation_response | Sets the response for auto creation prompts. If not set user will be prompted whether to create resources (suite, test case etc.) or not.<br>auto_creation_response: false/true
suite_id | specifies the Suite ID for the Test Run to be created under<br>suite_id: 213
run_id | specifies the Run ID for the Test Run to be created under<br>run_id: 12
case_id | specifies the case ID to be updated with new results. If present also run_id needs to be provided<br>case_id: 123

Default configuration file
--------------------------
Default configuration file should be named `config.yaml` or `config.yml` and be stored in the same directory
as the trcli executable file. The default path for pip installation of executable depends on your system and python settings (venv).

Please check where TRCLI was installed by using `which trcli` or `where trcli` command
depending on the operating system.

Custom configuration file
-------------------------
Apart from default configuration file a custom one can be passed after -c/--config
as a parameter. For more details check [Command line](#Command-line) section.

Environment variables
=====================
It is possible to pass parameters and options to trcli tool by setting environment variables.
The variable should be named as follows: TR_CLI_Parameter_name_capitalized

For exmaple for -c/--config: TR_CLI_CONFIG

```
Note: One exception to this rule is for --yes/--no parameters.
One should use: TR_CLI_AUTO_CREATION_RESPONSE (false/true).
true - agree for auto creation<br>
false - do not agree for auto creation.
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

Command line
============
```
$ trcli
TestRail Connect v0.1
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
  --title            Title of Test Run to be created in TestRail.
  -u, --username     Username.
  -p, --password     Password.
  -k, --key          API key.
  -v, --verbose      Output all API calls and their results.
  --verify           Verify the data was added correctly.
  -b, --batch-size   Configurable batch size.  [default: (50); x>=2]
  -t, --timeout      Batch timeout duration.  [default: (30); x>=0]
  --suite-id         Suite ID for the results they are reporting.  [x>=1]
  --run-id           Run ID for the results they are reporting (otherwise the
                     tool will attempt to create a new run).  [x>=1]
  --case-id          Case ID for the results they are reporting (otherwise the
                     tool will attempt to create a new run).  [x>=1]
  -y, --yes          answer 'yes' to all prompts around auto-creation
  -n, --no           answer 'no' to all prompts around auto-creation
  -s, --silent       Silence stdout
  --help             Show this message and exit.

Commands:
  parse_junit  Parse Junit XML files (& similar)
```

Setting parameters from different places
========================================
User can choose to set parameters from different places like default config file,
environment variables, custom config file, cli parameters or in some cases use
default values.
The priority (1-highest, 5-lowest) of setting parameters from different places is as follows:

priority|source
 ---|---
1|cli parameters
2|custom config file
3|environment variables
4|default config file
5|default value


Installation
============

From the source code:
```
pip install .
```

Without cloning the repository:
```
pip install git+https://github.com/gurock/trcli.git
```

Return values and messaging
===========================
trcli tool will return `0` to the console in case of success and value greater than `1` (usually `1` or `2`) in other cases.
Messages that are being printed on the console are being redirected to `sys.stdout` or `sys.stderr`.

Parsers
=======

Parsers are located in `/trcli/readers/`. To add new parser please read desired file and fill required dataclasses with the data (located in `/trcli/data_classes/`).

Available commands/parsers:

`parse_junit` - XML Junit files compatibile with Jenkins and pytest reporting schemas
```
$ trcli parse_junit --help
Usage: trcli parse_junit [OPTIONS]

  Parse Junit XML files (& similar)

Options:
  -f, --file   Filename and path.
  --help       Show this message and exit.

```


XML junit file tag|Test Rail mapped to
 ---|---
\<testsuites>|suite
\<suite>|section
\<testcase>|case
\<testcase ***time=1***> | run - elapsed time of test case execution
\<testcase>***\<skipped or error>***\</testcase>|run - result of case
\<error>***"message"***\</error> | run - comment result of case
\<properties>***\<property>\</property>***\</properties> | All properties joined and sent as run description
name or title attributes on every level|name 


Uploading test results from Junit file
======================================

TR CLI tool expects suite, sections and test cases IDs to be present in result file.<br>
In case any of IDs are missing the tool will try to add new item to TestRail. This<br>
might result in multiple suites/sections/test cases with same name being created in TestRail.<br>
Adding those resources to TestRail will not be done automatically and each time some of<br>
them are missing in TestRail user will be prompted if such should be added.<br>
Example content of result_file.xml:
```
<testsuites name="test suites root">
  <testsuite id="47" failures="0" errors="0" skipped="1" tests="1" time="0.05" name="Skipped test">
    <properties><property name="setting1" value="True"/></properties>
    <testcase id="72" classname="tests.test_junit_to_dataclass" name="test_case_1" time="159">
      <skipped type="pytest.skip" message="Please skip">skipped by user</skipped>
    </testcase>
    <testcase id="73" classname="tests.test_junit_to_dataclass" name="test_case_2" time="650">
    </testcase>
    <testcase id="74" classname="tests.test_junit_to_dataclass" name="test_case_3" time="159">
      <failure type="pytest.failure" message="Fail due to...">failed due to...</failure>
    </testcase>
  </testsuite>
</testsuites>
```

```
Note: id was not added to the testsuite. It can be provided either in result file
or by providing parameter --suite-id to the command.
```

Updating test result for single case
====================================

Updating test results can be made by using `--case-id` parameter.<br>
In case of update only one result can be updated at once. Together with case ID <br>
`--run-id` needs to be specified.

For example when passing `--case-id 1983` and `--run-id 193` result for test with ID 1983
will be updated under run with ID 193.

```
None: `--case-id` needs to be set to test case ID not to test ID (the one that can be seen in test run).
```

Multithreading
====================================
TRCLI allows user to upload test cases and results using multithreading. This is enabled by default and set to `MAX_WORKERS_ADD_CASE = 5` and
 `MAX_WORKERS_ADD_RESULTS = 10` in `trcli/settings.py`. To disable multithreading set those to `1`.

During performance tests we discovered that using more than 10 workers didn't improve time of upload and could cause errors. Please set it accordingly to your machine specs.
Average time for uploading:
- 2000 test cases was around 460 seconds
- 5000 test cases was around 1000 seconds

Unit Tests
==========

Running tests
-------------
Ensure testing libraries are installed. In the root directory, run:<br>
`python3 -m pip install -r ./tests/requirements.txt`<br>
To run all tests:<br>
`python3 -m pytest -c ./tests/pytest.ini -W ignore::pytest.PytestCollectionWarning --alluredir=./allure-results`<br>
List of all test markers can be found by running:<br>
`pytest --markers -c ./tests/pytest.ini`<br>

Folder structure
----------------
Folder|description
---|---
helpers|modules used during the tests usually to prepare needed data 
test_data|data used during the tests (files with input data, expected results, structures passed as pytest.mark.parameters etc.)

Jenkins configuration
---------------------
Jenkinsfile can be used to configure jenkins build (for unit tests). It can be found in
root folder.

Code structure
==============
Folder structure
----------------
|Folder|module|description|
|---|---|---|
api|-|modules to be used to communicate with TestRail over API.
api|api_client|Used for basic communication with TestRail over API. Handles retries and timeouts.
api|api_request_handler|Used for API communication with TestRail (getting and adding resources). It uses api_client for basic communication and api_data_provider to get bodies from internal data classes. <br>
api|api_response_verify|Used for verifying the response from TestRail.
api|results_uploader|Used for uploading the results into TestRail instance.
commands|-|commands that extends parsing functionality. For more details please check [Parsers](#Parsers) section.
commands|cmd_parse_junit|Junit parser command. It's used together with cli module. The idea is to have separate commands for different file parsers. This way it should be easier to extend trcli in case other result file format needs to be parsed.
data_classes|-|modules that are responsible for storing data parsed from result files in unified format
data_classes|dataclass_testrail|Used to store data parsed from result file. Contains common structures that are reflecting data structures within TestRail. Each reader should parse result file to those structures.
data_classes|validation_exception|Exception raised on validation errors
data_providers|-|module that is responsible for creating bodies for API calls
data_providers|api_data_provider|Module that is responsible for creating bodies for API calls
readers|-|modules that are responsible for parsing result files into internal data classes. Check [Parsers](#Parsers) section for more details
readers|file_parser|Contains basic abstract class to be used to create all results parsers.
readers|junit_xml|Junit result file parser. Used to parse result files into internal data structures.
root|constants|Contains constants used in whole code (error messages, prompt slogans, --help related strings etc.)
root|settings|Multithreading and some default settings.
root|cli|Main cli module responsible for parsing parameters from command line. It parses all parameters and runtime information into Environment class. 

Sending information to user (logging/prompting)
-----------------------------------------------
For printing messages on console and prompting users functions from Environment class should be used. <br>Those functions handles `--silent/--verbose/--yes/--no` parameters properly.