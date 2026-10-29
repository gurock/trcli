*** Settings ***
Resource    ../../../resources/common_keywords.robot


*** Test Cases ***
Successful Login With Nested Keywords
    [Documentation]    Exercises a 4-level-deep nested keyword call chain (Perform Login).
    [Tags]    JIRA-1234    priority-high    smoke
    Perform Login    john_doe    correct_password

Login Fails Deep In Nested Keyword Chain
    [Documentation]    Exercises failure propagation up through 3 levels of nested keywords.
    [Tags]    JIRA-1235    priority-high
    Perform Risky Operation

Login Test With All Message Levels
    [Documentation]    Exercises TRACE/DEBUG/INFO/WARN log messages plus nested keywords.
    [Tags]    JIRA-1236    priority-low
    Log All Message Levels
    Perform Login    jane_doe    another_password
