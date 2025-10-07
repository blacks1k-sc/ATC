#!/bin/bash

# Detailed Aircraft Data Table Viewer
# Usage: ./detailed_aircraft.sh

echo "🛩️  DETAILED ATC AIRCRAFT DATA TABLE"
echo "============================================="
echo ""

# Get detailed aircraft data
curl -s "http://localhost:3000/api/aircraft" | jq -r '
.aircraft[] | 
[
  .callsign,
  .aircraft_type.icao_type,
  .aircraft_type.wake,
  .airline.icao,
  .airline.name,
  (.position.lat | round * 10000 / 10000),
  (.position.lon | round * 10000 / 10000),
  .position.altitude_ft,
  .position.speed_kts,
  .position.heading,
  .flight_plan.origin,
  .flight_plan.destination,
  .flight_plan.runway,
  .controller,
  .phase // "N/A",
  .squawk_code,
  .icao24
] | @tsv
' | while IFS=$'\t' read -r callsign type wake airline airlinename lat lon alt spd hdg origin dest runway ctrl phase squawk icao24; do
  printf "%-12s %-8s %-4s %-6s %-25s %-10s %-10s %-8s %-8s %-6s %-6s  %-6s  %-6s %-8s %-8s %-6s %-8s\n" \
    "$callsign" "$type" "$wake" "$airline" "${airlinename:0:24}" "$lat" "$lon" "$alt" "$spd" "$hdg" "$origin" "$dest" "$runway" "$ctrl" "$phase" "$squawk" "$icao24"
done

echo ""
echo "📊 Total Aircraft: $(curl -s "http://localhost:3000/api/aircraft" | jq '.aircraft | length')"
echo "🔄 Engine Status: $(curl -s "http://localhost:3000/api/health" | jq -r '.overall')"
echo ""
echo "Legend:"
echo "  CALLSIGN    - Aircraft callsign"
echo "  TYPE        - Aircraft type (B748, A320, etc.)"
echo "  WAKE        - Wake category (H, M, L)"
echo "  AIRLINE     - Airline ICAO code"
echo "  AIRLINE NAME- Airline full name"
echo "  LAT/LON     - Position coordinates (4 decimal places)"
echo "  ALT         - Altitude in feet"
echo "  SPD         - Speed in knots"
echo "  HDG         - Heading in degrees"
echo "  ORIGIN      - Flight origin airport"
echo "  DEST        - Flight destination"
echo "  RUNWAY      - Assigned runway"
echo "  CTRL        - Controller (ENGINE, ATC, etc.)"
echo "  PHASE       - Flight phase (CRUISE, DESCENT, etc.)"
echo "  SQUAWK      - Transponder code"
echo "  ICAO24      - ICAO 24-bit address"
