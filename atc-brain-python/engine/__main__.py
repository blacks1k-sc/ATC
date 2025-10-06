"""
Entry point for running the kinematics engine as a module.
Usage: python -m engine.core_engine
"""

import asyncio
from .core_engine import main

if __name__ == "__main__":
    asyncio.run(main())

