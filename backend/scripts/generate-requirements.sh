#!/bin/bash
# Script to generate requirements files

set -e

echo "🔧 Generating requirements files..."

# Generate main requirements.txt with all dependencies
pip freeze > requirements-full.txt

# Generate production requirements (excluding dev packages)
pip freeze | grep -v -E "pytest|black|flake8|mypy|ipython|pylint|sphinx|mkdocs" > requirements-prod.txt

# Generate requirements-dev.txt from dev extras
pip freeze | grep -E "pytest|black|flake8|mypy|ipython|pylint|sphinx|mkdocs" > requirements-dev.txt

echo "✅ Requirements files generated:"
echo "  - requirements-full.txt (all dependencies)"
echo "  - requirements-prod.txt (production only)"
echo "  - requirements-dev.txt (development only)"