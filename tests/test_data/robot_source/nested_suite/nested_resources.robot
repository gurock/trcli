*** Keywords ***
Recurse To Depth
    [Documentation]    Recurses ``${depth}`` times, logging at each level, to exercise
    ...    deep keyword nesting (10+ levels) through a transparent IF/ELSE branch.
    [Arguments]    ${depth}
    IF    ${depth} <= 0
        Log    Reached the bottom    level=INFO
    ELSE
        Log    At depth ${depth}    level=DEBUG
        Recurse To Depth    ${depth - 1}
    END

Iterate And Branch
    [Documentation]    Exercises a FOR loop containing an IF/ELSE, each branch calling
    ...    a further nested keyword - keywords inside loops/branches must still be
    ...    extracted at their true keyword-call depth.
    [Arguments]    ${count}
    FOR    ${i}    IN RANGE    ${count}
        Log    Loop iteration ${i}    level=INFO
        IF    ${i} % 2 == 0
            Log Even Branch    ${i}
        ELSE
            Log Odd Branch    ${i}
        END
    END

Log Even Branch
    [Arguments]    ${i}
    Log    Even: ${i}    level=INFO

Log Odd Branch
    [Arguments]    ${i}
    Log    Odd: ${i}    level=WARN

Accept Many Argument Types
    [Documentation]    Exercises string, boolean-variable, list (@{}), and named/dict
    ...    (&{}-style keyword args) argument styles in a single call.
    [Arguments]    ${str_arg}    ${var_arg}    @{list_arg}    &{dict_arg}
    Log    Received ${str_arg}    level=INFO

No Op Keyword
    [Documentation]    A keyword with no arguments and no messages/nested calls.
    No Operation

Only Logs No Nested Keyword
    [Documentation]    A keyword whose only body content is a log message - no
    ...    nested keyword call beneath it.
    Log    Only a log line, no nested keyword call    level=INFO

Special Characters Keyword
    [Arguments]    ${text}
    Log    Special: ${text}    level=INFO

Call Many Keywords
    [Documentation]    Calls ``No Operation`` ``${count}`` times via a FOR loop, for
    ...    performance testing with 50+ keyword calls in a single test.
    [Arguments]    ${count}
    FOR    ${i}    IN RANGE    ${count}
        No Operation
    END
