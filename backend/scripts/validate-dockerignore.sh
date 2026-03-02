#!/bin/bash
# Script to validate that sensitive files are not accidentally included

echo "🔍 Validating .dockerignore..."

# Files that should never be in the build context
SENSITIVE_FILES=(
    ".env"
    ".env.production"
    ".env.staging"
    "credentials.json"
    "service-account.json"
    "*.pem"
    "*.key"
    "secrets/"
)

# Create a temporary build context and list files
docker build -f Dockerfile --no-cache --pull -t temp-context . > /dev/null 2>&1

# Check for sensitive files
for pattern in "${SENSITIVE_FILES[@]}"; do
    if docker run --rm temp-context find . -name "$pattern" 2>/dev/null | grep -q .; then
        echo "❌ ERROR: Found sensitive file matching pattern: $pattern"
        exit 1
    fi
done

echo "✅ All checks passed - no sensitive files found"
docker rmi temp-context > /dev/null 2>&1