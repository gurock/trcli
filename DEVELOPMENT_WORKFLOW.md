# Development Workflow Guide

This guide explains the automated quality checks and policy validation integrated into the TRCLI development workflow.

## Table of Contents

1. [Pre-Commit Setup](#pre-commit-setup)
2. [Commit Message Format](#commit-message-format)
3. [Pull Request Process](#pull-request-process)
4. [Automated Checks](#automated-checks)
5. [Troubleshooting](#troubleshooting)

---

## Pre-Commit Setup

Pre-commit hooks ensure code quality before commits are made, catching issues early in development.

### Installation

```bash
# Install pre-commit
pip install pre-commit

# Install the git hooks
pre-commit install

# Install commit-msg hook for JIRA validation
pre-commit install --hook-type commit-msg

# (Optional) Run hooks on all files
pre-commit run --all-files
```

### What Gets Checked

The pre-commit hooks run the following checks automatically:

#### Code Formatting
- **Black** - Python code formatter (line length: 120)

### Skipping Hooks (Use Sparingly)

```bash
# Skip all hooks (not recommended)
git commit --no-verify -m "your message"

# Skip specific hook
SKIP=black git commit -m "your message"
```

---

## Commit Message Format

It's recommended to include an issue reference (JIRA ticket or GitHub issue) in your commit messages for better traceability.

### Valid Formats

**JIRA Tickets:**
```bash
# Format 1: JIRA key with colon
git commit -m "TRCLI-123: Add new feature for XML parsing"

# Format 2: JIRA key with space
git commit -m "TRCLI-456 Fix bug in API request handler"

# Format 3: JIRA key in brackets
git commit -m "[TRCLI-789] Update documentation"
```

**GitHub Issues:**
```bash
# Format 1: GIT prefix with issue number
git commit -m "GIT-123: Add new feature for XML parsing"

# Format 2: Hash symbol with issue number
git commit -m "#456: Fix bug in API request handler"

# Format 3: Brackets with hash
git commit -m "[#789] Update documentation"
```

### Special Cases (No Issue Reference Required)

- Merge commits: `Merge branch 'feature/xyz' into main`
- Release commits: `Release v1.2.3`
- Version bumps: `Bump version to 1.2.3`
- Reverts: `Revert "TRCLI-123: Add feature"` or `Revert "#123: Add feature"`

### Why This Matters

- **Traceability**: Links code changes to requirements/bugs
- **Project Management**: Enables automatic issue tracking and updates
- **Release Notes**: Simplifies changelog generation
- **Code Review**: Provides context for reviewers
- **Documentation**: Easy to find all commits related to a specific issue

---

## Pull Request Process

### 1. Create Your Branch

```bash
# Feature branch
git checkout -b feature/TRCLI-123-add-xml-parser

# Bug fix branch
git checkout -b fix/TRCLI-456-api-timeout

# Documentation
git checkout -b docs/TRCLI-789-update-readme
```

### 2. PR Title Format (Recommended)

It's recommended to use [Conventional Commits](https://www.conventionalcommits.org/) format for clarity:

```
type(scope): description
```

**Valid Types:**
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation changes
- `style`: Code style changes (formatting, no logic change)
- `refactor`: Code refactoring (no feature change)
- `perf`: Performance improvements
- `test`: Adding or updating tests
- `build`: Build system changes
- `ci`: CI/CD pipeline changes
- `chore`: Maintenance tasks

**Examples:**
```
feat(parser): add support for JUnit XML format
fix(api): handle timeout errors gracefully
docs(readme): update installation instructions
refactor(cli): simplify argument parsing logic
test(parser): add edge case tests for empty files
```

### 3. Fill Out PR Template

The PR template includes required sections:
- Issue reference (GitHub or JIRA)
- Solution description
- Changes made
- Test steps
- Checklist items

**All checklist items must be completed** before requesting review.

### 4. Automated PR Checks

When you open a PR, the following checks run automatically:

#### ✅ PR Validation
- Checks for issue reference (JIRA or GitHub)
- Ensures PR description is complete

#### 📋 Checklist Enforcement
- Verifies all checklist items are checked
- Ensures required sections are filled
- Adds/removes labels based on completion

---

## Automated Checks

### Build & Test Workflow

Runs on every PR and push to main:
- Tests on Python 3.10, 3.11, 3.12, 3.13
- Tests on Ubuntu and Windows
- Code coverage must be ≥ 80%
- All tests must pass

### PR Validation

**Checks:**
- Issue reference (JIRA ticket or GitHub issue)
- PR description completeness

### Checklist Enforcement

**Validates:**
- All checklist items are completed
- Required sections have content
- Issue reference exists
- Test steps provided

**Labels:**
- `ready-for-review`: All checks passed
- `incomplete-pr`: Missing required items

---

## Troubleshooting

### Pre-Commit Hook Failures

#### "Black would reformat"
**Problem**: Code formatting doesn't match Black style.

**Solution**:
```bash
# Let Black fix it automatically
pre-commit run black --all-files

# Then commit again
git add .
git commit -m "Your commit message"
```

### PR Check Failures

#### "Issue reference missing"
**Problem**: No issue reference in PR title or description.

**Solution**: Add issue reference:

**JIRA ticket:**
- In PR title: `feat(api): TRCLI-123 Add endpoint`
- In PR body: Link to JIRA or mention `TRCLI-123`

**GitHub issue:**
- In PR title: `feat(api): GIT-456 Add endpoint` or `feat(api): #789 Add endpoint`
- In PR body: `Fixes #123` or `Resolves GIT-456` or link to GitHub issue

#### "Checklist incomplete"
**Problem**: Not all checklist items are checked.

**Solution**: Complete all items or remove non-applicable ones.

---

## Best Practices

### Commit Frequently
- Make small, logical commits
- Each commit should have a single purpose
- Write descriptive commit messages

### Run Pre-Commit Before Pushing
```bash
# Test your changes locally first
pre-commit run --all-files
pytest tests/
```

### Keep PRs Small
- Aim for <400 lines changed per PR
- Break large features into multiple PRs
- Easier to review and less likely to introduce bugs

### Test Coverage
- Maintain ≥80% code coverage
- Test edge cases
- Include integration tests where applicable

---

## Quick Reference

### Pre-Commit Commands
```bash
pre-commit install                    # Initial setup
pre-commit install --hook-type commit-msg
pre-commit run --all-files           # Run on all files
pre-commit run <hook-id>             # Run specific hook
SKIP=<hook-id> git commit            # Skip specific hook
```

### Git Workflow
```bash
# Using JIRA ticket
git checkout -b feature/TRCLI-123-description
git add .
git commit -m "TRCLI-123: Description"
git push origin feature/TRCLI-123-description

# Using GitHub issue
git checkout -b feature/GIT-456-description
git add .
git commit -m "GIT-456: Description"
# or
git commit -m "#456: Description"
git push origin feature/GIT-456-description

# Open PR with semantic title
```

### Testing
```bash
pytest tests/                         # Run all tests
pytest tests/test_xyz.py             # Run specific test
pytest --cov=trcli --cov-report=html # Coverage report
```

### Useful Links
- [Conventional Commits](https://www.conventionalcommits.org/)
- [Pre-commit Framework](https://pre-commit.com/)

---

## Getting Help

- **Pre-commit issues**: Check `.pre-commit-config.yaml` configuration
- **PR workflow issues**: Review `.github/workflows/` files
- **General questions**: Open an issue or ask in team chat

Happy coding! 🚀
