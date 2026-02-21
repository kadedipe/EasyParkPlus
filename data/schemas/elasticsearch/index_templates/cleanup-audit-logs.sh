#!/bin/bash

# Audit Logs Cleanup Script
# Deletes audit logs older than retention period

ES_URL=${1:-"http://localhost:9200"}
AUTH=${2:-""}
RETENTION_DAYS=${3:-2555}  # 7 years default
INDEX_PATTERN="audit-logs-*"

echo "Audit Logs Cleanup Script"
echo "========================="
echo "Retention period: $RETENTION_DAYS days"
echo "Index pattern: $INDEX_PATTERN"

# Calculate cutoff date
CUTOFF_DATE=$(date -d "-${RETENTION_DAYS} days" +%Y-%m-%d)
CUTOFF_TIMESTAMP=$(date -d "$CUTOFF_DATE" +%s)000

echo "Cutoff date: $CUTOFF_DATE"

# Find indices to delete
if [ -n "$AUTH" ]; then
    INDICES=$(curl -s -u "$AUTH" "${ES_URL}/_cat/indices/${INDEX_PATTERN}?h=index,creation.date.string&format=json")
else
    INDICES=$(curl -s "${ES_URL}/_cat/indices/${INDEX_PATTERN}?h=index,creation.date.string&format=json")
fi

echo "$INDICES" | jq -c '.[]' | while read -r index; do
    INDEX_NAME=$(echo "$index" | jq -r '.index')
    CREATION_DATE=$(echo "$index" | jq -r '.["creation.date.string"]')
    
    # Extract date from index name or creation date
    if [[ $INDEX_NAME =~ audit-logs-([0-9]{4})\.([0-9]{2})\.([0-9]{2}) ]]; then
        INDEX_DATE="${BASH_REMATCH[1]}-${BASH_REMATCH[2]}-${BASH_REMATCH[3]}"
    else
        # Try to parse creation date
        INDEX_DATE=$(date -d "$CREATION_DATE" +%Y-%m-%d 2>/dev/null)
    fi
    
    if [ -n "$INDEX_DATE" ]; then
        if [[ "$INDEX_DATE" < "$CUTOFF_DATE" ]]; then
            echo "Deleting index: $INDEX_NAME (created: $INDEX_DATE)"
            
            if [ -n "$AUTH" ]; then
                curl -s -X DELETE -u "$AUTH" "${ES_URL}/${INDEX_NAME}" | jq '.'
            else
                curl -s -X DELETE "${ES_URL}/${INDEX_NAME}" | jq '.'
            fi
        fi
    fi
done