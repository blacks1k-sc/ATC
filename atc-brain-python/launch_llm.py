#!/usr/bin/env python3
"""
Launch script for the ATC two-tier planning controller.

Components started:
  - ResourceRegistry (in-memory, event-driven)
  - RegistryEventSubscriber (Redis → registry updates)
  - RuleEngine (deterministic tier-1 decisions)
  - QwenClient (Ollama qwen2.5:7b, tier-2 LLM)
  - PlanningCycle (runs every 10 seconds)

Requirements:
  - Ollama running with qwen2.5:7b (ollama pull qwen2.5:7b)
  - PostgreSQL database running (migrate_db_v2.py applied)
  - Redis server running
  - Engine running and publishing events to atc:events

Usage:
    python launch_llm.py
"""

import asyncio
import logging
import sys
import os

import asyncpg
import redis.asyncio as redis

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from dotenv import load_dotenv

load_dotenv()

from llm.resource_registry import ResourceRegistry, RegistryEventSubscriber
from llm.rule_engine import RuleEngine
from llm.qwen_client import QwenClient
from llm.planning_cycle import PlanningCycle


def setup_logging():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler("llm_dispatcher.log"),
        ],
    )
    logging.getLogger("asyncio").setLevel(logging.WARNING)
    logging.getLogger("asyncpg").setLevel(logging.WARNING)
    logging.getLogger("aiohttp").setLevel(logging.WARNING)


DB_CONFIG = {
    "host": os.getenv("DB_HOST", "localhost"),
    "port": int(os.getenv("DB_PORT", "5432")),
    "database": os.getenv("DB_NAME", "atc_system"),
    "user": os.getenv("DB_USER", "postgres"),
    "password": os.getenv("DB_PASSWORD", "password"),
    "min_size": 2,
    "max_size": 10,
}

REDIS_CONFIG = {
    "host": os.getenv("REDIS_HOST", "localhost"),
    "port": int(os.getenv("REDIS_PORT", "6379")),
    "password": os.getenv("REDIS_PASSWORD") or None,
    "db": 0,
    "decode_responses": True,
}


async def main():
    print("=" * 60)
    print("ATC Planning Controller — Qwen2.5-7B + Rule Engine")
    print("=" * 60)

    setup_logging()
    logger = logging.getLogger(__name__)
    logger.info("Initializing components...")

    # --- Database pool ---
    db_pool = await asyncpg.create_pool(**DB_CONFIG)
    logger.info("DB pool ready")

    # --- Redis client ---
    redis_client = redis.Redis(**REDIS_CONFIG)
    await redis_client.ping()
    logger.info("Redis connected")

    # --- Core components ---
    registry = ResourceRegistry()
    rule_engine = RuleEngine()
    qwen = QwenClient()
    await qwen.initialize()

    # --- Wire event subscriber ---
    event_sub = RegistryEventSubscriber(registry, redis_client)

    # --- Planning cycle ---
    cycle = PlanningCycle(db_pool, registry, rule_engine, qwen)

    logger.info("Starting tasks...")
    tasks = [
        asyncio.create_task(event_sub.run(), name="registry-subscriber"),
        asyncio.create_task(cycle.run(), name="planning-cycle"),
    ]

    try:
        await asyncio.gather(*tasks)
    except KeyboardInterrupt:
        logger.info("Shutdown requested")
    except Exception as e:
        logger.error("Fatal error: %s", e, exc_info=True)
        sys.exit(1)
    finally:
        for t in tasks:
            t.cancel()
        await qwen.close()
        await db_pool.close()
        await redis_client.close()
        logger.info("Shutdown complete")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nExiting...")
        sys.exit(0)
