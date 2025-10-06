"""
Aircraft state management with database integration.
Handles querying, caching, and updating aircraft state.
"""

import asyncpg
import os
from typing import List, Dict, Any, Optional
from dotenv import load_dotenv

load_dotenv()


class StateManager:
    """Manages aircraft state with PostgreSQL backend."""
    
    def __init__(self):
        self.pool: Optional[asyncpg.Pool] = None
        self.cache: Dict[int, Dict[str, Any]] = {}
        
        self.db_config = {
            "host": os.getenv("DB_HOST", "localhost"),
            "port": int(os.getenv("DB_PORT", "5432")),
            "database": os.getenv("DB_NAME", "atc_system"),
            "user": os.getenv("DB_USER", "postgres"),
            "password": os.getenv("DB_PASSWORD", "password"),
            "min_size": 5,
            "max_size": int(os.getenv("DB_POOL_SIZE", "20")),
        }
    
    async def connect(self):
        """Initialize database connection pool."""
        if self.pool is None:
            try:
                self.pool = await asyncpg.create_pool(**self.db_config)
                print("✅ StateManager: Database connection established")
            except Exception as e:
                print(f"❌ StateManager: Failed to connect to database: {e}")
                raise
    
    async def disconnect(self):
        """Close database connection pool."""
        if self.pool:
            await self.pool.close()
            self.pool = None
            print("🔌 StateManager: Database connection closed")
    
    async def get_active_arrivals(self, controller: str = "ENGINE") -> List[Dict[str, Any]]:
        """
        Fetch all active arrival aircraft controlled by specified controller.
        
        Args:
            controller: Controller name (default "ENGINE")
        
        Returns:
            List of aircraft dictionaries
        """
        if not self.pool:
            await self.connect()
        
        query = """
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
            WHERE ai.status = 'active'
              AND ai.controller = $1
              AND ai.flight_type = 'ARRIVAL'
            ORDER BY ai.created_at DESC
            LIMIT 100;
        """
        
        try:
            async with self.pool.acquire() as conn:
                rows = await conn.fetch(query, controller)
                
                aircraft_list = []
                for row in rows:
                    aircraft = dict(row)
                    
                    # Parse JSONB fields
                    if isinstance(aircraft.get("position"), str):
                        import json
                        aircraft["position"] = json.loads(aircraft["position"])
                    
                    if isinstance(aircraft.get("flight_plan"), str):
                        import json
                        aircraft["flight_plan"] = json.loads(aircraft["flight_plan"])
                    
                    aircraft_list.append(aircraft)
                    
                    # Update cache
                    self.cache[aircraft["id"]] = aircraft
                
                return aircraft_list
                
        except Exception as e:
            print(f"❌ StateManager: Error fetching aircraft: {e}")
            return []
    
    async def update_aircraft_state(self, aircraft_id: int, updates: Dict[str, Any]) -> bool:
        """
        Update aircraft state in database.
        
        Args:
            aircraft_id: Aircraft instance ID
            updates: Dictionary of fields to update
        
        Returns:
            True if successful, False otherwise
        """
        if not self.pool:
            await self.connect()
        
        # Build dynamic UPDATE query
        set_clauses = []
        values = []
        param_idx = 1
        
        for key, value in updates.items():
            if key == "position":
                import json
                set_clauses.append(f"position = ${param_idx}::jsonb")
                values.append(json.dumps(value))
            elif key in ["target_speed_kts", "target_heading_deg", "target_altitude_ft",
                        "vertical_speed_fpm", "phase", "last_event_fired", "controller"]:
                set_clauses.append(f"{key} = ${param_idx}")
                values.append(value)
            param_idx += 1
        
        if not set_clauses:
            return True  # Nothing to update
        
        # Add updated_at timestamp
        set_clauses.append(f"updated_at = NOW()")
        
        # Add aircraft_id as final parameter
        values.append(aircraft_id)
        
        query = f"""
            UPDATE aircraft_instances
            SET {', '.join(set_clauses)}
            WHERE id = ${param_idx}
        """
        
        try:
            async with self.pool.acquire() as conn:
                await conn.execute(query, *values)
                
                # Update cache
                if aircraft_id in self.cache:
                    self.cache[aircraft_id].update(updates)
                
                return True
                
        except Exception as e:
            print(f"❌ StateManager: Error updating aircraft {aircraft_id}: {e}")
            return False
    
    async def mark_touchdown(self, aircraft_id: int) -> bool:
        """
        Mark aircraft as landed (inactive).
        
        Args:
            aircraft_id: Aircraft instance ID
        
        Returns:
            True if successful
        """
        return await self.update_aircraft_state(aircraft_id, {
            "status": "landed",
            "controller": "GROUND",
            "phase": "TOUCHDOWN"
        })
    
    async def handoff_to_atc(self, aircraft_id: int, new_controller: str) -> bool:
        """
        Transfer control to another controller.
        
        Args:
            aircraft_id: Aircraft instance ID
            new_controller: New controller name (e.g., "ENTRY_ATC")
        
        Returns:
            True if successful
        """
        return await self.update_aircraft_state(aircraft_id, {
            "controller": new_controller
        })
    
    def get_cached_aircraft(self, aircraft_id: int) -> Optional[Dict[str, Any]]:
        """
        Get aircraft from cache.
        
        Args:
            aircraft_id: Aircraft instance ID
        
        Returns:
            Aircraft dict or None
        """
        return self.cache.get(aircraft_id)
    
    def clear_cache(self):
        """Clear the aircraft cache."""
        self.cache.clear()
    
    async def create_event(self, event_data: Dict[str, Any]) -> bool:
        """
        Create a new event in the database.
        
        Args:
            event_data: Event data dictionary with keys:
                - level: 'DEBUG' | 'INFO' | 'WARN' | 'ERROR' | 'FATAL'
                - type: Event type string
                - message: Event message
                - details: Optional details dict
                - aircraft_id: Optional aircraft ID
                - sector: Optional sector string
                - frequency: Optional frequency string
                - direction: Optional direction ('TX' | 'RX' | 'CPDLC' | 'XFER' | 'SYS')
        
        Returns:
            True if successful, False otherwise
        """
        if not self.pool:
            await self.connect()
        
        
        query = """
            INSERT INTO events (level, type, message, details, aircraft_id, sector, frequency, direction)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
            RETURNING id
        """
        
        try:
            async with self.pool.acquire() as conn:
                # Convert details to JSON string if provided
                details_json = None
                if event_data.get("details"):
                    import json
                    details_json = json.dumps(event_data["details"])
                
                result = await conn.fetchrow(query, 
                    event_data.get("level", "INFO"),
                    event_data.get("type", "system.event"),
                    event_data.get("message", ""),
                    details_json,
                    event_data.get("aircraft_id"),
                    event_data.get("sector"),
                    event_data.get("frequency"),
                    event_data.get("direction", "SYS")
                )
                
                return result is not None
                
        except Exception as e:
            print(f"❌ StateManager: Error creating event: {e}")
            return False

