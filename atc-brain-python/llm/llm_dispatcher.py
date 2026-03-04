"""
LLM Dispatcher: Event-driven AI controller for ATC system.
Subscribes to Redis events, builds context, calls LLMs, and applies decisions.
"""

import asyncio
import json
import logging
import os
import subprocess
from datetime import datetime
from typing import Dict, Any, Optional, List
from dotenv import load_dotenv

import asyncpg
import redis.asyncio as redis

from .llm_schemas import AirClearance, GroundClearance
from .llm_prompts import build_air_prompt, build_ground_prompt
from .safety_validator import SafetyValidator

load_dotenv()

logger = logging.getLogger(__name__)


class AirLLMClient:
    """Real Air LLM client using Mistral-7B via Ollama for airborne aircraft control."""
    
    def __init__(self, safety_validator: Optional[SafetyValidator] = None):
        self.name = "AirLLM"
        self.model = "mistral"  # Ollama model name
        self.safety_validator = safety_validator
    
    async def _call_ollama(self, prompt: str) -> str:
        """
        Call Ollama asynchronously to run Mistral-7B.
        
        Args:
            prompt: Input prompt for the model
            
        Returns:
            Raw model output string
        """
        try:
            # Run ollama run mistral with prompt
            process = await asyncio.create_subprocess_exec(
                "ollama", "run", self.model,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await process.communicate(input=prompt.encode())
            
            if process.returncode != 0:
                logger.error(f"Ollama error: {stderr.decode()}")
                return ""
            
            return stdout.decode().strip()
            
        except Exception as e:
            logger.error(f"Error calling Ollama: {e}")
            return ""
    
    async def generate_decision(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate decision from Air LLM using Mistral-7B.
        
        Args:
            context: Context dictionary with aircraft state, zone info, etc.
            
        Returns:
            Decision structure with clearance or None if invalid
        """
        aircraft_id = context.get("aircraft_id")
        
        try:
            # Build prompt
            prompt = build_air_prompt(context)
            
            # Call LLM
            logger.info(f"Calling Mistral-7B for Air clearance (aircraft {aircraft_id})")
            raw_output = await self._call_ollama(prompt)
            
            if not raw_output:
                logger.error(f"Empty response from Ollama for aircraft {aircraft_id}")
                return self._fallback_decision(context)
            
            # Parse JSON safely
            clearance = self._parse_json_response(raw_output)
            if not clearance:
                # Retry once with fix prompt
                logger.warning(f"Invalid JSON from LLM for aircraft {aircraft_id}, retrying with fix prompt")
                fix_prompt = f"The previous output was not valid JSON. Please output ONLY valid JSON matching this schema:\n{{\n  \"action_type\": \"string\",\n  \"target_altitude_ft\": integer or null,\n  \"target_speed_kts\": integer or null,\n  \"target_heading_deg\": integer or null,\n  \"waypoints\": array or null,\n  \"runway\": string or null\n}}\n\nJSON only:"
                raw_output = await self._call_ollama(fix_prompt)
                clearance = self._parse_json_response(raw_output)
                
                if not clearance:
                    logger.error(f"Still invalid JSON after retry for aircraft {aircraft_id}")
                    return self._fallback_decision(context)
            
            # Validate safety
            if self.safety_validator:
                is_safe = await self.safety_validator.validate_air_clearance(aircraft_id, clearance, context)
                if not is_safe:
                    logger.warning(f"Air clearance failed safety validation for aircraft {aircraft_id}")
                    return self._fallback_decision(context, validation_failed=True)
            
            # Convert to decision structure
            decision = {
                "clearance_type": clearance.get("action_type", "VECTORING"),
                "aircraft_id": aircraft_id,
                "instructions": clearance,
                "reason": "LLM-generated clearance",
                "confidence": 0.85,
                "validated": True
            }
            
            logger.info(f"Generated valid air clearance for aircraft {aircraft_id}: {clearance.get('action_type')}")
            return decision
            
        except Exception as e:
            logger.error(f"Error generating air decision for aircraft {aircraft_id}: {e}")
            return self._fallback_decision(context)
    
    def _parse_json_response(self, raw_output: str) -> Optional[Dict[str, Any]]:
        """
        Parse JSON from LLM output, handling common issues.
        
        Args:
            raw_output: Raw LLM output string
            
        Returns:
            Parsed dict or None if invalid
        """
        try:
            # Try direct parse
            return json.loads(raw_output)
        except json.JSONDecodeError:
            # Try to extract JSON from markdown code blocks
            if "```json" in raw_output:
                start = raw_output.find("```json") + 7
                end = raw_output.find("```", start)
                json_str = raw_output[start:end].strip()
                try:
                    return json.loads(json_str)
                except json.JSONDecodeError:
                    pass
            
            # Try to find JSON object in output
            start = raw_output.find("{")
            end = raw_output.rfind("}") + 1
            if start >= 0 and end > start:
                json_str = raw_output[start:end]
                try:
                    return json.loads(json_str)
                except json.JSONDecodeError:
                    pass
            
            return None
    
    def _fallback_decision(self, context: Dict[str, Any], validation_failed: bool = False) -> Dict[str, Any]:
        """
        Generate fallback decision when LLM fails or validation fails.
        
        Args:
            context: Aircraft context
            validation_failed: Whether this is due to validation failure
            
        Returns:
            Safe fallback decision
        """
        aircraft_id = context.get("aircraft_id")
        zone = context.get("current_zone", "UNKNOWN")
        aircraft = context.get("aircraft", {})
        current_altitude = aircraft.get("altitude_ft", 10000)
        
        # Conservative fallback: maintain current altitude, reduce speed
        return {
            "clearance_type": "VECTORING",
            "aircraft_id": aircraft_id,
            "instructions": {
                "action_type": "VECTORING",
                "target_altitude_ft": current_altitude,
                "target_speed_kts": 250,
                "target_heading_deg": None,
                "waypoints": None,
                "runway": None
            },
            "reason": "Fallback (LLM failure)" if not validation_failed else "Fallback (validation failed)",
            "confidence": 0.50,
            "validated": False
            }


class GroundLLMClient:
    """Real Ground LLM client using Mistral-7B via Ollama for surface operations."""
    
    def __init__(self, safety_validator: Optional[SafetyValidator] = None):
        self.name = "GroundLLM"
        self.model = "mistral"  # Ollama model name
        self.safety_validator = safety_validator
    
    async def _call_ollama(self, prompt: str) -> str:
        """
        Call Ollama asynchronously to run Mistral-7B.
        
        Args:
            prompt: Input prompt for the model
            
        Returns:
            Raw model output string
        """
        try:
            # Run ollama run mistral with prompt
            process = await asyncio.create_subprocess_exec(
                "ollama", "run", self.model,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await process.communicate(input=prompt.encode())
            
            if process.returncode != 0:
                logger.error(f"Ollama error: {stderr.decode()}")
                return ""
            
            return stdout.decode().strip()
            
        except Exception as e:
            logger.error(f"Error calling Ollama: {e}")
            return ""
    
    async def generate_decision(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate decision from Ground LLM using Mistral-7B.
        
        Args:
            context: Context dictionary with aircraft state, gate info, etc.
            
        Returns:
            Decision structure with clearance or None if invalid
        """
        aircraft_id = context.get("aircraft_id")
        
        try:
            # Build prompt
            prompt = build_ground_prompt(context)
            
            # Call LLM
            logger.info(f"Calling Mistral-7B for Ground clearance (aircraft {aircraft_id})")
            raw_output = await self._call_ollama(prompt)
            
            if not raw_output:
                logger.error(f"Empty response from Ollama for aircraft {aircraft_id}")
                return self._fallback_decision(context)
            
            # Parse JSON safely
            clearance = self._parse_json_response(raw_output)
            if not clearance:
                # Retry once with fix prompt
                logger.warning(f"Invalid JSON from LLM for aircraft {aircraft_id}, retrying with fix prompt")
                fix_prompt = f"The previous output was not valid JSON. Please output ONLY valid JSON matching this schema:\n{{\n  \"action_type\": \"string\",\n  \"assigned_gate\": string or null,\n  \"taxi_route\": array or null,\n  \"runway\": string or null\n}}\n\nJSON only:"
                raw_output = await self._call_ollama(fix_prompt)
                clearance = self._parse_json_response(raw_output)
                
                if not clearance:
                    logger.error(f"Still invalid JSON after retry for aircraft {aircraft_id}")
                    return self._fallback_decision(context)
            
            # Validate safety
            if self.safety_validator:
                is_safe = await self.safety_validator.validate_ground_clearance(aircraft_id, clearance, context)
                if not is_safe:
                    logger.warning(f"Ground clearance failed safety validation for aircraft {aircraft_id}")
                    return self._fallback_decision(context, validation_failed=True)
            
            # Convert to decision structure
            decision = {
                "clearance_type": clearance.get("action_type", "TAXI_CLEARANCE"),
                "aircraft_id": aircraft_id,
                "instructions": clearance,
                "reason": "LLM-generated clearance",
                "confidence": 0.85,
                "validated": True
            }
            
            logger.info(f"Generated valid ground clearance for aircraft {aircraft_id}: {clearance.get('action_type')}")
            return decision
            
        except Exception as e:
            logger.error(f"Error generating ground decision for aircraft {aircraft_id}: {e}")
            return self._fallback_decision(context)
    
    def _parse_json_response(self, raw_output: str) -> Optional[Dict[str, Any]]:
        """
        Parse JSON from LLM output, handling common issues.
        
        Args:
            raw_output: Raw LLM output string
            
        Returns:
            Parsed dict or None if invalid
        """
        try:
            # Try direct parse
            return json.loads(raw_output)
        except json.JSONDecodeError:
            # Try to extract JSON from markdown code blocks
            if "```json" in raw_output:
                start = raw_output.find("```json") + 7
                end = raw_output.find("```", start)
                json_str = raw_output[start:end].strip()
                try:
                    return json.loads(json_str)
                except json.JSONDecodeError:
                    pass
            
            # Try to find JSON object in output
            start = raw_output.find("{")
            end = raw_output.rfind("}") + 1
            if start >= 0 and end > start:
                json_str = raw_output[start:end]
                try:
                    return json.loads(json_str)
                except json.JSONDecodeError:
                    pass
            
            return None
    
    def _fallback_decision(self, context: Dict[str, Any], validation_failed: bool = False) -> Dict[str, Any]:
        """
        Generate fallback decision when LLM fails or validation fails.
        
        Args:
            context: Aircraft context
            validation_failed: Whether this is due to validation failure
            
        Returns:
            Safe fallback decision (hold position)
        """
        aircraft_id = context.get("aircraft_id")
        event_type = context.get("event_type", "UNKNOWN")
        
        # Conservative fallback: assign a default gate
        return {
            "clearance_type": "GATE_ASSIGNMENT",
            "aircraft_id": aircraft_id,
            "instructions": {
                "action_type": "GATE_ASSIGNMENT",
                "assigned_gate": "C32",  # Default gate
                "taxi_route": None,
                "runway": None
            },
            "reason": "Fallback (LLM failure)" if not validation_failed else "Fallback (validation failed)",
            "confidence": 0.50,
            "validated": False
        }


class ContextBuilder:
    """Builds context for LLM decision making from database state."""
    
    def __init__(self, db_pool: asyncpg.Pool):
        self.db_pool = db_pool
    
    async def build_aircraft_context(self, aircraft_id: int, event_type: str) -> Dict[str, Any]:
        """
        Build full context for aircraft decision making.
        
        Args:
            aircraft_id: Aircraft instance ID
            event_type: Event type that triggered the decision
            
        Returns:
            Context dictionary with aircraft state, zone info, clearances, etc.
        """
        async with self.db_pool.acquire() as conn:
            # Fetch aircraft full details
            aircraft_query = """
                SELECT 
                    ai.*,
                    at.icao_type,
                    at.cruise_speed_kts,
                    at.max_speed_kts,
                    al.icao as airline_icao,
                    al.name as airline_name
                FROM aircraft_instances ai
                LEFT JOIN aircraft_types at ON ai.aircraft_type_id = at.id
                LEFT JOIN airlines al ON ai.airline_id = al.id
                WHERE ai.id = $1
            """
            aircraft_row = await conn.fetchrow(aircraft_query, aircraft_id)
            
            if not aircraft_row:
                logger.error(f"Aircraft {aircraft_id} not found")
                return {}
            
            aircraft = dict(aircraft_row)
            
            # Parse JSONB fields
            if isinstance(aircraft.get("position"), str):
                aircraft["position"] = json.loads(aircraft["position"])
            if isinstance(aircraft.get("flight_plan"), str):
                aircraft["flight_plan"] = json.loads(aircraft["flight_plan"])
            
            # Get current_zone if column exists, otherwise determine from distance
            current_zone = aircraft.get("current_zone")
            if not current_zone:
                from engine.zone_detector import determine_zone
                distance_nm = aircraft.get("distance_to_airport_nm", 999.0)
                current_zone = determine_zone(float(distance_nm)) if distance_nm else "UNKNOWN"
            
            # Fetch active clearances (if table exists)
            active_clearances = []
            try:
                clearances_query = """
                    SELECT id, clearance_type, instructions, status, issued_at
                    FROM clearances
                    WHERE aircraft_id = $1 AND status = 'ACTIVE'
                    ORDER BY issued_at DESC
                    LIMIT 5
                """
                clearance_rows = await conn.fetch(clearances_query, aircraft_id)
                active_clearances = [dict(row) for row in clearance_rows]
                for clr in active_clearances:
                    if isinstance(clr.get("instructions"), str):
                        clr["instructions"] = json.loads(clr["instructions"])
            except Exception as e:
                # Clearances table might not exist yet
                logger.debug(f"Could not fetch clearances (table may not exist): {e}")
                active_clearances = []
            
            # Fetch aircraft in current zone (for context)
            # Check if current_zone column exists
            zone_column_exists = await conn.fetchval("""
                SELECT EXISTS (
                    SELECT FROM information_schema.columns 
                    WHERE table_schema = 'public' 
                    AND table_name = 'aircraft_instances' 
                    AND column_name = 'current_zone'
                )
            """)
            
            if zone_column_exists:
                zone_aircraft_query = """
                    SELECT id, callsign, position, current_zone, distance_to_airport_nm
                    FROM aircraft_instances
                    WHERE current_zone = $1 AND status = 'active' AND id != $2
                    ORDER BY distance_to_airport_nm
                    LIMIT 10
                """
                zone_aircraft_rows = await conn.fetch(zone_aircraft_query, current_zone, aircraft_id)
            else:
                # Fallback: use distance-based filtering if current_zone doesn't exist
                # Get aircraft within similar distance range (±10 NM)
                distance = aircraft.get("distance_to_airport_nm", 999.0)
                zone_aircraft_query = """
                    SELECT id, callsign, position, distance_to_airport_nm
                    FROM aircraft_instances
                    WHERE status = 'active' 
                      AND id != $1
                      AND distance_to_airport_nm BETWEEN $2 - 10 AND $2 + 10
                    ORDER BY distance_to_airport_nm
                    LIMIT 10
                """
                zone_aircraft_rows = await conn.fetch(zone_aircraft_query, aircraft_id, distance)
            zone_aircraft = []
            for row in zone_aircraft_rows:
                ac = dict(row)
                if isinstance(ac.get("position"), str):
                    ac["position"] = json.loads(ac["position"])
                zone_aircraft.append({
                    "id": ac["id"],
                    "callsign": ac["callsign"],
                    "distance_nm": float(ac.get("distance_to_airport_nm", 0))
                })
            
            # Determine next/previous zones
            next_zone = self._get_next_zone(current_zone)
            prev_zone = self._get_previous_zone(current_zone)
            
            # Fetch summary of next zone aircraft
            next_zone_summary = []
            if next_zone and zone_column_exists:
                next_zone_query = """
                    SELECT COUNT(*) as count, 
                           AVG(distance_to_airport_nm) as avg_distance
                    FROM aircraft_instances
                    WHERE current_zone = $1 AND status = 'active'
                """
                next_row = await conn.fetchrow(next_zone_query, next_zone)
                if next_row:
                    next_zone_summary = {
                        "zone": next_zone,
                        "aircraft_count": next_row["count"],
                        "avg_distance_nm": float(next_row["avg_distance"] or 0)
                    }
            
            # Build context
            context = {
                "aircraft_id": aircraft_id,
                "event_type": event_type,
                "current_zone": current_zone,
                "aircraft": {
                    "id": aircraft["id"],
                    "callsign": aircraft["callsign"],
                    "position": aircraft["position"],
                    "current_zone": current_zone,
                    "distance_to_airport_nm": float(aircraft.get("distance_to_airport_nm", 0)),
                    "altitude_ft": aircraft["position"].get("altitude_ft", 0),
                    "speed_kts": aircraft["position"].get("speed_kts", 0),
                    "heading": aircraft["position"].get("heading", 0),
                    "phase": aircraft.get("phase", "UNKNOWN"),
                    "aircraft_type": aircraft.get("icao_type"),
                    "airline": aircraft.get("airline_icao")
                },
                "active_clearances": active_clearances,
                "current_zone_aircraft": zone_aircraft,
                "next_zone": next_zone_summary,
                "previous_zone": prev_zone,
                "timestamp": datetime.utcnow().isoformat() + "Z"
            }
            
            return context
    
    def _get_next_zone(self, current_zone: str) -> Optional[str]:
        """Get next zone in sequence."""
        zone_sequence = {
            "ENTRY": "ENROUTE_50",
            "ENROUTE_50": "ENROUTE_20",
            "ENROUTE_20": "APPROACH_5",
            "APPROACH_5": "RUNWAY",
            "RUNWAY": None
        }
        return zone_sequence.get(current_zone)
    
    def _get_previous_zone(self, current_zone: str) -> Optional[str]:
        """Get previous zone in sequence."""
        zone_sequence = {
            "ENTRY": None,
            "ENROUTE_50": "ENTRY",
            "ENROUTE_20": "ENROUTE_50",
            "APPROACH_5": "ENROUTE_20",
            "RUNWAY": "APPROACH_5"
        }
        return zone_sequence.get(current_zone)


class DecisionRouter:
    """Converts LLM JSON decisions into engine instructions."""
    
    def __init__(self, db_pool: asyncpg.Pool):
        self.db_pool = db_pool
    
    async def apply_decision(self, decision: Dict[str, Any]) -> bool:
        """
        Apply LLM decision to aircraft state in database.
        Only writes target fields if clearance passed validation.
        
        Args:
            decision: LLM decision JSON structure
            
        Returns:
            True if successful
        """
        aircraft_id = decision.get("aircraft_id")
        clearance_type = decision.get("clearance_type")
        instructions = decision.get("instructions", {})
        validated = decision.get("validated", False)
        
        if not aircraft_id:
            logger.error("Decision missing aircraft_id")
            return False
        
        # Check if clearance passed validation
        if not validated:
            logger.warning(
                f"Skipping database write for aircraft {aircraft_id}: "
                f"clearance did not pass validation"
            )
            # Still store the clearance for logging/audit, but don't update aircraft state
            try:
                async with self.db_pool.acquire() as conn:
                    await self._store_clearance(conn, decision)
                return False
            except Exception as e:
                logger.error(f"Error storing failed clearance for aircraft {aircraft_id}: {e}")
            return False
        
        try:
            async with self.db_pool.acquire() as conn:
                # Extract instruction values
                target_altitude = instructions.get("target_altitude_ft")
                target_speed = instructions.get("target_speed_kts")
                target_heading = instructions.get("target_heading_deg")
                assigned_gate = instructions.get("assigned_gate")
                taxi_route = instructions.get("taxi_route")
                
                # Build update dict (only fields that exist in aircraft_instances table)
                updates = {}
                if target_altitude is not None:
                    updates["target_altitude_ft"] = target_altitude
                if target_speed is not None:
                    updates["target_speed_kts"] = target_speed
                if target_heading is not None:
                    updates["target_heading_deg"] = target_heading
                
                # Update aircraft state only if validated
                if updates:
                    set_clauses = []
                    values = []
                    param_idx = 1
                    
                    for key, value in updates.items():
                        set_clauses.append(f"{key} = ${param_idx}")
                        values.append(value)
                        param_idx += 1
                    
                    set_clauses.append("updated_at = NOW()")
                    values.append(aircraft_id)
                    
                    update_query = f"""
                        UPDATE aircraft_instances
                        SET {', '.join(set_clauses)}
                        WHERE id = ${param_idx}
                    """
                    
                    await conn.execute(update_query, *values)
                    logger.info(
                        f"Applied validated clearance to aircraft {aircraft_id}: {clearance_type} "
                        f"(updates: {list(updates.keys())})"
                    )
                
                # Store validated clearance in database
                clearance_id = await self._store_clearance(conn, decision)
                
                # Create event in events table for logging (so it appears in frontend logs)
                await self._create_clearance_event(conn, aircraft_id, decision, clearance_id)
                
                return True
                
        except Exception as e:
            logger.error(f"Error applying decision for aircraft {aircraft_id}: {e}")
            return False
    
    async def _store_clearance(self, conn: asyncpg.Connection, decision: Dict[str, Any]) -> Optional[int]:
        """
        Store clearance in database (if clearances table exists).
        
        Args:
            conn: Database connection
            decision: LLM decision structure
            
        Returns:
            Clearance ID if successful, None otherwise
        """
        try:
            clearance_type = decision.get("clearance_type")
            aircraft_id = decision.get("aircraft_id")
            instructions = decision.get("instructions", {})
            reason = decision.get("reason", "")
            confidence = decision.get("confidence", 0.0)
            
            # Determine issued_by based on clearance type
            if clearance_type in ["STAR_ASSIGNMENT", "VECTORING", "DESCENT_PROFILE", 
                                 "SPEED_ASSIGNMENT", "RUNWAY_ASSIGNMENT", "LANDING_CLEARANCE"]:
                issued_by = "AIR_LLM"
            else:
                issued_by = "GROUND_LLM"
            
            # Check if clearances table exists
            table_check = """
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_schema = 'public' 
                    AND table_name = 'clearances'
                )
            """
            table_exists = await conn.fetchval(table_check)
            
            if not table_exists:
                logger.debug("Clearances table does not exist, skipping clearance storage")
                return None
            
            insert_query = """
                INSERT INTO clearances 
                (aircraft_id, clearance_type, issued_by, instructions, reason, confidence, status)
                VALUES ($1, $2, $3, $4, $5, $6, 'ACTIVE')
                RETURNING id
            """
            
            result = await conn.fetchrow(
                insert_query,
                aircraft_id,
                clearance_type,
                issued_by,
                json.dumps(instructions),
                reason,
                confidence
            )
            
            if result:
                logger.debug(f"Stored clearance {result['id']} for aircraft {aircraft_id}")
                return result["id"]
            return None
            
        except Exception as e:
            logger.warning(f"Could not store clearance (table may not exist): {e}")
            return None
    
    async def _create_clearance_event(
        self, 
        conn: asyncpg.Connection, 
        aircraft_id: int, 
        decision: Dict[str, Any],
        clearance_id: Optional[int]
    ) -> None:
        """
        Create event in events table for logging (so LLM decisions appear in frontend logs).
        
        Args:
            conn: Database connection
            aircraft_id: Aircraft ID
            decision: LLM decision structure
            clearance_id: Clearance ID if stored
        """
        try:
            # Check if events table exists
            table_check = await conn.fetchval("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_schema = 'public' 
                    AND table_name = 'events'
                )
            """)
            
            if not table_check:
                return  # Events table doesn't exist
            
            # Get aircraft callsign for the message
            aircraft_row = await conn.fetchrow(
                "SELECT callsign FROM aircraft_instances WHERE id = $1",
                aircraft_id
            )
            callsign = aircraft_row["callsign"] if aircraft_row else f"Aircraft {aircraft_id}"
            
            # Format clearance message
            clearance_type = decision.get("clearance_type", "UNKNOWN")
            instructions = decision.get("instructions", {})
            validated = decision.get("validated", True)
            
            # Build instruction text
            inst_parts = []
            if instructions.get("target_altitude_ft"):
                inst_parts.append(f"ALT {instructions['target_altitude_ft']}ft")
            if instructions.get("target_speed_kts"):
                inst_parts.append(f"SPD {instructions['target_speed_kts']}kts")
            if instructions.get("target_heading_deg"):
                inst_parts.append(f"HDG {instructions['target_heading_deg']}°")
            if instructions.get("assigned_gate"):
                inst_parts.append(f"GATE {instructions['assigned_gate']}")
            if instructions.get("taxi_route"):
                inst_parts.append(f"TAXI {'-'.join(instructions['taxi_route'])}")
            
            inst_text = ", ".join(inst_parts) if inst_parts else clearance_type
            validation_status = "VALIDATED" if validated else "NOT VALIDATED"
            
            message = f"LLM CLEARANCE: {callsign} - {clearance_type} ({inst_text}) [{validation_status}]"
            
            # Determine sector based on clearance type
            if decision.get("clearance_type") in ["STAR_ASSIGNMENT", "VECTORING", "DESCENT_PROFILE", 
                                                   "SPEED_ASSIGNMENT", "RUNWAY_ASSIGNMENT", "LANDING_CLEARANCE"]:
                sector = "APP"  # Approach
            else:
                sector = "GND"  # Ground
            
            # Insert event
            await conn.execute("""
                INSERT INTO events (level, type, message, details, aircraft_id, sector, direction)
                VALUES ($1, $2, $3, $4, $5, $6, $7)
            """,
                "INFO",
                "llm.clearance_issued",
                message,
                json.dumps({
                    "clearance_type": clearance_type,
                    "clearance_id": clearance_id,
                    "instructions": instructions,
                    "validated": validated,
                    "reason": decision.get("reason", ""),
                    "confidence": decision.get("confidence", 0.0)
                }),
                aircraft_id,
                sector,
                "SYS"  # System-generated
            )
            
        except Exception as e:
            logger.debug(f"Could not create clearance event (events table may not exist or error): {e}")


class LLMDispatcher:
    """Main dispatcher that subscribes to Redis events and triggers LLM decisions."""
    
    def __init__(self):
        self.redis_client: Optional[redis.Redis] = None
        self.db_pool: Optional[asyncpg.Pool] = None
        self.running = False
        
        # Will be initialized after DB connection
        self.safety_validator: Optional[SafetyValidator] = None
        self.air_llm: Optional[AirLLMClient] = None
        self.ground_llm: Optional[GroundLLMClient] = None
        self.context_builder: Optional[ContextBuilder] = None
        self.decision_router: Optional[DecisionRouter] = None
        
        # Event processing queue
        self.event_queue: asyncio.Queue = asyncio.Queue()
        
        # Redis config
        self.redis_config = {
            "host": os.getenv("REDIS_HOST", "localhost"),
            "port": int(os.getenv("REDIS_PORT", "6379")),
            "password": os.getenv("REDIS_PASSWORD") or None,
            "db": 0,
            "decode_responses": True,
        }
        self.redis_channel = os.getenv("EVENT_CHANNEL", "atc:events")
        
        # Database config
        self.db_config = {
            "host": os.getenv("DB_HOST", "localhost"),
            "port": int(os.getenv("DB_PORT", "5432")),
            "database": os.getenv("DB_NAME", "atc_system"),
            "user": os.getenv("DB_USER", "postgres"),
            "password": os.getenv("DB_PASSWORD", "password"),
            "min_size": 5,
            "max_size": 20,
        }
    
    async def initialize(self):
        """Initialize Redis and database connections."""
        logger.info("Initializing LLM Dispatcher...")
        
        # Connect to Redis
        try:
            self.redis_client = redis.Redis(**self.redis_config)
            await self.redis_client.ping()
            logger.info(f"Connected to Redis on channel '{self.redis_channel}'")
        except Exception as e:
            logger.error(f"Failed to connect to Redis: {e}")
            raise
        
        # Connect to database
        try:
            self.db_pool = await asyncpg.create_pool(**self.db_config)
            logger.info("Connected to PostgreSQL database")
        except Exception as e:
            logger.error(f"Failed to connect to database: {e}")
            raise
        
        # Initialize helpers
        self.safety_validator = SafetyValidator(self.db_pool)
        self.air_llm = AirLLMClient(self.safety_validator)
        self.ground_llm = GroundLLMClient(self.safety_validator)
        self.context_builder = ContextBuilder(self.db_pool)
        self.decision_router = DecisionRouter(self.db_pool)
        
        logger.info("LLM Dispatcher initialized with Mistral-7B via Ollama")
    
    async def shutdown(self):
        """Shutdown connections."""
        logger.info("Shutting down LLM Dispatcher...")
        
        self.running = False
        
        if self.redis_client:
            await self.redis_client.close()
        
        if self.db_pool:
            await self.db_pool.close()
        
        logger.info("LLM Dispatcher shutdown complete")
    
    async def subscribe_to_events(self):
        """Subscribe to Redis events and queue them for processing."""
        pubsub = self.redis_client.pubsub()
        await pubsub.subscribe(self.redis_channel)
        
        logger.info(f"Subscribed to Redis channel: {self.redis_channel}")
        
        try:
            async for message in pubsub.listen():
                if message["type"] == "message":
                    try:
                        event_data = json.loads(message["data"])
                        event_type = event_data.get("type")
                        
                        # Filter for LLM-relevant events
                        if event_type in [
                            "aircraft.created",  # Trigger LLM when aircraft first created
                            "zone.boundary_crossed",
                            "clearance.completed",
                            "runway.landed",
                            "runway.vacated"
                        ]:
                            # Process aircraft.created immediately (don't queue) to prevent drifting
                            if event_type == "aircraft.created":
                                logger.info(f"Received aircraft.created event - processing immediately")
                                asyncio.create_task(self.process_event(event_data))
                            else:
                                await self.event_queue.put(event_data)
                                logger.debug(f"Queued event: {event_type}")
                    except json.JSONDecodeError as e:
                        logger.error(f"Failed to parse event message: {e}")
                    except Exception as e:
                        logger.error(f"Error processing event: {e}")
        
        except asyncio.CancelledError:
            logger.info("Event subscription cancelled")
        finally:
            await pubsub.unsubscribe(self.redis_channel)
            await pubsub.close()
    
    async def process_event(self, event_data: Dict[str, Any]):
        """
        Process a single event and trigger LLM decision.
        
        Args:
            event_data: Event data from Redis
        """
        event_type = event_data.get("type")
        data = event_data.get("data", {})
        
        # Handle different event data structures
        if event_type == "aircraft.created":
            # aircraft.created has aircraft object in data
            aircraft = data.get("aircraft", {})
            aircraft_id = aircraft.get("id")
            flight_type = aircraft.get("flight_type")
            
            # Only process ARRIVAL aircraft
            if flight_type != "ARRIVAL":
                logger.debug(f"Skipping {event_type} for non-arrival aircraft {aircraft_id}")
                return
        else:
            # Other events have aircraft_id directly in data
            aircraft_id = data.get("aircraft_id")
        
        if not aircraft_id:
            logger.warning(f"Event {event_type} missing aircraft_id")
            return
        
        try:
            # Build context
            context = await self.context_builder.build_aircraft_context(aircraft_id, event_type)
            if not context:
                logger.warning(f"Failed to build context for aircraft {aircraft_id}")
                return
            
            # Determine which LLM to call
            if event_type in ["aircraft.created", "zone.boundary_crossed", "clearance.completed"]:
                # Air LLM - also trigger on aircraft creation to get initial clearance
                logger.info(f"Calling Air LLM for aircraft {aircraft_id} (event: {event_type})")
                decision = await self.air_llm.generate_decision(context)
            elif event_type in ["runway.landed", "runway.vacated"]:
                # Ground LLM
                logger.info(f"Calling Ground LLM for aircraft {aircraft_id} (event: {event_type})")
                decision = await self.ground_llm.generate_decision(context)
            else:
                logger.warning(f"Unknown event type: {event_type}")
                return
            
            # Apply decision
            success = await self.decision_router.apply_decision(decision)
            if success:
                logger.info(f"Applied {decision.get('clearance_type')} for aircraft {aircraft_id}")
            else:
                logger.error(f"Failed to apply decision for aircraft {aircraft_id}")
        
        except Exception as e:
            logger.error(f"Error processing event {event_type} for aircraft {aircraft_id}: {e}")
    
    async def event_processor(self):
        """Background task that processes events from queue."""
        logger.info("Event processor started")
        
        try:
            while self.running:
                try:
                    # Wait for event with timeout
                    event_data = await asyncio.wait_for(
                        self.event_queue.get(),
                        timeout=1.0
                    )
                    
                    # Process event in background (non-blocking)
                    asyncio.create_task(self.process_event(event_data))
                    
                except asyncio.TimeoutError:
                    continue
                except Exception as e:
                    logger.error(f"Error in event processor: {e}")
        
        except asyncio.CancelledError:
            logger.info("Event processor cancelled")
    
    async def periodic_aircraft_check(self):
        """
        Periodically check for aircraft without clearances and process them.
        Runs every 30 seconds to catch any aircraft that might have been missed.
        """
        while self.running:
            try:
                await asyncio.sleep(30)  # Check every 30 seconds
                if self.running:
                    await self.process_existing_aircraft()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in periodic aircraft check: {e}")
    
    async def process_existing_aircraft(self):
        """
        Process all existing active aircraft that don't have active clearances.
        This ensures aircraft get LLM guidance immediately on startup.
        """
        try:
            async with self.db_pool.acquire() as conn:
                # Check if clearances table exists
                table_check = await conn.fetchval("""
                    SELECT EXISTS (
                        SELECT FROM information_schema.tables 
                        WHERE table_schema = 'public' 
                        AND table_name = 'clearances'
                    )
                """)
                
                if table_check:
                    # Find all active ARRIVAL aircraft without active clearances
                    query = """
                        SELECT DISTINCT ai.id, ai.callsign, ai.flight_type, ai.created_at
                        FROM aircraft_instances ai
                        LEFT JOIN clearances c ON ai.id = c.aircraft_id AND c.status = 'ACTIVE'
                        WHERE ai.status = 'active'
                          AND ai.flight_type = 'ARRIVAL'
                          AND ai.controller = 'ENGINE'
                          AND c.id IS NULL
                        ORDER BY ai.created_at DESC
                        LIMIT 50
                    """
                else:
                    # Clearances table doesn't exist - process all active ARRIVAL aircraft without targets
                    query = """
                        SELECT ai.id, ai.callsign, ai.flight_type, ai.created_at
                        FROM aircraft_instances ai
                        WHERE ai.status = 'active'
                          AND ai.flight_type = 'ARRIVAL'
                          AND ai.controller = 'ENGINE'
                          AND (ai.target_altitude_ft IS NULL 
                               AND ai.target_speed_kts IS NULL 
                               AND ai.target_heading_deg IS NULL)
                        ORDER BY ai.created_at DESC
                        LIMIT 50
                    """
                
                rows = await conn.fetch(query)
                
                if rows:
                    logger.info(f"Found {len(rows)} active aircraft without clearances - processing immediately...")
                    for row in rows:
                        aircraft_id = row["id"]
                        callsign = row["callsign"]
                        logger.info(f"Processing existing aircraft {callsign} (ID: {aircraft_id})")
                        
                        # Create synthetic event to trigger LLM
                        event_data = {
                            "type": "aircraft.created",
                            "timestamp": datetime.utcnow().isoformat() + "Z",
                            "data": {
                                "aircraft": {
                                    "id": aircraft_id,
                                    "callsign": callsign,
                                    "flight_type": "ARRIVAL"
                                }
                            }
                        }
                        
                        # Process immediately (don't queue)
                        await self.process_event(event_data)
                        
                        # Small delay to avoid overwhelming the system
                        await asyncio.sleep(0.5)
                else:
                    logger.info("No active aircraft without clearances found")
        except Exception as e:
            logger.error(f"Error processing existing aircraft: {e}")
    
    async def run(self):
        """Run the dispatcher main loop."""
        await self.initialize()
        
        self.running = True
        
        # Process existing aircraft immediately (before starting event loop)
        logger.info("Checking for existing aircraft without clearances...")
        await self.process_existing_aircraft()
        
        # Start event subscription and processing tasks
        subscribe_task = asyncio.create_task(self.subscribe_to_events())
        processor_task = asyncio.create_task(self.event_processor())
        
        # Start periodic check for aircraft without clearances (every 30 seconds)
        periodic_check_task = asyncio.create_task(self.periodic_aircraft_check())
        
        logger.info("LLM Dispatcher running...")
        logger.info("Listening for events: aircraft.created, zone.boundary_crossed, clearance.completed, runway.landed, runway.vacated")
        
        try:
            # Run until cancelled
            await asyncio.gather(subscribe_task, processor_task, periodic_check_task)
        except KeyboardInterrupt:
            logger.info("\nKeyboard interrupt received")
        finally:
            subscribe_task.cancel()
            processor_task.cancel()
            periodic_check_task.cancel()
            
            try:
                await asyncio.gather(subscribe_task, processor_task, periodic_check_task, return_exceptions=True)
            except Exception:
                pass
            
            await self.shutdown()

