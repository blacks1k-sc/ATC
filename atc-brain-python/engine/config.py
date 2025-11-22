"""
Configuration module for the kinematics engine.
Controls operational modes and performance tuning.
"""

import os
from dotenv import load_dotenv

load_dotenv()


class EngineConfig:
    """Engine configuration with DEV/PROD mode support."""
    
    # ========== Mode Configuration ==========
    DEV_MODE = os.getenv("ENGINE_MODE", "PROD").upper() == "DEV"
    PROD_MODE = not DEV_MODE
    
    # ========== Debug Configuration ==========
    DEBUG_PRINTS = os.getenv("DEBUG_PRINTS", "false").lower() == "true"
    
    # ========== Worker Configuration ==========
    # Database worker
    DB_BATCH_INTERVAL_SEC = 1.0  # Batch DB writes every 1 second
    DB_BATCH_SIZE = 100  # Maximum batch size for single executemany call
    
    # Redis worker
    REDIS_BATCH_INTERVAL_SEC = 0.05 if PROD_MODE else 0.1  # 50ms in prod, 100ms in dev
    REDIS_BATCH_SIZE = 20 if PROD_MODE else 10  # Smaller batches in dev
    
    # Telemetry worker
    TELEMETRY_INTERVAL_SEC = 10.0 if PROD_MODE else 30.0  # 10s in prod, 30s in dev
    TELEMETRY_BATCH_SIZE = 100
    
    # ========== Queue Configuration ==========
    IO_QUEUE_MAX_SIZE = 1000  # Max snapshots in queue before blocking
    
    # ========== Logging Configuration ==========
    LOG_LEVEL = "INFO" if PROD_MODE else "DEBUG"
    LOG_TICK_DURATION = True  # Log tick duration
    LOG_WORKER_STATS = DEV_MODE  # Log worker statistics in dev mode
    
    # ========== Telemetry Configuration ==========
    TELEMETRY_DIR = os.getenv("TELEMETRY_DIR", "./telemetry/phaseA")
    
    # ========== Database Configuration ==========
    DB_POOL_MIN_SIZE = 5
    DB_POOL_MAX_SIZE = 20 if PROD_MODE else 10
    
    # ========== Redis Configuration ==========
    REDIS_POOL_MIN_SIZE = 5
    REDIS_POOL_MAX_SIZE = 20 if PROD_MODE else 10
    
    # ========== Performance Tuning ==========
    # In dev mode, reduce frequency of certain operations
    DB_UPDATE_FREQUENCY = 1 if PROD_MODE else 2  # Every N ticks
    EVENT_LOG_FREQUENCY = 1 if PROD_MODE else 5  # Every N ticks
    
    @classmethod
    def print_config(cls):
        """Print current configuration."""
        mode = "DEVELOPMENT" if cls.DEV_MODE else "PRODUCTION"
        print(f"\nEngine Configuration ({mode} MODE)")
        print(f"   DB Batch Interval: {cls.DB_BATCH_INTERVAL_SEC}s")
        print(f"   Redis Batch Interval: {cls.REDIS_BATCH_INTERVAL_SEC*1000:.0f}ms")
        print(f"   Telemetry Interval: {cls.TELEMETRY_INTERVAL_SEC}s")
        print(f"   Queue Max Size: {cls.IO_QUEUE_MAX_SIZE}")
        print(f"   Log Level: {cls.LOG_LEVEL}")
        print()


# Create singleton instance
config = EngineConfig()

