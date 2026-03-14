#!/usr/bin/env bash

set -euo pipefail

API_URL="${API_URL:-http://localhost:8000/api/boats/report}"
BOAT_ID="${1:-boat-1}"
GPS_LAT="${2:-34.1025}"
GPS_LON="${3:--77.3970}"
HEADING="${4:-95}"
TIMESTAMP="$(date +%s)"

curl -sS -X POST "$API_URL" \
  -H "Content-Type: application/json" \
  -d @- <<EOF
{
  "boat_id": "$BOAT_ID",
  "timestamp": $TIMESTAMP,
  "gps_lat": $GPS_LAT,
  "gps_lon": $GPS_LON,
  "heading": $HEADING,
  "detections": []
}
EOF

