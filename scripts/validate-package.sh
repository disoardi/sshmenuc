#!/usr/bin/env bash
################################################################################
# SCRIPT: validate-package.sh
# AUTHOR: Davide Isoardi
# PURPOSE: Validate package metadata and build before PyPI publishing
# DATE: 2026-02-16
################################################################################

set -e

echo "🔍 Validating package metadata..."

# Check email format in pyproject.toml
EMAIL=$(grep "authors" pyproject.toml | grep -oE '<[^>]+>')
if [[ "$EMAIL" =~ \.\@ ]]; then
    echo "❌ Invalid email format: period before @ in '$EMAIL'"
    exit 1
fi
echo "✅ Email format valid"

# Check version consistency
PYPROJECT_VERSION=$(grep "^version" pyproject.toml | cut -d'"' -f2)
INIT_VERSION=$(grep "__version__" sshmenuc/__init__.py | cut -d'"' -f2)
DOCS_VERSION=$(grep "^release = " docs/conf.py | cut -d"'" -f2)

if [ "$PYPROJECT_VERSION" != "$INIT_VERSION" ] || [ "$PYPROJECT_VERSION" != "$DOCS_VERSION" ]; then
    echo "❌ Version mismatch:"
    echo "   pyproject.toml: $PYPROJECT_VERSION"
    echo "   __init__.py: $INIT_VERSION"
    echo "   docs/conf.py: $DOCS_VERSION"
    exit 1
fi
echo "✅ Version consistent: $PYPROJECT_VERSION"

# Build package
echo "🔨 Building package..."
poetry build

# Validate with twine
echo "🔍 Running twine check..."
pip install -q twine 2>/dev/null || true
twine check dist/* || exit 1

echo ""
echo "✅ Package validation passed!"
echo "📦 Ready to publish: sshmenuc $PYPROJECT_VERSION"
