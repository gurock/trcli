import json
import click

from trcli.cli import pass_environment, Environment, CONTEXT_SETTINGS
from trcli.constants import FAULT_MAPPING
from trcli.readers.gherkin_parser import GherkinParser
from serde import to_dict


@click.command(context_settings=CONTEXT_SETTINGS)
@click.option(
    "-f",
    "--file",
    type=click.Path(exists=True),
    metavar="",
    required=True,
    help="Path to Gherkin .feature file to parse.",
)
@click.option("--output", type=click.Path(), metavar="", help="Optional output file path to save parsed JSON.")
@click.option("--pretty", is_flag=True, help="Pretty print JSON output with indentation.")
@click.option(
    "--case-matcher",
    metavar="",
    default="auto",
    type=click.Choice(["auto", "name", "property"], case_sensitive=False),
    help="Mechanism to match cases between the report and TestRail.",
)
@click.option("--suite-name", metavar="", help="Override suite name (defaults to feature name).")
@click.option("-v", "--verbose", is_flag=True, help="Enable verbose logging output.")
@click.pass_context
@pass_environment
def cli(environment: Environment, context: click.Context, file: str, output: str, pretty: bool, **kwargs):
    """Parse Gherkin .feature files

    This command parses Gherkin/BDD .feature files and converts them into
    TestRail data structure format.

    """
    environment.cmd = "parse_gherkin"
    environment.file = file
    environment.case_matcher = kwargs.get("case_matcher", "auto").upper()
    environment.suite_name = kwargs.get("suite_name")

    # Set up logging
    if kwargs.get("verbose"):
        environment.verbose = True

    try:
        # Parse the feature file
        if environment.verbose:
            environment.log(f"Starting Gherkin parser for file: {file}")

        parser = GherkinParser(environment)
        parsed_suites = parser.parse_file()

        # Convert to dictionary format (manual serialization to include skipped fields)
        suites_data = []
        for suite in parsed_suites:
            # Manually serialize the suite to include testsections
            sections_data = []
            for section in suite.testsections:
                # Manually serialize test cases
                cases_data = []
                for case in section.testcases:
                    case_dict = {
                        "title": case.title,
                        "case_id": case.case_id,
                        "custom_automation_id": case.custom_automation_id,
                        "case_fields": case.case_fields,
                    }
                    # Include result if present
                    if case.result:
                        result_data = {
                            "status_id": case.result.status_id,
                            "comment": case.result.comment,
                            "elapsed": case.result.elapsed,
                        }
                        # Include steps
                        if case.result.custom_step_results:
                            steps_data = []
                            for step in case.result.custom_step_results:
                                steps_data.append(
                                    {
                                        "content": step.content,
                                        "status_id": step.status_id if hasattr(step, "status_id") else None,
                                    }
                                )
                            result_data["custom_step_results"] = steps_data
                        case_dict["result"] = result_data
                    cases_data.append(case_dict)

                # Serialize properties
                properties_data = []
                if section.properties:
                    for prop in section.properties:
                        properties_data.append(
                            {
                                "name": prop.name,
                                "value": prop.value,
                            }
                        )

                section_dict = {
                    "name": section.name,
                    "testcases": cases_data,
                    "properties": properties_data,
                }
                sections_data.append(section_dict)

            suite_dict = {
                "name": suite.name,
                "source": suite.source,
                "testsections": sections_data,
            }
            suites_data.append(suite_dict)

        # Prepare JSON output
        output_data = {
            "suites": suites_data,
            "summary": {
                "total_suites": len(suites_data),
                "total_sections": sum(len(suite.get("testsections", [])) for suite in suites_data),
                "total_cases": sum(
                    len(section.get("testcases", []))
                    for suite in suites_data
                    for section in suite.get("testsections", [])
                ),
                "source_file": file,
            },
        }

        # Format JSON
        if pretty:
            json_output = json.dumps(output_data, indent=2, ensure_ascii=False)
        else:
            json_output = json.dumps(output_data, ensure_ascii=False)

        # Output results
        if output:
            # Save to file
            with open(output, "w", encoding="utf-8") as f:
                f.write(json_output)
            environment.log(f"✓ Parsed results saved to: {output}")
            environment.log(f"  Total suites: {output_data['summary']['total_suites']}")
            environment.log(f"  Total sections: {output_data['summary']['total_sections']}")
            environment.log(f"  Total test cases: {output_data['summary']['total_cases']}")
        else:
            # Print to stdout
            print(json_output)

        if environment.verbose:
            environment.log("✓ Gherkin parsing completed successfully")

    except FileNotFoundError:
        environment.elog(FAULT_MAPPING["missing_file"])
        exit(1)
    except ValueError as e:
        environment.elog(f"Error parsing Gherkin file: {str(e)}")
        exit(1)
    except Exception as e:
        environment.elog(f"Unexpected error during parsing: {str(e)}")
        if environment.verbose:
            import traceback

            environment.elog(traceback.format_exc())
        exit(1)
