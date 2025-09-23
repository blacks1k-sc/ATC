"""
Uniqueness registries for aircraft data generation.
"""

from typing import Set


class UniquenessRegistry:
    """Registry to ensure uniqueness of generated values."""
    
    def __init__(self):
        self.registrations: Set[str] = set()
        self.icao24_addresses: Set[str] = set()
        self.callsigns: Set[str] = set()
        self.squawks: Set[str] = set()
    
    def add_registration(self, registration: str) -> bool:
        """Add a registration and return True if it was unique."""
        if registration in self.registrations:
            return False
        self.registrations.add(registration)
        return True
    
    def add_icao24(self, icao24: str) -> bool:
        """Add an ICAO24 address and return True if it was unique."""
        if icao24 in self.icao24_addresses:
            return False
        self.icao24_addresses.add(icao24)
        return True
    
    def add_callsign(self, callsign: str) -> bool:
        """Add a callsign and return True if it was unique."""
        if callsign in self.callsigns:
            return False
        self.callsigns.add(callsign)
        return True
    
    def add_squawk(self, squawk: str) -> bool:
        """Add a squawk code and return True if it was unique."""
        if squawk in self.squawks:
            return False
        self.squawks.add(squawk)
        return True
    
    def is_registration_unique(self, registration: str) -> bool:
        """Check if a registration is unique."""
        return registration not in self.registrations
    
    def is_icao24_unique(self, icao24: str) -> bool:
        """Check if an ICAO24 address is unique."""
        return icao24 not in self.icao24_addresses
    
    def is_callsign_unique(self, callsign: str) -> bool:
        """Check if a callsign is unique."""
        return callsign not in self.callsigns
    
    def is_squawk_unique(self, squawk: str) -> bool:
        """Check if a squawk code is unique."""
        return squawk not in self.squawks
    
    def clear(self):
        """Clear all registries."""
        self.registrations.clear()
        self.icao24_addresses.clear()
        self.callsigns.clear()
        self.squawks.clear()
    
    def get_stats(self) -> dict:
        """Get registry statistics."""
        return {
            "registrations": len(self.registrations),
            "icao24_addresses": len(self.icao24_addresses),
            "callsigns": len(self.callsigns),
            "squawks": len(self.squawks)
        }
