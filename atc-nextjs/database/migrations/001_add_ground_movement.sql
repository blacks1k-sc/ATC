-- Migration 001: Ground movement fields
-- Adds taxiway routing, gate assignment, and missing columns to aircraft_instances.

ALTER TABLE aircraft_instances
    ADD COLUMN IF NOT EXISTS waypoint_sequence  JSONB,
    ADD COLUMN IF NOT EXISTS current_zone       VARCHAR(50),
    ADD COLUMN IF NOT EXISTS gate_assigned      VARCHAR(10),
    ADD COLUMN IF NOT EXISTS landing_runway     VARCHAR(10),
    ADD COLUMN IF NOT EXISTS taxiway_route      JSONB;

-- Index for fast lookup of ground-controller aircraft
CREATE INDEX IF NOT EXISTS idx_aircraft_instances_controller
    ON aircraft_instances(controller);

CREATE INDEX IF NOT EXISTS idx_aircraft_instances_gate
    ON aircraft_instances(gate_assigned);
