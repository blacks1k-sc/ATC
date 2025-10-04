"""
Database connection manager for PostgreSQL
"""

import asyncio
import logging
from typing import Optional, Dict, Any, List
import asyncpg
from config.settings import Settings

logger = logging.getLogger(__name__)

class DatabaseManager:
    """Manages PostgreSQL database connections"""
    
    def __init__(self, settings: Settings):
        self.settings = settings
        self.pool: Optional[asyncpg.Pool] = None
        self._connection = None
    
    async def connect(self):
        """Create database connection pool"""
        try:
            self.pool = await asyncpg.create_pool(
                self.settings.database_url,
                min_size=1,
                max_size=10,
                command_timeout=60
            )
            logger.info("Database connection pool created")
        except Exception as e:
            logger.error(f"Failed to create database pool: {e}")
            raise
    
    async def disconnect(self):
        """Close database connection pool"""
        if self.pool:
            await self.pool.close()
            logger.info("Database connection pool closed")
    
    async def health_check(self) -> bool:
        """Check database connection health"""
        try:
            if not self.pool:
                return False
            
            async with self.pool.acquire() as conn:
                await conn.fetchval("SELECT 1")
            return True
        except Exception as e:
            logger.error(f"Database health check failed: {e}")
            return False
    
    async def fetch_one(self, query: str, *args) -> Optional[Dict[str, Any]]:
        """Fetch a single row from database"""
        try:
            async with self.pool.acquire() as conn:
                row = await conn.fetchrow(query, *args)
                return dict(row) if row else None
        except Exception as e:
            logger.error(f"Database fetch_one failed: {e}")
            raise
    
    async def fetch_all(self, query: str, *args) -> List[Dict[str, Any]]:
        """Fetch all rows from database"""
        try:
            async with self.pool.acquire() as conn:
                rows = await conn.fetch(query, *args)
                return [dict(row) for row in rows]
        except Exception as e:
            logger.error(f"Database fetch_all failed: {e}")
            raise
    
    async def execute(self, query: str, *args) -> str:
        """Execute a query and return the result"""
        try:
            async with self.pool.acquire() as conn:
                result = await conn.execute(query, *args)
                return result
        except Exception as e:
            logger.error(f"Database execute failed: {e}")
            raise
    
    async def get_active_aircraft(self) -> List[Dict[str, Any]]:
        """Get all active aircraft from database"""
        query = """
            SELECT 
                ai.*,
                at.manufacturer,
                at.model,
                al.name as airline_name,
                al.icao_code as airline_icao
            FROM aircraft_instances ai
            LEFT JOIN aircraft_types at ON ai.aircraft_type_id = at.id
            LEFT JOIN airlines al ON ai.airline_id = al.id
            WHERE ai.flight_phase != 'COMPLETED'
            ORDER BY ai.spawn_time DESC
        """
        return await self.fetch_all(query)
    
    async def get_waypoints_by_airport(self, airport_icao: str) -> List[Dict[str, Any]]:
        """Get waypoints for a specific airport"""
        query = """
            SELECT * FROM waypoints 
            WHERE airport_icao = $1 
            ORDER BY name
        """
        return await self.fetch_all(query, airport_icao)
    
    async def get_procedures_by_airport(self, airport_icao: str) -> List[Dict[str, Any]]:
        """Get procedures (SID/STAR) for a specific airport"""
        query = """
            SELECT * FROM procedures 
            WHERE airport_icao = $1 
            ORDER BY type, name
        """
        return await self.fetch_all(query, airport_icao)
    
    async def get_runways_by_airport(self, airport_icao: str) -> List[Dict[str, Any]]:
        """Get runways for a specific airport"""
        query = """
            SELECT * FROM runways 
            WHERE airport_icao = $1 
            ORDER BY runway_number
        """
        return await self.fetch_all(query, airport_icao)
    
    async def update_aircraft_position(self, aircraft_id: int, lat: float, lon: float, 
                                     altitude: int, heading: float, speed: float):
        """Update aircraft position in database"""
        query = """
            UPDATE aircraft_instances 
            SET 
                lat = $2,
                lon = $3,
                altitude = $4,
                heading = $5,
                speed = $6,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = $1
        """
        await self.execute(query, aircraft_id, lat, lon, altitude, heading, speed)
    
    async def update_aircraft_phase(self, aircraft_id: int, flight_phase: str):
        """Update aircraft flight phase"""
        query = """
            UPDATE aircraft_instances 
            SET 
                flight_phase = $2,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = $1
        """
        await self.execute(query, aircraft_id, flight_phase)
    
    async def get_aircraft_by_id(self, aircraft_id: int) -> Optional[Dict[str, Any]]:
        """Get specific aircraft by ID"""
        query = """
            SELECT 
                ai.*,
                at.manufacturer,
                at.model,
                al.name as airline_name,
                al.icao_code as airline_icao
            FROM aircraft_instances ai
            LEFT JOIN aircraft_types at ON ai.aircraft_type_id = at.id
            LEFT JOIN airlines al ON ai.airline_id = al.id
            WHERE ai.id = $1
        """
        return await self.fetch_one(query, aircraft_id)
