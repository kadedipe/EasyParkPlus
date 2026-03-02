#!/bin/bash

# Audit Logs Rollover Script
# This script manually triggers rollover for audit logs indices

ES_URL=${1:-"http://localhost:9200"}
AUTH=${2:-""}
ALIAS="audit-logs"

echo "Checking current write index for alias: $ALIAS"

# Get current write index
if [ -n "$AUTH" ]; then
    RESPONSE=$(curl -s -u "$AUTH" "${ES_URL}/${ALIAS}/_alias")
else
    RESPONSE=$(curl -s "${ES_URL}/${ALIAS}/_alias")
fi

CURRENT_INDEX=$(echo $RESPONSE | jq -r 'keys[]' | head -1)
echo "Current write index: $CURRENT_INDEX"

# Get index stats
if [ -n "$AUTH" ]; then
    STATS=$(curl -s -u "$AUTH" "${ES_URL}/${CURRENT_INDEX}/_stats")
else
    STATS=$(curl -s "${ES_URL}/${CURRENT_INDEX}/_stats")
fi

DOC_COUNT=$(echo $STATS | jq '.primaries.docs.count')
SIZE=$(echo $STATS | jq '.primaries.store.size_in_bytes')
SIZE_MB=$((SIZE / 1024 / 1024))

echo "Document count: $DOC_COUNT"
echo "Index size: ${SIZE_MB}MB"

# Check rollover conditions
ROLLOVER=false
REASON=""

if [ $DOC_COUNT -gt 50000000 ]; then
    ROLLOVER=true
    REASON="Document count exceeded 50M"
elif [ $SIZE_MB -gt 51200 ]; then
    ROLLOVER=true
    REASON="Index size exceeded 50GB"
fi

if [ "$ROLLOVER" = true ]; then
    echo "Rollover condition met: $REASON"
    echo "Triggering rollover..."
    
    if [ -n "$AUTH" ]; then
        curl -s -X POST -u "$AUTH" "${ES_URL}/${ALIAS}/_rollover" \
            -H "Content-Type: application/json" \
            -d '{
                "conditions": {
                    "max_age": "30d",
                    "max_docs": 50000000,
                    "max_size": "50gb"
                }
            }' | jq '.'
    else
        curl -s -X POST "${ES_URL}/${ALIAS}/_rollover" \
            -H "Content-Type: application/json" \
            -d '{
                "conditions": {
                    "max_age": "30d",
                    "max_docs": 50000000,
                    "max_size": "50gb"
                }
            }' | jq '.'
    fi
else
    echo "No rollover conditions met"
fi