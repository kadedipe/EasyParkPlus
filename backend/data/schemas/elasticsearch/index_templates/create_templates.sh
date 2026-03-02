#!/bin/bash

# Elasticsearch Index Template Creation Script
# Usage: ./create_templates.sh [elasticsearch_url] [username:password]

ES_URL=${1:-"http://localhost:9200"}
AUTH=${2:-""}

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${YELLOW}Creating Elasticsearch index templates for Parking Management System${NC}"
echo "================================================"

# Function to create template
create_template() {
    local name=$1
    local file=$2
    
    echo -e "\n${YELLOW}Creating template: ${name}${NC}"
    
    if [ -n "$AUTH" ]; then
        curl -s -X PUT "${ES_URL}/_index_template/${name}" \
            -H "Content-Type: application/json" \
            -u "$AUTH" \
            -d @"$file" | jq '.'
    else
        curl -s -X PUT "${ES_URL}/_index_template/${name}" \
            -H "Content-Type: application/json" \
            -d @"$file" | jq '.'
    fi
    
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✓ Template ${name} created successfully${NC}"
    else
        echo -e "${RED}✗ Failed to create template ${name}${NC}"
    fi
}

# Function to create component template
create_component_template() {
    local name=$1
    local file=$2
    
    echo -e "\n${YELLOW}Creating component template: ${name}${NC}"
    
    if [ -n "$AUTH" ]; then
        curl -s -X PUT "${ES_URL}/_component_template/${name}" \
            -H "Content-Type: application/json" \
            -u "$AUTH" \
            -d @"$file" | jq '.'
    else
        curl -s -X PUT "${ES_URL}/_component_template/${name}" \
            -H "Content-Type: application/json" \
            -d @"$file" | jq '.'
    fi
    
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✓ Component template ${name} created successfully${NC}"
    else
        echo -e "${RED}✗ Failed to create component template ${name}${NC}"
    fi
}

# Function to create ILM policy
create_ilm_policy() {
    local name=$1
    local policy=$2
    
    echo -e "\n${YELLOW}Creating ILM policy: ${name}${NC}"
    
    if [ -n "$AUTH" ]; then
        curl -s -X PUT "${ES_URL}/_ilm/policy/${name}" \
            -H "Content-Type: application/json" \
            -u "$AUTH" \
            -d @"$policy" | jq '.'
    else
        curl -s -X PUT "${ES_URL}/_ilm/policy/${name}" \
            -H "Content-Type: application/json" \
            -d @"$policy" | jq '.'
    fi