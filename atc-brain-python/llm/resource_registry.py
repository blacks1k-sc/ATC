"""
ResourceRegistry — single source of truth for all ATC resource assignments.

Tracks runway/gate occupancy and approach queue in memory.
Subscribed to engine Redis events to keep state up to date.
"""

import asyncio
import json
import logging
import os
from typing import Optional

import redis.asyncio as redis

logger = logging.getLogger(__name__)


class ResourceRegistry:
    """In-memory registry of runway/gate assignments and approach queue."""

    RUNWAYS = ["05L", "05R", "23L", "23R", "06L", "06R", "15L", "15R", "33L", "33R"]
    GATES = ["A12", "A15", "B12", "B15", "C12", "C15", "D12", "D15"]

    def __init__(self):
        self._lock = asyncio.Lock()
        self._runways: dict[str, Optional[int]] = {r: None for r in self.RUNWAYS}
        self._gates: dict[str, Optional[int]] = {g: None for g in self.GATES}
        # Ordered by enqueue time (FCFS)
        self._approach_queue: list[int] = []

    # ------------------------------------------------------------------
    # Runway ops
    # ------------------------------------------------------------------

    async def assign_runway(self, runway: str, aircraft_id: int) -> bool:
        async with self._lock:
            if self._runways.get(runway) is not None:
                return False
            self._runways[runway] = aircraft_id
            logger.info(f"[Registry] Runway {runway} assigned to aircraft {aircraft_id}")
            return True

    async def release_runway(self, runway: str) -> None:
        async with self._lock:
            prev = self._runways.get(runway)
            self._runways[runway] = None
            logger.info(f"[Registry] Runway {runway} released (was: {prev})")

    async def get_free_runways(self) -> list[str]:
        async with self._lock:
            return [r for r, owner in self._runways.items() if owner is None]

    # ------------------------------------------------------------------
    # Gate ops
    # ------------------------------------------------------------------

    async def assign_gate(self, gate: str, aircraft_id: int) -> bool:
        async with self._lock:
            if self._gates.get(gate) is not None:
                return False
            self._gates[gate] = aircraft_id
            logger.info(f"[Registry] Gate {gate} assigned to aircraft {aircraft_id}")
            return True

    async def release_gate(self, gate: str) -> None:
        async with self._lock:
            self._gates[gate] = None

    async def get_free_gates(self) -> list[str]:
        async with self._lock:
            return [g for g, owner in self._gates.items() if owner is None]

    # ------------------------------------------------------------------
    # Approach queue
    # ------------------------------------------------------------------

    async def enqueue_approach(self, aircraft_id: int, distance_nm: float) -> None:
        async with self._lock:
            if aircraft_id not in self._approach_queue:
                self._approach_queue.append(aircraft_id)
                logger.info(
                    f"[Registry] Aircraft {aircraft_id} queued for approach "
                    f"(dist={distance_nm:.1f}NM, queue_pos={len(self._approach_queue)})"
                )

    async def dequeue_approach(self, aircraft_id: int) -> None:
        async with self._lock:
            if aircraft_id in self._approach_queue:
                self._approach_queue.remove(aircraft_id)

    # ------------------------------------------------------------------
    # Snapshot (no lock — caller reads; slight staleness is acceptable)
    # ------------------------------------------------------------------

    def snapshot(self) -> dict:
        return {
            "runways": dict(self._runways),
            "gates": dict(self._gates),
            "approach_queue": list(self._approach_queue),
        }


class RegistryEventSubscriber:
    """Subscribes to engine Redis events and updates ResourceRegistry."""

    def __init__(self, registry: ResourceRegistry, redis_client: redis.Redis):
        self.registry = registry
        self.redis_client = redis_client
        self.channel = os.getenv("EVENT_CHANNEL", "atc:events")

    async def run(self):
        pubsub = self.redis_client.pubsub()
        await pubsub.subscribe(self.channel)
        logger.info(f"[RegistrySubscriber] Subscribed to Redis channel '{self.channel}'")

        async for message in pubsub.listen():
            if message["type"] != "message":
                continue
            try:
                envelope = json.loads(message["data"])
                event_type = envelope.get("type", "")
                data = envelope.get("data", {})
                await self._handle(event_type, data)
            except Exception as e:
                logger.warning(f"[RegistrySubscriber] Error handling message: {e}")

    async def _handle(self, event_type: str, data: dict):
        aircraft_data = data.get("aircraft", {})
        aircraft_id = aircraft_data.get("id")

        if event_type == "aircraft.threshold_event":
            ev = data.get("event_type", "")

            if ev == "runway.landed":
                runway = data.get("runway") or aircraft_data.get("runway_assigned")
                if runway and aircraft_id:
                    await self.registry.assign_runway(runway, aircraft_id)
                    await self.registry.dequeue_approach(aircraft_id)

            elif ev == "runway.vacated":
                runway = data.get("vacated_runway") or data.get("runway")
                if runway:
                    await self.registry.release_runway(runway)

            elif ev in ("zone.boundary_crossed", "aircraft.entered_entry_zone"):
                distance = aircraft_data.get("distance_to_airport_nm", 99)
                if distance <= 15 and aircraft_id:
                    await self.registry.enqueue_approach(aircraft_id, distance)
