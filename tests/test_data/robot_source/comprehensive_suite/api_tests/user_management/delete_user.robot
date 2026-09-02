*** Settings ***
Resource    ../../../resources/common_keywords.robot


*** Test Cases ***
Delete User Successfully
    [Documentation]    Simple passing test in a deeper suite nesting level.
    [Tags]    JIRA-2004    priority-medium
    Log    Deleting user account    level=INFO

Delete Nonexistent User Fails
    [Documentation]    Directly-failing test (no nested keyword involved) for contrast against nested failures.
    [Tags]    JIRA-2005    priority-high
    Fail    User does not exist, cannot delete
