"""
RuleEngine — deterministic tier-1 clearance decisions.

Handles all standard, unambiguous cases without calling the LLM.
Returns None when the case is complex enough to need the LLM.
"""

import logging

logger = logging.getLogger(__name__)


class RuleEngine:
    """
    Deterministic clearance decisions based on aircraft phase/distance.
    All decisions are side-effect free — caller applies them.
    """

    def decide(self, aircraft: dict, registry_snapshot: dict) -> dict | None:
        """
        Returns a clearance dict or None (hand off to LLM).

        Clearance dict keys (all optional):
            target_altitude_ft, target_speed_kts, target_heading_deg,
            runway, gate, action_type, taxi_instruction
        """
        phase = aircraft.get("phase", "")
        position = aircraft.get("position", {})
        alt = position.get("altitude_ft", 0)
        distance = aircraft.get("distance_to_airport_nm", 999)
        free_runways = registry_snapshot.get("free_runways", [])
        free_gates = registry_snapshot.get("free_gates", [])
        approach_queue = registry_snapshot.get("approach_queue", [])
        aircraft_id = aircraft.get("id")

        # ------------------------------------------------------------------
        # CASE 1: Initial descent trigger — cruise aircraft with no target
        # ------------------------------------------------------------------
        if phase == "CRUISE" and aircraft.get("target_altitude_ft") is None:
            logger.debug(f"[RuleEngine] {aircraft.get('callsign')} CASE1: initial descent")
            return {"target_altitude_ft": 15000, "target_speed_kts": 280}

        # ------------------------------------------------------------------
        # CASE 2: Standard descent profile by distance bracket
        # ------------------------------------------------------------------
        if phase == "DESCENT":
            if distance > 40:
                return {"target_altitude_ft": 10000, "target_speed_kts": 250}
            elif distance > 25:
                return {"target_altitude_ft": 6000, "target_speed_kts": 210}

        # ------------------------------------------------------------------
        # CASE 3: Approach — within 15NM, no runway assigned yet
        # ------------------------------------------------------------------
        if phase == "APPROACH" and not aircraft.get("runway_assigned"):
            if len(free_runways) == 0:
                # No free runways — LLM handles sequencing/hold
                return None

            if len(free_runways) == 1:
                rwy = free_runways[0]
                logger.info(
                    f"[RuleEngine] {aircraft.get('callsign')} CASE3: "
                    f"single free runway {rwy}"
                )
                return {
                    "runway": rwy,
                    "target_altitude_ft": 3000,
                    "target_speed_kts": 170,
                    "target_heading_deg": self._runway_heading(rwy),
                }

            # Multiple free runways with multiple aircraft approaching
            # If this aircraft is at the front of the approach queue, assign best runway
            if approach_queue and approach_queue[0] == aircraft_id:
                rwy = self._preferred_runway(free_runways)
                logger.info(
                    f"[RuleEngine] {aircraft.get('callsign')} CASE3: "
                    f"front of queue, assigning {rwy}"
                )
                return {
                    "runway": rwy,
                    "target_altitude_ft": 3000,
                    "target_speed_kts": 170,
                    "target_heading_deg": self._runway_heading(rwy),
                }

            # Not at front of queue — LLM decides sequencing
            return None

        # ------------------------------------------------------------------
        # CASE 4: Touchdown — needs taxi clearance to gate
        # ------------------------------------------------------------------
        if phase == "TOUCHDOWN" and not aircraft.get("gate_assigned"):
            if free_gates:
                gate = free_gates[0]
                logger.info(
                    f"[RuleEngine] {aircraft.get('callsign')} CASE4: "
                    f"taxi to gate {gate}"
                )
                return {
                    "gate": gate,
                    "taxi_instruction": f"Taxi to gate {gate} via Taxiway Alpha",
                }

        return None  # Unhandled → LLM

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _runway_heading(self, runway: str) -> int:
        """Convert runway designator to magnetic heading (e.g. '05L' → 50)."""
        digits = "".join(c for c in runway if c.isdigit())
        try:
            return int(digits) * 10
        except ValueError:
            return 0

    def _preferred_runway(self, free_runways: list[str]) -> str:
        """
        Prefer 23L/23R (into prevailing wind at CYYZ ~230°).
        Fall back to first available.
        """
        for preferred in ("23L", "23R", "05L", "05R"):
            if preferred in free_runways:
                return preferred
        return free_runways[0]
