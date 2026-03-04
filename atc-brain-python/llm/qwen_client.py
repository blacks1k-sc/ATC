"""
QwenClient — persistent aiohttp session for Ollama HTTP API.

Replaces the old subprocess-per-event approach with a single batched call
per planning cycle.
"""

import json
import logging
from typing import Any

import aiohttp

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = (
    "You are an ATC controller for Toronto Pearson International Airport (CYYZ). "
    "You control multiple aircraft simultaneously. "
    "CYYZ runways: 05L/23R, 05R/23L, 06L/24R, 06R/24L, 15L/33R, 15R/33L. "
    "Prevailing wind: 230 degrees. Prefer 23L or 23R for arrivals when free. "
    "Never assign the same runway to two aircraft. "
    "Maintain 3 NM lateral OR 1000 ft vertical separation between all aircraft. "
    "Output valid JSON only — no prose, no markdown fences."
)


class QwenClient:
    """Single persistent session for Ollama qwen2.5:7b."""

    MODEL = "qwen2.5:7b"
    URL = "http://localhost:11434/api/chat"

    def __init__(self):
        self._session: aiohttp.ClientSession | None = None

    async def initialize(self):
        self._session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=45)
        )
        logger.info(f"[QwenClient] Session initialized (model={self.MODEL})")

    async def close(self):
        if self._session:
            await self._session.close()
            self._session = None

    async def decide_batch(
        self,
        aircraft_list: list[dict],
        registry: dict,
        conflicts: list[dict] | None = None,
    ) -> list[dict]:
        """
        Single LLM call for all aircraft needing complex decisions.

        Args:
            aircraft_list: Aircraft dicts that rule engine couldn't handle.
            registry: Full registry snapshot (runways, gates, approach_queue).
            conflicts: Optional list of separation conflict descriptions.

        Returns:
            List of clearance dicts (one per aircraft, aircraft_id keyed).
        """
        if not self._session:
            raise RuntimeError("QwenClient not initialized — call initialize() first")

        prompt = self._build_batch_prompt(aircraft_list, registry, conflicts or [])

        payload = {
            "model": self.MODEL,
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
            "format": "json",
            "stream": False,
        }

        try:
            async with self._session.post(self.URL, json=payload) as resp:
                resp.raise_for_status()
                result = await resp.json()
                content = result["message"]["content"]
                parsed = json.loads(content)
                clearances = parsed.get("clearances", [])
                logger.info(
                    f"[QwenClient] Received {len(clearances)} clearance(s) "
                    f"for {len(aircraft_list)} aircraft"
                )
                return clearances
        except aiohttp.ClientError as e:
            logger.error(f"[QwenClient] HTTP error: {e}")
            return []
        except json.JSONDecodeError as e:
            logger.error(f"[QwenClient] JSON parse error: {e}")
            return []
        except Exception as e:
            logger.error(f"[QwenClient] Unexpected error: {e}", exc_info=True)
            return []

    # ------------------------------------------------------------------
    # Prompt builder
    # ------------------------------------------------------------------

    def _build_batch_prompt(
        self,
        aircraft_list: list[dict],
        registry: dict,
        conflicts: list[dict],
    ) -> str:
        runway_lines = "\n".join(
            f"  {rwy}: {'OCCUPIED by aircraft ' + str(owner) if owner else 'FREE'}"
            for rwy, owner in registry["runways"].items()
        )
        gate_lines = "\n".join(
            f"  {gate}: {'OCCUPIED' if owner else 'FREE'}"
            for gate, owner in registry["gates"].items()
        )
        aircraft_lines = "\n".join(
            f"  [{i + 1}] {ac.get('callsign', '?')} (id={ac.get('id')}): "
            f"phase={ac.get('phase', '?')}, "
            f"dist={ac.get('distance_to_airport_nm', 0):.1f}NM, "
            f"alt={ac.get('position', {}).get('altitude_ft', 0)}ft, "
            f"spd={ac.get('position', {}).get('speed_kts', 0)}kts, "
            f"hdg={ac.get('position', {}).get('heading', 0)}\u00b0, "
            f"runway_assigned={ac.get('runway_assigned') or 'none'}, "
            f"gate_assigned={ac.get('gate_assigned') or 'none'}"
            for i, ac in enumerate(aircraft_list)
        )

        conflict_block = ""
        if conflicts:
            conflict_lines = "\n".join(
                f"  {c.get('callsign_a')} and {c.get('callsign_b')}: "
                f"{c.get('lateral_nm', 0):.1f}NM lateral, "
                f"{c.get('vertical_ft', 0)}ft vertical — RESOLVE IMMEDIATELY"
                for c in conflicts
            )
            conflict_block = f"\nACTIVE SEPARATION CONFLICTS (MUST RESOLVE):\n{conflict_lines}\n"

        approach_q = registry.get("approach_queue", [])
        queue_str = (
            "  " + " → ".join(str(x) for x in approach_q)
            if approach_q
            else "  (empty)"
        )

        return (
            f"RUNWAY STATE:\n{runway_lines}\n\n"
            f"GATE STATE:\n{gate_lines}\n\n"
            f"APPROACH QUEUE (FCFS order):\n{queue_str}\n"
            f"{conflict_block}\n"
            f"AIRCRAFT NEEDING DECISIONS:\n{aircraft_lines}\n\n"
            "Issue clearances. Rules:\n"
            "  - 3NM lateral OR 1000ft vertical separation minimum\n"
            "  - One aircraft per runway at a time\n"
            "  - Use null for fields you are not changing\n\n"
            'Output JSON: {"clearances": [{"aircraft_id": <int>, '
            '"target_altitude_ft": <int|null>, '
            '"target_speed_kts": <int|null>, '
            '"target_heading_deg": <int|null>, '
            '"runway": <str|null>, '
            '"gate": <str|null>}]}'
        )
