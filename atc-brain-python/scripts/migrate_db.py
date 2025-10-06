#!/usr/bin/env python3
"""
Database migration script to add engine control fields to aircraft_instances table.
Run this before starting the kinematics engine.
"""

import asyncio
import asyncpg
import os
from dotenv import load_dotenv

load_dotenv()

DB_CONFIG = {
    "host": os.getenv("DB_HOST", "localhost"),
    "port": int(os.getenv("DB_PORT", "5432")),
    "database": os.getenv("DB_NAME", "atc_system"),
    "user": os.getenv("DB_USER", "postgres"),
    "password": os.getenv("DB_PASSWORD", "password"),
}


async def migrate():
    """Apply database migration to add engine control fields."""
    print("🔧 Connecting to database...")
    conn = await asyncpg.connect(**DB_CONFIG)
    
    try:
        print("📝 Applying migration: Adding engine control fields...")
        
        # Add new columns for engine control
        await conn.execute("""
            ALTER TABLE aircraft_instances
            ADD COLUMN IF NOT EXISTS controller VARCHAR(20) DEFAULT 'ENGINE',
            ADD COLUMN IF NOT EXISTS target_speed_kts FLOAT,
            ADD COLUMN IF NOT EXISTS target_heading_deg FLOAT,
            ADD COLUMN IF NOT EXISTS target_altitude_ft FLOAT,
            ADD COLUMN IF NOT EXISTS vertical_speed_fpm FLOAT DEFAULT 0,
            ADD COLUMN IF NOT EXISTS flight_type VARCHAR(10),
            ADD COLUMN IF NOT EXISTS phase VARCHAR(20),
            ADD COLUMN IF NOT EXISTS last_event_fired VARCHAR(50);
        """)
        
        print("✅ Migration completed successfully!")
        
        # Verify the migration
        columns = await conn.fetch("""
            SELECT column_name, data_type 
            FROM information_schema.columns 
            WHERE table_name = 'aircraft_instances'
            AND column_name IN (
                'controller', 'target_speed_kts', 'target_heading_deg',
                'target_altitude_ft', 'vertical_speed_fpm', 'flight_type',
                'phase', 'last_event_fired'
            )
            ORDER BY column_name;
        """)
        
        print("\n📊 Verified columns:")
        for col in columns:
            print(f"  - {col['column_name']}: {col['data_type']}")
        
    except Exception as e:
        print(f"❌ Migration failed: {e}")
        raise
    finally:
        await conn.close()
        print("\n🔌 Database connection closed")


if __name__ == "__main__":
    asyncio.run(migrate())

