"""
Physical constants and performance envelopes for aircraft kinematics.
All values derived from real aviation standards.
"""

import math

# ========== Time Step ==========
DT = 1.0  # seconds - fixed 1 Hz tick rate

# ========== Acceleration Limits ==========
# Based on typical jet transport acceleration capabilities
A_ACC_MAX = 0.6  # kt/s - maximum acceleration (positive)
A_DEC_MAX = 0.8  # kt/s - maximum deceleration (negative)

# ========== Bank Angle Limits ==========
PHI_MAX_DEG = 25.0  # degrees - maximum bank angle
PHI_MAX_RAD = math.radians(PHI_MAX_DEG)  # radians

# ========== Vertical Speed Limits ==========
# fpm = feet per minute
H_DOT_CLIMB_MAX = 2500.0  # fpm - maximum climb rate (cruise)
H_DOT_CLIMB_MAX_APPROACH = 1800.0  # fpm - capped during approach
H_DOT_DESCENT_MAX = 3000.0  # fpm - maximum descent rate (cruise)
H_DOT_DESCENT_MAX_APPROACH = 1800.0  # fpm - capped during approach (stabilized)

# ========== Glideslope Parameters ==========
GLIDESLOPE_ANGLE_DEG = 3.0  # degrees - standard ILS glideslope
GLIDESLOPE_ANGLE_RAD = math.radians(GLIDESLOPE_ANGLE_DEG)
GLIDESLOPE_SLOPE = math.tan(GLIDESLOPE_ANGLE_RAD)  # ~0.0524

# ========== Physical Constants ==========
G = 9.80665  # m/s² - standard gravity

# ========== Distance Thresholds ==========
# Nautical miles from airport
ENTRY_ZONE_THRESHOLD_NM = 30.0  # Enter ATC control zone
HANDOFF_READY_THRESHOLD_NM = 20.0  # Ready for approach handoff
TOUCHDOWN_ALTITUDE_FT = 50.0  # AGL - consider touchdown below this

# ========== Random Drift (Uncontrolled Aircraft) ==========
# Applied when no specific target is set
DRIFT_SPEED_KT = 5.0  # ± knots
DRIFT_HEADING_DEG = 2.0  # ± degrees

# ========== Coordinate Conversion ==========
NM_PER_DEGREE_LAT = 60.0  # nautical miles per degree latitude
FT_PER_NM = 6076.0  # feet per nautical mile
KT_TO_NM_PER_SEC = 1.0 / 3600.0  # knots to nautical miles per second

# ========== Default Aircraft Performance ==========
# Used when specific aircraft type data unavailable
DEFAULT_CRUISE_SPEED_KTS = 450.0  # knots
DEFAULT_APPROACH_SPEED_KTS = 180.0  # knots
DEFAULT_MIN_SPEED_KTS = 140.0  # knots - stall protection
DEFAULT_MAX_SPEED_KTS = 550.0  # knots

# ========== Phase Definitions ==========
PHASE_CRUISE = "CRUISE"
PHASE_DESCENT = "DESCENT"
PHASE_APPROACH = "APPROACH"
PHASE_FINAL = "FINAL"
PHASE_TOUCHDOWN = "TOUCHDOWN"

# ========== Event Types ==========
EVENT_ENTERED_ENTRY_ZONE = "ENTERED_ENTRY_ZONE"
EVENT_HANDOFF_READY = "HANDOFF_READY"
EVENT_TOUCHDOWN = "TOUCHDOWN"
EVENT_STATE_SNAPSHOT = "STATE_SNAPSHOT"

# ========== Logging Configuration ==========
TELEMETRY_BUFFER_SIZE = 100  # snapshots to buffer before writing
LOG_FORMAT = "json"  # json or csv

# ========== Airport Reference (CYYZ - Toronto Pearson) ==========
CYYZ_LAT = 43.6777  # degrees
CYYZ_LON = -79.6248  # degrees
CYYZ_ELEVATION_FT = 569.0  # feet MSL
CYYZ_MAGNETIC_VARIATION = -10.0  # degrees (West is negative)

# ========== Tick Timing ==========
MAX_TICK_DRIFT_SEC = 0.05  # maximum acceptable drift per tick
TICK_WARNING_THRESHOLD_SEC = 0.1  # log warning if tick takes longer

# ========== Database Query Limits ==========
MAX_ACTIVE_AIRCRAFT = 100  # maximum aircraft to process per tick

