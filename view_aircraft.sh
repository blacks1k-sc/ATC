#!/bin/bash

# Aircraft Data Table Viewer
# Usage: ./view_aircraft.sh

echo "🛩️  ATC AIRCRAFT DATA TABLE"
echo "================================"
echo ""

# Get aircraft data and format as table
curl -s "http://localhost:3000/api/aircraft" | jq -r '
.aircraft[] | 
[
  .callsign,
  .aircraft_type.icao_type,
  .airline.icao,
  (.position.lat | round * 100 / 100),
  (.position.lon | round * 100 / 100),
  .position.altitude_ft,
  .position.speed_kts,
  .position.heading,
  .flight_plan.origin,
  .flight_plan.destination,
  .controller,
  .phase // "N/A"
] | @tsv
' | while IFS=$'\t' read -r callsign type airline lat lon alt spd hdg origin dest ctrl phase; do
  printf "%-10s %-8s %-7s %-8s %-8s %-8s %-8s %-7s %-6s  %-6s  %-8s %-8s\n" \
    "$callsign" "$type" "$airline" "$lat" "$lon" "$alt" "$spd" "$hdg" "$origin" "$dest" "$ctrl" "$phase"
done

echo ""
echo "📊 Total Aircraft: $(curl -s "http://localhost:3000/api/aircraft" | jq '.aircraft | length')"
echo "🔄 Engine Status: $(curl -s "http://localhost:3000/api/health" | jq -r '.overall')"
echo ""
echo "Legend:"
echo "  CALLSIGN - Aircraft callsign"
echo "  TYPE     - Aircraft type (B748, A320, etc.)"
echo "  AIRLINE  - Airline ICAO code"
echo "  LAT/LON  - Position coordinates"
echo "  ALT      - Altitude in feet"
echo "  SPD      - Speed in knots"
echo "  HDG      - Heading in degrees"
echo "  ORIGIN   - Flight origin airport"
echo "  DEST     - Flight destination"
echo "  CTRL     - Controller (ENGINE, ATC, etc.)"
echo "  PHASE    - Flight phase (CRUISE, DESCENT, etc.)"
