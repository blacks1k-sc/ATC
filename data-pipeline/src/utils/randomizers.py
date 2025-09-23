"""
Random data generators for aircraft records.
"""

import random
import string
from typing import List, Literal, Optional
from ..models import Airline, TypeSpec
from .registries import UniquenessRegistry


class AircraftRandomizer:
    """Random data generator for aircraft records."""
    
    def __init__(self, registry: UniquenessRegistry, seed: Optional[int] = None):
        self.registry = registry
        if seed is not None:
            random.seed(seed)
    
    def random_icao24(self) -> str:
        """Generate a random 24-bit ICAO address in hex."""
        while True:
            # Generate random 24-bit value
            icao24 = f"{random.randint(0, 0xFFFFFF):06X}"
            if self.registry.add_icao24(icao24):
                return icao24
    
    def random_registration(self, country: str = "CA") -> str:
        """Generate a random aircraft registration."""
        country_prefixes = {
            "CA": "C-",
            "US": "N",
            "GB": "G-",
            "DE": "D-",
            "FR": "F-",
            "IT": "I-",
            "ES": "EC-",
            "NL": "PH-",
            "CH": "HB-",
            "AT": "OE-",
            "SE": "SE-",
            "NO": "LN-",
            "DK": "OY-",
            "FI": "OH-",
            "IE": "EI-",
            "JP": "JA",
            "KR": "HL",
            "CN": "B-",
            "HK": "B-H",
            "SG": "9V-",
            "TH": "HS-",
            "AE": "A6-",
            "QA": "A7-",
            "TR": "TC-",
            "MX": "XA-",
            "CL": "CC-",
            "CO": "HK-",
            "PA": "HP-",
            "ET": "ET-",
            "ZA": "ZS-",
            "KE": "5Y-",
            "AU": "VH-",
            "NZ": "ZK-",
        }
        
        prefix = country_prefixes.get(country, "C-")
        
        while True:
            if country in ["US", "JP", "KR", "AU", "NZ"]:
                # US format: N123AB, JP format: JA123A, etc.
                suffix = "".join(random.choices(string.ascii_uppercase, k=2))
                number = f"{random.randint(1, 999):03d}"
                registration = f"{prefix}{number}{suffix}"
            else:
                # Most other countries: C-ABCD, G-ABCD, etc.
                suffix = "".join(random.choices(string.ascii_uppercase, k=3))
                registration = f"{prefix}{suffix}"
            
            if self.registry.add_registration(registration):
                return registration
    
    def random_callsign(self, airline: Airline) -> str:
        """Generate a random callsign for an airline."""
        while True:
            # Generate flight number
            flight_number = f"{random.randint(1, 9999):04d}"
            callsign = f"{airline.icao}{flight_number}"
            
            if self.registry.add_callsign(callsign):
                return callsign
    
    def random_flight_number(self) -> str:
        """Generate a random flight number."""
        return f"{random.randint(1, 9999):04d}"
    
    def random_squawk(self) -> str:
        """Generate a random squawk code."""
        while True:
            # Squawk codes are 4 digits, 0-7 for each digit
            squawk = f"{random.randint(0, 7)}{random.randint(0, 7)}{random.randint(0, 7)}{random.randint(0, 7)}"
            
            if self.registry.add_squawk(squawk):
                return squawk
    
    def random_aircraft_type_for_airline(self, airline: Airline, available_types: List[TypeSpec]) -> TypeSpec:
        """Select a random aircraft type appropriate for the airline."""
        # Define airline-type mappings for more realistic assignments
        # This is a subset of known mappings - for global data, we'll be more flexible
        airline_type_preferences = {
            # Major carriers - widebody and narrowbody
            "ACA": ["A20N", "A21N", "A319", "A320", "A321", "A332", "A333", "A359", "B38M", "B738", "B739", "B77W", "B77L", "B788", "B789"],
            "UAL": ["A20N", "A21N", "A319", "A320", "A321", "A332", "A333", "A359", "B38M", "B738", "B739", "B77W", "B77L", "B788", "B789", "B744", "B748"],
            "AAL": ["A20N", "A21N", "A319", "A320", "A321", "A332", "A333", "A359", "B38M", "B738", "B739", "B77W", "B77L", "B788", "B789", "B744", "B748"],
            "DAL": ["A20N", "A21N", "A319", "A320", "A321", "A332", "A333", "A359", "B38M", "B738", "B739", "B77W", "B77L", "B788", "B789", "B744", "B748"],
            "BAW": ["A20N", "A21N", "A319", "A320", "A321", "A332", "A333", "A359", "A388", "B38M", "B738", "B739", "B77W", "B77L", "B788", "B789", "B744", "B748"],
            "DLH": ["A20N", "A21N", "A319", "A320", "A321", "A332", "A333", "A359", "A388", "B38M", "B738", "B739", "B77W", "B77L", "B788", "B789", "B744", "B748"],
            "AFR": ["A20N", "A21N", "A319", "A320", "A321", "A332", "A333", "A359", "A388", "B38M", "B738", "B739", "B77W", "B77L", "B788", "B789"],
            "KLM": ["A20N", "A21N", "A319", "A320", "A321", "A332", "A333", "A359", "B38M", "B738", "B739", "B77W", "B77L", "B788", "B789"],
            "JAL": ["A20N", "A21N", "A319", "A320", "A321", "A332", "A333", "A359", "A388", "B38M", "B738", "B739", "B77W", "B77L", "B788", "B789", "B744", "B748"],
            "ANA": ["A20N", "A21N", "A319", "A320", "A321", "A332", "A333", "A359", "A388", "B38M", "B738", "B739", "B77W", "B77L", "B788", "B789", "B744", "B748"],
            "UAE": ["A20N", "A21N", "A319", "A320", "A321", "A332", "A333", "A359", "A388", "B77W", "B77L", "B788", "B789", "B744", "B748"],
            "QTR": ["A20N", "A21N", "A319", "A320", "A321", "A332", "A333", "A359", "A388", "B77W", "B77L", "B788", "B789", "B744", "B748"],
            "QFA": ["A20N", "A21N", "A319", "A320", "A321", "A332", "A333", "A359", "A388", "B38M", "B738", "B739", "B77W", "B77L", "B788", "B789", "B744", "B748"],
            
            # Regional carriers - narrowbody and regional jets
            "WJA": ["B38M", "B738", "B739", "B77W", "B77L", "B788", "B789"],
            "POE": ["E170", "E175", "E190", "E195"],
            "SWA": ["B38M", "B738", "B739"],
            "JBU": ["A20N", "A21N", "A319", "A320", "A321", "E170", "E175", "E190", "E195"],
            "ASA": ["B38M", "B738", "B739", "E170", "E175", "E190", "E195"],
            "NKS": ["A20N", "A21N", "A319", "A320", "A321"],
            "FFT": ["A20N", "A21N", "A319", "A320", "A321"],
            "SKW": ["CRJ2", "CRJ7", "CRJ9", "E170", "E175", "E190", "E195"],
            "RPA": ["CRJ2", "CRJ7", "CRJ9", "E170", "E175", "E190", "E195"],
            "ASH": ["CRJ2", "CRJ7", "CRJ9", "E170", "E175", "E190", "E195"],
            "ENY": ["CRJ2", "CRJ7", "CRJ9", "E170", "E175", "E190", "E195"],
            "PDT": ["CRJ2", "CRJ7", "CRJ9", "E170", "E175", "E190", "E195"],
            "JIA": ["CRJ2", "CRJ7", "CRJ9", "E170", "E175", "E190", "E195"],
            
            # Cargo carriers
            "FDX": ["B77W", "B77L", "B788", "B789", "B744", "B748", "A332", "A333"],
            "UPS": ["B77W", "B77L", "B788", "B789", "B744", "B748", "A332", "A333"],
            "DHK": ["B77W", "B77L", "B788", "B789", "B744", "B748", "A332", "A333"],
            "CLX": ["B77W", "B77L", "B744", "B748"],
        }
        
        # Get preferred types for this airline, or use all available types
        preferred_types = airline_type_preferences.get(airline.icao, [])
        
        if preferred_types:
            # Filter available types to only those preferred by this airline
            available_preferred = [t for t in available_types if t.icao_type in preferred_types]
            if available_preferred:
                return random.choice(available_preferred)
        
        # For unknown airlines, use intelligent filtering based on airline characteristics
        # Cargo airlines tend to use widebody aircraft
        if any(keyword in airline.name.lower() for keyword in ['cargo', 'freight', 'express', 'logistics']):
            widebody_types = [t for t in available_types if t.wake in ['H', 'J']]
            if widebody_types:
                return random.choice(widebody_types)
        
        # Regional airlines tend to use smaller aircraft
        if any(keyword in airline.name.lower() for keyword in ['regional', 'express', 'connection', 'commuter']):
            small_types = [t for t in available_types if t.wake == 'L']
            if small_types:
                return random.choice(small_types)
        
        # Fallback to any available type
        return random.choice(available_types)
    
    def random_country_for_airline(self, airline: Airline) -> str:
        """Get the country code for an airline's registration."""
        country_mapping = {
            "ACA": "CA", "WJA": "CA", "POE": "CA", "TSC": "CA", "SWG": "CA", "FLE": "CA", "WSW": "CA",
            "UAL": "US", "AAL": "US", "DAL": "US", "SWA": "US", "JBU": "US", "ASA": "US", "NKS": "US", "FFT": "US", "HAL": "US",
            "SKW": "US", "RPA": "US", "ASH": "US", "ENY": "US", "PDT": "US", "JIA": "US", "FDX": "US", "UPS": "US",
            "BAW": "GB", "DLH": "DE", "AFR": "FR", "KLM": "NL", "IBE": "ES", "SWR": "CH", "AUA": "AT", "SAS": "SE",
            "FIN": "FI", "EIN": "IE", "JAL": "JP", "ANA": "JP", "KAL": "KR", "AAR": "KR", "CES": "CN", "CSN": "CN",
            "CCA": "CN", "CPA": "HK", "SIA": "SG", "THA": "TH", "UAE": "AE", "QTR": "QA", "ETD": "AE", "THY": "TR",
            "AMX": "MX", "LAN": "CL", "AVA": "CO", "CMP": "PA", "ETH": "ET", "SAA": "ZA", "KQA": "KE",
            "QFA": "AU", "VOZ": "AU", "DHK": "DE", "CLX": "LU"
        }
        
        return country_mapping.get(airline.icao, "CA")  # Default to Canada
