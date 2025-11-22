"""
Core kinematics engine with 1 Hz deterministic tick loop.
Orchestrates aircraft state updates, event emission, and database persistence.

Architecture:
- Main tick loop runs at 1 Hz (deterministic physics)
- Three async workers consume from a shared queue:
  * db_worker: Batches DB writes every 1s
  * redis_worker: Batches Redis publishes every 20-50ms
  * telemetry_worker: Writes telemetry every 10s
- Ray distributed computing for CPU-intensive physics simulation
  * Aircraft physics executed on remote cluster (ASUS @ 192.168.2.142)
  * MacBook orchestrates, manages I/O, and coordinates visualization
"""

import asyncio
import time
import json
import os
import logging
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional
from dotenv import load_dotenv

# Ray distributed computing
try:
    import ray
    from .kinematics_ray import update_aircraft_state_remote
    RAY_AVAILABLE = True
except ImportError:
    RAY_AVAILABLE = False
    logger_temp = logging.getLogger(__name__)
    logger_temp.warning("Ray not available - falling back to local execution")

from .state_manager import StateManager
from .event_publisher import EventPublisher
from .spawn_listener import SpawnListener
from .kinematics import update_aircraft_state
from .airport_data import get_airport_data
from .config import config
from .constants import (
    DT,
    ENTRY_ZONE_THRESHOLD_NM,
    HANDOFF_READY_THRESHOLD_NM,
    TOUCHDOWN_ALTITUDE_FT,
    EVENT_ENTERED_ENTRY_ZONE,
    EVENT_HANDOFF_READY,
    EVENT_TOUCHDOWN,
    TICK_WARNING_THRESHOLD_SEC,
    CYYZ_ELEVATION_FT,
)
from .geo_utils import altitude_msl_to_agl, distance_to_airport
from .zone_detector import determine_zone, has_zone_changed

load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO if config.LOG_LEVEL == "INFO" else logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class KinematicsEngine:
    """Main kinematics engine controller with async worker architecture and Ray distribution."""
    
    def __init__(self, ray_address: Optional[str] = None, use_ray: bool = True):
        """
        Initialize the kinematics engine.
        
        Args:
            ray_address: Ray cluster address (e.g., "ray://192.168.2.142:10001")
                        If None, uses environment variable RAY_ADDRESS or defaults to local
            use_ray: Whether to use Ray distributed execution (default: True if available)
        """
        self.state_manager = StateManager()
        self.event_publisher = EventPublisher()
        self.spawn_listener = SpawnListener(self.state_manager, self.on_aircraft_spawned)
        
        self.airport = get_airport_data()
        self.project_root = Path(__file__).resolve().parent.parent
        
        self.tick_count = 0
        self.running = False
        self.start_time = 0.0
        
        # Ray distributed computing setup
        self.use_ray = use_ray and RAY_AVAILABLE
        self.ray_address = ray_address or os.getenv("RAY_ADDRESS", "ray://192.168.2.142:10001")
        self.ray_initialized = False
        
        # ========== Async Queue and Workers ==========
        # Shared queue for physics loop -> async workers
        self.io_queue: asyncio.Queue = asyncio.Queue(maxsize=config.IO_QUEUE_MAX_SIZE)
        
        # Worker tasks
        self.db_worker_task: Optional[asyncio.Task] = None
        self.redis_worker_task: Optional[asyncio.Task] = None
        self.telemetry_worker_task: Optional[asyncio.Task] = None
        
        # Worker buffers
        self.db_updates_buffer: List[Dict[str, Any]] = []
        self.redis_events_buffer: List[tuple[str, Dict[str, Any]]] = []
        self.telemetry_buffer: List[Dict[str, Any]] = []
        self.pending_db_events: List[Dict[str, Any]] = []
        
        # Telemetry
        self.telemetry_dir = config.TELEMETRY_DIR
        
        # Statistics
        self.stats = {
            "aircraft_processed": 0,
            "events_fired": 0,
            "total_ticks": 0,
            "avg_tick_duration": 0.0,
            "db_writes": 0,
            "redis_publishes": 0,
            "telemetry_writes": 0,
            "ray_tasks_executed": 0,
            "ray_fallbacks": 0,
        }
        
        # Worker statistics
        self.worker_stats = {
            "db_batches": 0,
            "redis_batches": 0,
            "telemetry_batches": 0,
            "queue_size_max": 0,
        }
    
    async def initialize(self):
        """Initialize all subsystems and spawn async workers."""
        logger.info("Initializing Kinematics Engine...")
        config.print_config()
        
        # Initialize Ray distributed computing
        if self.use_ray:
            try:
                logger.info(f"Connecting to Ray cluster at {self.ray_address}...")
                runtime_env = {
                    "working_dir": str(self.project_root),
                }
                ray.init(
                    address=self.ray_address,
                    ignore_reinit_error=True,
                    runtime_env=runtime_env,
                )
                self.ray_initialized = True
                
                # Verify cluster resources
                resources = ray.cluster_resources()
                logger.info("Ray cluster connected!")
                logger.info(f"   Cluster resources: {resources}")
                logger.info(f"   Available CPUs: {resources.get('CPU', 0)}")
                logger.info(f"   Available nodes: {len(ray.nodes())}")
                
            except Exception as e:
                logger.error(f"Failed to connect to Ray cluster: {e}")
                logger.warning("   Falling back to local execution")
                self.use_ray = False
                self.ray_initialized = False
        else:
            logger.info("Ray disabled - using local execution")
        
        # Connect to database
        await self.state_manager.connect()
        
        # Connect to Redis (async)
        await self.event_publisher.connect()
        self.spawn_listener.connect()
        
        # Load airport data
        logger.info(f"Airport: {self.airport}")
        logger.info(f"   Entry waypoints: {len(self.airport.entry_waypoints)}")
        
        # Create telemetry directory
        os.makedirs(self.telemetry_dir, exist_ok=True)
        
        # Spawn async workers
        logger.info("Starting async workers...")
        self.db_worker_task = asyncio.create_task(self.db_worker())
        self.redis_worker_task = asyncio.create_task(self.redis_worker())
        self.telemetry_worker_task = asyncio.create_task(self.telemetry_worker())
        
        mode = "Ray distributed" if self.use_ray else "local"
        logger.info(f"Kinematics Engine initialized ({mode} mode)")
    
    async def shutdown(self):
        """Shutdown all subsystems and cancel async workers."""
        logger.info("\nShutting down Kinematics Engine...")
        
        self.running = False
        
        # Cancel async workers
        logger.info("   Stopping async workers...")
        workers = [self.db_worker_task, self.redis_worker_task, self.telemetry_worker_task]
        for worker in workers:
            if worker:
                worker.cancel()
        
        # Wait for workers to finish with timeout
        try:
            await asyncio.wait_for(
                asyncio.gather(*[w for w in workers if w], return_exceptions=True),
                timeout=5.0
            )
        except asyncio.TimeoutError:
            logger.warning("   Workers did not stop gracefully within timeout")
        except Exception as e:
            logger.error(f"   Error stopping workers: {e}")
        
        # Flush remaining items in buffers
        logger.info("   Flushing remaining buffers...")
        await self._flush_all_buffers()
        
        # Disconnect from database
        await self.state_manager.disconnect()
        
        # Disconnect from Redis (async)
        await self.event_publisher.disconnect()
        self.spawn_listener.disconnect()
        
        # Shutdown Ray
        if self.ray_initialized:
            logger.info("   Shutting down Ray...")
            try:
                ray.shutdown()
                logger.info("   Ray shutdown complete")
            except Exception as e:
                logger.error(f"   Error shutting down Ray: {e}")
        
        # Print statistics
        self.print_statistics()
        
        logger.info("Kinematics Engine shutdown complete")
    
    async def on_aircraft_spawned(self, aircraft: Dict[str, Any]):
        """
        Callback when new aircraft is spawned.
        
        Args:
            aircraft: Aircraft data dictionary
        """
        callsign = aircraft.get("callsign", "UNKNOWN")
        aircraft_id = aircraft.get("id")
        logger.info(f"   ENGINE now controlling: {callsign}")
        
        # Queue database event for batch processing
        self.pending_db_events.append({
            "level": "INFO",
            "type": "aircraft.engine_assigned",
            "message": f"ENGINE assigned control of {callsign}",
            "details": {
                "callsign": callsign,
                "controller": "ENGINE",
                "phase": "CRUISE"
            },
            "aircraft_id": aircraft_id,
            "sector": "ENGINE",
            "direction": "SYS"
        })
    
    # ========== Async Workers ==========
    
    async def db_worker(self):
        """
        Database worker: Batches and writes aircraft state updates to Postgres.
        Runs every 1 second using asyncpg.executemany.
        """
        logger.info("   DB worker started")
        
        try:
            while self.running or not self.io_queue.empty():
                try:
                    # Wait for batch interval or until shutdown
                    await asyncio.sleep(config.DB_BATCH_INTERVAL_SEC)
                    
                    # Flush accumulated updates
                    if self.db_updates_buffer:
                        updates_to_write = self.db_updates_buffer[:config.DB_BATCH_SIZE]
                        self.db_updates_buffer = self.db_updates_buffer[config.DB_BATCH_SIZE:]
                        
                        # Batch write to DB
                        count = await self.state_manager.batch_update_aircraft_states(updates_to_write)
                        
                        self.stats["db_writes"] += count
                        self.worker_stats["db_batches"] += 1
                        
                        if config.LOG_WORKER_STATS:
                            logger.debug(f"   DB worker: wrote {count} aircraft updates")
                    
                    # Flush pending events
                    if self.pending_db_events:
                        events_to_write = self.pending_db_events[:config.DB_BATCH_SIZE]
                        self.pending_db_events = self.pending_db_events[config.DB_BATCH_SIZE:]
                        
                        count = await self.state_manager.batch_create_events(events_to_write)
                        
                        if config.LOG_WORKER_STATS:
                            logger.debug(f"   DB worker: wrote {count} events")
                
                except asyncio.CancelledError:
                    logger.info("   DB worker cancelled")
                    break
                except Exception as e:
                    logger.error(f"   DB worker error: {e}")
        
        finally:
            logger.info("   DB worker stopped")
    
    async def redis_worker(self):
        """
        Redis worker: Batches and publishes aircraft updates to Redis.
        Runs every 20-50ms for real-time UI updates.
        """
        logger.info("   Redis worker started")
        
        try:
            while self.running or not self.io_queue.empty():
                try:
                    # Wait for batch interval
                    await asyncio.sleep(config.REDIS_BATCH_INTERVAL_SEC)
                    
                    # Flush accumulated events
                    if self.redis_events_buffer:
                        events_to_publish = self.redis_events_buffer[:config.REDIS_BATCH_SIZE]
                        self.redis_events_buffer = self.redis_events_buffer[config.REDIS_BATCH_SIZE:]
                        
                        # Batch publish to Redis
                        count = await self.event_publisher.batch_publish_events(events_to_publish)
                        
                        self.stats["redis_publishes"] += count
                        self.worker_stats["redis_batches"] += 1
                        
                        if config.LOG_WORKER_STATS:
                            logger.debug(f"   Redis worker: published {count} events")
                
                except asyncio.CancelledError:
                    logger.info("   Redis worker cancelled")
                    break
                except Exception as e:
                    logger.error(f"   Redis worker error: {e}")
        
        finally:
            logger.info("   Redis worker stopped")
    
    async def telemetry_worker(self):
        """
        Telemetry worker: Writes aggregated telemetry to disk.
        Runs every 10 seconds (configurable).
        """
        logger.info("   Telemetry worker started")
        
        try:
            while self.running or not self.io_queue.empty():
                try:
                    # Wait for telemetry interval
                    await asyncio.sleep(config.TELEMETRY_INTERVAL_SEC)
                    
                    # Flush telemetry buffer
                    if self.telemetry_buffer:
                        await self._flush_telemetry_to_disk()
                        self.stats["telemetry_writes"] += 1
                        self.worker_stats["telemetry_batches"] += 1
                        
                        if config.LOG_WORKER_STATS:
                            logger.debug(f"   Telemetry worker: flushed {len(self.telemetry_buffer)} snapshots")
                
                except asyncio.CancelledError:
                    logger.info("   Telemetry worker cancelled")
                    break
                except Exception as e:
                    logger.error(f"   Telemetry worker error: {e}")
        
        finally:
            logger.info("   Telemetry worker stopped")
    
    async def _flush_all_buffers(self):
        """Flush all remaining buffered data on shutdown."""
        try:
            # Flush DB updates
            if self.db_updates_buffer:
                await self.state_manager.batch_update_aircraft_states(self.db_updates_buffer)
                logger.info(f"   Flushed {len(self.db_updates_buffer)} DB updates")
                self.db_updates_buffer.clear()
            
            # Flush DB events
            if self.pending_db_events:
                await self.state_manager.batch_create_events(self.pending_db_events)
                logger.info(f"   Flushed {len(self.pending_db_events)} DB events")
                self.pending_db_events.clear()
            
            # Flush Redis events
            if self.redis_events_buffer:
                await self.event_publisher.batch_publish_events(self.redis_events_buffer)
                logger.info(f"   Flushed {len(self.redis_events_buffer)} Redis events")
                self.redis_events_buffer.clear()
            
            # Flush telemetry
            if self.telemetry_buffer:
                await self._flush_telemetry_to_disk()
                logger.info(f"   Flushed {len(self.telemetry_buffer)} telemetry snapshots")
        
        except Exception as e:
            logger.error(f"   Error flushing buffers: {e}")
    
    async def _flush_telemetry_to_disk(self):
        """Write telemetry buffer to disk."""
        if not self.telemetry_buffer:
            return
        
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        filename = f"{self.telemetry_dir}/engine_{timestamp}.jsonl"
        
        try:
            with open(filename, 'a') as f:
                for snapshot in self.telemetry_buffer:
                    f.write(json.dumps(snapshot) + "\n")
            
            self.telemetry_buffer.clear()
        
        except Exception as e:
            logger.error(f"   Failed to write telemetry: {e}")
    
    async def tick(self):
        """
        Execute one engine tick (1 Hz).
        Fetches aircraft, applies kinematics, prepares updates for async workers.
        
        THIS METHOD MUST REMAIN NON-BLOCKING to preserve 1 Hz determinism.
        All I/O is delegated to async workers via buffers.
        """
        tick_start = time.time()
        
        # Fetch active arrivals controlled by ENGINE (only blocking DB call)
        aircraft_list = await self.state_manager.get_active_arrivals(controller="ENGINE")
        
        if not aircraft_list:
            # No aircraft to process this tick
            return
        
        # Process all aircraft using Ray distributed execution or local fallback
        if self.use_ray and self.ray_initialized:
            try:
                # Ray distributed execution - offload to ASUS cluster
                # Submit all aircraft updates as parallel Ray tasks
                futures = [update_aircraft_state_remote.remote(ac, DT) for ac in aircraft_list]
                
                # Gather results from remote workers
                updated_aircraft = ray.get(futures)
                
                # Track Ray execution
                self.stats["ray_tasks_executed"] += len(futures)
                
                # Process results (extract events, prepare DB updates)
                for aircraft, updated in zip(aircraft_list, updated_aircraft):
                    try:
                        self._process_aircraft_results(aircraft, updated)
                    except Exception as e:
                        callsign = aircraft.get("callsign", "UNKNOWN")
                        logger.error(f"Error processing results for {callsign}: {e}")
            
            except Exception as e:
                logger.error(f"Ray execution error: {e}")
                logger.warning("Falling back to local execution for this tick")
                self.stats["ray_fallbacks"] += 1
                # Fallback to local execution
                for aircraft in aircraft_list:
                    try:
                        self.process_aircraft_sync(aircraft)
                    except Exception as e:
                        callsign = aircraft.get("callsign", "UNKNOWN")
                        logger.error(f"Error processing {callsign}: {e}")
        else:
            # Local execution fallback (no Ray available)
            for aircraft in aircraft_list:
                try:
                    self.process_aircraft_sync(aircraft)
                except Exception as e:
                    callsign = aircraft.get("callsign", "UNKNOWN")
                    logger.error(f"Error processing {callsign}: {e}")
        
        # Update statistics
        self.stats["aircraft_processed"] += len(aircraft_list)
        self.stats["total_ticks"] += 1
        
        # Prepare state snapshot periodically (every 10 ticks)
        if self.tick_count % 10 == 0:
            # Prepare snapshot event (non-blocking)
            snapshot_event = self.event_publisher.prepare_state_snapshot_event(
                self.tick_count, aircraft_list
            )
            self.redis_events_buffer.append(snapshot_event)
            
            # Queue database event for engine status
            self.pending_db_events.append({
                "level": "INFO",
                "type": "engine.status",
                "message": f"Engine tick {self.tick_count}: processing {len(aircraft_list)} aircraft",
                "details": {
                    "tick_count": self.tick_count,
                    "aircraft_count": len(aircraft_list),
                    "stats": self.stats,
                    "worker_stats": self.worker_stats
                },
                "sector": "ENGINE",
                "direction": "SYS"
            })
        
        # Track queue size
        queue_size = len(self.db_updates_buffer) + len(self.redis_events_buffer)
        self.worker_stats["queue_size_max"] = max(self.worker_stats["queue_size_max"], queue_size)
        
        # Check tick duration
        tick_duration = time.time() - tick_start
        self.stats["avg_tick_duration"] = (
            (self.stats["avg_tick_duration"] * (self.tick_count - 1) + tick_duration) / self.tick_count
            if self.tick_count > 0 else tick_duration
        )
        
        if tick_duration > TICK_WARNING_THRESHOLD_SEC:
            logger.warning(f"Tick {self.tick_count} took {tick_duration:.3f}s (threshold: {TICK_WARNING_THRESHOLD_SEC}s)")
    
    def _process_aircraft_results(self, original_aircraft: Dict[str, Any], updated: Dict[str, Any]):
        """
        Process results from Ray remote execution.
        Extracts events, prepares DB updates, and queues telemetry.
        
        This mirrors process_aircraft_sync but works with pre-computed results from Ray.
        
        Args:
            original_aircraft: Original aircraft data (before update)
            updated: Updated aircraft data (from Ray remote worker)
        """
        aircraft_id = original_aircraft["id"]
        callsign = original_aircraft.get("callsign", "UNKNOWN")
        
        # Extract updated state
        position = updated["position"]
        distance_nm = updated.get("distance_to_airport_nm", 999.0)
        altitude_ft = position["altitude_ft"]
        altitude_agl = altitude_msl_to_agl(altitude_ft, CYYZ_ELEVATION_FT)
        
        # Determine phase
        phase = self.determine_phase(distance_nm, altitude_agl)
        updated["phase"] = phase
        
        # ========== LLM Event Detection ==========
        # Check zone boundary crossing
        zone_event = self._check_zone_boundary_crossed(original_aircraft, updated)
        if zone_event:
            self.redis_events_buffer.append((
                "zone.boundary_crossed",
                zone_event
            ))
            self.stats["events_fired"] += 1
        
        # Check clearance completion
        clearance_event = self._check_clearance_completed(original_aircraft, updated)
        if clearance_event:
            self.redis_events_buffer.append((
                "clearance.completed",
                clearance_event
            ))
            self.stats["events_fired"] += 1
        
        # Check runway landing
        landing_event = self._check_runway_landed(original_aircraft, updated)
        if landing_event:
            self.redis_events_buffer.append((
                "runway.landed",
                landing_event
            ))
            self.stats["events_fired"] += 1
        
        # Check runway vacated
        vacated_event = self._check_runway_vacated(original_aircraft, updated)
        if vacated_event:
            self.redis_events_buffer.append((
                "runway.vacated",
                vacated_event
            ))
            self.stats["events_fired"] += 1
        
        # Check threshold events (existing)
        last_event = original_aircraft.get("last_event_fired") or ""
        new_event = None
        
        if altitude_agl < TOUCHDOWN_ALTITUDE_FT and EVENT_TOUCHDOWN not in last_event:
            new_event = EVENT_TOUCHDOWN
            if config.DEBUG_PRINTS:
                logger.debug(f"TOUCHDOWN: {callsign} at {altitude_agl:.0f} ft AGL")
            
            self.db_updates_buffer.append({
                "aircraft_id": aircraft_id,
                "status": "landed",
                "controller": "GROUND",
                "phase": "TOUCHDOWN"
            })
            
            self.pending_db_events.append({
                "level": "INFO",
                "type": "aircraft.touchdown",
                "message": f"{callsign} touchdown at {altitude_agl:.0f} ft AGL",
                "details": {
                    "callsign": callsign,
                    "altitude_agl": altitude_agl,
                    "position": position,
                    "event_type": new_event
                },
                "aircraft_id": aircraft_id,
                "sector": "TWR",
                "direction": "SYS"
            })
            
            threshold_event = self.event_publisher.prepare_threshold_event(new_event, updated)
            self.redis_events_buffer.append(threshold_event)
            self.stats["events_fired"] += 1
            return
        
        elif distance_nm <= HANDOFF_READY_THRESHOLD_NM and EVENT_HANDOFF_READY not in last_event:
            new_event = EVENT_HANDOFF_READY
            if config.DEBUG_PRINTS:
                logger.debug(f"HANDOFF_READY: {callsign} at {distance_nm:.1f} NM")
            
            self.pending_db_events.append({
                "level": "INFO",
                "type": "aircraft.handoff_ready",
                "message": f"{callsign} ready for handoff at {distance_nm:.1f} NM",
                "details": {
                    "callsign": callsign,
                    "distance_nm": distance_nm,
                    "position": position,
                    "event_type": new_event
                },
                "aircraft_id": aircraft_id,
                "sector": "APP",
                "direction": "SYS"
            })
            
            threshold_event = self.event_publisher.prepare_threshold_event(new_event, updated)
            self.redis_events_buffer.append(threshold_event)
            self.stats["events_fired"] += 1
        
        elif distance_nm <= ENTRY_ZONE_THRESHOLD_NM and EVENT_ENTERED_ENTRY_ZONE not in last_event:
            new_event = EVENT_ENTERED_ENTRY_ZONE
            if config.DEBUG_PRINTS:
                logger.debug(f"ENTERED_ENTRY_ZONE: {callsign} at {distance_nm:.1f} NM")
            
            self.pending_db_events.append({
                "level": "INFO",
                "type": "aircraft.entered_entry_zone",
                "message": f"{callsign} entered entry zone at {distance_nm:.1f} NM",
                "details": {
                    "callsign": callsign,
                    "distance_nm": distance_nm,
                    "position": position,
                    "event_type": new_event
                },
                "aircraft_id": aircraft_id,
                "sector": "CTR",
                "direction": "SYS"
            })
            
            threshold_event = self.event_publisher.prepare_threshold_event(new_event, updated)
            self.redis_events_buffer.append(threshold_event)
            self.stats["events_fired"] += 1
        
        # Update last_event_fired
        if new_event:
            if last_event:
                updated["last_event_fired"] = f"{last_event},{new_event}"
            else:
                updated["last_event_fired"] = new_event
        
        # Prepare database update
        db_update = {
            "aircraft_id": aircraft_id,
            "position": position,
            "vertical_speed_fpm": updated.get("vertical_speed_fpm"),
            "phase": phase,
            "distance_to_airport_nm": distance_nm,
        }
        
        # Update current_zone if it changed
        if "current_zone" in updated:
            db_update["current_zone"] = updated["current_zone"]
        
        if new_event:
            db_update["last_event_fired"] = updated["last_event_fired"]
        
        # Queue DB update
        self.db_updates_buffer.append(db_update)
        
        # Queue Redis position update
        position_event = self.event_publisher.prepare_aircraft_position_event(updated)
        self.redis_events_buffer.append(position_event)
        
        # Add to telemetry buffer
        self.add_telemetry_snapshot(updated)
    
    def process_aircraft_sync(self, aircraft: Dict[str, Any]):
        """
        Process one aircraft: update kinematics, check thresholds, prepare events.
        
        THIS METHOD IS SYNCHRONOUS (pure computation, no I/O).
        All I/O is delegated to async workers via buffers.
        
        Args:
            aircraft: Aircraft data dictionary
        """
        aircraft_id = aircraft["id"]
        callsign = aircraft.get("callsign", "UNKNOWN")
        
        # Apply kinematics formulas (pure computation)
        updated = update_aircraft_state(aircraft, DT)
        
        # Extract updated state
        position = updated["position"]
        distance_nm = updated.get("distance_to_airport_nm", 999.0)
        altitude_ft = position["altitude_ft"]
        altitude_agl = altitude_msl_to_agl(altitude_ft, CYYZ_ELEVATION_FT)
        
        # Determine phase
        phase = self.determine_phase(distance_nm, altitude_agl)
        updated["phase"] = phase
        
        # ========== LLM Event Detection ==========
        # Check zone boundary crossing
        zone_event = self._check_zone_boundary_crossed(aircraft, updated)
        if zone_event:
            self.redis_events_buffer.append((
                "zone.boundary_crossed",
                zone_event
            ))
            self.stats["events_fired"] += 1
        
        # Check clearance completion
        clearance_event = self._check_clearance_completed(aircraft, updated)
        if clearance_event:
            self.redis_events_buffer.append((
                "clearance.completed",
                clearance_event
            ))
            self.stats["events_fired"] += 1
        
        # Check runway landing
        landing_event = self._check_runway_landed(aircraft, updated)
        if landing_event:
            self.redis_events_buffer.append((
                "runway.landed",
                landing_event
            ))
            self.stats["events_fired"] += 1
        
        # Check runway vacated
        vacated_event = self._check_runway_vacated(aircraft, updated)
        if vacated_event:
            self.redis_events_buffer.append((
                "runway.vacated",
                vacated_event
            ))
            self.stats["events_fired"] += 1
        
        # Check threshold events (existing)
        last_event = aircraft.get("last_event_fired") or ""
        new_event = None
        
        if altitude_agl < TOUCHDOWN_ALTITUDE_FT and EVENT_TOUCHDOWN not in last_event:
            new_event = EVENT_TOUCHDOWN
            if config.DEBUG_PRINTS:
                logger.debug(f"TOUCHDOWN: {callsign} at {altitude_agl:.0f} ft AGL")
            
            # Queue DB update to mark as landed
            self.db_updates_buffer.append({
                "aircraft_id": aircraft_id,
                "status": "landed",
                "controller": "GROUND",
                "phase": "TOUCHDOWN"
            })
            
            # Queue database event
            self.pending_db_events.append({
                "level": "INFO",
                "type": "aircraft.touchdown",
                "message": f"{callsign} touchdown at {altitude_agl:.0f} ft AGL",
                "details": {
                    "callsign": callsign,
                    "altitude_agl": altitude_agl,
                    "position": position,
                    "event_type": new_event
                },
                "aircraft_id": aircraft_id,
                "sector": "TWR",
                "direction": "SYS"
            })
            
            # Queue Redis event
            threshold_event = self.event_publisher.prepare_threshold_event(new_event, updated)
            self.redis_events_buffer.append(threshold_event)
            self.stats["events_fired"] += 1
            
            # Stop processing this aircraft
            return
        
        elif distance_nm <= HANDOFF_READY_THRESHOLD_NM and EVENT_HANDOFF_READY not in last_event:
            new_event = EVENT_HANDOFF_READY
            if config.DEBUG_PRINTS:
                logger.debug(f"HANDOFF_READY: {callsign} at {distance_nm:.1f} NM")
            
            # Queue database event
            self.pending_db_events.append({
                "level": "INFO",
                "type": "aircraft.handoff_ready",
                "message": f"{callsign} ready for handoff at {distance_nm:.1f} NM",
                "details": {
                    "callsign": callsign,
                    "distance_nm": distance_nm,
                    "position": position,
                    "event_type": new_event
                },
                "aircraft_id": aircraft_id,
                "sector": "APP",
                "direction": "SYS"
            })
            
            # Queue Redis event
            threshold_event = self.event_publisher.prepare_threshold_event(new_event, updated)
            self.redis_events_buffer.append(threshold_event)
            self.stats["events_fired"] += 1
        
        elif distance_nm <= ENTRY_ZONE_THRESHOLD_NM and EVENT_ENTERED_ENTRY_ZONE not in last_event:
            new_event = EVENT_ENTERED_ENTRY_ZONE
            if config.DEBUG_PRINTS:
                logger.debug(f"ENTERED_ENTRY_ZONE: {callsign} at {distance_nm:.1f} NM")
            
            # Queue database event
            self.pending_db_events.append({
                "level": "INFO",
                "type": "aircraft.entered_entry_zone",
                "message": f"{callsign} entered entry zone at {distance_nm:.1f} NM",
                "details": {
                    "callsign": callsign,
                    "distance_nm": distance_nm,
                    "position": position,
                    "event_type": new_event
                },
                "aircraft_id": aircraft_id,
                "sector": "CTR",
                "direction": "SYS"
            })
            
            # Queue Redis event
            threshold_event = self.event_publisher.prepare_threshold_event(new_event, updated)
            self.redis_events_buffer.append(threshold_event)
            self.stats["events_fired"] += 1
        
        # Update last_event_fired
        if new_event:
            if last_event:
                updated["last_event_fired"] = f"{last_event},{new_event}"
            else:
                updated["last_event_fired"] = new_event
        
        # Prepare database update
        db_update = {
            "aircraft_id": aircraft_id,
            "position": position,
            "vertical_speed_fpm": updated.get("vertical_speed_fpm"),
            "phase": phase,
            "distance_to_airport_nm": distance_nm,
        }
        
        # Update current_zone if it changed
        if "current_zone" in updated:
            db_update["current_zone"] = updated["current_zone"]
        
        if new_event:
            db_update["last_event_fired"] = updated["last_event_fired"]
        
        # Queue DB update (non-blocking)
        self.db_updates_buffer.append(db_update)
        
        # Queue Redis position update (non-blocking)
        position_event = self.event_publisher.prepare_aircraft_position_event(updated)
        self.redis_events_buffer.append(position_event)
        
        # Add to telemetry buffer (non-blocking)
        self.add_telemetry_snapshot(updated)
    
    # ========== LLM Event Detection Helpers ==========
    
    def _check_zone_boundary_crossed(self, aircraft: Dict[str, Any], updated: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Check if aircraft crossed zone boundary and emit zone.boundary_crossed event.
        
        Args:
            aircraft: Original aircraft data
            updated: Updated aircraft data after physics
            
        Returns:
            Event data dict if zone changed, None otherwise
        """
        distance_nm = updated.get("distance_to_airport_nm", 999.0)
        current_zone = aircraft.get("current_zone")
        new_zone = determine_zone(distance_nm)
        
        if has_zone_changed(current_zone, new_zone):
            # Update aircraft zone in updated dict
            updated["current_zone"] = new_zone
            
            event_data = {
                "aircraft_id": aircraft.get("id"),
                "from_zone": current_zone,
                "to_zone": new_zone,
                "distance_nm": distance_nm,
                "timestamp": datetime.utcnow().isoformat() + "Z"
            }
            return event_data
        return None
    
    def _check_clearance_completed(self, aircraft: Dict[str, Any], updated: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Check if aircraft reached clearance target (altitude/heading/speed/waypoint).
        
        Tolerances:
        - Altitude: ±100 ft
        - Speed: ±5 kts
        - Heading: ±5°
        - Waypoint: within 0.5 NM
        
        Args:
            aircraft: Original aircraft data
            updated: Updated aircraft data after physics
            
        Returns:
            Event data dict if clearance completed, None otherwise
        """
        position = updated.get("position", {})
        current_alt = position.get("altitude_ft", 0)
        current_speed = position.get("speed_kts", 0)
        current_heading = position.get("heading", 0)
        target_alt = aircraft.get("target_altitude_ft")
        target_speed = aircraft.get("target_speed_kts")
        target_heading = aircraft.get("target_heading_deg")
        vertical_speed = updated.get("vertical_speed_fpm", 0)
        
        completed_item = None
        clearance_id = aircraft.get("last_completed_clearance_id")  # Placeholder - will be from DB
        
        # Check altitude clearance
        if target_alt is not None:
            alt_diff = abs(current_alt - target_alt)
            if alt_diff < 100 and abs(vertical_speed) < 100:
                completed_item = "altitude"
        
        # Check speed clearance
        if target_speed is not None and completed_item is None:
            speed_diff = abs(current_speed - target_speed)
            if speed_diff < 5:
                completed_item = "speed"
        
        # Check heading clearance
        if target_heading is not None and completed_item is None:
            heading_diff = abs((current_heading - target_heading + 180) % 360 - 180)
            if heading_diff < 5:
                completed_item = "heading"
        
        # Check waypoint clearance (if waypoint_sequence exists)
        waypoint_sequence = aircraft.get("waypoint_sequence")
        if waypoint_sequence and isinstance(waypoint_sequence, list) and len(waypoint_sequence) > 0:
            next_waypoint = waypoint_sequence[0]
            if isinstance(next_waypoint, dict) and "lat" in next_waypoint and "lon" in next_waypoint:
                wp_lat = next_waypoint.get("lat")
                wp_lon = next_waypoint.get("lon")
                wp_distance = distance_to_airport(
                    position.get("lat", 0),
                    position.get("lon", 0),
                    wp_lat,
                    wp_lon
                )
                if wp_distance < 0.5:  # Within 0.5 NM
                    completed_item = "waypoint"
        
        if completed_item:
            event_data = {
                "aircraft_id": aircraft.get("id"),
                "clearance_id": clearance_id,
                "completed_item": completed_item,
                "timestamp": datetime.utcnow().isoformat() + "Z"
            }
            return event_data
        return None
    
    def _check_runway_landed(self, aircraft: Dict[str, Any], updated: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Check if aircraft landed (AGL < 50 ft and position intersects runway polygon).
        
        Args:
            aircraft: Original aircraft data
            updated: Updated aircraft data after physics
            
        Returns:
            Event data dict if landed, None otherwise
        """
        position = updated.get("position", {})
        altitude_ft = position.get("altitude_ft", 0)
        altitude_agl = altitude_msl_to_agl(altitude_ft, CYYZ_ELEVATION_FT)
        
        # Check altitude threshold
        if altitude_agl >= TOUCHDOWN_ALTITUDE_FT:
            return None
        
        # Check runway intersection (simplified - check if near airport)
        lat = position.get("lat", 0)
        lon = position.get("lon", 0)
        distance_nm = distance_to_airport(lat, lon)
        
        # Simple check: if very close to airport (< 0.5 NM) and low altitude, assume on runway
        # TODO: Enhance with actual runway polygon intersection
        if distance_nm < 0.5:
            # Check if we have runway data and do proper intersection
            runway_name = self._find_intersecting_runway(lat, lon)
            if runway_name:
                event_data = {
                    "aircraft_id": aircraft.get("id"),
                    "landing_runway": runway_name,
                    "touchdown_speed_kts": position.get("speed_kts", 0),
                    "timestamp": datetime.utcnow().isoformat() + "Z"
                }
                return event_data
        
        return None
    
    def _check_runway_vacated(self, aircraft: Dict[str, Any], updated: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Check if aircraft exited runway surface and entered first taxiway node.
        
        Args:
            aircraft: Original aircraft data
            updated: Updated aircraft data after physics
            
        Returns:
            Event data dict if vacated, None otherwise
        """
        # Check if aircraft was previously on runway
        if aircraft.get("phase") != "TOUCHDOWN" and aircraft.get("status") != "landed":
            return None
        
        position = updated.get("position", {})
        lat = position.get("lat", 0)
        lon = position.get("lon", 0)
        
        # Check if aircraft is now on taxiway (simplified - check distance from runway)
        # TODO: Enhance with actual taxiway node intersection
        distance_nm = distance_to_airport(lat, lon)
        
        # Simple heuristic: if moved away from airport center or entered taxiway area
        # For now, if aircraft is on ground and moved, assume vacated
        altitude_ft = position.get("altitude_ft", 0)
        altitude_agl = altitude_msl_to_agl(altitude_ft, CYYZ_ELEVATION_FT)
        
        if altitude_agl < 10:  # On ground
            # Check if near taxiway (simplified - within airport bounds)
            if distance_nm < 0.3:  # Within airport
                taxiway_name = self._find_nearest_taxiway(lat, lon)
                if taxiway_name:
                    # Find which runway was vacated from aircraft state
                    vacated_runway = aircraft.get("landing_runway") or "UNKNOWN"
                    event_data = {
                        "aircraft_id": aircraft.get("id"),
                        "vacated_runway": vacated_runway,
                        "taxiway": taxiway_name,
                        "timestamp": datetime.utcnow().isoformat() + "Z"
                    }
                    return event_data
        
        return None
    
    def _find_intersecting_runway(self, lat: float, lon: float) -> Optional[str]:
        """
        Find which runway the aircraft position intersects (simplified).
        
        Args:
            lat, lon: Aircraft position
            
        Returns:
            Runway name or None
        """
        if not self.airport or not self.airport.runways:
            return None
        
        # Simple distance-based check (can be enhanced with polygon intersection)
        for runway in self.airport.runways:
            coords = runway.get("coordinates", [])
            if coords and len(coords) > 0:
                # Check distance to runway centerline
                if isinstance(coords[0], list) and len(coords[0]) >= 2:
                    rw_lat = coords[0][1] if len(coords[0]) > 1 else coords[0][0]
                    rw_lon = coords[0][0]
                    distance = distance_to_airport(lat, lon, rw_lat, rw_lon)
                    if distance < 0.1:  # Within 0.1 NM of runway
                        return runway.get("ref") or runway.get("name", "UNKNOWN")
        
        return None
    
    def _find_nearest_taxiway(self, lat: float, lon: float) -> Optional[str]:
        """
        Find nearest taxiway to aircraft position (simplified).
        
        Args:
            lat, lon: Aircraft position
            
        Returns:
            Taxiway name or None
        """
        # Placeholder - would need taxiway data from airport_data
        # For now, return a generic taxiway name if within airport bounds
        distance_nm = distance_to_airport(lat, lon)
        if distance_nm < 0.3:
            return "TAXIWAY_A"  # Placeholder
        return None
    
    def determine_phase(self, distance_nm: float, altitude_agl: float) -> str:
        """
        Determine flight phase based on distance and altitude.
        
        Args:
            distance_nm: Distance to airport (nautical miles)
            altitude_agl: Altitude above ground (feet)
        
        Returns:
            Phase string
        """
        if altitude_agl < 500:
            return "FINAL"
        elif distance_nm < 10.0:
            return "APPROACH"
        elif distance_nm < 30.0:
            return "DESCENT"
        else:
            return "CRUISE"
    
    def add_telemetry_snapshot(self, aircraft: Dict[str, Any]):
        """
        Add aircraft snapshot to telemetry buffer (non-blocking).
        Telemetry worker will flush periodically.
        
        Args:
            aircraft: Aircraft data dictionary
        """
        position = aircraft.get("position", {})
        
        snapshot = {
            "tick": self.tick_count,
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "id": aircraft.get("id"),
            "callsign": aircraft.get("callsign"),
            "lat": position.get("lat"),
            "lon": position.get("lon"),
            "altitude_ft": position.get("altitude_ft"),
            "speed_kts": position.get("speed_kts"),
            "heading": position.get("heading"),
            "vertical_speed_fpm": aircraft.get("vertical_speed_fpm"),
            "distance_to_airport_nm": aircraft.get("distance_to_airport_nm"),
            "controller": aircraft.get("controller"),
            "phase": aircraft.get("phase"),
        }
        
        self.telemetry_buffer.append(snapshot)
    
    def print_statistics(self):
        """Print engine and worker statistics."""
        runtime = time.time() - self.start_time if self.start_time else 0
        
        logger.info("\nEngine Statistics:")
        logger.info(f"   Runtime: {runtime:.1f}s ({runtime/60:.1f}m)")
        logger.info(f"   Total ticks: {self.stats['total_ticks']}")
        logger.info(f"   Aircraft processed: {self.stats['aircraft_processed']}")
        logger.info(f"   Events fired: {self.stats['events_fired']}")
        logger.info(f"   Avg tick duration: {self.stats['avg_tick_duration']*1000:.2f}ms")
        
        if self.use_ray:
            logger.info("\nRay Distributed Statistics:")
            logger.info(f"   Ray tasks executed: {self.stats['ray_tasks_executed']}")
            logger.info(f"   Ray fallbacks: {self.stats['ray_fallbacks']}")
        
        logger.info("\nWorker Statistics:")
        logger.info(f"   DB writes: {self.stats['db_writes']} (batches: {self.worker_stats['db_batches']})")
        logger.info(f"   Redis publishes: {self.stats['redis_publishes']} (batches: {self.worker_stats['redis_batches']})")
        logger.info(f"   Telemetry writes: {self.stats['telemetry_writes']} (batches: {self.worker_stats['telemetry_batches']})")
        logger.info(f"   Max queue size: {self.worker_stats['queue_size_max']}")
    
    async def run(self, duration_seconds: int = 0):
        """
        Run the main engine loop.
        
        Args:
            duration_seconds: Run for specified duration (0 = infinite)
        """
        await self.initialize()
        
        # Start spawn listener in background
        listener_task = self.spawn_listener.start_background_task()
        
        self.running = True
        self.start_time = time.time()
        
        logger.info(f"\nStarting engine tick loop (1 Hz, dt={DT}s)")
        if duration_seconds > 0:
            logger.info(f"   Running for {duration_seconds}s")
        else:
            logger.info(f"   Running indefinitely (Ctrl+C to stop)")
        logger.info("")
        
        try:
            target_interval = DT
            
            while self.running:
                self.tick_count += 1
                tick_start = time.time()
                
                # Execute tick (deterministic physics)
                await self.tick()
                
                # Drift compensation
                elapsed = time.time() - tick_start
                sleep_time = max(0, target_interval - elapsed)
                
                await asyncio.sleep(sleep_time)
                
                # Check duration limit
                if duration_seconds > 0 and (time.time() - self.start_time) >= duration_seconds:
                    logger.info(f"\nReached duration limit ({duration_seconds}s)")
                    break
        
        except KeyboardInterrupt:
            logger.info("\n\nKeyboard interrupt received")
        
        finally:
            # Cancel listener task
            listener_task.cancel()
            try:
                await listener_task
            except asyncio.CancelledError:
                pass
            
            await self.shutdown()


async def main():
    """Main entry point for the kinematics engine."""
    import argparse
    
    parser = argparse.ArgumentParser(description="ATC Kinematics Engine - Phase 1")
    parser.add_argument(
        "--duration",
        type=int,
        default=0,
        help="Run duration in seconds (0 = infinite)",
    )
    parser.add_argument(
        "--test",
        action="store_true",
        help="Run 60-second test simulation",
    )
    
    args = parser.parse_args()
    
    duration = 60 if args.test else args.duration
    
    engine = KinematicsEngine()
    await engine.run(duration_seconds=duration)


if __name__ == "__main__":
    asyncio.run(main())

