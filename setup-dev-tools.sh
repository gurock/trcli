#!/bin/bash

# TRCLI Development Tools Setup Script
# This script sets up pre-commit hooks and development tools

set -e

echo "=========================================="
echo "TRCLI Development Tools Setup"
echo "=========================================="
echo ""

# Check Python version
echo "Checking Python version..."
python_version=$(python3 --version 2>&1 | awk '{print $2}')
echo "✓ Python version: $python_version"
echo ""

# Install pre-commit
echo "Installing pre-commit..."
pip install pre-commit
echo "✓ Pre-commit installed"
echo ""

# Install git hooks
echo "Installing git hooks..."
pre-commit install
echo "✓ Git hooks installed"
echo ""

# Run pre-commit on all files (optional)
echo "Would you like to run pre-commit checks on all files now? (y/n)"
read -r response
if [[ "$response" == "y" || "$response" == "Y" ]]; then
    echo "Running pre-commit checks..."
    pre-commit run --all-files || true
    echo ""
fi

echo "=========================================="
echo "Setup Complete! ✓"
echo "=========================================="
echo ""
echo "Next steps:"
echo "1. Read DEVELOPMENT_WORKFLOW.md for detailed guidelines"
echo "2. Use semantic PR titles (e.g., feat(api): add new endpoint)"
echo "3. Include issue references in commits for traceability (recommended)"
echo ""
echo "Happy coding! 🚀"
