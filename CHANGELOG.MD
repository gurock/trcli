TRCLI Changelog

This project adheres to [Semantic Versioning](https://semver.org/). Version numbers are formatted as `MAJOR.MINOR.PATCH`, where:

- **MAJOR**: Breaking changes, where backward compatibility is broken.
- **MINOR**: New features that are backward-compatible.
- **PATCH**: Bug fixes or minor changes that do not affect backward compatibility.

## [1.9.8]

_released 10-04-2024

### Fixed
 - Add Run description bug getting wiped; Fixes issue #250
### Added
 - NEW HTTP Proxy feature facility!

## [1.9.7]

_released 09-02-2024

### Fixed
- Fix a dependency issue on pyserde, reverted back to previous version in the 0.12.* series with less stricter type enforcement. Fixes #266 and #267.

## [1.9.6]

_released 08-30-2024

### Fixed
 - Request dependency version update; Fixes issue #234
 - Parsing for Glob; Fixes issue #241
 - Cleanup End to End tests
 - Fix unit tests assertions when ran via TOX
### Added
 - Add RUN Command; Resolves issue #236
 - Updated required dependencies flexibility
 - Added TOX for testing and dependencies automation

## [1.9.5]

_released 03-22-2024

### Fixed
- fixes #218 by trimming title to max characters
- fix #219 by adding missing elapsed time on test results for RF tests

## [1.9.4]

_released 03-09-2024

### Fixed

-[XML] Fix parsing of testrail_case_field with empty xml but value present 

## [1.9.3]

_released 03-07-2024

### Added
- added test for #212; support for processing properties using cdata 

## [1.9.2]

_released 03-06-2024

### Fixed
- fix #211 on wrong beartype dependency

## [1.9.1]

_released 03-05-2024

### Fixed

- limit test case title. fixes #207 

## [1.9.0]

_released 02-08-2024

### Added
- improve README.md copy paste
- preliminary support for Robot Framework 7.0 new output.xml format

## [1.8.0]

_released 12-21-2023

### Fixed
- Update setup.py with newer click version
- compatibility run on python 3.8 and 3.9 
- Added python 3.8 support

## [1.7.0]

_released 12-12-2023

### Fixed

- make title argument optional
- fixes #177, adding workaround for buggy legacy server response

## [1.6.3]

_released 12-07-2023

### Fixed
- remove unnecessary created sections
- fix issue #181 

## [1.6.2]

_released 08-27-2023

### Added
- End-to-end tests
- Keep existing suite on rollback: fix#166

## [1.6.1]

_released 09-11-2023

###Fixed
- Resolve legacy endpoint call

## [1.6.0]

_released 09-06-2023

### Added
- Native Robot Framework report parser using command parse_robot
- Test run update allows adding new tests
- Add new test run to a test plan using --plan-id option (with configurations support using the --config-ids option)
- Update test run inside test plans using --run-id only
- New JUnit property for result steps named (i.e.:  <property name="testrail_result_step" value="passed:Go to home page"/>)
- Select suite or create new suite using name with the --suite-name option
- Report path with wildcard support to merge multiple reports and submit results to one run (i.e.: -f junit-report-*)

## Fixed
- Fixed suite lookup by name method

## [1.5.0]

_released 04-12-2023

### Added
- OpenAPI parser

## [v1.4.4]
_released 04-07-2023

### Fixed
- Ignore inline ids 

## [v1.4.3]
_released 02-23-2023

### Fixed
- Ignore suite and section IDs in JUnit report

## [v1.4.2]
_released 02-10-2023

### Fixed
- Fix automation_id check to support empty case field configs
### Added
- Add Content-Type headers to GET requests

## [v1.4.1]
_released 02-10-2023

### Fixed
- Fix case and result fields bug

## [v1.4.0]
_released 02-09-2023

### Added
- Integration with SauceLabs saucectl reports
- Support for multi-select field values in cmd args and properties (i.e.: "custom_multitype:[1,3]")
- Specify test case IDs in test case name or property
- Create the test run under a milestone using the --milestone-id option
- Elapsed time in milliseconds using the --allow-ms option
- Ability to enrich test cases and test case results through properties with: Case fields, Result fields, Result comments

## [v1.3.1]
_released 11-26-2022

### Fixed
- Fix case and result fields bug

## [v1.3.0]
_released 08-01-2022

### Added
- Updates to README
- New attachments on results functionality using testcase properties
- ADD attachment parsing

## [v1.2.0]
_released 11-09-2022

### Added
- Support for legacy endpoint responses without pagination

## [v1.1.0]
_released 10-07-2022

### Fixed
- Fix run description in one line

### Added
- Support for --case-fields to add regular and custom fields values to test cases
- Support for --run-description to add your custom run description
- Support for --insecure requests

## [1.0] 
_released 16-04-2022
- **Initial Public Release:** The first public release of `trcli`.