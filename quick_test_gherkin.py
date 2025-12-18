#!/usr/bin/env python3
"""Quick test script to parse any .feature file"""

import sys
from pathlib import Path
from gherkin.parser import Parser
from gherkin.token_scanner import TokenScanner
import json


def parse_feature(filepath):
    """Parse a Gherkin feature file and display key information."""
    with open(filepath, "r", encoding="utf-8") as f:
        feature_text = f.read()

    parser = Parser()
    scanner = TokenScanner(feature_text)
    doc = parser.parse(scanner)

    feature = doc["feature"]

    print(f"\n{'='*60}")
    print(f"Feature: {feature['name']}")
    print(f"{'='*60}")

    # Count elements
    scenarios = [c for c in feature["children"] if "scenario" in c]
    backgrounds = [c for c in feature["children"] if "background" in c]

    print(f"\nSummary:")
    print(f"  Backgrounds: {len(backgrounds)}")
    print(f"  Scenarios: {len(scenarios)}")

    print(f"\nScenarios:")
    for idx, child in enumerate(scenarios, 1):
        scenario = child["scenario"]
        tags = [tag["name"] for tag in scenario.get("tags", [])]
        steps = scenario.get("steps", [])
        examples = scenario.get("examples", [])

        scenario_type = "Scenario Outline" if examples else "Scenario"
        print(f"  {idx}. [{scenario_type}] {scenario['name']}")
        print(f"     Tags: {', '.join(tags) if tags else 'None'}")
        print(f"     Steps: {len(steps)}")
        if examples:
            total_examples = sum(len(ex.get("tableBody", [])) for ex in examples)
            print(f"     Example rows: {total_examples}")

    return doc


if __name__ == "__main__":
    if len(sys.argv) > 1:
        feature_file = Path(sys.argv[1])
    else:
        # Default to sample file
        feature_file = Path(__file__).parent / "tests" / "test_data" / "FEATURE" / "sample_login.feature"

    if not feature_file.exists():
        print(f"Error: File not found: {feature_file}")
        sys.exit(1)

    parse_feature(feature_file)
    print(f"\n{'='*60}")
    print("✓ Parsing successful!")
    print(f"{'='*60}\n")
