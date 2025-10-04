-- Enhanced ATC system database schema with full persistence and event logging

-- Aircraft types table (reference data from pipeline)
CREATE TABLE IF NOT EXISTS aircraft_types (
    id SERIAL PRIMARY KEY,
    icao_type VARCHAR(10) UNIQUE NOT NULL,
    wake VARCHAR(1) NOT NULL,
    engines JSONB NOT NULL,
    dimensions JSONB,
    mtow_kg FLOAT NOT NULL,
    cruise_speed_kts FLOAT NOT NULL,
    max_speed_kts FLOAT NOT NULL,
    range_nm FLOAT NOT NULL,
    ceiling_ft FLOAT NOT NULL,
    climb_rate_fpm FLOAT NOT NULL,
    takeoff_ground_run_ft FLOAT NOT NULL,
    landing_ground_roll_ft FLOAT NOT NULL,
    engine_thrust_lbf FLOAT NOT NULL,
    notes JSONB,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Airlines table (reference data from pipeline)
CREATE TABLE IF NOT EXISTS airlines (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    icao VARCHAR(3) UNIQUE NOT NULL,
    iata VARCHAR(2) UNIQUE,
    country VARCHAR(2),
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Aircraft instances table (generated aircraft with unique identifiers)
CREATE TABLE IF NOT EXISTS aircraft_instances (
    id SERIAL PRIMARY KEY,
    icao24 VARCHAR(6) UNIQUE NOT NULL,
    registration VARCHAR(10) UNIQUE NOT NULL,
    callsign VARCHAR(10) UNIQUE NOT NULL,
    aircraft_type_id INTEGER REFERENCES aircraft_types(id) ON DELETE RESTRICT,
    airline_id INTEGER REFERENCES airlines(id) ON DELETE RESTRICT,
    position JSONB NOT NULL,
    status VARCHAR(20) DEFAULT 'active',
    squawk_code VARCHAR(4),
    flight_plan JSONB,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Events table (time-ordered log with message, level, type, details, and optional aircraft link)
CREATE TABLE IF NOT EXISTS events (
    id SERIAL PRIMARY KEY,
    timestamp TIMESTAMP DEFAULT NOW(),
    level VARCHAR(10) NOT NULL CHECK (level IN ('DEBUG', 'INFO', 'WARN', 'ERROR', 'FATAL')),
    type VARCHAR(50) NOT NULL,
    message TEXT NOT NULL,
    details JSONB,
    aircraft_id INTEGER REFERENCES aircraft_instances(id) ON DELETE SET NULL,
    sector VARCHAR(20),
    frequency VARCHAR(10),
    direction VARCHAR(10) CHECK (direction IN ('TX', 'RX', 'CPDLC', 'XFER', 'SYS')),
    created_at TIMESTAMP DEFAULT NOW()
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_aircraft_types_icao_type ON aircraft_types(icao_type);
CREATE INDEX IF NOT EXISTS idx_airlines_icao ON airlines(icao);
CREATE INDEX IF NOT EXISTS idx_airlines_iata ON airlines(iata);

CREATE INDEX IF NOT EXISTS idx_aircraft_instances_icao24 ON aircraft_instances(icao24);
CREATE INDEX IF NOT EXISTS idx_aircraft_instances_registration ON aircraft_instances(registration);
CREATE INDEX IF NOT EXISTS idx_aircraft_instances_callsign ON aircraft_instances(callsign);
CREATE INDEX IF NOT EXISTS idx_aircraft_instances_type_id ON aircraft_instances(aircraft_type_id);
CREATE INDEX IF NOT EXISTS idx_aircraft_instances_airline_id ON aircraft_instances(airline_id);
CREATE INDEX IF NOT EXISTS idx_aircraft_instances_status ON aircraft_instances(status);
CREATE INDEX IF NOT EXISTS idx_aircraft_instances_position ON aircraft_instances USING GIN(position);
CREATE INDEX IF NOT EXISTS idx_aircraft_instances_created_at ON aircraft_instances(created_at);

CREATE INDEX IF NOT EXISTS idx_events_timestamp ON events(timestamp);
CREATE INDEX IF NOT EXISTS idx_events_level ON events(level);
CREATE INDEX IF NOT EXISTS idx_events_type ON events(type);
CREATE INDEX IF NOT EXISTS idx_events_aircraft_id ON events(aircraft_id);
CREATE INDEX IF NOT EXISTS idx_events_sector ON events(sector);
CREATE INDEX IF NOT EXISTS idx_events_created_at ON events(created_at);

-- Function to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Triggers to automatically update updated_at
CREATE TRIGGER update_aircraft_types_updated_at 
    BEFORE UPDATE ON aircraft_types 
    FOR EACH ROW 
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_airlines_updated_at 
    BEFORE UPDATE ON airlines 
    FOR EACH ROW 
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_aircraft_instances_updated_at 
    BEFORE UPDATE ON aircraft_instances 
    FOR EACH ROW 
    EXECUTE FUNCTION update_updated_at_column();

-- Function to generate unique ICAO24 addresses
CREATE OR REPLACE FUNCTION generate_icao24() RETURNS VARCHAR(6) AS $$
DECLARE
    chars VARCHAR(16) := '0123456789ABCDEF';
    result VARCHAR(6) := '';
    i INTEGER;
BEGIN
    FOR i IN 1..6 LOOP
        result := result || substr(chars, floor(random() * 16)::integer + 1, 1);
    END LOOP;
    RETURN result;
END;
$$ LANGUAGE plpgsql;

-- Function to generate unique registration numbers
CREATE OR REPLACE FUNCTION generate_registration(airline_icao VARCHAR(3)) RETURNS VARCHAR(10) AS $$
DECLARE
    numbers VARCHAR(4);
BEGIN
    numbers := lpad(floor(random() * 9000 + 1000)::text, 4, '0');
    RETURN airline_icao || numbers;
END;
$$ LANGUAGE plpgsql;

-- Function to generate unique callsigns
CREATE OR REPLACE FUNCTION generate_callsign(airline_icao VARCHAR(3)) RETURNS VARCHAR(10) AS $$
DECLARE
    numbers VARCHAR(4);
BEGIN
    numbers := lpad(floor(random() * 9000 + 1000)::text, 4, '0');
    RETURN airline_icao || numbers;
END;
$$ LANGUAGE plpgsql;

-- NEW: Waypoints table for navigation
CREATE TABLE IF NOT EXISTS waypoints (
    id SERIAL PRIMARY KEY,
    name VARCHAR(10) UNIQUE NOT NULL,
    lat DECIMAL(10, 7) NOT NULL,
    lon DECIMAL(11, 7) NOT NULL,
    description TEXT,
    type VARCHAR(20), -- 'ARRIVAL', 'DEPARTURE', 'ENROUTE', 'IAF', 'FAF'
    airport_icao VARCHAR(4),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- NEW: Procedures table (SIDs/STARs)
CREATE TABLE IF NOT EXISTS procedures (
    id SERIAL PRIMARY KEY,
    name VARCHAR(50) NOT NULL,
    type VARCHAR(10) NOT NULL, -- 'SID' or 'STAR'
    runway_id VARCHAR(10),
    airport_icao VARCHAR(4) NOT NULL,
    waypoint_sequence JSONB NOT NULL, -- Array of waypoint names in order
    altitude_restrictions JSONB, -- Altitude constraints at each waypoint
    speed_restrictions JSONB, -- Speed constraints at each waypoint
    description TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(name, airport_icao)
);

-- NEW: Gates table for departures
CREATE TABLE IF NOT EXISTS gates (
    id SERIAL PRIMARY KEY,
    gate_number VARCHAR(10) UNIQUE NOT NULL,
    terminal VARCHAR(5),
    lat DECIMAL(10, 7) NOT NULL,
    lon DECIMAL(11, 7) NOT NULL,
    airport_icao VARCHAR(4) NOT NULL,
    status VARCHAR(20) DEFAULT 'available', -- 'available', 'occupied'
    occupied_by_aircraft_id INTEGER REFERENCES aircraft_instances(id),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- NEW: Taxiways table for ground movement
CREATE TABLE IF NOT EXISTS taxiways (
    id SERIAL PRIMARY KEY,
    name VARCHAR(10) NOT NULL,
    from_point VARCHAR(50), -- Gate, runway, or intersection
    to_point VARCHAR(50),
    path JSONB, -- Array of lat/lon coordinates
    length_meters DECIMAL(10, 2),
    airport_icao VARCHAR(4) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- NEW: Aircraft history for archived flights
CREATE TABLE IF NOT EXISTS aircraft_history (
    id SERIAL PRIMARY KEY,
    original_aircraft_id INTEGER, -- Reference to original aircraft_instances.id
    icao24 VARCHAR(6) NOT NULL,
    registration VARCHAR(10) NOT NULL,
    callsign VARCHAR(10) NOT NULL,
    aircraft_type_id INTEGER,
    airline_id INTEGER,
    operation_type VARCHAR(10), -- 'ARRIVAL' or 'DEPARTURE'
    spawn_time TIMESTAMP,
    completion_time TIMESTAMP,
    spawn_location JSONB, -- Initial position
    exit_location JSONB, -- Final position
    assigned_procedure VARCHAR(50),
    assigned_runway VARCHAR(10),
    assigned_gate VARCHAR(10),
    total_flight_time_seconds INTEGER,
    total_events_logged INTEGER,
    archived_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- NEW: Runway occupancy tracking
CREATE TABLE IF NOT EXISTS runway_occupancy (
    id SERIAL PRIMARY KEY,
    runway_id VARCHAR(10) NOT NULL,
    aircraft_id INTEGER REFERENCES aircraft_instances(id),
    occupancy_type VARCHAR(20), -- 'landing', 'takeoff', 'crossing'
    occupied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    cleared_at TIMESTAMP,
    is_occupied BOOLEAN DEFAULT TRUE
);

-- NEW: Add comprehensive fields to aircraft_instances
ALTER TABLE aircraft_instances ADD COLUMN IF NOT EXISTS
    assigned_procedure_id INTEGER REFERENCES procedures(id),
    current_waypoint_index INTEGER DEFAULT 0,
    next_waypoint_name VARCHAR(10),
    operation_type VARCHAR(10) DEFAULT 'ARRIVAL', -- 'ARRIVAL' or 'DEPARTURE'
    spawn_gate VARCHAR(10), -- For departures: which gate they start at
    assigned_taxiway_route JSONB, -- Planned taxi route
    go_around_count INTEGER DEFAULT 0, -- Track go-arounds
    cleared_altitude INTEGER, -- ATC cleared altitude
    cleared_speed INTEGER, -- ATC cleared speed
    cleared_heading INTEGER; -- ATC cleared heading

-- Index for performance
CREATE INDEX IF NOT EXISTS idx_aircraft_operation_type ON aircraft_instances(operation_type);
CREATE INDEX IF NOT EXISTS idx_gates_status ON gates(status);
CREATE INDEX IF NOT EXISTS idx_runway_occupancy ON runway_occupancy(runway_id, is_occupied);
CREATE INDEX IF NOT EXISTS idx_aircraft_history_operation ON aircraft_history(operation_type);
