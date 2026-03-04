#!/usr/bin/env python3
"""
Run script for LLM Dispatcher.
Initializes Redis, PostgreSQL, and starts the dispatcher in a persistent loop.
"""

import asyncio
import logging
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from llm.llm_dispatcher import LLMDispatcher

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


async def main():
    """Main entry point."""
    logger.info("=" * 60)
    logger.info("LLM Dispatcher - Starting")
    logger.info("=" * 60)
    
    dispatcher = LLMDispatcher()
    
    try:
        await dispatcher.run()
    except KeyboardInterrupt:
        logger.info("\nShutdown requested by user")
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        raise
    finally:
        logger.info("LLM Dispatcher stopped")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("\nExiting...")
        sys.exit(0)

