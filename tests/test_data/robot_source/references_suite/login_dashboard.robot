*** Settings ***
Documentation    Real-world-style page-object suite: a single test that logs in and verifies
...              a dashboard, built from several layers of small, single-purpose user keywords
...              (the way many real customer suites are structured), rather than one flat test
...              body. Modeled after a genuine anonymized customer output.xml sample.
Suite Setup      Initialize Test Suite
Suite Teardown    Finalize Test Suite


*** Variables ***
${SAMPLE_USERNAME}      sample_user@example.com
${SAMPLE_PASSWORD}      SamplePassword123
${EXPECTED_TITLE}       Sample Dashboard


*** Test Cases ***
Sample Login And Dashboard Verification
    [Documentation]    Verifies a user can log in and reach the dashboard.
    [Tags]    refs:TSTRAIL-5
    [Setup]    Start Application
    Log In As User    ${SAMPLE_USERNAME}    ${SAMPLE_PASSWORD}
    Verify Dashboard Displayed    ${EXPECTED_TITLE}
    [Teardown]    Stop Application


*** Keywords ***
Initialize Test Suite
    [Documentation]    Runs once before any test in the suite.
    Log    Initializing test suite...

Finalize Test Suite
    [Documentation]    Runs once after all tests in the suite.
    Log    Finalizing test suite...

Start Application
    [Documentation]    High-level setup step.
    Open Application Under Test

Open Application Under Test
    [Documentation]    Simulates launching the application/browser.
    Launch Browser Session
    Navigate To Base URL

Launch Browser Session
    [Documentation]    Simulates starting a browser instance.
    Log    Starting browser session...

Navigate To Base URL
    [Documentation]    Simulates navigating to the application's base URL.
    Log    Navigating to base URL...

Log In As User
    [Arguments]    ${username}    ${password}
    [Documentation]    High-level login step.
    Login With Credentials    ${username}    ${password}

Login With Credentials
    [Arguments]    ${username}    ${password}
    [Documentation]    Simulates logging in with a given username and password.
    Enter Username    ${username}
    Enter Password    ${password}
    Submit Login Form

Enter Username
    [Arguments]    ${username}
    [Documentation]    Simulates entering a username into a login field.
    Log    Entering username: ${username}

Enter Password
    [Arguments]    ${password}
    [Documentation]    Simulates entering a password into a login field.
    Log    Entering password (masked): ${password.replace('.', '*')}

Submit Login Form
    [Documentation]    Simulates clicking the login/submit button.
    Log    Submitting login form...

Verify Dashboard Displayed
    [Arguments]    ${expected_title}
    [Documentation]    High-level verification step.
    Verify Page Title Equals    ${expected_title}

Verify Page Title Equals
    [Arguments]    ${expected_title}
    [Documentation]    Simulates verifying that the current page title matches the expected value.
    ${actual_title}=    Get Current Page Title
    Should Be Equal As Strings    ${actual_title}    ${expected_title}
    Log    Page title verified: ${actual_title}

Get Current Page Title
    [Documentation]    Simulates retrieving the current page title.
    RETURN    Sample Dashboard

Stop Application
    [Documentation]    High-level teardown step.
    Close Application Under Test

Close Application Under Test
    [Documentation]    Simulates closing the application/browser.
    Log Out Of Application
    Quit Browser Session

Log Out Of Application
    [Documentation]    Simulates logging out of the application.
    Log    Logging out...

Quit Browser Session
    [Documentation]    Simulates closing the browser instance.
    Log    Closing browser session...
