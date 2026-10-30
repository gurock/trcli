*** Settings ***
Resource    ../../../resources/common_keywords.robot


*** Test Cases ***
Create User Successfully
    [Documentation]    Passing test with multiple named arguments.
    [Tags]    JIRA-2001    priority-high
    Create User With Args    alice    alice@example.com    role=admin    active=${TRUE}

Create User With Failing Setup
    [Documentation]    Exercises test-level [Setup] failure -> test marked FAIL.
    [Tags]    JIRA-2002    priority-high
    [Setup]    Failing Setup Keyword
    Log    This body should not really execute meaningfully since setup fails    level=INFO

Create User With Failing Teardown
    [Documentation]    Exercises test-level [Teardown] failure -> test marked FAIL even though body passes.
    [Tags]    JIRA-2003    priority-medium
    Log    Main test body executes fine    level=INFO
    [Teardown]    Failing Teardown Keyword
