#!/bin/bash

# Environment Setup Script

set -e

ENV_FILE="../.env"
EXAMPLE_ENV_FILE="../.env.example"

# Check if .env already exists
if [ -f "${ENV_FILE}" ]; then
    read -p ".env file already exists. Overwrite? (y/N) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# Copy example env file
cp "${EXAMPLE_ENV_FILE}" "${ENV_FILE}"

# Generate random secrets
generate_secret() {
    openssl rand -hex 32
}

# Update secrets in .env file
if [[ "$OSTYPE" == "darwin"* ]]; then
    # macOS
    sed -i '' "s/your-secret-key-here/$(generate_secret)/g" "${ENV_FILE}"
    sed -i '' "s/your-jwt-secret-key-here/$(generate_secret)/g" "${ENV_FILE}"
else
    # Linux
    sed -i "s/your-secret-key-here/$(generate_secret)/g" "${ENV_FILE}"
    sed -i "s/your-jwt-secret-key-here/$(generate_secret)/g" "${ENV_FILE}"
fi

# Prompt for database password
read -sp "Enter database password: " DB_PASSWORD
echo
sed -i "s/your-db-password/${DB_PASSWORD}/g" "${ENV_FILE}"

# Prompt for environment
read -p "Enter environment (development/production): " ENVIRONMENT
sed -i "s/ENVIRONMENT=development/ENVIRONMENT=${ENVIRONMENT}/g" "${ENV_FILE}"

echo "Environment setup completed successfully!"
echo "Please review ${ENV_FILE} and update any additional settings."