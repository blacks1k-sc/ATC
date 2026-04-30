"""
CYYZ (Toronto Pearson) taxiway network for ground routing.

Provides Dijkstra-based routing from runway exits to gates with unique
per-aircraft segment reservation and asyncio-safe gate assignment.
"""

import asyncio
import heapq
import logging
import math
from typing import Dict, List, Optional, Set, Tuple

logger = logging.getLogger(__name__)


def _haversine_nm(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Great-circle distance in nautical miles."""
    R = 3440.065
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dl = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dl / 2) ** 2
    return R * 2 * math.asin(math.sqrt(a))


# ---------------------------------------------------------------------------
# CYYZ Network Definition
# node tuple: (lat, lon, node_type)
# node_type: 'runway_exit' | 'intersection' | 'apron'
# ---------------------------------------------------------------------------

NODES: Dict[str, Tuple[float, float, str]] = {
    # ── Runway exit nodes ──────────────────────────────────────────────────
    # 23R  (aircraft land heading SW, exit to north taxiways)
    "EX23R_HS1": (43.6842, -79.6482, "runway_exit"),
    "EX23R_HS2": (43.6855, -79.6515, "runway_exit"),
    # 23L  (parallel runway, similar exits)
    "EX23L_HS1": (43.6818, -79.6510, "runway_exit"),
    # 05L  (aircraft land heading NE, exit mid-field or NE end)
    "EX05L_MID": (43.6748, -79.6210, "runway_exit"),
    "EX05L_NE":  (43.6878, -79.6568, "runway_exit"),
    # 05R
    "EX05R_MID": (43.6724, -79.6245, "runway_exit"),
    # 06L / 24R (diagonal runway)
    "EX06L_N":   (43.6742, -79.6095, "runway_exit"),
    "EX24R_N":   (43.6737, -79.6332, "runway_exit"),
    # 15L / 15R / 33L / 33R (crosswind, simplified to nearest Alpha/Bravo)
    "EX15L":     (43.6780, -79.6198, "runway_exit"),
    "EX15R":     (43.6768, -79.6205, "runway_exit"),

    # ── Alpha taxiway (main E-W parallel, south of terminals) ──────────────
    "ALPHA_E":   (43.6835, -79.6488, "intersection"),
    "ALPHA_C1":  (43.6812, -79.6438, "intersection"),
    "ALPHA_C2":  (43.6790, -79.6382, "intersection"),
    "ALPHA_W":   (43.6775, -79.6338, "intersection"),

    # ── Bravo taxiway (connects Alpha to T3 / 06L area) ───────────────────
    "BRAVO_N":   (43.6808, -79.6268, "intersection"),
    "BRAVO_S":   (43.6784, -79.6265, "intersection"),

    # ── Charlie (east N-S corridor) ────────────────────────────────────────
    "CHARLIE_S": (43.6845, -79.6462, "intersection"),
    "CHARLIE_N": (43.6868, -79.6390, "intersection"),

    # ── Delta (main N-S corridor to T1) ───────────────────────────────────
    "DELTA_S":   (43.6855, -79.6355, "intersection"),
    "DELTA_N":   (43.6878, -79.6305, "intersection"),

    # ── Echo / Foxtrot / Golf (T1 approach spurs) ─────────────────────────
    "ECHO":      (43.6870, -79.6262, "intersection"),
    "FOXTROT":   (43.6852, -79.6242, "intersection"),
    "GOLF":      (43.6822, -79.6252, "intersection"),

    # ── Terminal apron entry nodes ─────────────────────────────────────────
    "T1A_APR":   (43.6888, -79.6182, "apron"),   # Pier A domestic/US transborder
    "T1B_APR":   (43.6895, -79.6215, "apron"),   # Pier B international
    "T1C_APR":   (43.6902, -79.6248, "apron"),   # Pier C international
    "T1D_APR":   (43.6895, -79.6275, "apron"),   # Pier D international
    "T1F_APR":   (43.6878, -79.6298, "apron"),   # Pier F wide-body
    "T3_APR":    (43.6800, -79.6258, "apron"),   # Terminal 3
}

# Edges: (node_a, node_b, taxiway_segment_name)  — all bidirectional
EDGES: List[Tuple[str, str, str]] = [
    # ── Runway exits → main taxiways ──────────────────────────────────────
    ("EX23R_HS1",  "ALPHA_E",   "HS1"),
    ("EX23R_HS2",  "ALPHA_E",   "HS2"),
    ("EX23L_HS1",  "ALPHA_E",   "HS3"),
    ("EX05L_MID",  "ALPHA_C2",  "ND3"),
    ("EX05L_NE",   "ALPHA_E",   "ND1"),
    ("EX05R_MID",  "ALPHA_W",   "ND4"),
    ("EX06L_N",    "BRAVO_S",   "ND6"),
    ("EX24R_N",    "ALPHA_W",   "ND7"),
    ("EX15L",      "BRAVO_N",   "ND8"),
    ("EX15R",      "BRAVO_S",   "ND9"),

    # ── Alpha E-W segments ────────────────────────────────────────────────
    ("ALPHA_E",   "ALPHA_C1",  "A"),
    ("ALPHA_C1",  "ALPHA_C2",  "A"),
    ("ALPHA_C2",  "ALPHA_W",   "A"),

    # ── Alpha → Bravo cross connectors ────────────────────────────────────
    ("ALPHA_C2",  "BRAVO_N",  "NB1"),
    ("ALPHA_W",   "BRAVO_S",  "NB2"),

    # ── Bravo N-S ─────────────────────────────────────────────────────────
    ("BRAVO_N",   "BRAVO_S",   "B"),
    ("BRAVO_N",   "GOLF",      "NC1"),

    # ── Charlie (east N-S) ────────────────────────────────────────────────
    ("ALPHA_E",    "CHARLIE_S",  "C"),
    ("CHARLIE_S",  "CHARLIE_N",  "C"),
    ("CHARLIE_N",  "DELTA_S",    "NC2"),

    # ── Delta N-S ─────────────────────────────────────────────────────────
    ("ALPHA_C1",  "DELTA_S",   "D"),
    ("DELTA_S",   "DELTA_N",   "D"),
    ("DELTA_N",   "ECHO",      "ND2"),

    # ── Echo / Foxtrot / Golf spurs ───────────────────────────────────────
    ("ALPHA_C2",  "ECHO",      "E"),
    ("ECHO",      "FOXTROT",   "EF"),
    ("FOXTROT",   "GOLF",      "FG"),
    ("GOLF",      "T3_APR",    "GT3"),
    ("BRAVO_S",   "T3_APR",    "BT3"),

    # ── T1 apron connections ──────────────────────────────────────────────
    ("DELTA_N",   "T1A_APR",   "NA1"),
    ("ECHO",      "T1A_APR",   "NA2"),
    ("ECHO",      "T1B_APR",   "NB3"),
    ("DELTA_N",   "T1B_APR",   "NB4"),
    ("ECHO",      "T1C_APR",   "NC3"),
    ("FOXTROT",   "T1C_APR",   "NC4"),
    ("FOXTROT",   "T1D_APR",   "ND5"),
    ("FOXTROT",   "T1F_APR",   "NF1"),
    ("GOLF",      "T1F_APR",   "NF2"),

    # ── Inter-apron service roads ──────────────────────────────────────────
    ("T1A_APR",   "T1B_APR",   "PA"),
    ("T1B_APR",   "T1C_APR",   "PB"),
    ("T1C_APR",   "T1D_APR",   "PC"),
    ("T1D_APR",   "T1F_APR",   "PD"),
    ("T1F_APR",   "T3_APR",    "PF"),
]

# Gates: gate_id -> (apron_node, lat, lon)
GATES: Dict[str, Tuple[str, float, float]] = {
    # Terminal 1 Pier A — domestic / US transborder
    "A1":   ("T1A_APR", 43.6890, -79.6172),
    "A4":   ("T1A_APR", 43.6891, -79.6175),
    "A8":   ("T1A_APR", 43.6892, -79.6178),
    "A12":  ("T1A_APR", 43.6893, -79.6181),
    "A16":  ("T1A_APR", 43.6894, -79.6184),
    "A20":  ("T1A_APR", 43.6895, -79.6187),
    "A24":  ("T1A_APR", 43.6896, -79.6190),
    # Terminal 1 Pier B — international
    "B2":   ("T1B_APR", 43.6896, -79.6208),
    "B6":   ("T1B_APR", 43.6897, -79.6212),
    "B12":  ("T1B_APR", 43.6898, -79.6216),
    "B18":  ("T1B_APR", 43.6899, -79.6220),
    "B24":  ("T1B_APR", 43.6900, -79.6224),
    "B30":  ("T1B_APR", 43.6901, -79.6228),
    "B36":  ("T1B_APR", 43.6902, -79.6232),
    # Terminal 1 Pier C — international
    "C1":   ("T1C_APR", 43.6903, -79.6242),
    "C6":   ("T1C_APR", 43.6904, -79.6246),
    "C12":  ("T1C_APR", 43.6905, -79.6250),
    "C18":  ("T1C_APR", 43.6906, -79.6254),
    "C22":  ("T1C_APR", 43.6907, -79.6258),
    # Terminal 1 Pier D — international
    "D1":   ("T1D_APR", 43.6896, -79.6268),
    "D6":   ("T1D_APR", 43.6897, -79.6272),
    "D12":  ("T1D_APR", 43.6898, -79.6276),
    "D18":  ("T1D_APR", 43.6899, -79.6280),
    "D24":  ("T1D_APR", 43.6900, -79.6284),
    # Terminal 1 Pier F — wide-body international
    "F71":  ("T1F_APR", 43.6879, -79.6292),
    "F75":  ("T1F_APR", 43.6880, -79.6296),
    "F79":  ("T1F_APR", 43.6881, -79.6300),
    "F83":  ("T1F_APR", 43.6882, -79.6304),
    "F87":  ("T1F_APR", 43.6883, -79.6308),
    "F91":  ("T1F_APR", 43.6884, -79.6312),
    "F95":  ("T1F_APR", 43.6885, -79.6316),
    # Terminal 3
    "T3-1": ("T3_APR",  43.6802, -79.6250),
    "T3-2": ("T3_APR",  43.6804, -79.6252),
    "T3-3": ("T3_APR",  43.6806, -79.6254),
    "T3-4": ("T3_APR",  43.6808, -79.6256),
    "T3-5": ("T3_APR",  43.6810, -79.6258),
    "T3-6": ("T3_APR",  43.6812, -79.6260),
}

# First taxiway node(s) reached after vacating each runway
RUNWAY_EXITS: Dict[str, List[str]] = {
    "05L": ["EX05L_MID", "EX05L_NE"],
    "23R": ["EX23R_HS1", "EX23R_HS2"],
    "05R": ["EX05R_MID"],
    "23L": ["EX23L_HS1"],
    "06L": ["EX06L_N"],
    "24R": ["EX24R_N"],
    "15L": ["EX15L"],
    "33R": ["EX15L"],
    "15R": ["EX15R"],
    "33L": ["EX15R"],
}

# Ground taxi speed targets (knots)
GROUND_SPEED_KTS = 15
GATE_APPROACH_SPEED_KTS = 5
# Waypoint advance threshold on ground (NM) — much tighter than airborne 1.0 NM
GROUND_WP_ADVANCE_NM = 0.08


# ---------------------------------------------------------------------------
# TaxiwayNetwork
# ---------------------------------------------------------------------------

class TaxiwayNetwork:
    """
    CYYZ taxiway graph with asyncio-safe gate and segment occupancy.

    One global instance shared by the kinematics engine.
    All state-mutating methods are async and hold self._lock.
    Read-only queries (get_free_gates, snapshot) are sync for zero overhead.
    """

    def __init__(self):
        self._lock = asyncio.Lock()

        # Build adjacency list: node -> [(neighbor, segment_name, cost_nm)]
        self._nodes: Dict[str, Tuple[float, float, str]] = dict(NODES)
        self._adj: Dict[str, List[Tuple[str, str, float]]] = {n: [] for n in self._nodes}
        for node_a, node_b, seg in EDGES:
            cost = _haversine_nm(*self._nodes[node_a][:2], *self._nodes[node_b][:2])
            self._adj[node_a].append((node_b, seg, cost))
            self._adj[node_b].append((node_a, seg, cost))

        # segment_key -> aircraft_id (or None means free)
        self._segment_occ: Dict[str, Optional[int]] = {}
        # gate_id -> aircraft_id (or None means free)
        self._gate_occ: Dict[str, Optional[int]] = {g: None for g in GATES}
        # aircraft_id -> gate_id
        self._ac_gate: Dict[int, str] = {}
        # aircraft_id -> list of reserved segment_keys
        self._ac_segs: Dict[int, List[str]] = {}

        logger.info(
            "[TaxiwayNet] CYYZ network ready: %d nodes, %d edges, %d gates",
            len(self._nodes), len(EDGES), len(GATES),
        )

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _seg_key(a: str, b: str, seg: str) -> str:
        """Canonical bidirectional key for a taxiway segment."""
        lo, hi = (a, b) if a < b else (b, a)
        return f"{lo}|{hi}|{seg}"

    def _dijkstra(
        self,
        start: str,
        end: str,
        penalise: Optional[Set[str]] = None,
    ) -> Optional[List[Tuple[str, str, str]]]:
        """
        Shortest path from start to end.
        Returns list of (from_node, to_node, segment_name) tuples, or None.
        Occupied segments receive a 10 NM penalty but are never blocked.
        """
        PENALTY = 10.0
        dist: Dict[str, float] = {start: 0.0}
        # heap: (cost, node, path)
        heap: List[Tuple[float, str, List[Tuple[str, str, str]]]] = [(0.0, start, [])]

        while heap:
            cost, node, path = heapq.heappop(heap)
            if cost > dist.get(node, float("inf")) + 1e-9:
                continue
            if node == end:
                return path
            for nb, seg, base in self._adj.get(node, []):
                key = self._seg_key(node, nb, seg)
                extra = PENALTY if (penalise and key in penalise) else 0.0
                new_cost = cost + base + extra
                if new_cost < dist.get(nb, float("inf")):
                    dist[nb] = new_cost
                    heapq.heappush(heap, (new_cost, nb, path + [(node, nb, seg)]))
        return None

    # ------------------------------------------------------------------
    # Gate assignment
    # ------------------------------------------------------------------

    async def assign_gate(
        self,
        aircraft_id: int,
        preferred_terminal: Optional[str] = None,
    ) -> Optional[str]:
        """
        Atomically assign a free gate to aircraft_id.
        preferred_terminal: 'A'|'B'|'C'|'D'|'F'|'T3' (optional preference).
        Returns the gate id, or None if all gates are occupied.
        """
        async with self._lock:
            if aircraft_id in self._ac_gate:
                return self._ac_gate[aircraft_id]  # idempotent

            free = [g for g, owner in self._gate_occ.items() if owner is None]
            if not free:
                logger.warning("[TaxiwayNet] No free gates for aircraft %d", aircraft_id)
                return None

            if preferred_terminal:
                prefix = "T3" if preferred_terminal.upper() == "T3" else preferred_terminal.upper()
                preferred = [g for g in free if g.startswith(prefix)]
                if preferred:
                    free = preferred

            gate = free[0]
            self._gate_occ[gate] = aircraft_id
            self._ac_gate[aircraft_id] = gate
            logger.info("[TaxiwayNet] Gate %s → aircraft %d", gate, aircraft_id)
            return gate

    # ------------------------------------------------------------------
    # Route finding + reservation
    # ------------------------------------------------------------------

    async def find_and_reserve_route(
        self,
        aircraft_id: int,
        landing_runway: str,
        gate: str,
    ) -> Optional[Dict]:
        """
        Find shortest taxi route from landing_runway exit to gate,
        penalising already-occupied segments, then reserve all segments.

        Returns dict with:
            segments   : list of segment names (for taxi clearance display)
            node_path  : ordered list of node ids
            waypoints  : list of {name, lat, lon, altitude_ft, speed_kts}
            exit_node  : the runway exit node used
        """
        async with self._lock:
            gate_info = GATES.get(gate)
            if not gate_info:
                return None

            apron_node, gate_lat, gate_lon = gate_info
            exit_candidates = RUNWAY_EXITS.get(landing_runway, ["ALPHA_E"])
            occupied_keys: Set[str] = set(self._segment_occ.keys())

            best_path: Optional[List[Tuple[str, str, str]]] = None
            best_exit: str = exit_candidates[0]
            best_cost = float("inf")

            for exit_node in exit_candidates:
                if exit_node not in self._nodes:
                    continue
                path = self._dijkstra(exit_node, apron_node, penalise=occupied_keys)
                if path is not None and len(path) < best_cost:
                    best_cost = len(path)
                    best_path = path
                    best_exit = exit_node

            if best_path is None:
                logger.warning(
                    "[TaxiwayNet] No route found for aircraft %d from %s to %s",
                    aircraft_id, landing_runway, gate,
                )
                return None

            # Build node_path and deduplicated segment list
            node_path = [best_exit] + [step[1] for step in best_path]
            segments: List[str] = []
            seen_segs: set = set()
            for _, _, seg in best_path:
                if seg not in seen_segs:
                    segments.append(seg)
                    seen_segs.add(seg)

            # Reserve all traversed segments
            reserved: List[str] = []
            for from_n, to_n, seg in best_path:
                key = self._seg_key(from_n, to_n, seg)
                self._segment_occ[key] = aircraft_id
                reserved.append(key)
            self._ac_segs[aircraft_id] = reserved

            # Build kinematics waypoints (node coords + final gate position)
            waypoints: List[Dict] = []
            for n in node_path:
                lat, lon, _ = self._nodes[n]
                waypoints.append({
                    "name": n,
                    "lat": lat,
                    "lon": lon,
                    "altitude_ft": 569,
                    "speed_kts": GROUND_SPEED_KTS,
                })
            waypoints.append({
                "name": gate,
                "lat": gate_lat,
                "lon": gate_lon,
                "altitude_ft": 569,
                "speed_kts": GATE_APPROACH_SPEED_KTS,
            })

            logger.info(
                "[TaxiwayNet] Aircraft %d: %s → %s via %s (%d waypoints)",
                aircraft_id, landing_runway, gate,
                " → ".join(segments), len(waypoints),
            )
            return {
                "segments": segments,
                "node_path": node_path,
                "waypoints": waypoints,
                "exit_node": best_exit,
            }

    # ------------------------------------------------------------------
    # Release on gate arrival
    # ------------------------------------------------------------------

    async def release_aircraft(self, aircraft_id: int) -> None:
        """Release all segments and the gate held by aircraft_id."""
        async with self._lock:
            for key in self._ac_segs.pop(aircraft_id, []):
                self._segment_occ.pop(key, None)
            gate = self._ac_gate.pop(aircraft_id, None)
            if gate:
                self._gate_occ[gate] = None
                logger.info("[TaxiwayNet] Gate %s released (aircraft %d)", gate, aircraft_id)

    # ------------------------------------------------------------------
    # Read-only helpers (no lock — slight staleness is fine)
    # ------------------------------------------------------------------

    def get_free_gates(self) -> List[str]:
        return [g for g, owner in self._gate_occ.items() if owner is None]

    def get_aircraft_gate(self, aircraft_id: int) -> Optional[str]:
        return self._ac_gate.get(aircraft_id)

    def get_nearest_exit_node(self, lat: float, lon: float, runway: str) -> str:
        """Return the runway exit node closest to the given position."""
        candidates = RUNWAY_EXITS.get(runway, ["ALPHA_E"])
        best, best_d = candidates[0], float("inf")
        for n in candidates:
            if n in self._nodes:
                nlat, nlon, _ = self._nodes[n]
                d = _haversine_nm(lat, lon, nlat, nlon)
                if d < best_d:
                    best_d, best = d, n
        return best

    def snapshot(self) -> Dict:
        return {
            "free_gates": self.get_free_gates(),
            "occupied_gates": {g: v for g, v in self._gate_occ.items() if v is not None},
            "occupied_segments": len(self._segment_occ),
            "aircraft_gates": dict(self._ac_gate),
        }


# ---------------------------------------------------------------------------
# Module-level singleton
# ---------------------------------------------------------------------------

_network: Optional[TaxiwayNetwork] = None


def get_taxiway_network() -> TaxiwayNetwork:
    """Return (or create) the global CYYZ TaxiwayNetwork instance."""
    global _network
    if _network is None:
        _network = TaxiwayNetwork()
    return _network
