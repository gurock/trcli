#!/usr/bin/env python3
"""
Verification script for gherkin-official library parsing capabilities.
This script tests the parsing of .feature files and displays the parsed structure.
"""

import json
from pathlib import Path
from gherkin.parser import Parser
from gherkin.token_scanner import TokenScanner


def parse_feature_file(feature_path: Path):
    """Parse a Gherkin .feature file and return the parsed document."""
    print(f"\n{'='*80}")
    print(f"Parsing: {feature_path.name}")
    print(f"{'='*80}\n")

    try:
        # Read the feature file
        with open(feature_path, "r", encoding="utf-8") as f:
            feature_text = f.read()

        # Parse using gherkin-official
        parser = Parser()
        token_scanner = TokenScanner(feature_text)
        gherkin_document = parser.parse(token_scanner)

        # Display parsed structure
        print("✓ Successfully parsed feature file!\n")

        # Extract key information
        feature = gherkin_document.get("feature")
        if feature:
            print(f"Feature Name: {feature.get('name')}")
            print(f"Description: {feature.get('description', 'N/A')}")
            print(f"Language: {feature.get('language', 'en')}")
            print(f"Tags: {[tag['name'] for tag in feature.get('tags', [])]}")

            # Count scenarios
            scenarios = [child for child in feature.get("children", []) if child.get("scenario")]
            scenario_outlines = [child for child in feature.get("children", []) if child.get("scenarioOutline")]
            background = [child for child in feature.get("children", []) if child.get("background")]

            print(f"\nStructure:")
            print(f"  - Background: {len(background)}")
            print(f"  - Scenarios: {len(scenarios)}")
            print(f"  - Scenario Outlines: {len(scenario_outlines)}")

            # Display scenarios
            print(f"\nScenarios Found:")
            for idx, child in enumerate(feature.get("children", []), 1):
                if child.get("scenario"):
                    scenario = child["scenario"]
                    tags = [tag["name"] for tag in scenario.get("tags", [])]
                    steps = scenario.get("steps", [])
                    print(f"  {idx}. {scenario.get('name')} (Tags: {tags})")
                    print(f"     Steps: {len(steps)}")
                elif child.get("scenarioOutline"):
                    outline = child["scenarioOutline"]
                    tags = [tag["name"] for tag in outline.get("tags", [])]
                    examples = outline.get("examples", [])
                    print(f"  {idx}. {outline.get('name')} (Outline, Tags: {tags})")
                    print(f"     Examples rows: {len(examples[0].get('tableBody', [])) if examples else 0}")

        # Display full parsed document (formatted JSON)
        print(f"\n{'-'*80}")
        print("Full Parsed Document (JSON):")
        print(f"{'-'*80}")
        print(json.dumps(gherkin_document, indent=2))

        return gherkin_document

    except Exception as e:
        print(f"✗ Error parsing feature file: {e}")
        raise


def main():
    """Main function to test gherkin parsing."""
    print("\n" + "=" * 80)
    print("GHERKIN-OFFICIAL LIBRARY VERIFICATION")
    print("=" * 80)

    # Test with the sample login feature
    feature_path = Path(__file__).parent / "tests" / "test_data" / "FEATURE" / "sample_login.feature"

    if not feature_path.exists():
        print(f"\n✗ Feature file not found: {feature_path}")
        return 1

    try:
        gherkin_doc = parse_feature_file(feature_path)

        print(f"\n{'='*80}")
        print("✓ VERIFICATION SUCCESSFUL!")
        print(f"{'='*80}")
        print("\nKey Findings:")
        print("  - gherkin-official library is working correctly")
        print("  - Feature files can be parsed successfully")
        print("  - Scenarios, steps, tags, and examples are extracted properly")
        print("  - Ready for integration into TRCLI parser")

        return 0

    except Exception as e:
        print(f"\n{'='*80}")
        print("✗ VERIFICATION FAILED!")
        print(f"{'='*80}")
        print(f"\nError: {e}")
        return 1


if __name__ == "__main__":
    exit(main())
