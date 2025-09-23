"""
Geographic utilities for aircraft positioning and routing.
"""

import random
import math
from typing import List, Tuple, Literal, Optional


class GeographicUtils:
    """Utilities for geographic calculations and route generation."""
    
    def __init__(self, seed: Optional[int] = None):
        if seed is not None:
            random.seed(seed)
    
    # Major airports with their coordinates
    AIRPORTS = {
        # North America
        "CYYZ": (43.6777, -79.6248),  # Toronto Pearson
        "KJFK": (40.6413, -73.7781),  # New York JFK
        "KLAX": (33.9425, -118.4081), # Los Angeles
        "KORD": (41.9786, -87.9048),  # Chicago O'Hare
        "KMIA": (25.7959, -80.2870),  # Miami
        "KDFW": (32.8968, -97.0380),  # Dallas/Fort Worth
        "KATL": (33.6407, -84.4277),  # Atlanta
        "KSEA": (47.4502, -122.3088), # Seattle
        "KIAH": (29.9902, -95.3368),  # Houston
        "KBOS": (42.3656, -71.0096),  # Boston
        "KPHX": (33.4342, -112.0116), # Phoenix
        "KLAS": (36.0840, -115.1537), # Las Vegas
        "KDEN": (39.8561, -104.6737), # Denver
        "KDTW": (42.2162, -83.3554),  # Detroit
        "KPHL": (39.8729, -75.2437),  # Philadelphia
        "KMSP": (44.8848, -93.2223),  # Minneapolis
        "KCLT": (35.2144, -80.9473),  # Charlotte
        "KEWR": (40.6895, -74.1745),  # Newark
        "KSLC": (40.7899, -111.9791), # Salt Lake City
        "KPDX": (45.5898, -122.5951), # Portland
        "CYVR": (49.1967, -123.1815), # Vancouver
        "CYUL": (45.4706, -73.7408),  # Montreal
        "CYYC": (51.1314, -114.0103), # Calgary
        "CYEG": (53.3097, -113.5792), # Edmonton
        "CYOW": (45.3225, -75.6692),  # Ottawa
        "CYWG": (49.9100, -97.2399),  # Winnipeg
        "CYHZ": (44.8808, -63.5086),  # Halifax
        "CYQB": (46.7911, -71.3933),  # Quebec City
        
        # Europe
        "EGLL": (51.4700, -0.4543),   # London Heathrow
        "EGKK": (51.1481, -0.1903),   # London Gatwick
        "EGLC": (51.5054, 0.0553),    # London City
        "EDDF": (50.0379, 8.5622),    # Frankfurt
        "EDDM": (48.3538, 11.7861),   # Munich
        "LFPG": (49.0097, 2.5479),    # Paris CDG
        "LFPO": (48.7233, 2.3794),    # Paris Orly
        "EHAM": (52.3105, 4.7683),    # Amsterdam
        "LEMD": (40.4839, -3.5680),   # Madrid
        "LEBL": (41.2974, 2.0833),    # Barcelona
        "LSGG": (46.2381, 6.1090),    # Geneva
        "LSZH": (47.4647, 8.5492),    # Zurich
        "LOWW": (48.1103, 16.5697),   # Vienna
        "ESSA": (59.6519, 17.9186),   # Stockholm
        "EFHK": (60.3172, 24.9633),   # Helsinki
        "EIDW": (53.4264, -6.2499),   # Dublin
        "LIRF": (41.8045, 12.2509),   # Rome Fiumicino
        "LIME": (45.6736, 9.7042),    # Milan Malpensa
        "LEJX": (41.2974, 2.0833),    # Barcelona
        
        # Asia
        "RJTT": (35.7720, 140.3928),  # Tokyo Narita
        "RJAA": (35.7647, 140.3863),  # Tokyo Haneda
        "RKSI": (37.4602, 126.4407),  # Seoul Incheon
        "RKSG": (37.5583, 126.7906),  # Seoul Gimpo
        "ZSPD": (31.1434, 121.8052),  # Shanghai Pudong
        "ZBAA": (40.0799, 116.6031),  # Beijing Capital
        "VHHH": (22.3080, 113.9185),  # Hong Kong
        "WSSS": (1.3644, 103.9915),   # Singapore
        "VTBS": (13.6900, 100.7501),  # Bangkok Suvarnabhumi
        "VTBD": (13.9126, 100.6068),  # Bangkok Don Mueang
        
        # Middle East
        "OMDB": (25.2532, 55.3657),   # Dubai
        "OTHH": (25.2731, 51.6081),   # Doha
        "OMAA": (24.4330, 54.6511),   # Abu Dhabi
        "LTBA": (41.2753, 28.7519),   # Istanbul
        
        # Latin America
        "MMMX": (19.4363, -99.0721),  # Mexico City
        "SCEL": (33.3928, -70.7858),  # Santiago
        "SKBO": (4.7016, -74.1469),   # Bogota
        "MPTO": (9.0714, -79.3835),   # Panama City
        
        # Africa
        "HAAB": (8.9779, 38.7993),    # Addis Ababa
        "FAOR": (-26.1367, 28.2411),  # Johannesburg
        "HKJK": (-1.3192, 36.9278),   # Nairobi
        
        # Australia
        "YSSY": (-33.9399, 151.1753), # Sydney
        "YMML": (-37.6733, 144.8433), # Melbourne
        "YBBN": (-27.3842, 153.1175), # Brisbane
        "YPPH": (-31.9403, 115.9669), # Perth
    }
    
    def get_airport_coords(self, icao_code: str) -> Optional[Tuple[float, float]]:
        """Get coordinates for an airport by ICAO code."""
        return self.AIRPORTS.get(icao_code.upper())
    
    def get_yyz_routes(self) -> List[Tuple[str, str]]:
        """Get common routes from/to Toronto Pearson."""
        return [
            ("CYYZ", "KJFK"),   # Toronto - New York
            ("CYYZ", "KLAX"),   # Toronto - Los Angeles
            ("CYYZ", "KORD"),   # Toronto - Chicago
            ("CYYZ", "KMIA"),   # Toronto - Miami
            ("CYYZ", "KDFW"),   # Toronto - Dallas
            ("CYYZ", "KATL"),   # Toronto - Atlanta
            ("CYYZ", "KSEA"),   # Toronto - Seattle
            ("CYYZ", "KIAH"),   # Toronto - Houston
            ("CYYZ", "KBOS"),   # Toronto - Boston
            ("CYYZ", "KPHX"),   # Toronto - Phoenix
            ("CYYZ", "KLAS"),   # Toronto - Las Vegas
            ("CYYZ", "KDEN"),   # Toronto - Denver
            ("CYYZ", "KDTW"),   # Toronto - Detroit
            ("CYYZ", "KPHL"),   # Toronto - Philadelphia
            ("CYYZ", "KMSP"),   # Toronto - Minneapolis
            ("CYYZ", "KCLT"),   # Toronto - Charlotte
            ("CYYZ", "KEWR"),   # Toronto - Newark
            ("CYYZ", "KSLC"),   # Toronto - Salt Lake City
            ("CYYZ", "KPDX"),   # Toronto - Portland
            ("CYYZ", "CYVR"),   # Toronto - Vancouver
            ("CYYZ", "CYUL"),   # Toronto - Montreal
            ("CYYZ", "CYYC"),   # Toronto - Calgary
            ("CYYZ", "CYEG"),   # Toronto - Edmonton
            ("CYYZ", "CYOW"),   # Toronto - Ottawa
            ("CYYZ", "CYWG"),   # Toronto - Winnipeg
            ("CYYZ", "CYHZ"),   # Toronto - Halifax
            ("CYYZ", "CYQB"),   # Toronto - Quebec City
            ("CYYZ", "EGLL"),   # Toronto - London Heathrow
            ("CYYZ", "EGKK"),   # Toronto - London Gatwick
            ("CYYZ", "EDDF"),   # Toronto - Frankfurt
            ("CYYZ", "EDDM"),   # Toronto - Munich
            ("CYYZ", "LFPG"),   # Toronto - Paris CDG
            ("CYYZ", "LFPO"),   # Toronto - Paris Orly
            ("CYYZ", "EHAM"),   # Toronto - Amsterdam
            ("CYYZ", "LEMD"),   # Toronto - Madrid
            ("CYYZ", "LEBL"),   # Toronto - Barcelona
            ("CYYZ", "LSGG"),   # Toronto - Geneva
            ("CYYZ", "LSZH"),   # Toronto - Zurich
            ("CYYZ", "LOWW"),   # Toronto - Vienna
            ("CYYZ", "ESSA"),   # Toronto - Stockholm
            ("CYYZ", "EFHK"),   # Toronto - Helsinki
            ("CYYZ", "EIDW"),   # Toronto - Dublin
            ("CYYZ", "LIRF"),   # Toronto - Rome
            ("CYYZ", "LIME"),   # Toronto - Milan
            ("CYYZ", "RJTT"),   # Toronto - Tokyo Narita
            ("CYYZ", "RJAA"),   # Toronto - Tokyo Haneda
            ("CYYZ", "RKSI"),   # Toronto - Seoul Incheon
            ("CYYZ", "ZSPD"),   # Toronto - Shanghai
            ("CYYZ", "ZBAA"),   # Toronto - Beijing
            ("CYYZ", "VHHH"),   # Toronto - Hong Kong
            ("CYYZ", "WSSS"),   # Toronto - Singapore
            ("CYYZ", "VTBS"),   # Toronto - Bangkok
            ("CYYZ", "OMDB"),   # Toronto - Dubai
            ("CYYZ", "OTHH"),   # Toronto - Doha
            ("CYYZ", "OMAA"),   # Toronto - Abu Dhabi
            ("CYYZ", "LTBA"),   # Toronto - Istanbul
            ("CYYZ", "MMMX"),   # Toronto - Mexico City
            ("CYYZ", "SCEL"),   # Toronto - Santiago
            ("CYYZ", "SKBO"),   # Toronto - Bogota
            ("CYYZ", "MPTO"),   # Toronto - Panama City
            ("CYYZ", "HAAB"),   # Toronto - Addis Ababa
            ("CYYZ", "FAOR"),   # Toronto - Johannesburg
            ("CYYZ", "HKJK"),   # Toronto - Nairobi
            ("CYYZ", "YSSY"),   # Toronto - Sydney
            ("CYYZ", "YMML"),   # Toronto - Melbourne
            ("CYYZ", "YBBN"),   # Toronto - Brisbane
            ("CYYZ", "YPPH"),   # Toronto - Perth
        ]
    
    def random_route(self, origin: str = "CYYZ") -> Tuple[str, str]:
        """Get a random route from the specified origin."""
        if origin == "CYYZ":
            routes = self.get_yyz_routes()
        else:
            # For other origins, create routes to major hubs
            routes = []
            for dest in ["KJFK", "KLAX", "KORD", "KMIA", "KDFW", "KATL", "KSEA", "EGLL", "EDDF", "LFPG", "EHAM", "RJTT", "RKSI", "ZSPD", "VHHH", "WSSS", "OMDB", "OTHH"]:
                if dest != origin:
                    routes.append((origin, dest))
        
        return random.choice(routes)
    
    def calculate_distance(self, lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """Calculate distance between two points in kilometers using Haversine formula."""
        R = 6371  # Earth's radius in kilometers
        
        dlat = math.radians(lat2 - lat1)
        dlon = math.radians(lon2 - lon1)
        
        a = (math.sin(dlat/2) * math.sin(dlat/2) + 
             math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * 
             math.sin(dlon/2) * math.sin(dlon/2))
        
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
        distance = R * c
        
        return distance
    
    def calculate_bearing(self, lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """Calculate bearing from point 1 to point 2 in degrees."""
        dlat = math.radians(lat2 - lat1)
        dlon = math.radians(lon2 - lon1)
        
        y = math.sin(dlon) * math.cos(math.radians(lat2))
        x = (math.cos(math.radians(lat1)) * math.sin(math.radians(lat2)) - 
             math.sin(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.cos(dlon))
        
        bearing = math.degrees(math.atan2(y, x))
        return (bearing + 360) % 360
    
    def spawn_position(self, status: Literal["PARKED", "TAXI", "TAKEOFF", "ENROUTE", "APPROACH", "LANDING"], 
                      origin: str, destination: str) -> Tuple[float, float, int, int, int]:
        """Generate position data based on flight status."""
        origin_coords = self.get_airport_coords(origin)
        dest_coords = self.get_airport_coords(destination)
        
        if not origin_coords or not dest_coords:
            # Fallback to YYZ coordinates
            origin_coords = (43.6777, -79.6248)
            dest_coords = (40.6413, -73.7781)
        
        if status == "PARKED":
            # Random position near origin airport
            lat = origin_coords[0] + random.uniform(-0.01, 0.01)
            lon = origin_coords[1] + random.uniform(-0.01, 0.01)
            altitude = random.randint(0, 100)
            heading = random.randint(0, 359)
            speed = random.randint(0, 5)
            
        elif status == "TAXI":
            # Moving on ground near origin
            lat = origin_coords[0] + random.uniform(-0.005, 0.005)
            lon = origin_coords[1] + random.uniform(-0.005, 0.005)
            altitude = random.randint(0, 50)
            heading = random.randint(0, 359)
            speed = random.randint(10, 30)
            
        elif status == "TAKEOFF":
            # Just departed, climbing
            lat = origin_coords[0] + random.uniform(-0.02, 0.02)
            lon = origin_coords[1] + random.uniform(-0.02, 0.02)
            altitude = random.randint(1000, 5000)
            heading = self.calculate_bearing(origin_coords[0], origin_coords[1], dest_coords[0], dest_coords[1])
            speed = random.randint(150, 250)
            
        elif status == "ENROUTE":
            # Mid-flight, random position along route
            progress = random.uniform(0.1, 0.9)  # 10% to 90% of the way
            lat = origin_coords[0] + (dest_coords[0] - origin_coords[0]) * progress + random.uniform(-0.5, 0.5)
            lon = origin_coords[1] + (dest_coords[1] - origin_coords[1]) * progress + random.uniform(-0.5, 0.5)
            altitude = random.randint(30000, 45000)
            heading = self.calculate_bearing(origin_coords[0], origin_coords[1], dest_coords[0], dest_coords[1]) + random.uniform(-10, 10)
            speed = random.randint(400, 550)
            
        elif status == "APPROACH":
            # Approaching destination
            lat = dest_coords[0] + random.uniform(-0.1, 0.1)
            lon = dest_coords[1] + random.uniform(-0.1, 0.1)
            altitude = random.randint(2000, 8000)
            heading = self.calculate_bearing(origin_coords[0], origin_coords[1], dest_coords[0], dest_coords[1]) + random.uniform(-20, 20)
            speed = random.randint(200, 350)
            
        elif status == "LANDING":
            # Very close to destination
            lat = dest_coords[0] + random.uniform(-0.01, 0.01)
            lon = dest_coords[1] + random.uniform(-0.01, 0.01)
            altitude = random.randint(0, 1000)
            heading = random.randint(0, 359)
            speed = random.randint(120, 180)
            
        else:
            # Default to enroute
            lat = origin_coords[0] + random.uniform(-0.5, 0.5)
            lon = origin_coords[1] + random.uniform(-0.5, 0.5)
            altitude = random.randint(30000, 45000)
            heading = random.randint(0, 359)
            speed = random.randint(400, 550)
        
        # Normalize heading
        heading = int(heading) % 360
        
        return lat, lon, altitude, heading, speed
    
    def get_flight_phase(self, status: str) -> str:
        """Map flight status to flight phase."""
        phase_mapping = {
            "PARKED": "PARKED",
            "TAXI": "TAXI_OUT",
            "TAKEOFF": "TAKEOFF",
            "ENROUTE": "CRUISE",
            "APPROACH": "APPROACH",
            "LANDING": "LANDING"
        }
        return phase_mapping.get(status, "CRUISE")
