#!/usr/bin/env python3
"""Commit message validator for TRCLI project.

Ensures commit messages start with a valid issue reference (JIRA or GitHub).

Valid formats:
  JIRA tickets:
    - TRCLI-123: Add new feature
    - TRCLI-456 Fix bug in parser
    - [TRCLI-789] Update documentation

  GitHub issues:
    - GIT-123: Add new feature
    - GIT-456 Fix bug in parser
    - #123: Add new feature
    - [#456] Fix bug in parser

Special cases (allowed without issue reference):
  - Merge commits
  - Release commits (starting with "Release")
  - Version bump commits (starting with "Bump version")
  - Initial commits
"""

import re
import sys


def validate_commit_message(commit_msg_file):
    """Validate that commit message follows TRCLI conventions."""
    with open(commit_msg_file, "r") as f:
        commit_msg = f.read().strip()

    # Skip empty messages
    if not commit_msg:
        print("ERROR: Commit message is empty")
        return False

    # Allow merge commits
    if commit_msg.startswith("Merge"):
        return True

    # Allow release commits
    if commit_msg.startswith("Release") or commit_msg.startswith("Bump version"):
        return True

    # Allow revert commits
    if commit_msg.startswith("Revert"):
        return True

    # Check for issue reference at the start
    # JIRA patterns: TRCLI-123, [TRCLI-123], TRCLI-123:
    # GitHub patterns: GIT-123, #123, [GIT-123], [#123]
    issue_patterns = [
        r"^(\[)?TRCLI-\d+(\])?[:\s]",  # JIRA: TRCLI-123 or [TRCLI-123]
        r"^(\[)?GIT-\d+(\])?[:\s]",  # GitHub: GIT-123 or [GIT-123]
        r"^(\[)?#\d+(\])?[:\s]",  # GitHub: #123 or [#123]
    ]

    # Check if commit message matches any valid pattern
    for pattern in issue_patterns:
        if re.match(pattern, commit_msg):
            return True

    # If we get here, the commit message is invalid
    print("\n" + "=" * 70)
    print("COMMIT MESSAGE VALIDATION FAILED")
    print("=" * 70)
    print("\nYour commit message must start with an issue reference.")
    print("\nValid formats:")
    print("\n  JIRA tickets:")
    print("    - TRCLI-123: Add new feature")
    print("    - TRCLI-456 Fix bug in parser")
    print("    - [TRCLI-789] Update documentation")
    print("\n  GitHub issues:")
    print("    - GIT-123: Add new feature")
    print("    - GIT-456 Fix bug in parser")
    print("    - #123: Add new feature")
    print("    - [#456] Fix bug in parser")
    print("\nSpecial cases (no issue reference needed):")
    print("  - Merge commits")
    print("  - Release commits (start with 'Release')")
    print("  - Version bumps (start with 'Bump version')")
    print("  - Reverts (start with 'Revert')")
    print("\nYour commit message:")
    print(f"  {commit_msg}")
    print("\nPlease update your commit message and try again.")
    print("=" * 70 + "\n")

    return False


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("ERROR: No commit message file provided")
        sys.exit(1)

    commit_msg_file = sys.argv[1]

    if validate_commit_message(commit_msg_file):
        sys.exit(0)
    else:
        sys.exit(1)
