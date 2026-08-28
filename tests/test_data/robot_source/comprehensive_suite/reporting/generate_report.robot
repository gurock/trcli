*** Settings ***
Resource    ../../resources/common_keywords.robot
Suite Setup    Failing Suite Setup


*** Test Cases ***
Generate Daily Report
    [Documentation]    Would pass on its own, but suite setup fails first -> test marked FAIL.
    [Tags]    JIRA-3001    priority-medium
    Log    Generating daily report    level=INFO

Generate Weekly Report
    [Documentation]    Second test in the same suite, also affected by the suite setup failure.
    [Tags]    JIRA-3002    priority-low
    Log    Generating weekly report    level=INFO
