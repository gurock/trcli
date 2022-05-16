Contribution guidelines
=======================

Unit Tests
----------

### Running tests
Ensure testing libraries are installed. In the root directory, run:<br>
`python3 -m pip install -r ./tests/requirements.txt`<br>
To run all tests:<br>
`python3 -m pytest -c ./tests/pytest.ini -W ignore::pytest.PytestCollectionWarning --alluredir=./allure-results`<br>
List of all test markers can be found by running:<br>
`pytest --markers -c ./tests/pytest.ini`<br>

### Folder structure
| Folder    | description                                                                                                            |
|-----------|------------------------------------------------------------------------------------------------------------------------|
| helpers   | modules used during the tests usually to prepare needed data                                                           |
| test_data | data used during the tests (files with input data, expected results, structures passed as pytest.mark.parameters etc.) |

### Jenkins configuration
Jenkinsfile can be used to configure jenkins build (for unit tests). It can be found in
root folder.

Code structure
--------------

### Folder structure
| Folder         | module               | description                                                                                                                                                                                                                   |
|----------------|----------------------|-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| api            | -                    | modules to be used to communicate with TestRail over API.                                                                                                                                                                     |
| api            | api_client           | Used for basic communication with TestRail over API. Handles retries and timeouts.                                                                                                                                            |
| api            | api_request_handler  | Used for API communication with TestRail (getting and adding resources). It uses api_client for basic communication and api_data_provider to get bodies from internal data classes. <br>                                      |
| api            | api_response_verify  | Used for verifying the response from TestRail.                                                                                                                                                                                |
| api            | results_uploader     | Used for uploading the results into TestRail instance.                                                                                                                                                                        |
| commands       | -                    | commands that extends parsing functionality. For more details please check [Parsers](#Parsers) section.                                                                                                                       |
| commands       | cmd_parse_junit      | Junit parser command. It's used together with cli module. The idea is to have separate commands for different file parsers. This way it should be easier to extend trcli in case other result file format needs to be parsed. |
| data_classes   | -                    | modules that are responsible for storing data parsed from result files in unified format                                                                                                                                      |
| data_classes   | dataclass_testrail   | Used to store data parsed from result file. Contains common structures that are reflecting data structures within TestRail. Each reader should parse result file to those structures.                                         |
| data_classes   | validation_exception | Exception raised on validation errors                                                                                                                                                                                         |
| data_providers | -                    | module that is responsible for creating bodies for API calls                                                                                                                                                                  |
| data_providers | api_data_provider    | Module that is responsible for creating bodies for API calls                                                                                                                                                                  |
| readers        | -                    | modules that are responsible for parsing result files into internal data classes. Check [Parsers](#Parsers) section for more details                                                                                          |
| readers        | file_parser          | Contains basic abstract class to be used to create all results parsers.                                                                                                                                                       |
| readers        | junit_xml            | Junit result file parser. Used to parse result files into internal data structures.                                                                                                                                           |
| root           | constants            | Contains constants used in whole code (error messages, prompt slogans, --help related strings etc.)                                                                                                                           |
| root           | settings             | Multithreading and some default settings.                                                                                                                                                                                     |
| root           | cli                  | Main cli module responsible for parsing parameters from command line. It parses all parameters and runtime information into Environment class.                                                                                |

### Parsers
Parsers are located in `/trcli/readers/`. To add a new parser please read the desired file and fill required dataclasses with the data (located in `/trcli/data_classes/`).

### Sending information to user (logging/prompting)
For printing messages on console and prompting users functions from Environment class should be used. <br>Those functions handles `--silent/--verbose/--yes/--no` parameters properly.
