trcli - The TestRail CLI client
================================
TR CLI (trcli) is a command line tool for interacting with TestRail.

Configuration files
===================
Configuration files can be used to pass parameters, options, settings
and preferences to trcli tool. The configuration files should be written in YAML format.

Possible fields:<br>
host - specifies the URL of the TestRail instance in which to send the results<br>
project - specifies the name of the Project the Test Run should be created under<br>
file - specifies the filename and/or path of the result file to be used<br>
title -  Specifies the title of the Test Run to be created in TestRail<br>
verbose - enables verbose mode when true (false by default)<br>
silence - enables silence mode when true (false by default)<br>
config - specifies the filename and/or path of the configuration file to be used<br>
batch_size - specifies the batch size of results to pass to TestRail ((50 by default, maximum to be determined by Dev Partner stress testing)<br>
timeout - specifies how many seconds to wait for more results before termination (30 by default)<br>
auto_creation_response - Sets the response for auto creation prompts (Yes/No). If not set user will be prompted whether to create resources (suite, test case etc.) or not.<br>
suite_id - specifies the Suite ID for the Test Run to be created under<br>
run_id - specifies the Run ID for the Test Run to be created under<br>

Default configuration file
--------------------------
Default configuration file should be named config.yaml and be stored in the same directory
as the trcli executable file.

Custom configuration file
-------------------------
Apart from default configuration file a custom one can be passed after -c/--config
as a parameter. For more details check Command line section.

Environment variables
=====================
It is possible to pass parameters and options to trcli tool by setting environment variables.
The variable should be named as follows: TR_CLI_Parameter_name_capitalized

For exmaple for -c/--config: TR_CLI_CONFIG

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
  -c, --config PATH               Optional path definition for testrail-
                                  credentials file or CF file.
  -h, --host TEXT                 Hostname of instance.
  --project TEXT                  Name of project the Test Run should be
                                  created under.
  --title TEXT                    Title of Test Run to be created in TestRail.
  -u, --username TEXT             Username.
  -p, --password TEXT             Password.
  -k, --key TEXT                  API key.
  -v, --verbose                   Enables verbose logging.
  --verify                        Verify the data was added correctly.
  -b, --batch-size INTEGER RANGE  Configurable batch size.  [default: (50);
                                  x>=2]
  -t, --timeout INTEGER RANGE     Batch timeout duration.  [default: (30);
                                  x>=0]
  --suite-id INTEGER RANGE        Suite ID for the results they are reporting.
                                  [x>=1]
  --run-id INTEGER RANGE          Run ID for the results they are reporting
                                  (otherwise the tool will attempt to create a
                                  new run).  [x>=1]
  --case-id INTEGER RANGE         (otherwise the tool will attempt to create a
                                  new run).  [x>=1]
  -y, --yes                       answer 'yes' to all prompts around auto-
                                  creation
  -n, --no                        answer 'no' to all prompts around auto-
                                  creation
  -s, --silent                    Silence stdout
  --help                          Show this message and exit.

Commands:
  parse_junit
```

```
$ trcli parse_junit --help
Usage: trcli parse_junit [OPTIONS]

Options:
  -f, --file PATH  Filename and path.
  --help           Show this message and exit.
```

Installation
============
```
pip install .
```

