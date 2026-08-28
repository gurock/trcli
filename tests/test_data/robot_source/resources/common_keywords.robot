*** Comment ***
Shared keywords for comprehensive Robot Framework parser test data.
Deliberately NOT a runnable suite (no [Test Cases] section) - imported via Resource only.


*** Keywords ***
Perform Login
    [Documentation]    Top-level keyword: 4 levels of nested keyword calls.
    [Arguments]    ${username}    ${password}
    Enter Credentials    ${username}    ${password}
    Submit Login Form

Enter Credentials
    [Arguments]    ${username}    ${password}
    Type Username    ${username}
    Type Password    ${password}

Type Username
    [Arguments]    ${username}
    Log    Typing username: ${username}    level=INFO

Type Password
    [Arguments]    ${password}
    Log    Typing password    level=DEBUG

Submit Login Form
    Log    Submitting login form    level=INFO
    Click Login Button

Click Login Button
    Log    Login button clicked    level=TRACE

Perform Risky Operation
    [Documentation]    Nested keyword chain that fails 3 custom levels deep.
    Validate Preconditions
    Execute Operation

Validate Preconditions
    Log    Validating preconditions    level=INFO

Execute Operation
    Prepare Payload
    Send Request And Validate

Prepare Payload
    Log    Preparing request payload    level=DEBUG

Send Request And Validate
    Log    Sending request    level=INFO
    Fail    Deeply nested failure at level 4

Create User With Args
    [Documentation]    Keyword exercising multiple positional + named/default arguments.
    [Arguments]    ${username}    ${email}    ${role}=member    ${active}=${TRUE}
    Log    Creating user ${username} with email=${email}, role=${role}, active=${active}    level=INFO

Log All Message Levels
    [Documentation]    Emits one message at each supported Robot Framework log level.
    Log    trace level message    level=TRACE
    Log    debug level message    level=DEBUG
    Log    info level message    level=INFO
    Log    warn level message    level=WARN

Failing Setup Keyword
    Fail    Intentional setup failure for test data coverage

Failing Teardown Keyword
    Fail    Intentional teardown failure for test data coverage

Failing Suite Setup
    Fail    Intentional suite setup failure for test data coverage
