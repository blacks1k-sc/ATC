from flask import Flask, render_template_string, jsonify, request
import pandas as pd
import folium
import json
import os
from datetime import datetime

app = Flask(__name__)

# ==========================
# CONFIGURATION
# ==========================
CENTER_LAT, CENTER_LON = 43.6775, -79.6303  # CYYZ VOR
RANGE_NM = [10, 20, 30, 40, 60]
NM_TO_KM = 1.852
ZOOM_START = 10
ZOOM_MAX = 13
ZOOM_MIN = 9

color_map = {
    "Common": "limegreen",
    "Landing": "deepskyblue",
    "Takeoff": "orange"
}

# Global aircraft data
aircraft_data = []

def load_waypoint_data():
    """Load waypoint data from CSV files"""
    try:
        # Get the directory of this script
        script_dir = os.path.dirname(os.path.abspath(__file__))
        
        df_common = pd.read_csv(os.path.join(script_dir, "yyz_common_waypoints_with_altitude.csv"))
        df_common["Category"] = "Common"

        df_landing = pd.read_csv(os.path.join(script_dir, "yyz_landing_waypoints_with_altitude.csv"))
        df_landing.rename(columns={"Waypoint Name": "Label"}, inplace=True, errors="ignore")
        df_landing["Category"] = "Landing"

        df_takeoff = pd.read_csv(os.path.join(script_dir, "yyz_takeoff_waypoints_with_altitude.csv"))
        df_takeoff.rename(columns={"Waypoint Name": "Label"}, inplace=True, errors="ignore")
        df_takeoff["Category"] = "Takeoff"

        return pd.concat([df_common, df_landing, df_takeoff], ignore_index=True)
    except Exception as e:
        print(f"Error loading waypoint data: {e}")
        return pd.DataFrame()

def create_radar_map():
    """Create the radar map with waypoints and runways"""
    m = folium.Map(
        location=[CENTER_LAT, CENTER_LON],
        tiles="CartoDB dark_matter",
        zoom_start=ZOOM_START,
        min_zoom=ZOOM_MIN,
        max_zoom=ZOOM_MAX,
        control_scale=True
    )

    # Draw range rings
    for r_nm in RANGE_NM:
        folium.Circle(
            radius=r_nm * NM_TO_KM * 1000,  # NM → km → m
            location=[CENTER_LAT, CENTER_LON],
            color="gray",
            weight=1,
            fill=False,
            dash_array="5,5",
            opacity=0.4,
            tooltip=f"{r_nm} NM"
        ).add_to(m)

    # Center marker
    folium.CircleMarker(
        [CENTER_LAT, CENTER_LON],
        radius=5,
        color="red",
        fill=True,
        fill_opacity=1,
        tooltip="CYYZ VOR / Airport Center"
    ).add_to(m)

    # Runways
    runways = [
        {"name": "05/23", "ends": [(43.673889, -79.663889), (43.694722, -79.633333)]},
        {"name": "06L/24R", "ends": [(43.660000, -79.622222), (43.679133, -79.596761)]},
        {"name": "06R/24L", "ends": [(43.658300, -79.621928), (43.675292, -79.597236)]},
        {"name": "15L/33R", "ends": [(43.691944, -79.642219), (43.669997, -79.613892)]},
        {"name": "15R/33L", "ends": [(43.685833, -79.651667), (43.667500, -79.628333)]},
    ]

    for rw in runways:
        coords = rw["ends"]
        folium.PolyLine(
            coords,
            color="white",
            weight=5,
            opacity=0.9,
            tooltip=f"Runway {rw['name']}"
        ).add_to(m)
        # Add threshold dots
        folium.CircleMarker(coords[0], radius=3, color="cyan", fill=True, fill_opacity=1).add_to(m)
        folium.CircleMarker(coords[1], radius=3, color="magenta", fill=True, fill_opacity=1).add_to(m)

    # Load and add waypoints
    df_all = load_waypoint_data()
    for _, row in df_all.iterrows():
        lat, lon = row["Latitude"], row["Longitude"]
        name = row.get("Label", "")
        cat = row["Category"]
        dist = row.get("Distance_nm", "")
        bearing = row.get("Bearing_mag", "")
        alt = row.get("Altitude_ft", "N/A")
        color = color_map.get(cat, "white")

        tooltip_text = (
            f"<b>{name}</b><br>"
            f"Category: {cat}<br>"
            f"Altitude: {alt:,} ft<br>"
            f"Distance: {dist:.2f} NM<br>"
            f"Bearing (Mag): {bearing if bearing==bearing else 'N/A'}°<br>"
            f"Lat: {lat:.5f}<br>"
            f"Lon: {lon:.5f}"
        )

        folium.CircleMarker(
            location=[lat, lon],
            radius=3,
            color=color,
            fill=True,
            fill_opacity=0.9,
            tooltip=folium.Tooltip(tooltip_text, sticky=True)
        ).add_to(m)

    # Add aircraft markers
    for aircraft in aircraft_data:
        folium.CircleMarker(
            location=[aircraft['lat'], aircraft['lon']],
            radius=8,
            color='#00ffff',
            fill=True,
            fill_opacity=0.9,
            tooltip=folium.Tooltip(
                f"<b>{aircraft['callsign']}</b><br>"
                f"Type: {aircraft.get('type', 'N/A')}<br>"
                f"Altitude: {aircraft.get('altitude', 'N/A')} ft<br>"
                f"Speed: {aircraft.get('speed', 'N/A')} kts<br>"
                f"Status: {aircraft.get('status', 'N/A')}",
                sticky=True
            )
        ).add_to(m)

    # Limit pan/viewbox
    delta_deg = 60 * NM_TO_KM / 111  # ~60 NM in degrees
    bounds = [
        [CENTER_LAT - delta_deg, CENTER_LON - delta_deg],
        [CENTER_LAT + delta_deg, CENTER_LON + delta_deg],
    ]
    m.fit_bounds(bounds)

    return m

@app.route('/')
def radar_map():
    """Serve the radar map"""
    m = create_radar_map()
    return m._repr_html_()

@app.route('/api/aircraft', methods=['GET', 'POST'])
def aircraft_endpoint():
    """Handle aircraft data"""
    global aircraft_data
    
    if request.method == 'POST':
        data = request.get_json()
        aircraft_data = data.get('aircraft', [])
        return jsonify({"status": "success", "count": len(aircraft_data)})
    
    return jsonify({"aircraft": aircraft_data})

@app.route('/api/health')
def health():
    """Health check endpoint"""
    return jsonify({"status": "healthy", "timestamp": datetime.now().isoformat()})

if __name__ == '__main__':
    print("🚁 Starting Radar Service...")
    print("📍 Map available at: http://localhost:5001")
    print("🛩️  Aircraft API at: http://localhost:5001/api/aircraft")
    app.run(host='0.0.0.0', port=5001, debug=True)
