*** Settings ***
Documentation    Fixtures for the recursive _extract_steps() nested-keyword extraction
...    tests: deep nesting, FOR/IF transparency, argument-type variety, empty/logs-only
...    keywords, special characters, high keyword counts, and setup/teardown nesting.
Resource    nested_resources.robot

*** Test Cases ***
Deep Recursive Nesting
    Recurse To Depth    ${12}

For Loop With If Else Branches
    Iterate And Branch    4

Argument Type Variety
    Accept Many Argument Types    hello    ${TRUE}    a    b    c    key=value

Keyword With No Args And No Messages
    No Op Keyword

Keyword With Only Messages No Nested Call
    Only Logs No Nested Keyword

Keyword With Special Characters In Arguments
    Special Characters Keyword    Line with "quotes", a comma, and Ünïcödé ☺ <tag>

Fifty Plus Keyword Calls
    Call Many Keywords    55

Test With Setup And Teardown Around Nesting
    [Setup]    Recurse To Depth    ${2}
    Log    Body executes    level=INFO
    [Teardown]    Recurse To Depth    ${2}
