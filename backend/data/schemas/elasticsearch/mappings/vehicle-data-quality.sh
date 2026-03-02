#!/bin/bash

# Vehicle Data Quality Check Script
# Validates and reports on vehicle data quality in Elasticsearch

ES_URL=${1:-"http://localhost:9200"}
AUTH=${2:-""}
INDEX_PATTERN="vehicles-*"

echo "Vehicle Data Quality Check"
echo "=========================="
echo ""

# Function to run query and extract value
run_query() {
    local query="$1"
    local field="$2"
    
    if [ -n "$AUTH" ]; then
        curl -s -u "$AUTH" -X GET "${ES_URL}/${INDEX_PATTERN}/_search" \
            -H "Content-Type: application/json" \
            -d "$query" | jq -r "$field"
    else
        curl -s -X GET "${ES_URL}/${INDEX_PATTERN}/_search" \
            -H "Content-Type: application/json" \
            -d "$query" | jq -r "$field"
    fi
}

# Total vehicle count
TOTAL_QUERY='{
  "size": 0,
  "track_total_hits": true
}'
TOTAL=$(run_query "$TOTAL_QUERY" '.hits.total.value')
echo "Total vehicles: $TOTAL"

# Vehicles with missing license plate
MISSING_PLATE_QUERY='{
  "size": 0,
  "query": {
    "bool": {
      "must_not": {
        "exists": {
          "field": "license_plate"
        }
      }
    }
  },
  "track_total_hits": true
}'
MISSING_PLATE=$(run_query "$MISSING_PLATE_QUERY" '.hits.total.value')
MISSING_PLATE_PCT=$(echo "scale=2; $MISSING_PLATE * 100 / $TOTAL" | bc)
echo "Missing license plate: $MISSING_PLATE ($MISSING_PLATE_PCT%)"

# Vehicles with missing VIN
MISSING_VIN_QUERY='{
  "size": 0,
  "query": {
    "bool": {
      "must_not": {
        "exists": {
          "field": "vin"
        }
      }
    }
  },
  "track_total_hits": true
}'
MISSING_VIN=$(run_query "$MISSING_VIN_QUERY" '.hits.total.value')
MISSING_VIN_PCT=$(echo "scale=2; $MISSING_VIN * 100 / $TOTAL" | bc)
echo "Missing VIN: $MISSING_VIN ($MISSING_VIN_PCT%)"

# Vehicles with expired registration
EXPIRED_REG_QUERY='{
  "size": 0,
  "query": {
    "range": {
      "registration.expiry_date": {
        "lt": "now"
      }
    }
  },
  "track_total_hits": true
}'
EXPIRED_REG=$(run_query "$EXPIRED_REG_QUERY" '.hits.total.value')
EXPIRED_REG_PCT=$(echo "scale=2; $EXPIRED_REG * 100 / $TOTAL" | bc)
echo "Expired registration: $EXPIRED_REG ($EXPIRED_REG_PCT%)"

# Vehicles with expired insurance
EXPIRED_INS_QUERY='{
  "size": 0,
  "query": {
    "range": {
      "insurance.expiry_date": {
        "lt": "now"
      }
    }
  },
  "track_total_hits": true
}'
EXPIRED_INS=$(run_query "$EXPIRED_INS_QUERY" '.hits.total.value')
EXPIRED_INS_PCT=$(echo "scale=2; $EXPIRED_INS * 100 / $TOTAL" | bc)
echo "Expired insurance: $EXPIRED_INS ($EXPIRED_INS_PCT%)"

# Blacklisted vehicles
BLACKLISTED_QUERY='{
  "size": 0,
  "query": {
    "term": {
      "status.is_blacklisted": true
    }
  },
  "track_total_hits": true
}'
BLACKLISTED=$(run_query "$BLACKLISTED_QUERY" '.hits.total.value')
BLACKLISTED_PCT=$(echo "scale=2; $BLACKLISTED * 100 / $TOTAL" | bc)
echo "Blacklisted vehicles: $BLACKLISTED ($BLACKLISTED_PCT%)"

# Active vehicles
ACTIVE_QUERY='{
  "size": 0,
  "query": {
    "term": {
      "status.is_active": true
    }
  },
  "track_total_hits": true
}'
ACTIVE=$(run_query "$ACTIVE_QUERY" '.hits.total.value')
ACTIVE_PCT=$(echo "scale=2; $ACTIVE * 100 / $TOTAL" | bc)
echo "Active vehicles: $ACTIVE ($ACTIVE_PCT%)"

# Currently parked vehicles
PARKED_QUERY='{
  "size": 0,
  "query": {
    "exists": {
      "field": "current_session.id"
    }
  },
  "track_total_hits": true
}'
PARKED=$(run_query "$PARKED_QUERY" '.hits.total.value')
PARKED_PCT=$(echo "scale=2; $PARKED * 100 / $TOTAL" | bc)
echo "Currently parked: $PARKED ($PARKED_PCT%)"

echo ""
echo "Vehicle Type Distribution:"
TYPE_QUERY='{
  "size": 0,
  "aggs": {
    "by_type": {
      "terms": {
        "field": "vehicle_type",
        "size": 20
      }
    }
  }
}'
run_query "$TYPE_QUERY" '.aggregations.by_type.buckets[] | "  \(.key): \(.doc_count)"'

echo ""
echo "Top Vehicle Makes:"
MAKE_QUERY='{
  "size": 0,
  "aggs": {
    "by_make": {
      "terms": {
        "field": "make.keyword",
        "size": 10
      }
    }
  }
}'
run_query "$MAKE_QUERY" '.aggregations.by_make.buckets[] | "  \(.key): \(.doc_count)"'

echo ""
echo "Data Quality Score:"
QUALITY_SCORE=$(echo "scale=2; (100 - ($MISSING_PLATE_PCT + $MISSING_VIN_PCT)/2)" | bc)
echo "  Overall: $QUALITY_SCORE%"

if (( $(echo "$QUALITY_SCORE > 95" | bc -l) )); then
    echo "  Grade: A"
elif (( $(echo "$QUALITY_SCORE > 90" | bc -l) )); then
    echo "  Grade: B"
elif (( $(echo "$QUALITY_SCORE > 80" | bc -l) )); then
    echo "  Grade: C"
else
    echo "  Grade: D - Improvement needed"
fi