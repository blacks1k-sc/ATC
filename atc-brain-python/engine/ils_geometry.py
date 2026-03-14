"""
ILS approach geometry for CYYZ (Toronto Pearson).

Provides:
- Runway threshold coordinates and headings
- Extended centerline / FAF / intercept point computation
- Per-aircraft waypoint sequence (ENTRY → INTERCEPT → FAF → THRESHOLD)
- Glideslope altitude at any distance from threshold
"""

import math
from typing import List, Dict, Any, Tuple

# ─── Constants ────────────────────────────────────────────────────────────────
NM_PER_DEGREE_LAT = 60.0
FT_PER_NM = 6076.0
GLIDESLOPE_DEG = 3.0
CYYZ_ELEVATION_FT = 569.0

# ─── Real CYYZ runway data ─────────────────────────────────────────────────────
# threshold = where aircraft touch down (the end they land on)
# heading   = magnetic heading an aircraft flies on approach
# Coordinates from CYYZ charts / radar-map.html polylines
CYYZ_RUNWAYS: Dict[str, Dict[str, Any]] = {
    "05": {
        "heading": 50,
        "threshold": (43.673889, -79.663889),   # SW end — land heading 050
        "display_name": "RWY 05  (HDG 050°)",
    },
    "23": {
        "heading": 230,
        "threshold": (43.694722, -79.633333),   # NE end — land heading 230
        "display_name": "RWY 23  (HDG 230°) — Preferred",
    },
    "06L": {
        "heading": 60,
        "threshold": (43.660000, -79.622222),   # SW end
        "display_name": "RWY 06L (HDG 060°)",
    },
    "24R": {
        "heading": 240,
        "threshold": (43.679133, -79.596761),   # NE end
        "display_name": "RWY 24R (HDG 240°)",
    },
    "06R": {
        "heading": 60,
        "threshold": (43.658300, -79.621928),   # SW end
        "display_name": "RWY 06R (HDG 060°)",
    },
    "24L": {
        "heading": 240,
        "threshold": (43.675292, -79.597236),   # NE end
        "display_name": "RWY 24L (HDG 240°)",
    },
    "15L": {
        "heading": 150,
        "threshold": (43.691944, -79.642219),   # NW end
        "display_name": "RWY 15L (HDG 150°)",
    },
    "33R": {
        "heading": 330,
        "threshold": (43.669997, -79.613892),   # SE end
        "display_name": "RWY 33R (HDG 330°)",
    },
    "15R": {
        "heading": 150,
        "threshold": (43.685833, -79.651667),   # NW end
        "display_name": "RWY 15R (HDG 150°)",
    },
    "33L": {
        "heading": 330,
        "threshold": (43.667500, -79.628333),   # SE end
        "display_name": "RWY 33L (HDG 330°)",
    },
}

# Runways shown in selection UI (paired opposites)
SELECTABLE_RUNWAYS = [
    "23", "05",
    "24R", "06L",
    "24L", "06R",
    "33R", "15L",
    "33L", "15R",
]


# ─── Core geometry ─────────────────────────────────────────────────────────────

def offset_point(
    lat: float, lon: float,
    bearing_deg: float,
    distance_nm: float,
) -> Tuple[float, float]:
    """
    Move lat/lon by distance_nm along bearing_deg.
    Uses flat-earth approximation (accurate for < 200 NM).
    """
    bearing_rad = math.radians(bearing_deg)
    cos_lat = math.cos(math.radians(lat))
    delta_lat = (distance_nm / NM_PER_DEGREE_LAT) * math.cos(bearing_rad)
    delta_lon = (distance_nm / NM_PER_DEGREE_LAT) * math.sin(bearing_rad) / max(cos_lat, 0.001)
    return lat + delta_lat, lon + delta_lon


def bearing_between(
    lat1: float, lon1: float,
    lat2: float, lon2: float,
) -> float:
    """Initial bearing from point 1 to point 2 (0–360°)."""
    lat1_r = math.radians(lat1)
    lat2_r = math.radians(lat2)
    d_lon_r = math.radians(lon2 - lon1)
    x = math.sin(d_lon_r) * math.cos(lat2_r)
    y = math.cos(lat1_r) * math.sin(lat2_r) - math.sin(lat1_r) * math.cos(lat2_r) * math.cos(d_lon_r)
    return (math.degrees(math.atan2(x, y)) + 360) % 360


def distance_nm(
    lat1: float, lon1: float,
    lat2: float, lon2: float,
) -> float:
    """Flat-earth distance in NM."""
    mid_lat = (lat1 + lat2) / 2.0
    cos_lat = math.cos(math.radians(mid_lat))
    dy = (lat2 - lat1) * NM_PER_DEGREE_LAT
    dx = (lon2 - lon1) * NM_PER_DEGREE_LAT * cos_lat
    return math.sqrt(dx * dx + dy * dy)


# ─── Glideslope ────────────────────────────────────────────────────────────────

def glideslope_altitude_ft(
    distance_to_threshold_nm: float,
    runway_elevation_ft: float = CYYZ_ELEVATION_FT,
) -> float:
    """
    Return the on-glideslope altitude (MSL) for a given distance from the
    runway threshold.  Uses a 3° glideslope: h = elev + tan(3°) × dist × ft/NM
    """
    return runway_elevation_ft + math.tan(math.radians(GLIDESLOPE_DEG)) * distance_to_threshold_nm * FT_PER_NM


# ─── Approach path geometry ────────────────────────────────────────────────────

def approach_direction(runway_id: str) -> float:
    """
    Direction FROM which aircraft approach.
    = reverse of the landing heading.
    E.g. landing HDG 230 → approach direction 050°  (aircraft come from NE).
    """
    return (CYYZ_RUNWAYS[runway_id]["heading"] + 180) % 360


def centerline_point(runway_id: str, distance_from_threshold_nm: float) -> Tuple[float, float]:
    """
    Return lat/lon of a point on the EXTENDED centerline at the given
    distance outbound from the threshold (i.e., in the approach direction).
    """
    rwy = CYYZ_RUNWAYS[runway_id]
    thr_lat, thr_lon = rwy["threshold"]
    return offset_point(thr_lat, thr_lon, approach_direction(runway_id), distance_from_threshold_nm)


def compute_waypoint_sequence(
    aircraft_lat: float,
    aircraft_lon: float,
    runway_id: str,
    queue_position: int = 0,
    base_intercept_nm: float = 20.0,
    spacing_nm: float = 5.0,
) -> List[Dict[str, Any]]:
    """
    Build the full waypoint sequence for one aircraft approaching runway_id.

    Waypoints (in order):
      ENTRY      — perpendicular offset from the intercept point; creates a
                   natural ~30-45° intercept angle onto the centerline
      INTERCEPT  — point on the extended centerline where aircraft joins the
                   ILS course; staggered 5 NM per queue position
      FAF        — Final Approach Fix at 15 NM from threshold (glideslope entry)
      THRESHOLD  — runway threshold (touchdown target)

    Args:
        aircraft_lat, aircraft_lon: Current aircraft position
        runway_id:     e.g. "23", "06L"
        queue_position: 0 = first in queue (closest intercept), 1 = second, …
        base_intercept_nm: Centerline distance for the first aircraft
        spacing_nm:    Extra distance per queue slot
    """
    rwy = CYYZ_RUNWAYS[runway_id]
    thr_lat, thr_lon = rwy["threshold"]
    app_dir = approach_direction(runway_id)          # e.g. 050° for RWY 23
    landing_hdg = float(rwy["heading"])              # e.g. 230° for RWY 23

    # ── Intercept point ───────────────────────────────────────────────────────
    intercept_dist = base_intercept_nm + queue_position * spacing_nm
    int_lat, int_lon = centerline_point(runway_id, intercept_dist)

    # ── Entry waypoint (offset perpendicular to centerline) ───────────────────
    # Determine which side of the centerline the aircraft is on.
    bearing_to_int = bearing_between(aircraft_lat, aircraft_lon, int_lat, int_lon)
    # Angle between aircraft's bearing to intercept and the approach direction
    angle_diff = (bearing_to_int - app_dir + 360) % 360

    if angle_diff <= 180:
        # Aircraft is to the LEFT of centerline (relative to approach direction)
        perp_dir = (app_dir - 90) % 360
    else:
        # Aircraft is to the RIGHT
        perp_dir = (app_dir + 90) % 360

    # Entry point: 15 NM perpendicular from intercept point
    ent_lat, ent_lon = offset_point(int_lat, int_lon, perp_dir, 15.0)

    # ── FAF ───────────────────────────────────────────────────────────────────
    faf_lat, faf_lon = centerline_point(runway_id, 15.0)

    return [
        {
            "lat": ent_lat, "lon": ent_lon,
            "type": "ENTRY",
            "name": f"ENTRY_{runway_id}",
            "target_altitude_ft": 6000,
            "target_speed_kts": 210,
            "target_heading_deg": None,   # steered by bearing to next wp
        },
        {
            "lat": int_lat, "lon": int_lon,
            "type": "INTERCEPT",
            "name": f"INTCP_{runway_id}_{queue_position}",
            "target_altitude_ft": 3000,
            "target_speed_kts": 170,
            "target_heading_deg": landing_hdg,
        },
        {
            "lat": faf_lat, "lon": faf_lon,
            "type": "FAF",
            "name": f"FAF_{runway_id}",
            "target_altitude_ft": glideslope_altitude_ft(15.0),
            "target_speed_kts": 150,
            "target_heading_deg": landing_hdg,
        },
        {
            "lat": thr_lat, "lon": thr_lon,
            "type": "THRESHOLD",
            "name": f"THR_{runway_id}",
            "target_altitude_ft": CYYZ_ELEVATION_FT + 50,
            "target_speed_kts": 140,
            "target_heading_deg": landing_hdg,
        },
    ]


def get_runway_info(runway_id: str) -> Dict[str, Any]:
    """Return runway data dict or raise KeyError if unknown."""
    if runway_id not in CYYZ_RUNWAYS:
        raise KeyError(f"Unknown runway: {runway_id}")
    rwy = CYYZ_RUNWAYS[runway_id].copy()
    rwy["id"] = runway_id
    rwy["approach_direction"] = approach_direction(runway_id)
    return rwy
