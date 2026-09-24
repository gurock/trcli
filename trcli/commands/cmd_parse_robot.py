from xml.etree.ElementTree import ParseError

import click
from robot.errors import DataError

from trcli import settings
from trcli.api.results_uploader import ResultsUploader
from trcli.cli import pass_environment, Environment, CONTEXT_SETTINGS
from trcli.commands.results_parser_helpers import (
    results_parser_options,
    print_config,
    update_existing_cases_options,
    handle_case_update_reporting,
)
from trcli.constants import FAULT_MAPPING
from trcli.data_classes.validation_exception import ValidationException
from trcli.readers.robot_xml import RobotParser


@click.command(context_settings=CONTEXT_SETTINGS)
@results_parser_options
@update_existing_cases_options
@click.pass_context
@pass_environment
def cli(environment: Environment, context: click.Context, *args, **kwargs):
    """Parse Robot Framework report and upload results to TestRail"""
    environment.cmd = "parse_robot"
    environment.set_parameters(context)
    environment.check_for_required_parameters()
    settings.ALLOW_ELAPSED_MS = environment.allow_ms
    print_config(environment)
    try:
        robot_parser = RobotParser(environment)
        parsed_suites = robot_parser.parse_file()

        # Check if any invalid quality ratings were found during parsing
        if robot_parser.invalid_quality_ratings_found:
            environment.elog(
                "\nERROR: One or more test results have invalid quality_rating values that were rejected.\n"
                "Cannot proceed with upload as quality_rating is required for tests that specify it.\n\n"
                "Please fix the invalid quality ratings in your test report and try again.\n\n"
                "Quality rating requirements:\n"
                "  - Maximum 15 categories\n"
                "  - Star values must be integers 0-5\n"
                "  - At least one category must have a value >= 1\n"
                "  - Must be valid JSON object format"
            )
            exit(1)

        case_update_results = None
        has_step_results = any(
            test_case.result and test_case.result.custom_step_results
            for suite in parsed_suites
            for section in suite.testsections
            for test_case in section.testcases
        )
        if has_step_results:
            environment.log(
                "Note: step content is now formatted as 'KeywordName(arg1, arg2, ...)' "
                "(previously just 'KeywordName'), and nested keyword calls are captured "
                "with indentation. If existing TestRail cases have steps uploaded by an "
                "earlier trcli version, they will not match this new content and may be "
                "duplicated or updated depending on your upload mode. See CHANGELOG.MD for "
                "details."
            )

        # Accumulate case-update results across all suites (rather than overwriting),
        # so that e.g. a failure in an earlier suite isn't silently discarded by a
        # later suite's results.
        accumulated_case_update_results = {"updated_cases": [], "skipped_cases": [], "failed_cases": []}
        for suite in parsed_suites:
            result_uploader = ResultsUploader(environment=environment, suite=suite)
            result_uploader.upload_results()

            # Collect case update results (from --update-existing-cases)
            if hasattr(result_uploader, "case_update_results") and result_uploader.case_update_results:
                for key in accumulated_case_update_results:
                    accumulated_case_update_results[key].extend(result_uploader.case_update_results.get(key, []))

        if any(accumulated_case_update_results.values()):
            case_update_results = accumulated_case_update_results

        # Handle case update reporting if enabled
        if environment.update_existing_cases == "yes" and case_update_results is not None:
            handle_case_update_reporting(environment, case_update_results)

            # Exit with error if there were case update failures (after reporting)
            if case_update_results.get("failed_cases"):
                exit(1)
    except FileNotFoundError as e:
        environment.elog(str(e))
        exit(1)
    except (ParseError, DataError):
        # ParseError: raw XML is not well-formed (xml.etree.ElementTree).
        # DataError: XML is well-formed but robot.api.ExecutionResult rejects its
        # content as invalid Robot Framework result data (e.g. malformed timestamps
        # or other schema violations) - surfaced by the ExecutionResult-based parser.
        environment.elog(FAULT_MAPPING["invalid_file"])
        exit(1)
    except ValidationException as exception:
        environment.elog(
            FAULT_MAPPING["dataclass_validation_error"].format(
                field=exception.field_name,
                class_name=exception.class_name,
                reason=exception.reason,
            )
        )
        exit(1)
