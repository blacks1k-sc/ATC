"""
Ray distributed wrappers for CPU-intensive kinematics functions.
These functions execute on remote Ray cluster nodes.
"""

import ray
from typing import Dict, Any
from .kinematics import update_aircraft_state as _update_aircraft_state_local
from .constants import DT


@ray.remote
def update_aircraft_state_remote(aircraft: Dict[str, Any], dt: float = DT) -> Dict[str, Any]:
    """
    Ray remote version of update_aircraft_state.
    Executes on remote Ray cluster nodes (ASUS machine at 192.168.2.142).
    
    This function performs CPU-intensive aircraft physics simulation including:
    - Speed, heading, and altitude updates
    - Holding pattern logic
    - Approach physics
    - Position calculations
    
    Args:
        aircraft: Aircraft state dictionary containing position, speed, heading, altitude
        dt: Time step in seconds (default: 1.0s for 1 Hz updates)
    
    Returns:
        Updated aircraft state dictionary with new position and flight parameters
    """
    return _update_aircraft_state_local(aircraft, dt)


@ray.remote
def update_aircraft_batch_remote(aircraft_list: list[Dict[str, Any]], dt: float = DT) -> list[Dict[str, Any]]:
    """
    Process a batch of aircraft on a single remote worker.
    Useful for larger batches where per-aircraft overhead is significant.
    
    Args:
        aircraft_list: List of aircraft state dictionaries
        dt: Time step in seconds
    
    Returns:
        List of updated aircraft state dictionaries
    """
    return [_update_aircraft_state_local(ac, dt) for ac in aircraft_list]

