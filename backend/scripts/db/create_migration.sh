#!/bin/bash
# parking-management/backend/scripts/db/create_migration.sh
# Helper script to create new migrations with proper structure

MIGRATIONS_DIR="${MIGRATIONS_DIR:-./migrations}"

create_migration_with_template() {
    local name=$1
    local timestamp=$(date +"%Y%m%d%H%M%S")
    local filename="${timestamp}_${name}"
    local up_file="${MIGRATIONS_DIR}/${filename}.up.sql"
    local down_file="${MIGRATIONS_DIR}/${filename}.down.sql"
    
    # Create up migration file with template
    cat > "${up_file}" << 'EOF'
-- Migration: {{name}}
-- Version: {{timestamp}}
-- Direction: UP
-- Author: {{USER}}
-- Date: {{date}}

BEGIN;

-- Add your migration changes here
-- Example:
-- CREATE TABLE new_table (
--     id SERIAL PRIMARY KEY,
--     created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
-- );

COMMIT;

-- Rollback: See {{filename}}.down.sql
EOF
    
    # Create down migration file with template
    cat > "${down_file}" << 'EOF'
-- Migration: {{name}}
-- Version: {{timestamp}}
-- Direction: DOWN
-- Author: {{USER}}
-- Date: {{date}}

BEGIN;

-- Add rollback statements here
-- Example:
-- DROP TABLE IF EXISTS new_table;

COMMIT;
EOF
    
    # Replace placeholders
    sed -i "s/{{name}}/${name}/g" "${up_file}" "${down_file}"
    sed -i "s/{{timestamp}}/${timestamp}/g" "${up_file}" "${down_file}"
    sed -i "s/{{USER}}/${USER:-unknown}/g" "${up_file}" "${down_file}"
    sed -i "s/{{date}}/$(date)/g" "${up_file}" "${down_file}"
    sed -i "s/{{filename}}/${filename}/g" "${up_file}" "${down_file}"
    
    echo "Created migration:"
    echo "  - ${up_file}"
    echo "  - ${down_file}"
}

# Usage
if [ $# -eq 0 ]; then
    echo "Usage: $0 <migration_name>"
    echo "Example: $0 add_payment_method_column"
    exit 1
fi

create_migration_with_template "$1"