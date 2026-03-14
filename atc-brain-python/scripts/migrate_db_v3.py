"""Migration v3: Add waypoint_sequence JSONB column to aircraft_instances."""

import asyncio
import asyncpg
import os
from dotenv import load_dotenv

load_dotenv()


async def migrate():
    conn = await asyncpg.connect(
        host=os.getenv("DB_HOST", "localhost"),
        port=int(os.getenv("DB_PORT", "5432")),
        database=os.getenv("DB_NAME", "atc_system"),
        user=os.getenv("DB_USER", "postgres"),
        password=os.getenv("DB_PASSWORD", "password"),
    )
    try:
        print("Applying migration v3...")
        await conn.execute("""
            ALTER TABLE aircraft_instances
            ADD COLUMN IF NOT EXISTS waypoint_sequence JSONB DEFAULT '[]'::jsonb;
        """)
        print("  Added waypoint_sequence JSONB column")
        print("Migration v3 complete.")
    finally:
        await conn.close()


if __name__ == "__main__":
    asyncio.run(migrate())
