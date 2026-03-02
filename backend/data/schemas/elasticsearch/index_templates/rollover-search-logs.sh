#!/bin/bash

# Search Logs Rollover Script
# Manages rollover and cleanup of search logs indices

ES_URL=${1:-"http://localhost:9200"}
AUTH=${2:-""}
ALIAS="search-logs"

echo "Search Logs Rollover Manager"
echo "============================"

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

if [ $DOC_COUNT -gt 20000000 ]; then
    ROLLOVER=true
    REASON="Document count exceeded 20M"
elif [ $SIZE_MB -gt 30720 ]; then
    ROLLOVER=true
    REASON="Index size exceeded 30GB"
fi

if [ "$ROLLOVER" = true ]; then
    echo "Rollover condition met: $REASON"
    echo "Triggering rollover..."
    
    if [ -n "$AUTH" ]; then
        curl -s -X POST -u "$AUTH" "${ES_URL}/${ALIAS}/_rollover" \
            -H "Content-Type: application/json" \
            -d '{
                "conditions": {
                    "max_age": "7d",
                    "max_docs": 20000000,
                    "max_size": "30gb"
                }
            }' | jq '.'
    else
        curl -s -X POST "${ES_URL}/${ALIAS}/_rollover" \
            -H "Content-Type: application/json" \
            -d '{
                "conditions": {
                    "max_age": "7d",
                    "max_docs": 20000000,
                    "max_size": "30gb"
                }
            }' | jq '.'
    fi
else
    echo "No rollover conditions met"
fi

# Check for old indices to delete
CUTOFF_DATE=$(date -d "-90 days" +%Y-%m-%d)
echo "Checking for indices older than $CUTOFF_DATE..."

if [ -n "$AUTH" ]; then
    INDICES=$(curl -s -u "$AUTH" "${ES_URL}/_cat/indices/search-logs-*?h=index,creation.date.string&format=json")
else
    INDICES=$(curl -s "${ES_URL}/_cat/indices/search-logs-*?h=index,creation.date.string&format=json")
fi

echo "$INDICES" | jq -c '.[]' | while read -r index; do
    INDEX_NAME=$(echo "$index" | jq -r '.index')
    CREATION_DATE=$(echo "$index" | jq -r '.["creation.date.string"]')
    
    # Skip if this is the current write index
    if [ "$INDEX_NAME" = "$CURRENT_INDEX" ]; then
        continue
    fi
    
    # Parse creation date
    if [[ $CREATION_DATE =~ ([0-9]{4}-[0-9]{2}-[0-9]{2}) ]]; then
        INDEX_DATE="${BASH_REMATCH[1]}"
        
        if [[ "$INDEX_DATE" < "$CUTOFF_DATE" ]]; then
            echo "Deleting old index: $INDEX_NAME (created: $INDEX_DATE)"
            
            if [ -n "$AUTH" ]; then
                curl -s -X DELETE -u "$AUTH" "${ES_URL}/${INDEX_NAME}" | jq '.'
            else
                curl -s -X DELETE "${ES_URL}/${INDEX_NAME}" | jq '.'
            fi
        fi
    fi
done