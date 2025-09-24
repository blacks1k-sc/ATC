# src/utils/estimators.py
from __future__ import annotations

import math

class AircraftParameterEstimator:
    """
    Derives missing aircraft parameters from available ICAO data
    """
    
    def __init__(self):
        # Constants and lookup tables
        self.wake_engine_mapping = {
            'L': {'JET': 1, 'TURBOPROP': 1, 'PISTON': 1},
            'M': {'JET': 2, 'TURBOPROP': 2, 'PISTON': 2}, 
            'H': {'JET': 2, 'TURBOPROP': 2, 'PISTON': 2},
            'J': {'JET': 4, 'TURBOPROP': 4, 'PISTON': 4}
        }
        
        self.cruise_factors = {
            'JET': 0.78,
            'TURBOPROP': 0.72,
            'PISTON': 0.68
        }
        
        self.thrust_to_weight_ratios = {
            'L': {'JET': 0.30, 'TURBOPROP': 0.20, 'PISTON': 0.15},
            'M': {'JET': 0.32, 'TURBOPROP': 0.22, 'PISTON': 0.18},
            'H': {'JET': 0.28, 'TURBOPROP': 0.25, 'PISTON': 0.20},
            'J': {'JET': 0.26, 'TURBOPROP': 0.28, 'PISTON': 0.22}
        }

    def estimate_engine_count(self, wake_category, engine_type, mtow_kg):
        """
        Formula 1: Engine Count Estimation
        Primary: Wake category + engine type lookup
        Secondary: MTOW thresholds for validation
        """
        # Primary method: Wake category mapping
        base_count = self.wake_engine_mapping.get(wake_category, {}).get(engine_type, 2)
        
        # MTOW-based validation and adjustment
        if engine_type == 'JET':
            if mtow_kg < 5000:  # Light jets
                engines = 1 if wake_category == 'L' else 2
            elif mtow_kg < 45000:  # Medium jets
                engines = 2
            elif mtow_kg < 180000:  # Heavy jets
                engines = min(base_count, 4)
            else:  # Super heavy
                engines = 4
        elif engine_type == 'TURBOPROP':
            if mtow_kg < 2500:
                engines = 1
            elif mtow_kg < 15000:
                engines = 2
            else:
                engines = min(base_count, 4)
        else:  # PISTON
            if mtow_kg < 2000:
                engines = 1
            else:
                engines = 2
                
        return engines

    def estimate_cruise_speed(self, max_speed_kts, engine_type, range_nm=None, ceiling_ft=None):
        """
        Formula 2: Cruise Speed Estimation
        Primary: Percentage of max speed based on engine type
        Secondary: Range-based validation
        """
        # Primary method: Max speed factor
        cruise_factor = self.cruise_factors.get(engine_type, 0.75)
        primary_estimate = max_speed_kts * cruise_factor
        
        # Secondary validation using range (if available)
        if range_nm and range_nm > 0:
            # Typical flight endurance: 3-8 hours depending on aircraft type
            if engine_type == 'JET':
                typical_endurance = 6.0  # hours
            elif engine_type == 'TURBOPROP':
                typical_endurance = 4.5  # hours
            else:
                typical_endurance = 4.0  # hours
                
            range_based_cruise = (range_nm / typical_endurance) * 1.1  # Account for routing
            
            # Use average if estimates are within 20% of each other
            if primary_estimate > 0 and abs(primary_estimate - range_based_cruise) / primary_estimate < 0.2:
                return (primary_estimate + range_based_cruise) / 2
        
        return round(primary_estimate)

    def estimate_engine_thrust(self, mtow_kg, wake_category, engine_type, engines_count, 
                              climb_rate_fpm=None, max_speed_kts=None):
        """
        Formula 3: Engine Thrust Estimation
        Based on thrust-to-weight ratio and performance characteristics
        """
        # Get base thrust-to-weight ratio
        twr = self.thrust_to_weight_ratios.get(wake_category, {}).get(engine_type, 0.25)
        
        # Adjust based on climb performance (if available)
        if climb_rate_fpm:
            if climb_rate_fpm > 2500:  # High performance
                twr *= 1.15
            elif climb_rate_fpm < 1200:  # Lower performance
                twr *= 0.90
        
        # Calculate total thrust in lbf (mtow in kg converted to lbs)
        mtow_lbs = mtow_kg * 2.20462
        total_thrust_lbf = mtow_lbs * twr
        
        # Per engine thrust
        per_engine_thrust = total_thrust_lbf / engines_count if engines_count > 0 else total_thrust_lbf
        
        return round(per_engine_thrust)

    def estimate_takeoff_ground_run(self, mtow_kg, engine_type, wake_category, 
                                   engine_thrust_lbf=None, wingspan_ft=None, climb_rate_fpm=None):
        """
        Formula 4: Takeoff Ground Run Estimation
        Based on weight, power loading, and performance characteristics
        """
        # Base distance per 1000 kg MTOW
        base_factors = {
            'JET': {'L': 1200, 'M': 1400, 'H': 1600, 'J': 1800},
            'TURBOPROP': {'L': 600, 'M': 800, 'H': 1000, 'J': 1200},
            'PISTON': {'L': 400, 'M': 600, 'H': 800, 'J': 1000}
        }
        
        base_factor = base_factors.get(engine_type, {}).get(wake_category, 1000)
        
        # Primary calculation
        base_distance = (mtow_kg / 1000) * base_factor
        
        # Adjust for climb performance
        if climb_rate_fpm:
            if climb_rate_fpm > 2000:
                base_distance *= 0.85  # Better climb = shorter takeoff
            elif climb_rate_fpm < 1000:
                base_distance *= 1.25  # Poor climb = longer takeoff
        
        # Adjust for wing loading (if wingspan available)
        if wingspan_ft and wingspan_ft > 0:
            wing_area_approx = wingspan_ft * (wingspan_ft * 0.7)  # Approximate aspect ratio
            wing_loading = (mtow_kg * 2.20462) / wing_area_approx  # lbs/sq ft
            
            if wing_loading > 50:  # High wing loading
                base_distance *= 1.1
            elif wing_loading < 25:  # Low wing loading
                base_distance *= 0.9
        
        return round(base_distance)

    def estimate_landing_ground_roll(self, takeoff_ground_run_ft, engine_type, wake_category, 
                                   mtow_kg=None, max_speed_kts=None):
        """
        Formula 5: Landing Ground Roll Estimation
        Typically 60-80% of takeoff distance with adjustments
        """
        # Base landing factors as percentage of takeoff
        landing_factors = {
            'JET': {'L': 0.70, 'M': 0.75, 'H': 0.80, 'J': 0.85},
            'TURBOPROP': {'L': 0.60, 'M': 0.65, 'H': 0.70, 'J': 0.75},
            'PISTON': {'L': 0.65, 'M': 0.70, 'H': 0.75, 'J': 0.80}
        }
        
        factor = landing_factors.get(engine_type, {}).get(wake_category, 0.75)
        base_landing = takeoff_ground_run_ft * factor
        
        # Adjust for approach speed (correlated with max speed)
        if max_speed_kts:
            if max_speed_kts > 400:  # High speed aircraft
                base_landing *= 1.1
            elif max_speed_kts < 200:  # Slower aircraft
                base_landing *= 0.9
        
        return round(base_landing)

    def estimate_all_parameters(self, icao_type, wake_category, engine_type, 
                               dimensions, mtow_kg, max_speed_kts, range_nm, 
                               ceiling_ft, climb_rate_fpm):
        """
        Complete parameter estimation pipeline
        """
        results = {}
        
        # Extract dimensions
        wingspan_ft = dimensions.get('wingspan_ft', 0) if dimensions else 0
        length_ft = dimensions.get('length_ft', 0) if dimensions else 0
        height_ft = dimensions.get('height_ft', 0) if dimensions else 0
        
        # 1. Engine Count
        engines_count = self.estimate_engine_count(wake_category, engine_type, mtow_kg)
        results['engines_count'] = engines_count
        
        # 2. Cruise Speed
        cruise_speed = self.estimate_cruise_speed(max_speed_kts, engine_type, range_nm, ceiling_ft)
        results['cruise_speed_kts'] = cruise_speed
        
        # 3. Engine Thrust
        engine_thrust = self.estimate_engine_thrust(mtow_kg, wake_category, engine_type, 
                                                   engines_count, climb_rate_fpm, max_speed_kts)
        results['engine_thrust_lbf'] = engine_thrust
        
        # 4. Takeoff Ground Run
        takeoff_run = self.estimate_takeoff_ground_run(mtow_kg, engine_type, wake_category,
                                                      engine_thrust, wingspan_ft, climb_rate_fpm)
        results['takeoff_ground_run_ft'] = takeoff_run
        
        # 5. Landing Ground Roll
        landing_roll = self.estimate_landing_ground_roll(takeoff_run, engine_type, wake_category,
                                                        mtow_kg, max_speed_kts)
        results['landing_ground_roll_ft'] = landing_roll
        
        return results


# Usage Example
def example_usage():
    estimator = AircraftParameterEstimator()
    
    # Example aircraft data
    sample_aircraft = {
        'icao_type': 'B738',
        'wake_category': 'M',
        'engine_type': 'JET',
        'dimensions': {
            'length_ft': 129.5,
            'wingspan_ft': 117.5,
            'height_ft': 41.2
        },
        'mtow_kg': 79015,
        'max_speed_kts': 544,
        'range_nm': 3383,
        'ceiling_ft': 41000,
        'climb_rate_fpm': 2500
    }
    
    # Estimate all missing parameters
    estimates = estimator.estimate_all_parameters(**sample_aircraft)
    
    print("Parameter Estimates:")
    print(f"Engine Count: {estimates['engines_count']}")
    print(f"Cruise Speed: {estimates['cruise_speed_kts']} kts")
    print(f"Engine Thrust: {estimates['engine_thrust_lbf']} lbf")
    print(f"Takeoff Ground Run: {estimates['takeoff_ground_run_ft']} ft")
    print(f"Landing Ground Roll: {estimates['landing_ground_roll_ft']} ft")

if __name__ == "__main__":
    example_usage()

__all__ = ["AircraftParameterEstimator"]
