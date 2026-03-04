"""
PlanningCycle — two-tier ATC controller loop.

Tier 1: RuleEngine handles standard cases deterministically.
Tier 2: QwenClient called ONCE per cycle with all remaining complex cases.

Replaces the old per-event LLMDispatcher pattern.
"""

import asyncio
import logging
import math
from typing import Optional

import asyncpg

from .resource_registry import ResourceRegistry
from .rule_engine import RuleEngine
from .qwen_client import QwenClient

logger = logging.getLogger(__name__)


class PlanningCycle:
    """Periodic planning loop — runs every INTERVAL_SEC seconds."""

    INTERVAL_SEC = 10

    def __init__(
        self,
        db_pool: asyncpg.Pool,
        registry: ResourceRegistry,
        rule_engine: RuleEngine,
        qwen: QwenClient,
    ):
        self.db_pool = db_pool
        self.registry = registry
        self.rule_engine = rule_engine
        self.qwen = qwen

    async def run(self):
        logger.info("[PlanningCycle] Started — interval=%ds", self.INTERVAL_SEC)
        while True:
            await asyncio.sleep(self.INTERVAL_SEC)
            try:
                await self._cycle()
            except Exception as e:
                logger.error("[PlanningCycle] Cycle error: %s", e, exc_info=True)

    # ------------------------------------------------------------------
    # Core cycle
    # ------------------------------------------------------------------

    async def _cycle(self):
        aircraft_list = await self._fetch_all_active()
        if not aircraft_list:
            return

        snap = self.registry.snapshot()
        snap["free_runways"] = [r for r, o in snap["runways"].items() if o is None]
        snap["free_gates"] = [g for g, o in snap["gates"].items() if o is None]

        # Separation conflict analysis (O(N²), N≤~20, <1ms)
        conflicts = self._compute_separation_conflicts(aircraft_list)
        if conflicts:
            logger.warning(
                "[PlanningCycle] %d separation conflict(s) detected", len(conflicts)
            )

        # Tier 1 — Rule engine
        rule_decisions: list[dict] = []
        llm_candidates: list[dict] = []

        for ac in aircraft_list:
            decision = self.rule_engine.decide(ac, snap)
            if decision is not None:
                rule_decisions.append({"aircraft_id": ac["id"], **decision})
            else:
                llm_candidates.append(ac)

        # Apply rule decisions immediately
        for decision in rule_decisions:
            await self._apply(decision)

        logger.info(
            "[PlanningCycle] Rule engine: %d decisions, %d → LLM",
            len(rule_decisions),
            len(llm_candidates),
        )

        # Tier 2 — LLM (single call)
        if llm_candidates:
            llm_decisions = await self.qwen.decide_batch(
                llm_candidates, snap, conflicts
            )
            accepted = 0
            for decision in llm_decisions:
                if await self._validate(decision):
                    await self._apply(decision)
                    accepted += 1
            logger.info(
                "[PlanningCycle] LLM: %d/%d decisions accepted",
                accepted,
                len(llm_decisions),
            )

    # ------------------------------------------------------------------
    # DB fetch
    # ------------------------------------------------------------------

    async def _fetch_all_active(self) -> list[dict]:
        async with self.db_pool.acquire() as conn:
            rows = await conn.fetch("""
                SELECT
                    id, callsign, icao24,
                    phase, controller,
                    target_altitude_ft, target_speed_kts, target_heading_deg,
                    runway_assigned, gate_assigned, clearance_seq,
                    position,
                    distance_to_airport_nm
                FROM aircraft_instances
                WHERE active = TRUE
                ORDER BY id;
            """)
        result = []
        for row in rows:
            ac = dict(row)
            # position is stored as JSON string in some setups
            if isinstance(ac.get("position"), str):
                import json
                try:
                    ac["position"] = json.loads(ac["position"])
                except Exception:
                    ac["position"] = {}
            result.append(ac)
        return result

    # ------------------------------------------------------------------
    # Validation (checks live registry, not snapshot)
    # ------------------------------------------------------------------

    async def _validate(self, decision: dict) -> bool:
        runway = decision.get("runway")
        gate = decision.get("gate")

        if runway:
            free = await self.registry.get_free_runways()
            if runway not in free:
                logger.warning(
                    "[PlanningCycle] Rejected LLM decision: runway %s already taken", runway
                )
                return False

        if gate:
            free = await self.registry.get_free_gates()
            if gate not in free:
                logger.warning(
                    "[PlanningCycle] Rejected LLM decision: gate %s already taken", gate
                )
                return False

        return True

    # ------------------------------------------------------------------
    # Apply — write to DB and update registry atomically
    # ------------------------------------------------------------------

    async def _apply(self, decision: dict):
        aircraft_id = decision.get("aircraft_id")
        if not aircraft_id:
            return

        runway = decision.get("runway")
        gate = decision.get("gate")

        # Atomically claim resources in registry first
        if runway:
            ok = await self.registry.assign_runway(runway, aircraft_id)
            if not ok:
                logger.warning(
                    "[PlanningCycle] Runway %s taken mid-apply for aircraft %d — skipping",
                    runway, aircraft_id,
                )
                return

        if gate:
            ok = await self.registry.assign_gate(gate, aircraft_id)
            if not ok:
                logger.warning(
                    "[PlanningCycle] Gate %s taken mid-apply for aircraft %d — skipping",
                    gate, aircraft_id,
                )
                return

        await self._write_to_db(aircraft_id, decision)

    async def _write_to_db(self, aircraft_id: int, decision: dict):
        updates: list[str] = []
        params: list = []
        idx = 1

        field_map = {
            "target_altitude_ft": "target_altitude_ft",
            "target_speed_kts": "target_speed_kts",
            "target_heading_deg": "target_heading_deg",
            "runway": "runway_assigned",
            "gate": "gate_assigned",
        }

        for key, col in field_map.items():
            val = decision.get(key)
            if val is not None:
                updates.append(f"{col} = ${idx}")
                params.append(val)
                idx += 1

        if not updates:
            return

        # Always bump clearance_seq
        updates.append(f"clearance_seq = clearance_seq + 1")
        params.append(aircraft_id)

        sql = f"UPDATE aircraft_instances SET {', '.join(updates)} WHERE id = ${idx}"

        try:
            async with self.db_pool.acquire() as conn:
                await conn.execute(sql, *params)

                # Write to clearances log table
                await conn.execute("""
                    INSERT INTO clearances
                        (aircraft_id, cleared_altitude_ft, cleared_speed_kts,
                         cleared_heading_deg, cleared_runway, cleared_gate)
                    VALUES ($1, $2, $3, $4, $5, $6)
                """,
                    aircraft_id,
                    decision.get("target_altitude_ft"),
                    decision.get("target_speed_kts"),
                    decision.get("target_heading_deg"),
                    decision.get("runway"),
                    decision.get("gate"),
                )
        except Exception as e:
            logger.error("[PlanningCycle] DB write failed for aircraft %d: %s", aircraft_id, e)

    # ------------------------------------------------------------------
    # Separation conflict detection
    # ------------------------------------------------------------------

    def _compute_separation_conflicts(self, aircraft_list: list[dict]) -> list[dict]:
        LATERAL_MIN_NM = 5.0
        VERTICAL_MIN_FT = 1000.0

        conflicts = []
        for i, a in enumerate(aircraft_list):
            for b in aircraft_list[i + 1:]:
                pos_a = a.get("position", {})
                pos_b = b.get("position", {})
                lat_a = pos_a.get("lat", 0)
                lon_a = pos_a.get("lon", 0)
                lat_b = pos_b.get("lat", 0)
                lon_b = pos_b.get("lon", 0)
                alt_a = pos_a.get("altitude_ft", 0)
                alt_b = pos_b.get("altitude_ft", 0)

                lateral = self._haversine_nm(lat_a, lon_a, lat_b, lon_b)
                vertical = abs(alt_a - alt_b)

                if lateral < LATERAL_MIN_NM and vertical < VERTICAL_MIN_FT:
                    conflicts.append({
                        "callsign_a": a.get("callsign", str(a.get("id"))),
                        "callsign_b": b.get("callsign", str(b.get("id"))),
                        "aircraft_id_a": a.get("id"),
                        "aircraft_id_b": b.get("id"),
                        "lateral_nm": lateral,
                        "vertical_ft": vertical,
                    })
        return conflicts

    @staticmethod
    def _haversine_nm(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        R_NM = 3440.065
        phi1, phi2 = math.radians(lat1), math.radians(lat2)
        dphi = math.radians(lat2 - lat1)
        dlam = math.radians(lon2 - lon1)
        a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlam / 2) ** 2
        return R_NM * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
