#!/usr/bin/env python3
"""
Database migration v2 — adds resource assignment columns and clearances table.
Run once before starting the new planning cycle.
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
    print("Connecting to database...")
    conn = await asyncpg.connect(**DB_CONFIG)

    try:
        print("Applying migration v2...")

        # Add resource-assignment columns to aircraft_instances
        await conn.execute("""
            ALTER TABLE aircraft_instances
            ADD COLUMN IF NOT EXISTS runway_assigned VARCHAR(10),
            ADD COLUMN IF NOT EXISTS gate_assigned   VARCHAR(10),
            ADD COLUMN IF NOT EXISTS clearance_seq   INTEGER DEFAULT 0;
        """)

        # Create clearances table
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS clearances (
                id                  SERIAL PRIMARY KEY,
                aircraft_id         INTEGER REFERENCES aircraft_instances(id),
                issued_at           TIMESTAMP DEFAULT NOW(),
                cleared_altitude_ft INTEGER,
                cleared_speed_kts   INTEGER,
                cleared_heading_deg INTEGER,
                cleared_runway      VARCHAR(10),
                cleared_gate        VARCHAR(10),
                status              VARCHAR(20) DEFAULT 'ACTIVE'
            );
        """)

        print("Migration v2 completed successfully.")

        # Verify
        cols = await conn.fetch("""
            SELECT column_name, data_type
            FROM information_schema.columns
            WHERE table_name = 'aircraft_instances'
              AND column_name IN ('runway_assigned', 'gate_assigned', 'clearance_seq')
            ORDER BY column_name;
        """)
        print("\nVerified aircraft_instances columns:")
        for c in cols:
            print(f"  - {c['column_name']}: {c['data_type']}")

        tbl = await conn.fetchval("""
            SELECT COUNT(*) FROM information_schema.tables
            WHERE table_name = 'clearances';
        """)
        print(f"\nclearances table exists: {bool(tbl)}")

    except Exception as e:
        print(f"Migration failed: {e}")
        raise
    finally:
        await conn.close()
        print("\nDatabase connection closed.")


if __name__ == "__main__":
    asyncio.run(migrate())
