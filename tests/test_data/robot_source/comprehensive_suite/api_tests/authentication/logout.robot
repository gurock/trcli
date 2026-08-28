*** Settings ***
Resource    ../../../resources/common_keywords.robot


*** Test Cases ***
Successful Logout
    [Documentation]    Simple passing test, sibling suite file under the same directory.
    [Tags]    JIRA-1237    priority-medium
    Log    Logging out user    level=INFO

Logout Test Is Skipped
    [Documentation]    Exercises SKIP status mapping.
    [Tags]    JIRA-1238    priority-low
    Skip    Skipping this test intentionally for coverage of SKIP status mapping

Logout With Multiple Argument Styles
    [Documentation]    Exercises positional + named/default keyword arguments.
    [Tags]    JIRA-1239    priority-medium
    Create User With Args    john_doe    john@example.com    role=admin    active=${TRUE}
    Create User With Args    jane_doe    jane@example.com
